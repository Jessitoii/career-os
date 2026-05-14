import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.core.state_machine import transition_state, ApplicationStatus
from app.models.application import Application
from app.agents.apply_worker import apply_to_job

@pytest.fixture
def mock_db_session(mocker):
    session = mocker.Mock()
    mock_app = Application(id="test-123", status=ApplicationStatus.approved, retry_count=0)
    session.query().filter().first.return_value = mock_app
    return session

def test_transition_state_valid(mock_db_session):
    # Transitioning from approved to applying should succeed
    app = transition_state(mock_db_session, "test-123", ApplicationStatus.applying, actor="test")
    assert app.status == ApplicationStatus.applying

def test_transition_state_invalid_hard_reject(mock_db_session):
    # Transitioning from approved directly to interview should raise ValueError
    with pytest.raises(ValueError, match="Invalid state transition"):
        transition_state(mock_db_session, "test-123", ApplicationStatus.interview, actor="test")

@patch('app.agents.apply_worker.is_paused', return_value=True)
def test_apply_worker_respects_kill_switch(mock_is_paused, mocker):
    # If kill switch is active, worker should defer (call self.retry)
    mock_self = mocker.Mock()
    apply_to_job.retry = mocker.Mock()
    
    # We pass bind=True task signature explicitly
    apply_to_job(mock_self, "test-123")
    assert mock_is_paused.called
    assert apply_to_job.retry.called
