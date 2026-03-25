"""
Unit tests for context managers: ProfileManager and TaskManager.
These tests do not require API keys.
"""
import json
import pytest
from models.user_profile import UserProfile
from models.task import Task
from context.profile_manager import ProfileManager
from context.task_manager import TaskManager


# ---------------------------------------------------------------------------
# ProfileManager
# ---------------------------------------------------------------------------

def test_profile_manager_returns_default_when_missing(tmp_profile_path):
    profile = ProfileManager.load()
    assert isinstance(profile, UserProfile)
    assert profile.name == ""
    assert profile.onboarding_complete is False


def test_profile_manager_save_and_load(tmp_profile_path):
    profile = ProfileManager.load()
    profile.name = "Test User"
    ProfileManager.save(profile)

    loaded = ProfileManager.load()
    assert loaded.name == "Test User"
    assert loaded.id == profile.id


def test_profile_manager_persists_onboarding_flag(tmp_profile_path):
    profile = ProfileManager.load()
    profile.onboarding_complete = True
    ProfileManager.save(profile)

    assert ProfileManager.load().onboarding_complete is True


# ---------------------------------------------------------------------------
# TaskManager — concurrency queue
# ---------------------------------------------------------------------------

@pytest.fixture
def tm(tmp_data_dir):
    """A fresh TaskManager instance backed by the tmp data dir."""
    return TaskManager()


def test_first_task_starts_as_running(tm):
    t = Task(
        trigger="user_initiated", agent_group="career",
        sub_agent="resume", title="Resume", thread_id="t1"
    )
    tm.register_task(t)
    assert tm.get_task(t.id).status == "running"


def test_second_task_queued_as_pending(tm):
    t1 = Task(trigger="user_initiated", agent_group="career", sub_agent="resume", title="R1", thread_id="t1")
    t2 = Task(trigger="user_initiated", agent_group="career", sub_agent="resume", title="R2", thread_id="t2")

    tm.register_task(t1)
    tm.register_task(t2)

    assert tm.get_task(t1.id).status == "running"
    assert tm.get_task(t2.id).status == "pending"


def test_pending_task_promoted_when_running_completes(tm):
    t1 = Task(trigger="user_initiated", agent_group="career", sub_agent="resume", title="R1", thread_id="t1")
    t2 = Task(trigger="user_initiated", agent_group="career", sub_agent="resume", title="R2", thread_id="t2")

    tm.register_task(t1)
    tm.register_task(t2)

    t1.status = "completed"
    tm.update_task(t1)

    assert tm.get_task(t2.id).status == "running"


def test_stale_running_tasks_cancelled_on_init(tm, tmp_data_dir):
    """A TaskManager restart cancels any tasks still marked 'running' on disk."""
    t = Task(trigger="user_initiated", agent_group="career", sub_agent="resume", title="Stale", thread_id="t1")
    tm.register_task(t)
    # t is now running — simulate a process restart with a new TaskManager instance
    TaskManager()

    log_path = tmp_data_dir / "career" / "logs" / f"{t.id}.json"
    assert log_path.exists()
    data = json.loads(log_path.read_text())
    assert data["status"] == "cancelled"


def test_tasks_isolated_by_agent_group(tm):
    """Concurrency limit is per agent group, not global."""
    career_t = Task(trigger="user_initiated", agent_group="career", sub_agent="resume", title="C", thread_id="c1")
    life_t = Task(trigger="user_initiated", agent_group="life", sub_agent="health", title="L", thread_id="l1")

    tm.register_task(career_t)
    tm.register_task(life_t)

    assert tm.get_task(career_t.id).status == "running"
    assert tm.get_task(life_t.id).status == "running"
