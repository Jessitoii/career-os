import httpx
import logging
import json
from pydantic import BaseModel
import numpy as np

from app.core.config import settings
from app.intelligence.llm_client import call_with_fallback
from app.intelligence.prompts import SCORING_SYSTEM_PROMPT, RelevanceScoreOutput

logger = logging.getLogger(__name__)

async def get_embedding(text: str) -> list[float]:
    """
    Get text embedding from local Ollama instance.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    payload = {
        "model": "nomic-embed-text",
        "prompt": text
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
        except httpx.RequestError as exc:
            logger.error(f"Failed to connect to Ollama: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Error getting embedding: {exc}")
            raise

def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    a = np.array(vec1)
    b = np.array(vec2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


async def score_job_relevance(user_profile_text: str, job_description: str) -> RelevanceScoreOutput:
    """
    2-Stage Filtering:
    1. Local Embedding check (fast/free). If too low, reject early.
    2. Remote LLM reasoning for deep analysis.
    """
    # 1. Local Filtering
    try:
        user_emb = await get_embedding(user_profile_text)
        job_emb = await get_embedding(job_description)
        sim = cosine_similarity(user_emb, job_emb)
        
        # If similarity is extremely low, we can reject it outright
        if sim < 0.40:
            return RelevanceScoreOutput(
                score=int(sim * 100),
                reasoning=["Rejected at embedding stage due to very low similarity."],
                critical_flags=["Low Semantic Match"],
                decision="reject"
            )
    except Exception as e:
        logger.warning(f"Embedding stage failed: {e}. Proceeding to LLM scoring fallback.")

    # 2. Remote LLM Scoring
    user_prompt = f"Candidate Profile:\n{user_profile_text}\n\nJob Description:\n{job_description}"
    
    result = await call_with_fallback(
        task="relevance_scoring",
        system=SCORING_SYSTEM_PROMPT,
        user=user_prompt,
        schema_model=RelevanceScoreOutput
    )
    
    return result
