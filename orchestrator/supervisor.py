import time
from typing import Callable
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from orchestrator.state import AgentState
from config.settings import settings
from context.task_manager import task_manager
from context.memory_distiller import MemoryDistiller

# Hard limits applied by every supervisor
MAX_ITERATIONS = 5
MAX_TOOL_CALLS = 15
MAX_EXECUTION_TIME_SEC = 300  # 5 minutes


def enforce_budget(state: AgentState) -> dict:
    """
    Check whether any budget limit has been exceeded.

    Returns a dict with a budget-breach AIMessage if a limit is blown,
    otherwise returns {}.
    """
    stats = state.get("budget_stats", {"iterations": 0, "tool_calls": 0, "start_time": time.time()})

    if stats["iterations"] >= MAX_ITERATIONS:
        return {"messages": [AIMessage(
            content="[SYSTEM] Budget Exceeded: Max iterations reached. Terminating early returning partial results.",
            name="supervisor_budget_guard",
        )]}
    if stats["tool_calls"] >= MAX_TOOL_CALLS:
        return {"messages": [AIMessage(
            content="[SYSTEM] Budget Exceeded: Max tool calls reached. Terminating early returning partial results.",
            name="supervisor_budget_guard",
        )]}
    if (time.time() - stats["start_time"]) >= MAX_EXECUTION_TIME_SEC:
        return {"messages": [AIMessage(
            content="[SYSTEM] Budget Exceeded: Time limit reached. Terminating early returning partial results.",
            name="supervisor_budget_guard",
        )]}
    return {}


def create_supervisor(
    group_name: str,
    members: list[str],
    system_prompt: str | None = None,
    model: str | None = None,
) -> Callable[[AgentState], dict]:
    """
    Create a supervisor node for an agent group.

    Handles, in order:
      1. Budget enforcement (fails the task on breach)
      2. Concurrency / task-status checks
      3. Memory-augmented LLM routing with structured output
      4. Task completion marking on termination
      5. Conversational responses for off-topic or clarifying turns

    Args:
        group_name:    Domain name, e.g. "career". Used in log messages and AIMessage names.
        members:       Sub-agent node names the LLM may route to.
        system_prompt: Domain-specific routing instructions injected before memory context.
                       When None, a minimal generic prompt is generated from group_name/members.
        model:         Gemini model name. Defaults to settings.model_supervisors.

    Returns:
        A callable suitable for use as a LangGraph node.
    """
    llm_model = model or settings.model_supervisors
    llm = ChatGoogleGenerativeAI(
        model=llm_model,
        api_key=settings.gemini_api_key if settings.gemini_api_key else None,
        temperature=0.0,
    )

    options = ["__end__"] + members

    # Defined inside the factory so each call gets a fresh class (Pydantic requirement).
    class RouteParams(BaseModel):
        next: str = Field(
            description=f"The next node to route to. MUST be one of {options}.",
        )
        conversational_response: str | None = Field(
            default=None,
            description=(
                "If the request is conversational or cannot be handled by any agent, "
                "set next='__end__' and provide a friendly reply here."
            ),
        )

    router_llm = llm.with_structured_output(RouteParams)

    _prompt = system_prompt or (
        f"You are the supervisor for the '{group_name}' agent group.\n"
        f"Route user requests to the appropriate sub-agent: {members}.\n"
        "If work is complete or the request is off-topic, route to '__end__'.\n"
        "For conversational turns, route to '__end__' and use conversational_response."
    )

    def supervisor_node(state: AgentState) -> dict:
        stats = state.get("budget_stats", {"iterations": 0, "tool_calls": 0, "start_time": time.time()})
        task_id = state.get("task_id")

        # --- 1. Budget check ---
        budget_breach = enforce_budget(state)
        if budget_breach:
            stats["iterations"] += 1
            budget_message = budget_breach["messages"][0]
            budget_message.additional_kwargs["force_end"] = True
            print(f"[{group_name} Supervisor] Budget breached. Forcing __end__")
            if task_id:
                t = task_manager.get_task(task_id)
                if t and t.status == "running":
                    t.status = "failed"
                    task_manager.update_task(t)
            return {
                "messages": [budget_message],
                "budget_stats": stats,
                "next": "__end__",
                "termination_signal": True,
            }

        # --- 2. Concurrency / task-status check ---
        if task_id:
            task = task_manager.get_task(task_id)
            if task and task.status == "pending":
                pending_msg = AIMessage(
                    content="[SYSTEM] Task is pending due to concurrency limits. Queued for later.",
                    name=f"{group_name}_supervisor",
                )
                pending_msg.additional_kwargs["force_end"] = True
                return {
                    "messages": [pending_msg],
                    "budget_stats": stats,
                    "next": "__end__",
                    "termination_signal": True,
                }
            if task and task.status in ("completed", "failed", "cancelled"):
                return {"budget_stats": stats, "next": "__end__"}

        # --- 3. LLM routing ---
        stats["iterations"] += 1
        print(f"[{group_name} Supervisor] Analyzing context for routing decision...")

        memory = MemoryDistiller.load_summary()
        sys_msg = SystemMessage(content=f"{_prompt}\n\nCross-Domain Context:\n{memory}")
        formatted_messages = [sys_msg] + state.get("messages", [])

        try:
            decision = router_llm.invoke(formatted_messages)
            next_node = decision.next if decision.next in options else "__end__"
            conversational_response = decision.conversational_response if decision else None
        except Exception as e:
            print(f"[{group_name} Supervisor] Structured routing failed: {e}. Falling back to __end__")
            return {
                "messages": [AIMessage(
                    content=f"[SYSTEM] Routing failed due to LLM error: {e}",
                    name="supervisor_error",
                )],
                "budget_stats": stats,
                "next": "__end__",
                "termination_signal": True,
            }

        print(f"[{group_name} Supervisor] Routing to: {next_node}")

        # --- 4. Mark task completed on termination ---
        if next_node == "__end__" and task_id:
            t = task_manager.get_task(task_id)
            if t and t.status == "running":
                t.status = "completed"
                task_manager.update_task(t)

        # --- 5. Conversational reply ---
        msgs = []
        if conversational_response:
            msgs.append(AIMessage(content=conversational_response, name=f"{group_name}_supervisor"))

        ret: dict = {"budget_stats": stats, "next": next_node}
        if msgs:
            ret["messages"] = msgs
        return ret

    return supervisor_node
