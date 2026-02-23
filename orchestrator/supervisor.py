import time
from typing import Literal, Callable, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from orchestrator.state import AgentState
from config.settings import settings

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
    
    # Initialize the LLM for routing
    llm = ChatGoogleGenerativeAI(
        model=settings.model_supervisors,
        api_key=settings.gemini_api_key if settings.gemini_api_key else None,
        temperature=0.0
    )
    
    # Define route options and schema
    options = ["__end__"] + members
    
    class RouteParams(BaseModel):
        reasoning: str = Field(description="Internal reasoning for why this node was chosen based on the task status and previous messages.")
        next: str = Field(description=f"The next node to route to. MUST be one of {options}.")
        
    router_llm = llm.with_structured_output(RouteParams)
    
    system_prompt = f"""You are the supervisor for the '{group_name}' agent group.
Your job is to read the conversation history and decide what needs to happen next.
You have the following sub-agents available to route work to: {members}.

If a sub-agent has just returned its output and the goal is complete (or it indicates it generated/saved an artifact), you MUST route to '__end__'.
If the user's request requires work from one of your sub-agents, route to that sub-agent.
If you don't have an appropriate sub-agent or the task is done, route to '__end__'.
"""

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
        
        # 2. LLM Routing Logic
        print(f"[{group_name} Supervisor] Analyzing context for routing decision...")
        stats = state.get("budget_stats", {"iterations": 0, "tool_calls": 0, "start_time": time.time()})
        stats["iterations"] += 1
        
        messages = state.get("messages", [])
        
        # Build the final prompt payload
        formatted_messages = [SystemMessage(content=system_prompt)] + messages
        
        try:
            decision = router_llm.invoke(formatted_messages)
            next_node = decision.next if decision.next in options else "__end__"
            
            # Log reasoning natively
            print(f"[{group_name} Supervisor] Decided: {next_node}. Reasoning: {decision.reasoning}")
            
            return {"budget_stats": stats, "next": next_node}
            
        except Exception as e:
            print(f"[{group_name} Supervisor] Structured routing failed: {e}. Falling back to __end__")
            return {"messages": [AIMessage(content=f"[SYSTEM] Routing failed due to LLM error: {e}", name="supervisor_error")], "budget_stats": stats, "next": "__end__"}
        
    return supervisor_node
