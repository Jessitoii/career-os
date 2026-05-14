import asyncio
import json
import logging
from typing import Callable, Any
from groq import AsyncGroq
import httpx
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    def __init__(self, limit_type: str, retry_after: int):
        self.limit_type = limit_type
        self.retry_after = retry_after

class InvalidJSONError(Exception):
    pass

class AllModelsExhaustedError(Exception):
    pass


MODEL_CHAINS = {
    "relevance_scoring": [
        {"provider": "groq",     "model": "llama-3-70b-8192"},
        {"provider": "groq",     "model": "mixtral-8x7b-32768"},
        {"provider": "cerebras", "model": "llama3.1-70b"},
        {"provider": "cerebras", "model": "llama3.1-8b"},
    ],
    "cv_tailoring": [
        {"provider": "groq",     "model": "llama-3-70b-8192"},
        {"provider": "cerebras", "model": "llama3.1-70b"},
    ],
    "dom_vision_fallback": [
        # Note: Vision requires gpt-4o or gemini normally, but falling back to groq text 
        # based on DOM text if vision isn't available, or wait for manual hitl
        {"provider": "groq", "model": "llama-3-70b-8192"} 
    ]
}

groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

async def call_groq(model: str, system: str, user: str) -> str:
    if not groq_client:
        raise Exception("Groq not configured")
    try:
        completion = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            model=model,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content
    except Exception as e:
        if "429" in str(e):
            # rudimentary parsing of groq rate limits
            if "per day" in str(e).lower() or "daily" in str(e).lower():
                raise RateLimitError("per_day", 0)
            else:
                raise RateLimitError("per_minute", 60)
        raise e

async def call_cerebras(model: str, system: str, user: str) -> str:
    if not settings.CEREBRAS_API_KEY:
        raise Exception("Cerebras not configured")
    
    headers = {
        "Authorization": f"Bearer {settings.CEREBRAS_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "response_format": {"type": "json_object"}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.cerebras.ai/v1/chat/completions", json=payload, headers=headers)
        if response.status_code == 429:
            err_text = response.text.lower()
            if "day" in err_text or "daily" in err_text:
                raise RateLimitError("per_day", 0)
            else:
                retry_after = int(response.headers.get("retry-after", 60))
                raise RateLimitError("per_minute", retry_after)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def call_model_provider(cfg: dict, system: str, user: str) -> str:
    provider = cfg["provider"]
    model = cfg["model"]
    
    if provider == "groq":
        return await call_groq(model, system, user)
    elif provider == "cerebras":
        return await call_cerebras(model, system, user)
    else:
        raise Exception(f"Unknown provider {provider}")

async def call_with_fallback(task: str, system: str, user: str, schema_model: type[BaseModel]) -> BaseModel:
    chain = MODEL_CHAINS.get(task, [])
    if not chain:
        raise ValueError(f"No model chain configured for task: {task}")
        
    for i, model_cfg in enumerate(chain):
        try:
            logger.info(f"Calling {model_cfg['provider']}/{model_cfg['model']} for task {task}")
            response_text = await call_model_provider(model_cfg, system, user)
            
            try:
                # Ensure it parses as JSON and matches schema
                data = json.loads(response_text)
                return schema_model(**data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Invalid JSON from {model_cfg['model']}: {e}")
                if i < len(chain) - 1:
                    continue # try next model
                raise InvalidJSONError(f"Failed to parse JSON: {e}")

        except RateLimitError as e:
            if e.limit_type == "per_minute":
                wait = e.retry_after + 1
                logger.info(f"Minute rate-limit. Waiting {wait}s...")
                await asyncio.sleep(wait)
                # Retry same model once. If we really wanted to, we could loop, but let's just proceed to next if it fails again.
                try:
                    response_text = await call_model_provider(model_cfg, system, user)
                    data = json.loads(response_text)
                    return schema_model(**data)
                except Exception:
                    continue
            elif e.limit_type == "per_day":
                logger.warning(f"[{model_cfg['provider']}] daily limit reached. Moving to next model...")
                continue
        except Exception as e:
            logger.error(f"Provider {model_cfg['provider']} failed: {e}")
            continue

    logger.error("All models exhausted")
    # In a real scenario, trigger Telegram HITL
    raise AllModelsExhaustedError(f"Task={task} exhausted all models.")
