"""
Orchestrator tests.

Unit tests (no LLM): budget enforcement, routing failsafe.
Integration tests (require GEMINI_API_KEY): full graph routing, checkpointing.
"""
import time
import pytest
from langchain_core.messages import HumanMessage, AIMessage
from orchestrator import orchestrator_graph, get_checkpoint_config
from orchestrator.supervisor import enforce_budget, MAX_ITERATIONS, MAX_TOOL_CALLS


# ---------------------------------------------------------------------------
# Unit: enforce_budget (no LLM required)
# ---------------------------------------------------------------------------

def test_enforce_budget_passes_when_under_limits():
    state = {
        "budget_stats": {"iterations": 0, "tool_calls": 0, "start_time": time.time()}
    }
    assert enforce_budget(state) == {}


def test_enforce_budget_triggers_on_iteration_overflow():
    state = {
        "budget_stats": {"iterations": MAX_ITERATIONS, "tool_calls": 0, "start_time": time.time()}
    }
    result = enforce_budget(state)
    assert "messages" in result
    assert "Budget Exceeded" in result["messages"][0].content


def test_enforce_budget_triggers_on_tool_call_overflow():
    state = {
        "budget_stats": {"iterations": 0, "tool_calls": MAX_TOOL_CALLS, "start_time": time.time()}
    }
    result = enforce_budget(state)
    assert "messages" in result
    assert "Budget Exceeded" in result["messages"][0].content


def test_enforce_budget_triggers_on_time_overflow():
    state = {
        "budget_stats": {"iterations": 0, "tool_calls": 0, "start_time": time.time() - 400}
    }
    result = enforce_budget(state)
    assert "messages" in result
    assert "Budget Exceeded" in result["messages"][0].content


def test_budget_enforcement_via_graph(budget_blown_state):
    """Graph terminates immediately when budget_stats already exceed limits."""
    config = get_checkpoint_config("life", "test_budget_unit")
    result = orchestrator_graph.invoke(budget_blown_state, config=config)
    messages = result.get("messages", [])

    assert any("Budget Exceeded" in m.content for m in messages), (
        "Graph should have short-circuited with budget exceeded message"
    )
    assert result.get("termination_signal") is True


def test_router_unknown_agent_routes_to_end():
    """An unrecognised active_agent silently terminates without error."""
    config = get_checkpoint_config("unknown", "test_unknown_agent")
    state = {
        "messages": [HumanMessage(content="hello")],
        "active_agent": "unknown_domain",
        "task_id": "t1",
    }
    # Should not raise; graph just ends with no new messages
    result = orchestrator_graph.invoke(state, config=config)
    assert result is not None


# ---------------------------------------------------------------------------
# Integration: full graph routing and checkpointing (need GEMINI_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_career_routing_reaches_branch(require_gemini_key):
    config = get_checkpoint_config("career", "integ_career_routing")
    state = {
        "messages": [HumanMessage(content="Help me update my resume")],
        "active_agent": "career",
        "task_id": "integ_task_1",
    }
    result = orchestrator_graph.invoke(state, config=config)
    messages = result.get("messages", [])
    assert len(messages) > 1, "Graph should have produced agent responses"


@pytest.mark.integration
def test_checkpointing_restores_state(require_gemini_key):
    config = get_checkpoint_config("career", "integ_checkpoint_thread")
    state1 = {
        "messages": [HumanMessage(content="Hello career agent")],
        "active_agent": "career",
        "task_id": "chk_task_1",
    }
    result1 = orchestrator_graph.invoke(state1, config=config)
    count1 = len(result1.get("messages", []))

    state2 = {
        "messages": [HumanMessage(content="Here is a follow up")],
        "active_agent": "career",
    }
    result2 = orchestrator_graph.invoke(state2, config=config)
    count2 = len(result2.get("messages", []))

    assert count2 > count1, "State was not restored from SQLite checkpoint"


@pytest.mark.integration
def test_onboarding_agent_responds(require_gemini_key):
    config = get_checkpoint_config("onboarding", "integ_onboarding")
    state = {
        "messages": [HumanMessage(content="Hi, I want to set up my profile")],
        "active_agent": "onboarding",
        "task_id": "ob_1",
    }
    result = orchestrator_graph.invoke(state, config=config)
    messages = result.get("messages", [])
    assert len(messages) > 1, "Onboarding agent should have replied"
