import time
from typing import Literal, Callable
from langchain_core.messages import AIMessage
from orchestrator.state import AgentState

# Define hard limits for safety
MAX_ITERATIONS = 5
MAX_TOOL_CALLS = 15
MAX_EXECUTION_TIME_SEC = 300  # 5 minutes

def enforce_budget(state: AgentState) -> dict:
    """
    Evaluates the budget_stats dictionary within the state.
    Returns a dictionary of updates if a budget is blown, otherwise returns {}.
    """
    stats = state.get("budget_stats", {"iterations": 0, "tool_calls": 0, "start_time": time.time()})
    
    # 1. Check Iterations
    if stats["iterations"] >= MAX_ITERATIONS:
         return {"messages": [AIMessage(content="[SYSTEM] Budget Exceeded: Max iterations reached. Terminating early returning partial results.", name="supervisor_budget_guard")]}
         
    # 2. Check Tool Calls
    if stats["tool_calls"] >= MAX_TOOL_CALLS:
         return {"messages": [AIMessage(content="[SYSTEM] Budget Exceeded: Max tool calls reached. Terminating early returning partial results.", name="supervisor_budget_guard")]}
         
    # 3. Check Time
    if (time.time() - stats["start_time"]) >= MAX_EXECUTION_TIME_SEC:
         return {"messages": [AIMessage(content="[SYSTEM] Budget Exceeded: Time limit reached. Terminating early returning partial results.", name="supervisor_budget_guard")]}
         
    return {}

def create_supervisor(group_name: str, members: list[str]) -> Callable[[AgentState], dict]:
    """
    Creates a supervisor node for an agent group.
    
    Args:
        group_name: The name of the group (e.g. "career")
        members: List of sub-agent node names (e.g. ["resume_agent", "job_search_agent"])
        
    Returns:
        A callable node that executes the supervisor logic.
    """
    
    # We would normally instantiate the generic LLM here bound to structural tools for routing.
    # For T4 MVP, we will construct the base shell and budget checking logic.
    
    def supervisor_node(state: AgentState) -> dict:
        # 1. Pre-flight budget check
        budget_breach = enforce_budget(state)
        if budget_breach:
             # If breached, we signal routing to END by setting a specific state flag or 
             # just relying on the conditional edge to detect the [SYSTEM] termination message.
             # For now, we update the state with the breach message.
             # Note: Iterations counter belongs to the graph cycles naturally, 
             # but we manually increment here for explicit budget tracking.
             
             stats = state.get("budget_stats", {"iterations": 0, "tool_calls": 0, "start_time": time.time()})
             stats["iterations"] += 1
             print(f"[{group_name} Supervisor] Budget breached. Forcing __end__")
             
             # LangGraph passes list updates via reducers. 
             # We embed a flag on the message kwargs natively so our mock router can explicitly read it.
             budget_message = budget_breach["messages"][0]
             budget_message.additional_kwargs["force_end"] = True
             
             return {"messages": [budget_message], "budget_stats": stats, "next": "__end__"}
             
        # Catch our checkpoint test follow-up message to ensure we don't just infinite loop 
        # since our mock isn't a real LLM that can decide to stop.
        if state.get("messages") and "Here is a follow up" in state["messages"][-1].content:
            stats = state.get("budget_stats", {"iterations": 0, "tool_calls": 0, "start_time": time.time()})
            return {"budget_stats": stats, "next": "__end__"}
        
        # 2. LLM Routing Logic (Mocked for T4 Orchestrator test)
        # Normally: The supervisor parses `state["messages"]`, decides which `member` in `members` should run next.
        
        # --- Mock Logic Start ---
        print(f"[{group_name} Supervisor] Routing evaluate...")
        stats = state.get("budget_stats", {"iterations": 0, "tool_calls": 0, "start_time": time.time()})
        stats["iterations"] += 1
        
        # Let's mock a simple cycle for testing: route to first member, then end.
        last_message = state["messages"][-1]
        
        if last_message.name and "agent" in last_message.name:
            # An agent just ran, end the cycle.
            return {"budget_stats": stats, "next": "__end__"}
        else:
            # User or system trigger, route to an agent (if any exist)
            next_node = members[0] if members else "__end__"
            return {"budget_stats": stats, "next": next_node}
        # --- Mock Logic End ---
        
    return supervisor_node
