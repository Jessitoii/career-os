import pytest
from unittest.mock import AsyncMock, patch
from httpx import RequestError
from app.intelligence.llm_client import call_with_fallback, RateLimitError, AllModelsExhaustedError
from app.intelligence.scoring import get_embedding, score_job_relevance
from app.intelligence.prompts import RelevanceScoreOutput, SCORING_SYSTEM_PROMPT

@pytest.mark.asyncio
async def test_call_with_fallback_success(mocker):
    """
    Test that call_with_fallback returns a valid schema when a provider succeeds.
    """
    mock_call = mocker.patch("app.intelligence.llm_client.call_model_provider", new_callable=AsyncMock)
    mock_call.return_value = '{"score": 90, "reasoning": ["Great fit"], "critical_flags": [], "decision": "auto_apply"}'
    
    result = await call_with_fallback(
        task="relevance_scoring",
        system=SCORING_SYSTEM_PROMPT,
        user="test",
        schema_model=RelevanceScoreOutput
    )
    
    assert isinstance(result, RelevanceScoreOutput)
    assert result.score == 90
    assert result.decision == "auto_apply"
    assert mock_call.call_count == 1

@pytest.mark.asyncio
async def test_call_with_fallback_exhaustion(mocker):
    """
    Test that call_with_fallback raises AllModelsExhaustedError if all models fail.
    """
    mock_call = mocker.patch("app.intelligence.llm_client.call_model_provider", new_callable=AsyncMock)
    mock_call.side_effect = RateLimitError("per_day", 0) # Trigger immediate fallback to next model
    
    with pytest.raises(AllModelsExhaustedError):
        await call_with_fallback(
            task="relevance_scoring",
            system="test",
            user="test",
            schema_model=RelevanceScoreOutput
        )

@pytest.mark.asyncio
async def test_get_embedding_ollama_mocked(mocker):
    """
    Test get_embedding with a mocked httpx response so it runs on PCs without Ollama.
    """
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
    mock_response.raise_for_status.return_value = None
    
    mock_post = mocker.patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    mock_post.return_value = mock_response
    
    emb = await get_embedding("test text")
    assert len(emb) == 3
    assert emb[0] == 0.1

@pytest.mark.asyncio
async def test_score_job_relevance_embedding_failure_fallback(mocker):
    """
    Test that score_job_relevance still calls the LLM even if Ollama connection fails.
    """
    mocker.patch("app.intelligence.scoring.get_embedding", side_effect=Exception("Ollama offline"))
    
    mock_llm = mocker.patch("app.intelligence.scoring.call_with_fallback", new_callable=AsyncMock)
    mock_llm.return_value = RelevanceScoreOutput(
        score=80, reasoning=["Used fallback"], critical_flags=[], decision="ask_user"
    )
    
    result = await score_job_relevance("candidate", "job")
    assert result.score == 80
    assert result.decision == "ask_user"
    mock_llm.assert_called_once()
