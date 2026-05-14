---
name: rate-limit-fallback
description: Use when implementing or debugging the LLM provider fallback chain — distinguishing per-minute vs per-day rate limits, routing between Groq/Cerebras/Ollama, or handling invalid JSON responses from LLMs. Triggers on: "rate limit", "429 hatası", "model zinciri", "fallback chain", "Groq limit", "Cerebras", "günlük kota", "dakikalık limit", "AllModelsExhausted", "call_with_fallback", "provider değiştir".
---

# Rate-Limit & Fallback Skill

## Use this skill when
- Implementing `call_with_fallback()` or `MODEL_CHAINS`
- Adding a new task type to the model chain
- Debugging a 429 error or unexpected provider failure
- Adding a new provider to the fallback sequence

## Do not use this skill when
- Platform-level rate limiting for browser automation (use `session-lifecycle`)

## Model Chain Configuration

```python
MODEL_CHAINS = {
    "relevance_scoring": [
        {"provider": "groq",     "model": "llama-3-70b-8192"},
        {"provider": "groq",     "model": "mixtral-8x7b-32768"},
        {"provider": "groq",     "model": "gemma2-9b-it"},
        {"provider": "cerebras", "model": "llama3.1-70b"},
        {"provider": "cerebras", "model": "llama3.1-8b"},
        {"provider": "ollama",   "model": "llama3:8b"},     # local last resort
    ],
    "cv_tailoring": [
        {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
        {"provider": "openai",    "model": "gpt-4o-mini"},
        {"provider": "groq",      "model": "llama-3-70b-8192"},
        {"provider": "ollama",    "model": "llama3:8b"},
    ],
    "rejection_categorize": [
        {"provider": "groq",     "model": "llama-3-70b-8192"},
        {"provider": "cerebras", "model": "llama3.1-8b"},
        {"provider": "ollama",   "model": "llama3:8b"},
    ],
    "interview_prep": [
        {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
        {"provider": "openai",    "model": "gpt-4o"},
        {"provider": "groq",      "model": "llama-3-70b-8192"},
    ],
    "dom_vision_fallback": [
        {"provider": "openai",  "model": "gpt-4o"},
        {"provider": "google",  "model": "gemini-1.5-pro"},
    ],
}
```

## Error Parsing

```python
def parse_rate_limit_error(error_response: dict) -> dict:
    headers  = error_response.get("headers", {})
    body     = error_response.get("body", {})
    retry_after = headers.get("retry-after") or headers.get("x-ratelimit-reset-requests")
    error_msg   = str(body.get("error", {}).get("message", "")).lower()
    is_daily    = any(kw in error_msg for kw in ["daily", "per day", "quota", "24-hour"])
    return {
        "limit_type": "per_day" if is_daily else "per_minute",
        "retry_after_seconds": int(retry_after) if retry_after else None,
    }
```

## Main Dispatcher

```python
async def call_with_fallback(task: str, payload: dict) -> dict:
    chain = MODEL_CHAINS[task]
    
    for i, model_cfg in enumerate(chain):
        try:
            response = await call_model(model_cfg, payload)
            return parse_json_response(response)
        
        except RateLimitError as e:
            parsed = parse_rate_limit_error(e.response)
            
            if parsed["limit_type"] == "per_minute":
                wait = (parsed["retry_after_seconds"] or 60) + 1
                logger.info(f"Minute limit on {model_cfg['model']}. Waiting {wait}s...")
                await asyncio.sleep(wait)
                # Retry same model once
                try:
                    return parse_json_response(await call_model(model_cfg, payload))
                except RateLimitError:
                    continue  # Move to next in chain
            
            elif parsed["limit_type"] == "per_day":
                logger.warning(f"Daily limit: {model_cfg['provider']}/{model_cfg['model']}. Next...")
                continue
        
        except InvalidJSONError:
            if i < len(chain) - 1:
                logger.warning(f"Bad JSON from {model_cfg['model']}. Trying next...")
                continue
    
    # All models exhausted
    await telegram_notify("🔴 Tüm modeller başarısız. Manuel kontrol gerekiyor.")
    raise AllModelsExhaustedError(task=task)
```

## Decision Flow
```
429 received
  ├── per_minute → wait retry_after+1s → retry same model → if fails again → next in chain
  └── per_day   → immediately next in chain
                   Groq (multiple) → Cerebras → Ollama (local)
                   All exhausted → Telegram alert + freeze task
```

## Safety
- Ollama (local) is always the final fallback — ensure it's running (`ollama serve`)
- Never exceed 3 retries on the same model in a single task execution
- Log every fallback event to `interaction_logs` with `action_type='model_fallback'`
