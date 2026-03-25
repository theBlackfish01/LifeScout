"""
Career agent group tests.

Unit tests: concurrency guard, budget guard (no LLM required).
Integration tests: routing to sub-agents, artifact generation (require GEMINI_API_KEY).
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
def clean_career_artifacts():
    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    yield


@pytest.fixture
def running_career_task(reset_task_manager):
    t = Task(
        trigger="user_initiated", agent_group="career",
        sub_agent="resume", title="Resume 1", thread_id="t1"
    )
    reset_task_manager.register_task(t)
    return t


@pytest.fixture
def pending_career_task(reset_task_manager, running_career_task):
    t = Task(
        trigger="user_initiated", agent_group="career",
        sub_agent="resume", title="Resume 2", thread_id="t2"
    )
    reset_task_manager.register_task(t)
    return t


# ---------------------------------------------------------------------------
# Unit: concurrency guard (no LLM required)
# ---------------------------------------------------------------------------

def test_second_career_task_queued_as_pending(running_career_task, pending_career_task, reset_task_manager):
    assert reset_task_manager.get_task(running_career_task.id).status == "running"
    assert reset_task_manager.get_task(pending_career_task.id).status == "pending"


def test_career_concurrency_guard_via_graph(pending_career_task):
    """Career supervisor returns a concurrency message for a pending task."""
    config = get_checkpoint_config("career", "career_concurrency_test")
    state = {
        "messages": [HumanMessage(content="Rewrite my resume")],
        "active_agent": "career",
        "task_id": pending_career_task.id,
    }
    result = orchestrator_graph.invoke(state, config=config)
    messages = result.get("messages", [])
    last_content = messages[-1].content if messages else ""
    assert "pending due to concurrency limits" in last_content


def test_career_budget_guard_terminates_graph():
    """Career supervisor short-circuits when budget_stats exceed limits."""
    config = get_checkpoint_config("career", "career_budget_test")
    state = {
        "messages": [HumanMessage(content="Help me")],
        "active_agent": "career",
        "budget_stats": {"iterations": 5, "tool_calls": 0, "start_time": 0.0},
    }
    result = orchestrator_graph.invoke(state, config=config)
    messages = result.get("messages", [])
    assert any("Budget Exceeded" in m.content for m in messages)
    assert result.get("termination_signal") is True


# ---------------------------------------------------------------------------
# Integration: routing and artifact generation (require GEMINI_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_career_routes_to_resume_agent(require_gemini_key, running_career_task, reset_task_manager):
    running_career_task.status = "completed"
    reset_task_manager.update_task(running_career_task)

    task_id = "integ_resume_task"
    config = get_checkpoint_config("career", "integ_career_resume")
    state = {
        "messages": [HumanMessage(content="Rewrite my resume for an Engineering Manager role.")],
        "active_agent": "career",
        "task_id": task_id,
    }
    result = orchestrator_graph.invoke(state, config=config)
    messages = result.get("messages", [])

    agent_names = [getattr(m, "name", None) for m in messages]
    assert "resume_agent" in agent_names, f"resume_agent not found in {agent_names}"

    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifacts = list(artifact_dir.glob(f"resume_{task_id}*.md"))
    assert artifacts, "Resume artifact file was not written to disk"
    assert artifacts[0].stat().st_size > 50


@pytest.mark.integration
def test_career_sets_termination_signal(require_gemini_key, running_career_task, reset_task_manager):
    running_career_task.status = "completed"
    reset_task_manager.update_task(running_career_task)

    config = get_checkpoint_config("career", "integ_career_term_signal")
    state = {
        "messages": [HumanMessage(content="Search for senior Python jobs in London.")],
        "active_agent": "career",
        "task_id": "integ_job_search",
    }
    result = orchestrator_graph.invoke(state, config=config)
    assert result.get("termination_signal") is True
