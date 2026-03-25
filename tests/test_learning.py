"""
Learning agent group tests.

Unit tests: concurrency guard (no LLM required).
Integration tests: routing to study_plan, course_rec, progress agents (require GEMINI_API_KEY).
"""
import shutil
import time
import uuid
import pytest
from pathlib import Path
from langchain_core.messages import HumanMessage
from orchestrator.graph import orchestrator_graph
from orchestrator.checkpoint import get_checkpoint_config
from models.task import Task
from models.user_profile import UserProfile, UserGoals
from context.profile_manager import ProfileManager
from config.settings import settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_learning_artifacts():
    artifact_dir = Path(settings.data_dir) / "learning" / "artifacts"
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    yield


@pytest.fixture
def learning_profile(tmp_profile_path):
    """Seed a profile with learning goals so agents have context."""
    profile = UserProfile(
        goals=UserGoals(
            career=["Become a Senior UI Engineer"],
            life=["Read 12 books this year"],
            learning=["Learn advanced React patterns", "Master LangGraph"],
        )
    )
    ProfileManager.save(profile)
    return profile


@pytest.fixture
def running_learning_task(reset_task_manager):
    t = Task(
        trigger="user_initiated", agent_group="learning",
        sub_agent="study_plan", title="Study Plan 1", thread_id="lrn1"
    )
    reset_task_manager.register_task(t)
    return t


@pytest.fixture
def pending_learning_task(reset_task_manager, running_learning_task):
    t = Task(
        trigger="user_initiated", agent_group="learning",
        sub_agent="course_rec", title="Course Rec 1", thread_id="lrn2",
        status="pending",
    )
    reset_task_manager.register_task(t)
    return t


# ---------------------------------------------------------------------------
# Unit: concurrency guard (no LLM required)
# ---------------------------------------------------------------------------

def test_second_learning_task_queued_as_pending(running_learning_task, pending_learning_task, reset_task_manager):
    assert reset_task_manager.get_task(running_learning_task.id).status == "running"
    assert reset_task_manager.get_task(pending_learning_task.id).status == "pending"


def test_learning_concurrency_guard_via_graph(pending_learning_task):
    """Learning supervisor returns a pending message for a pending task."""
    config = get_checkpoint_config("learning", "lrn_concurrency_test")
    state = {
        "messages": [HumanMessage(content="Recommend me LangGraph courses")],
        "active_agent": "learning",
        "task_id": pending_learning_task.id,
        "budget_stats": {"iterations": 0, "tool_calls": 0, "start_time": time.time()},
    }
    result = orchestrator_graph.invoke(state, config=config)
    messages = result.get("messages", [])
    assert any("pending due to concurrency limits" in m.content for m in messages)


# ---------------------------------------------------------------------------
# Integration: routing and artifact generation (require GEMINI_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("prompt,expected_agent,artifact_prefix", [
    (
        "I need a 4-week study plan to learn LangGraph.",
        "study_plan_agent",
        "study_plan",
    ),
    (
        "Recommend online courses to learn React optimization.",
        "course_rec_agent",
        "course_recs",
    ),
    (
        "I finished chapter 1 of my LangGraph book. Track my progress.",
        "progress_agent",
        "progress_report",
    ),
])
def test_learning_routing_and_artifact(
    require_gemini_key, learning_profile, running_learning_task, reset_task_manager,
    prompt, expected_agent, artifact_prefix,
):
    running_learning_task.status = "completed"
    reset_task_manager.update_task(running_learning_task)

    task_id = str(uuid.uuid4())
    config = get_checkpoint_config("learning", str(uuid.uuid4()))
    state = {
        "messages": [HumanMessage(content=prompt)],
        "active_agent": "learning",
        "task_id": task_id,
        "budget_stats": {"iterations": 0, "tool_calls": 0, "start_time": time.time()},
    }
    result = orchestrator_graph.invoke(state, config=config)
    messages = result.get("messages", [])

    agent_names = [getattr(m, "name", None) for m in messages]
    assert expected_agent in agent_names, f"{expected_agent} not found; got {agent_names}"

    artifact_dir = Path(settings.data_dir) / "learning" / "artifacts"
    artifacts = list(artifact_dir.glob(f"{artifact_prefix}_{task_id}*.md"))
    assert artifacts, f"Artifact {artifact_prefix}_{task_id}*.md not found in {artifact_dir}"
    assert artifacts[0].stat().st_size > 50


@pytest.mark.integration
def test_learning_sets_termination_signal(require_gemini_key, running_learning_task, reset_task_manager):
    running_learning_task.status = "completed"
    reset_task_manager.update_task(running_learning_task)

    config = get_checkpoint_config("learning", "integ_lrn_term_signal")
    state = {
        "messages": [HumanMessage(content="Create a study plan to learn Python.")],
        "active_agent": "learning",
        "task_id": "integ_study_plan",
        "budget_stats": {"iterations": 0, "tool_calls": 0, "start_time": time.time()},
    }
    result = orchestrator_graph.invoke(state, config=config)
    assert result.get("termination_signal") is True
