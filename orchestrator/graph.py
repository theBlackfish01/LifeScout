from typing import Annotated
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END

from orchestrator.state import AgentState
from orchestrator.supervisor import create_supervisor

from agents.onboarding.agent import onboarding_agent_node
from agents.settings.agent import settings_agent_node

from agents.career.supervisor import career_supervisor_node
from agents.career.resume import resume_agent_node
from agents.career.job_search import job_search_agent_node
from agents.career.interview_prep import interview_prep_agent_node
from agents.career.career_planning import career_planning_agent_node
from agents.career.linkedin import linkedin_agent_node
from agents.career.lead_generation import lead_generation_agent_node

from agents.life.supervisor import life_supervisor_node
from agents.life.goals import goals_agent_node
from agents.life.habits import habits_agent_node
from agents.life.health import health_agent_node
from agents.life.therapy import therapy_agent_node

from agents.learning.supervisor import learning_supervisor_node
from agents.learning.study_plan import study_plan_agent_node
from agents.learning.course_rec import course_rec_agent_node
from agents.learning.progress import progress_agent_node

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
    def route_next(state: AgentState) -> str:
        if state.get("termination_signal"):
            return END
        if "next" in state and state["next"] == "__end__":
            return END
        return agent_name
        
    branch.add_conditional_edges(
        "supervisor", 
        route_next, 
        {agent_name: agent_name, END: END}
    )
    branch.add_edge(agent_name, END)
    
    return branch.compile()

def create_career_branch() -> StateGraph:
    branch = StateGraph(AgentState)
    
    # 1. Add specialized nodes
    branch.add_node("resume_agent", resume_agent_node)
    branch.add_node("job_search_agent", job_search_agent_node)
    branch.add_node("interview_prep_agent", interview_prep_agent_node)
    branch.add_node("career_planning_agent", career_planning_agent_node)
    branch.add_node("linkedin_agent", linkedin_agent_node)
    branch.add_node("lead_generation_agent", lead_generation_agent_node)
    
    # 2. Add supervisor node
    branch.add_node("supervisor", career_supervisor_node)
    
    # 3. Add Edges
    branch.add_edge(START, "supervisor")
    
    def route_next(state: AgentState) -> str:
        if state.get("termination_signal"):
            return END
        nxt = state.get("next", "__end__")
        return END if nxt == "__end__" else nxt

    branch.add_conditional_edges(
        "supervisor",
        route_next,
        {
            "resume_agent": "resume_agent",
            "job_search_agent": "job_search_agent",
            "interview_prep_agent": "interview_prep_agent",
            "career_planning_agent": "career_planning_agent",
            "linkedin_agent": "linkedin_agent",
            "lead_generation_agent": "lead_generation_agent",
            END: END
        }
    )
    
    # Sub-agents always route back to the supervisor
    branch.add_edge("resume_agent", "supervisor")
    branch.add_edge("job_search_agent", "supervisor")
    branch.add_edge("interview_prep_agent", "supervisor")
    branch.add_edge("career_planning_agent", "supervisor")
    branch.add_edge("linkedin_agent", "supervisor")
    branch.add_edge("lead_generation_agent", "supervisor")
    
    return branch.compile()

def create_life_branch() -> StateGraph:
    branch = StateGraph(AgentState)
    
    # 1. Add specialized nodes
    branch.add_node("goals_agent", goals_agent_node)
    branch.add_node("habits_agent", habits_agent_node)
    branch.add_node("health_agent", health_agent_node)
    branch.add_node("therapy_agent", therapy_agent_node)
    
    # 2. Add supervisor node
    branch.add_node("supervisor", life_supervisor_node)
    
    # 3. Add Edges
    branch.add_edge(START, "supervisor")
    
    def route_next(state: AgentState) -> str:
        if state.get("termination_signal"):
            return END
        nxt = state.get("next", "__end__")
        return END if nxt == "__end__" else nxt

    branch.add_conditional_edges(
        "supervisor",
        route_next,
        {
            "goals_agent": "goals_agent",
            "habits_agent": "habits_agent",
            "health_agent": "health_agent",
            "therapy_agent": "therapy_agent",
            END: END
        }
    )
    
    # Sub-agents always route back to the supervisor
    branch.add_edge("goals_agent", "supervisor")
    branch.add_edge("habits_agent", "supervisor")
    branch.add_edge("health_agent", "supervisor")
    branch.add_edge("therapy_agent", "supervisor")
    
    return branch.compile()

def create_learning_branch() -> StateGraph:
    branch = StateGraph(AgentState)
    
    # 1. Add specialized nodes
    branch.add_node("study_plan_agent", study_plan_agent_node)
    branch.add_node("course_rec_agent", course_rec_agent_node)
    branch.add_node("progress_agent", progress_agent_node)
    
    # 2. Add supervisor node
    branch.add_node("supervisor", learning_supervisor_node)
    
    # 3. Add Edges
    branch.add_edge(START, "supervisor")
    
    def route_next(state: AgentState) -> str:
        if state.get("termination_signal"):
            return END
        nxt = state.get("next", "__end__")
        return END if nxt == "__end__" else nxt

    branch.add_conditional_edges(
        "supervisor",
        route_next,
        {
            "study_plan_agent": "study_plan_agent",
            "course_rec_agent": "course_rec_agent",
            "progress_agent": "progress_agent",
            END: END
        }
    )
    
    # Sub-agents always route back to the supervisor
    branch.add_edge("study_plan_agent", "supervisor")
    branch.add_edge("course_rec_agent", "supervisor")
    branch.add_edge("progress_agent", "supervisor")
    
    return branch.compile()

# --- Build the Main Orchestrator Graph ---

def router_node(state: AgentState) -> dict:
    import time
    # Refresh start_time on every invocation — budget timing is per-request, not
    # cumulative across turns.  Preserve any iterations/tool_calls already set by
    # the caller (e.g. test states that seed a blown budget).
    stats = state.get("budget_stats") or {}
    return {"budget_stats": {
        "iterations": stats.get("iterations", 0),
        "tool_calls": stats.get("tool_calls", 0),
        "start_time": time.time(),
    }}

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
    builder.add_node("career_branch", create_career_branch())
    builder.add_node("life_branch", create_life_branch())
    builder.add_node("learning_branch", create_learning_branch())
    
    # Standalone Agents (no supervisor needed)
    builder.add_node("onboarding_agent", onboarding_agent_node)
    builder.add_node("settings_agent", settings_agent_node)
    
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
