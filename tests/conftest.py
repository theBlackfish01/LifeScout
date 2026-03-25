"""
Shared pytest fixtures for LifeScout test suite.
"""
import os
import sys
import time
import types
import pytest
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage

# ---------------------------------------------------------------------------
# pytest_configure — runs before any module collection.
# Sets dummy env vars so that module-level ChatGoogleGenerativeAI
# instantiation in agents doesn't fail validation when no real key is present.
# Integration tests replace this with require_gemini_key / require_tavily_key
# fixtures that skip the test if the key is still the dummy value.
# ---------------------------------------------------------------------------
_DUMMY_KEY = "test_dummy_key_for_import"


def pytest_configure(config):
    os.environ.setdefault("GEMINI_API_KEY", _DUMMY_KEY)
    os.environ.setdefault("TAVILY_API_KEY", _DUMMY_KEY)


# ---------------------------------------------------------------------------
# WeasyPrint mock — must happen before any import that touches weasyprint,
# because GTK DLLs are unavailable in CI/Windows without a display server.
# ---------------------------------------------------------------------------
def _mock_weasyprint() -> None:
    if "weasyprint" not in sys.modules:
        mock = types.ModuleType("weasyprint")
        mock.HTML = lambda *a, **kw: type("_HTML", (), {"write_pdf": lambda *a, **kw: None})()
        mock.CSS = lambda *a, **kw: None
        sys.modules["weasyprint"] = mock


_mock_weasyprint()


# ---------------------------------------------------------------------------
# AgentState fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def agent_state():
    """Minimal valid AgentState for unit tests."""
    return {
        "messages": [HumanMessage(content="test message")],
        "active_agent": "career",
        "task_id": "test_task_1",
        "budget_stats": {"iterations": 0, "tool_calls": 0, "start_time": time.time()},
        "next": "",
        "termination_signal": False,
    }


@pytest.fixture
def budget_blown_state():
    """AgentState with iterations already exceeding MAX_ITERATIONS (5)."""
    return {
        "messages": [HumanMessage(content="Help me with life")],
        "active_agent": "life",
        "task_id": "task_budget_1",
        "budget_stats": {"iterations": 6, "tool_calls": 0, "start_time": time.time()},
        "next": "",
        "termination_signal": False,
    }


@pytest.fixture
def mock_ai_message():
    """Factory for creating mock AIMessage responses."""
    def _make(content: str = "Mock agent response", name: str = "test_agent") -> AIMessage:
        return AIMessage(content=content, name=name)
    return _make


# ---------------------------------------------------------------------------
# Infrastructure fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_task_manager():
    """Reset the task_manager singleton before and after every test."""
    from context.task_manager import task_manager
    task_manager.tasks.clear()
    yield task_manager
    task_manager.tasks.clear()


@pytest.fixture
def tmp_profile_path(tmp_path, monkeypatch):
    """
    Redirect ProfileManager to a temp file so tests never touch data/.
    Returns the Path to the temp profile JSON.
    """
    import context.profile_manager as pm_module
    tmp_profile = tmp_path / "user_profile.json"
    monkeypatch.setattr(pm_module, "PROFILE_PATH", tmp_profile)
    return tmp_profile


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """
    Redirect settings.data_dir and all derived path constants to a temp directory.
    Ensures tests never write to the real data/ tree.
    """
    import sys
    import config.settings  # ensure submodule is in sys.modules
    import context.memory_distiller as md_module
    import context.artifact_loader as al_module
    import context.profile_manager as pm_module

    # config/__init__.py re-exports 'settings' (the instance), shadowing the submodule
    # in config.__dict__. Use sys.modules to reliably get the actual module object.
    cfg_module = sys.modules["config.settings"]

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Patch the settings object in place (shared singleton).
    # cfg_module.settings is the Settings() instance; setattr works on mutable Pydantic models.
    monkeypatch.setattr(cfg_module.settings, "data_dir", str(data_dir))
    monkeypatch.setattr(cfg_module.settings, "checkpoints_dir", str(data_dir / "checkpoints"))

    # Re-patch module-level constants that were already bound at import time
    monkeypatch.setattr(pm_module, "PROFILE_PATH", data_dir / "user_profile.json")
    monkeypatch.setattr(md_module.MemoryDistiller, "STORE_PATH", data_dir / "memory" / "context_store.json")

    return data_dir


# ---------------------------------------------------------------------------
# Skip marker for tests that need real API keys
# ---------------------------------------------------------------------------

@pytest.fixture
def require_gemini_key():
    from config.settings import settings
    if not settings.gemini_api_key or settings.gemini_api_key == _DUMMY_KEY:
        pytest.skip("GEMINI_API_KEY not set (real key required for integration tests)")


@pytest.fixture
def require_tavily_key():
    from config.settings import settings
    if not settings.tavily_api_key or settings.tavily_api_key == _DUMMY_KEY:
        pytest.skip("TAVILY_API_KEY not set (real key required for integration tests)")
