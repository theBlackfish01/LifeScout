from typing import Annotated
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END

from orchestrator.state import AgentState
from orchestrator.supervisor import create_supervisor

# Define exact groups
CAREER_GROUP = "career"
LIFE_GROUP = "life"
LEARNING_GROUP = "learning"

# --- Mock Sub-Agents and Supervisors ---
# These simulate the graph nodes for T5-T8.
def dummy_agent_node(state: AgentState) -> dict:
    """A minimal node that pretends to do work."""
    return {"messages": [AIMessage(content=f"[{state['active_agent']} Sub-Agent] Executed.", name=f"{state['active_agent']}_agent")]}

def create_stub_branch(group_name: str) -> StateGraph:
    """Creates a standalone graph simulating a specialized agent group."""
    branch = StateGraph(AgentState)
    agent_name = f"{group_name}_agent"
    
    branch.add_node(agent_name, dummy_agent_node)
    
    # Normally the LLM acts as the router returning custom targets. We mocked it to route here or END.
    branch.add_node("supervisor", create_supervisor(group_name, [agent_name]))

    # Connect START to supervisor
    branch.add_edge(START, "supervisor")
    
    # Add cyclical edges based on the return state of the supervisor node mapping to actual node names
    # Supervisor routes back to 'agent_name' or END 
    # Here we simulate the Conditional Edges mapping the `"next"` return field back to physical string nodes.
    # In LangGraph v0.1: add_conditional_edges(source, router_function, map_dict)
    def route_next(state: AgentState) -> str:
        # In a real setup, `next` is extracted from an LLM call or returned explicitly 
        # Since we mocked the supervisor to return `next` explicitly, we might need to store it 
        # carefully in State. For simplicity of the mock, we can just look at message history
        # but since we want robust budget checking, let's just make the mock linear right now.
        return agent_name
        
    # We will build a simple loop for the mock: Supervisor -> Agent -> END
    branch.add_edge("supervisor", agent_name)
    branch.add_edge(agent_name, END)
    
    return branch.compile()

# --- Build the Main Orchestrator Graph ---

def router_node(state: AgentState) -> dict:
    # A standalone node isn't strictly necessary for pure conditional routing from START,
    # but is useful for logging logic or initializing stats.
    # We ensure budget stats are ready.
    if "budget_stats" not in state or not state["budget_stats"]:
        import time
        return {"budget_stats": {"iterations": 0, "tool_calls": 0, "start_time": time.time()}}
    return {}

def route_to_group(state: AgentState) -> str:
    """The central routing determinant reading active_agent from state."""
    active = state.get("active_agent", "").lower()
    if active == CAREER_GROUP:
        return "career_branch"
    elif active == LIFE_GROUP:
        return "life_branch"
    elif active == LEARNING_GROUP:
        return "learning_branch"
    elif active == "onboarding":
        return "onboarding_agent"
    elif active == "settings":
        return "settings_agent"
    else:
        # Failsafe
        return END

def build_orchestrator() -> StateGraph:
    """Compiles the top-level generic routing graph connecting context stubs."""
    builder = StateGraph(AgentState)
    
    # 1. The Global Entry Node
    builder.add_node("router", router_node)
    
    # 2. Add Group Branches
    builder.add_node("career_branch", create_stub_branch(CAREER_GROUP))
    builder.add_node("life_branch", create_stub_branch(LIFE_GROUP))
    builder.add_node("learning_branch", create_stub_branch(LEARNING_GROUP))
    
    # Standalone Agents (no supervisor needed)
    def stub_onboarding(s): return {"messages": [AIMessage(content="[Onboarding] Complete.", name="onboarding")]}
    def stub_settings(s): return {"messages": [AIMessage(content="[Settings] Updated.", name="settings")]}
    
    builder.add_node("onboarding_agent", stub_onboarding)
    builder.add_node("settings_agent", stub_settings)
    
    # 3. Edges
    builder.add_edge(START, "router")
    
    builder.add_conditional_edges(
        "router",
        route_to_group,
        {
            "career_branch": "career_branch",
            "life_branch": "life_branch",
            "learning_branch": "learning_branch",
            "onboarding_agent": "onboarding_agent",
            "settings_agent": "settings_agent",
            END: END
        }
    )
    
    # 4. Finish sub-paths
    builder.add_edge("career_branch", END)
    builder.add_edge("life_branch", END)
    builder.add_edge("learning_branch", END)
    builder.add_edge("onboarding_agent", END)
    builder.add_edge("settings_agent", END)

    from orchestrator.checkpoint import get_checkpointer
    checkpointer = get_checkpointer()

    return builder.compile(checkpointer=checkpointer)

# Singleton Export
orchestrator_graph = build_orchestrator()
