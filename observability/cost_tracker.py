"""
Token-usage cost tracker.

A LangChain callback handler that records prompt / completion tokens for every
LLM call, keyed by (thread_id, agent_name).  The singleton ``cost_tracker``
accumulates data across the server lifetime and exposes it via ``get_session``
and ``get_all_sessions`` for the /api/costs endpoint.
"""
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


@dataclass
class AgentUsage:
    """Token counts for a single agent within a session."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0
    tool_calls: int = 0

    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
        }


@dataclass
class SessionCost:
    """Aggregated costs for one thread/session."""
    thread_id: str
    started_at: float = field(default_factory=time.time)
    agents: dict[str, AgentUsage] = field(default_factory=dict)

    def _ensure_agent(self, name: str) -> AgentUsage:
        if name not in self.agents:
            self.agents[name] = AgentUsage()
        return self.agents[name]

    def record_llm(self, agent_name: str, token_usage: dict) -> None:
        usage = self._ensure_agent(agent_name)
        usage.prompt_tokens += token_usage.get("prompt_tokens", 0)
        usage.completion_tokens += token_usage.get("completion_tokens", 0)
        usage.total_tokens += token_usage.get("total_tokens", 0)
        usage.llm_calls += 1

    def record_tool(self, agent_name: str) -> None:
        usage = self._ensure_agent(agent_name)
        usage.tool_calls += 1

    def totals(self) -> dict:
        total = AgentUsage()
        for a in self.agents.values():
            total.prompt_tokens += a.prompt_tokens
            total.completion_tokens += a.completion_tokens
            total.total_tokens += a.total_tokens
            total.llm_calls += a.llm_calls
            total.tool_calls += a.tool_calls
        return total.to_dict()

    def to_dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "started_at": self.started_at,
            "agents": {k: v.to_dict() for k, v in self.agents.items()},
            "totals": self.totals(),
        }


class CostTracker:
    """Thread-safe accumulator for token costs across sessions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, SessionCost] = {}

    def _ensure_session(self, thread_id: str) -> SessionCost:
        if thread_id not in self._sessions:
            self._sessions[thread_id] = SessionCost(thread_id=thread_id)
        return self._sessions[thread_id]

    def record_llm(self, thread_id: str, agent_name: str, token_usage: dict) -> None:
        with self._lock:
            self._ensure_session(thread_id).record_llm(agent_name, token_usage)

    def record_tool(self, thread_id: str, agent_name: str) -> None:
        with self._lock:
            self._ensure_session(thread_id).record_tool(agent_name)

    def get_session(self, thread_id: str) -> dict | None:
        with self._lock:
            s = self._sessions.get(thread_id)
            return s.to_dict() if s else None

    def get_all_sessions(self) -> list[dict]:
        with self._lock:
            return [s.to_dict() for s in self._sessions.values()]

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


class CostCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback that feeds token usage into the CostTracker.

    Pass this as a callback when invoking the orchestrator graph::

        config = {
            "configurable": {"thread_id": ...},
            "callbacks": [CostCallbackHandler(tracker, thread_id)],
        }

    The handler extracts ``token_usage`` from the LLM response metadata and
    tracks tool invocations via ``on_tool_start``.
    """

    def __init__(self, tracker: CostTracker, thread_id: str) -> None:
        super().__init__()
        self.tracker = tracker
        self.thread_id = thread_id
        self._current_agent: str = "unknown"

    # -- Agent-name tracking (LangGraph sets run_name on node executions) --

    def on_chain_start(self, serialized: dict[str, Any], inputs: Any, **kwargs: Any) -> None:
        name = kwargs.get("name") or (serialized or {}).get("name", "")
        if name:
            self._current_agent = name

    # -- LLM calls --

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        for gen_list in response.generations:
            for gen in gen_list:
                token_usage = (gen.generation_info or {}).get("usage_metadata")
                if not token_usage:
                    token_usage = (response.llm_output or {}).get("token_usage", {})
                mapped = {
                    "prompt_tokens": token_usage.get("prompt_tokens")
                                     or token_usage.get("input_tokens", 0),
                    "completion_tokens": token_usage.get("completion_tokens")
                                         or token_usage.get("output_tokens", 0),
                    "total_tokens": token_usage.get("total_tokens", 0),
                }
                if not mapped["total_tokens"]:
                    mapped["total_tokens"] = mapped["prompt_tokens"] + mapped["completion_tokens"]
                self.tracker.record_llm(self.thread_id, self._current_agent, mapped)

    # -- Tool calls --

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        tool_name = (serialized or {}).get("name", "unknown_tool")
        self.tracker.record_tool(self.thread_id, tool_name)


# Singleton — importable from anywhere, wired into the /api/costs route
cost_tracker = CostTracker()
