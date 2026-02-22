import time
from typing import Literal
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from orchestrator.state import AgentState
from orchestrator.supervisor import enforce_budget
from config.settings import settings
from context.task_manager import task_manager

class Route(BaseModel):
    next: Literal[
        "resume_agent",
        "job_search_agent",
        "interview_prep_agent",
        "career_planning_agent",
        "linkedin_agent",
        "lead_generation_agent",
        "__end__"
    ] = Field(description="The next specialized agent to route to, or __end__ if the request is completed or not related to career.")

SUPERVISOR_PROMPT = """You are the Career Supervisor Agent.
Your job is to manage the user's career development requests by delegating tasks to specialized sub-agents.
You have access to the following sub-agents:
- resume_agent: Generates and optimizes CVs using document generator and web search.
- job_search_agent: Searches job postings via Tavily and tracks applications.
- interview_prep_agent: Generates interview Q&A and identifies skill gaps.
- career_planning_agent: Builds career roadmaps and sets milestones.
- linkedin_agent: Generates LinkedIn optimization recommendations and networking outreach drafts.
- lead_generation_agent: Proactively finds opportunities and evaluates leads against user profile.

Analyze the conversation history. If the user's request is best handled by one of these agents, route to it.
If the sub-agent has already executed and returned a helpful response completing the user's intent, route to "__end__".
If the request is unrelated to career, route to "__end__".
"""

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model=settings.model_supervisors,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

llm_with_tools = llm.with_structured_output(Route)

def career_supervisor_node(state: AgentState) -> dict:
    budget_breach = enforce_budget(state)
    
    # Track stats
    stats = state.get("budget_stats", {"iterations": 0, "tool_calls": 0, "start_time": time.time()})
    
    task_id = state.get("task_id")
    
    if budget_breach:
        stats["iterations"] += 1
        budget_message = budget_breach["messages"][0]
        budget_message.additional_kwargs["force_end"] = True
        
        # If task exists, fail it
        if task_id:
            t = task_manager.get_task(task_id)
            if t and t.status == "running":
                t.status = "failed"
                task_manager.update_task(t)

        return {"messages": [budget_message], "budget_stats": stats, "next": "__end__"}

    # Concurrency Check
    if task_id:
        task = task_manager.get_task(task_id)
        if task and task.status == "pending":
            return {
                "messages": [AIMessage(content="[SYSTEM] Task is pending due to concurrency limits. Queued for later.", name="career_supervisor")],
                "budget_stats": stats,
                "next": "__end__"
            }
        if task and task.status in ["completed", "failed", "cancelled"]:
            return {
                "budget_stats": stats,
                "next": "__end__"
            }

    messages = state.get("messages", [])
    sys_msg = SystemMessage(content=SUPERVISOR_PROMPT)
    formatted_messages = [sys_msg] + messages
    
    try:
        response = llm_with_tools.invoke(formatted_messages)
        next_node = response.next if response else "__end__"
    except Exception as e:
        print(f"[Career Supervisor] Structured output error: {e}")
        # fallback if gemini fails formatting
        next_node = "__end__"
    
    print(f"[Career Supervisor] Routing to: {next_node}")
    
    if next_node == "__end__" and task_id:
        t = task_manager.get_task(task_id)
        if t and t.status == "running":
            t.status = "completed"
            task_manager.update_task(t)
            
    stats["iterations"] += 1
    
    return {"budget_stats": stats, "next": next_node}
