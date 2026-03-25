"""
Life agent group tests.

Unit tests: concurrency guard (no LLM required).
Integration tests: routing, artifact generation, therapy disclaimer (require GEMINI_API_KEY).
"""
import shutil
import pytest
from pathlib import Path
from langchain_core.messages import HumanMessage
from orchestrator.graph import orchestrator_graph
from orchestrator.checkpoint import get_checkpoint_config
from models.task import Task
from config.settings import settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_life_artifacts():
    artifact_dir = Path(settings.data_dir) / "life" / "artifacts"
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    yield


@pytest.fixture
def running_life_task(reset_task_manager):
    t = Task(
        trigger="user_initiated", agent_group="life",
        sub_agent="health", title="Health 1", thread_id="l1"
    )
    reset_task_manager.register_task(t)
    return t


@pytest.fixture
def pending_life_task(reset_task_manager, running_life_task):
    t = Task(
        trigger="user_initiated", agent_group="life",
        sub_agent="health", title="Health 2", thread_id="l2"
    )
    reset_task_manager.register_task(t)
    return t


# ---------------------------------------------------------------------------
# Unit: concurrency guard (no LLM required)
# ---------------------------------------------------------------------------

def test_second_life_task_queued_as_pending(running_life_task, pending_life_task, reset_task_manager):
    assert reset_task_manager.get_task(running_life_task.id).status == "running"
    assert reset_task_manager.get_task(pending_life_task.id).status == "pending"


# ---------------------------------------------------------------------------
# Integration: routing, artifacts, and safety checks (require GEMINI_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_life_routes_to_health_agent(require_gemini_key, running_life_task, reset_task_manager):
    running_life_task.status = "completed"
    reset_task_manager.update_task(running_life_task)

    task_id = "integ_health_task"
    config = get_checkpoint_config("life", "integ_life_health")
    state = {
        "messages": [HumanMessage(content="Build me a marathon training health routine.")],
        "active_agent": "life",
        "task_id": task_id,
    }
    result = orchestrator_graph.invoke(state, config=config)
    messages = result.get("messages", [])

    agent_names = [getattr(m, "name", None) for m in messages]
    assert "health_agent" in agent_names, f"health_agent not found in {agent_names}"

    artifact_dir = Path(settings.data_dir) / "life" / "artifacts"
    artifacts = list(artifact_dir.glob(f"health_{task_id}*.md"))
    assert artifacts, "Health plan artifact was not written to disk"
    assert artifacts[0].stat().st_size > 50


@pytest.mark.integration
def test_therapy_disclaimer_always_present(require_gemini_key, running_life_task, reset_task_manager):
    """therapy_agent MUST prepend the safety disclaimer in its response."""
    running_life_task.status = "completed"
    reset_task_manager.update_task(running_life_task)

    config = get_checkpoint_config("life", "integ_life_therapy")
    state = {
        "messages": [HumanMessage(content="I'm feeling overwhelmed by work stress. Give me journaling tips.")],
        "active_agent": "life",
        "task_id": "integ_therapy_task",
    }
    result = orchestrator_graph.invoke(state, config=config)
    messages = result.get("messages", [])

    therapy_msgs = [m for m in messages if getattr(m, "name", None) == "therapy_agent"]
    assert therapy_msgs, "therapy_agent message not found in result"
    assert "I am not a professional therapist" in therapy_msgs[0].content, (
        "CRITICAL: therapy_agent did not include mandatory safety disclaimer"
    )


@pytest.mark.integration
def test_life_sets_termination_signal(require_gemini_key, running_life_task, reset_task_manager):
    running_life_task.status = "completed"
    reset_task_manager.update_task(running_life_task)

    config = get_checkpoint_config("life", "integ_life_term_signal")
    state = {
        "messages": [HumanMessage(content="Help me build a habit tracking plan.")],
        "active_agent": "life",
        "task_id": "integ_habits_task",
    }
    result = orchestrator_graph.invoke(state, config=config)
    assert result.get("termination_signal") is True
