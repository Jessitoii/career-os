---
name: scoring-engine
description: Use when building or modifying the job relevance scoring pipeline — embedding-based local filtering, LLM-based deep scoring, JSON output validation, or the confidence threshold routing logic. Triggers on: "relevance score", "ilan puanlama", "embedding filter", "cosine similarity", "Groq scoring", "LLM analiz", "confidence threshold", "auto_apply karar", "match reasoning", "hard-skill analizi", "vektör benzerliği".
---

# Scoring Engine Skill

## Use this skill when
- Building or modifying the two-stage filtering pipeline
- Writing or updating the relevance scoring prompt contract
- Implementing cosine similarity threshold logic
- Adding new scoring signals (visa detection, seniority match, salary range)
- Debugging why good jobs are being filtered out or bad jobs are passing

## Do not use this skill when
- Writing duplicate detection logic (use `duplicate-prevention`)
- Modifying how scores affect state transitions (use `session-lifecycle`)

## Two-Stage Pipeline

```
All scraped jobs
      │
      ▼
[Stage 1: Local Embedding Filter]  ← Ollama nomic-embed-text / bge-small
   cosine_similarity(profile, jd) < threshold → DISCARD
      │
      ▼ (top 10-20% pass)
[Stage 2: Remote LLM Scoring]  ← Groq Llama-3-70b (via call_with_fallback)
   structured JSON output → score + flags + decision
      │
      ├── score >= 85 → AUTO_APPLY (EXECUTION)
      ├── 60 <= score < 85 → AWAITING_APPROVAL (Telegram)
      └── score < 60 → DISCARDED
```

## Instructions

### Stage 1: Embedding Filter
```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

EMBEDDING_THRESHOLD = 0.65  # Tune based on Precision/Recall KPIs

async def embedding_filter(profile_summary: str, job_description: str) -> float:
    # Use local Ollama endpoint for cost efficiency
    profile_vec = await get_embedding(profile_summary)   # vector(384)
    jd_vec = await get_embedding(job_description)
    score = cosine_similarity([profile_vec], [jd_vec])[0][0]
    return float(score)

async def get_embedding(text: str) -> list[float]:
    resp = await httpx.post("http://localhost:11434/api/embeddings",
                            json={"model": "nomic-embed-text", "prompt": text})
    return resp.json()["embedding"]
```

### Stage 2: LLM Scoring Prompt Contract
System prompt (from `Prompt_Sözleşme_Kütüphanesi.md`):
```
Sen profesyonel bir teknik işe alım uzmanısın. Görevin aday profili ile iş tanımını
karşılaştırmak ve SADECE JSON formatında analiz dönmek.

Puanlama (0-100): Teknik beceri eşleşmesi, deneyim yılı, lokasyon uyumu.
Flags: Vize sponsoru, Almanca zorunluluğu, "Senior" beklentisi gibi engelları işaretle.
Karar: 85+ → 'auto_apply' | 60-85 → 'ask_user' | <60 → 'reject'

Kesinlikle JSON dışında metin ekleme.
```

### Output Schema Validation
```python
from pydantic import BaseModel, Field, validator

class ScoringOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    reasoning: list[str] = Field(min_items=1, max_items=5)
    critical_flags: list[str] = Field(default=[])
    decision: str = Field(regex="^(auto_apply|ask_user|reject)$")

def parse_scoring_response(raw: str) -> ScoringOutput:
    try:
        data = json.loads(raw)
        return ScoringOutput(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise InvalidJSONError(f"Scoring output invalid: {e}")
```

### Saving to DB
After scoring, always persist:
- `job_listings.relevance_score`
- `job_listings.relevance_reasoning` (TEXT[])
- `job_listings.detected_stack` (TEXT[])
- `job_listings.embedding` (vector — for future semantic duplicate detection)
- `job_listings.status` → update to `'scored'`

## Tuning
- If interview rate is low: raise `EMBEDDING_THRESHOLD` and tighten LLM system prompt
- If too many good jobs are rejected: lower `EMBEDDING_THRESHOLD`, check profile summary quality
- Track `Matched / Applied / Interview` funnel metrics (from `Career_OS_Spesifikasyonu.md`)
