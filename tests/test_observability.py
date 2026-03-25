"""
Observability module tests.

Unit tests: CostTracker accumulation, CostCallbackHandler, tracing config.
No API keys or LLM calls required.
"""
import os
import time
import pytest
from unittest.mock import MagicMock
from langchain_core.outputs import LLMResult, Generation

from observability.cost_tracker import (
    CostTracker,
    CostCallbackHandler,
    SessionCost,
    AgentUsage,
)
from observability.tracing import configure_tracing


# ---------------------------------------------------------------------------
# CostTracker unit tests
# ---------------------------------------------------------------------------

def test_cost_tracker_records_llm_usage():
    tracker = CostTracker()
    tracker.record_llm("thread_1", "career_supervisor", {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
    })
    session = tracker.get_session("thread_1")
    assert session is not None
    assert session["agents"]["career_supervisor"]["prompt_tokens"] == 100
    assert session["agents"]["career_supervisor"]["completion_tokens"] == 50
    assert session["agents"]["career_supervisor"]["total_tokens"] == 150
    assert session["agents"]["career_supervisor"]["llm_calls"] == 1


def test_cost_tracker_accumulates_across_calls():
    tracker = CostTracker()
    tracker.record_llm("t1", "agent_a", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
    tracker.record_llm("t1", "agent_a", {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30})
    session = tracker.get_session("t1")
    assert session["agents"]["agent_a"]["prompt_tokens"] == 30
    assert session["agents"]["agent_a"]["llm_calls"] == 2


def test_cost_tracker_separate_agents():
    tracker = CostTracker()
    tracker.record_llm("t1", "supervisor", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
    tracker.record_llm("t1", "job_search", {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300})
    session = tracker.get_session("t1")
    assert "supervisor" in session["agents"]
    assert "job_search" in session["agents"]
    assert session["totals"]["total_tokens"] == 315
    assert session["totals"]["llm_calls"] == 2


def test_cost_tracker_records_tool_calls():
    tracker = CostTracker()
    tracker.record_tool("t1", "tavily_search")
    tracker.record_tool("t1", "tavily_search")
    tracker.record_tool("t1", "robust_web_scrape")
    session = tracker.get_session("t1")
    assert session["agents"]["tavily_search"]["tool_calls"] == 2
    assert session["agents"]["robust_web_scrape"]["tool_calls"] == 1
    assert session["totals"]["tool_calls"] == 3


def test_cost_tracker_separate_sessions():
    tracker = CostTracker()
    tracker.record_llm("thread_a", "agent", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
    tracker.record_llm("thread_b", "agent", {"prompt_tokens": 99, "completion_tokens": 1, "total_tokens": 100})
    all_sessions = tracker.get_all_sessions()
    assert len(all_sessions) == 2
    ids = {s["thread_id"] for s in all_sessions}
    assert ids == {"thread_a", "thread_b"}


def test_cost_tracker_get_missing_session():
    tracker = CostTracker()
    assert tracker.get_session("nonexistent") is None


def test_cost_tracker_clear():
    tracker = CostTracker()
    tracker.record_llm("t1", "a", {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
    tracker.clear()
    assert tracker.get_all_sessions() == []


# ---------------------------------------------------------------------------
# CostCallbackHandler tests
# ---------------------------------------------------------------------------

def _make_llm_result(prompt_tokens: int, completion_tokens: int) -> LLMResult:
    """Build an LLMResult with token usage in generation_info (Gemini-style)."""
    gen = Generation(
        text="response text",
        generation_info={
            "usage_metadata": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
        },
    )
    return LLMResult(generations=[[gen]])


def test_callback_handler_records_on_llm_end():
    tracker = CostTracker()
    handler = CostCallbackHandler(tracker, "cb_thread")
    handler._current_agent = "test_agent"

    result = _make_llm_result(50, 25)
    handler.on_llm_end(result)

    session = tracker.get_session("cb_thread")
    assert session["agents"]["test_agent"]["prompt_tokens"] == 50
    assert session["agents"]["test_agent"]["completion_tokens"] == 25
    assert session["agents"]["test_agent"]["total_tokens"] == 75


def test_callback_handler_tracks_chain_name():
    tracker = CostTracker()
    handler = CostCallbackHandler(tracker, "cb_thread")

    handler.on_chain_start({"name": "career_supervisor"}, {})
    assert handler._current_agent == "career_supervisor"

    handler.on_chain_start({}, {}, name="job_search_agent")
    assert handler._current_agent == "job_search_agent"


def test_callback_handler_records_tool_start():
    tracker = CostTracker()
    handler = CostCallbackHandler(tracker, "cb_thread")

    handler.on_tool_start({"name": "search_jobs"}, "query")

    session = tracker.get_session("cb_thread")
    assert session["agents"]["search_jobs"]["tool_calls"] == 1


def test_callback_handler_handles_missing_usage():
    """LLM result with no token metadata should not crash."""
    tracker = CostTracker()
    handler = CostCallbackHandler(tracker, "t1")
    handler._current_agent = "safe"

    gen = Generation(text="response", generation_info={})
    result = LLMResult(generations=[[gen]])
    handler.on_llm_end(result)

    session = tracker.get_session("t1")
    assert session["agents"]["safe"]["llm_calls"] == 1
    assert session["agents"]["safe"]["total_tokens"] == 0


def test_callback_handler_input_output_token_keys():
    """Gemini sometimes uses input_tokens/output_tokens instead of prompt_tokens/completion_tokens."""
    tracker = CostTracker()
    handler = CostCallbackHandler(tracker, "t1")
    handler._current_agent = "gemini_agent"

    gen = Generation(
        text="resp",
        generation_info={
            "usage_metadata": {
                "input_tokens": 80,
                "output_tokens": 40,
                "total_tokens": 120,
            }
        },
    )
    result = LLMResult(generations=[[gen]])
    handler.on_llm_end(result)

    session = tracker.get_session("t1")
    assert session["agents"]["gemini_agent"]["prompt_tokens"] == 80
    assert session["agents"]["gemini_agent"]["completion_tokens"] == 40


# ---------------------------------------------------------------------------
# Tracing configuration tests
# ---------------------------------------------------------------------------

def test_configure_tracing_disabled_without_key(monkeypatch):
    """Tracing should be skipped when LANGSMITH_API_KEY is empty."""
    import config.settings as _mod
    import sys
    cfg_module = sys.modules["config.settings"]
    monkeypatch.setattr(cfg_module.settings, "langsmith_api_key", "")

    # Remove any leftover env var
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)

    result = configure_tracing()
    assert result is False
    assert os.environ.get("LANGCHAIN_TRACING_V2") is None


def test_configure_tracing_enabled_with_key(monkeypatch):
    """Tracing env vars should be set when an API key is provided."""
    import config.settings as _mod
    import sys
    cfg_module = sys.modules["config.settings"]
    monkeypatch.setattr(cfg_module.settings, "langsmith_api_key", "ls-test-key-123")
    monkeypatch.setattr(cfg_module.settings, "langsmith_project", "test-project")

    # Clean slate
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)

    result = configure_tracing()
    assert result is True
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGCHAIN_API_KEY"] == "ls-test-key-123"
    assert os.environ["LANGCHAIN_PROJECT"] == "test-project"
