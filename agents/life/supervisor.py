import time
from typing import Literal
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from orchestrator.state import AgentState
from orchestrator.supervisor import enforce_budget
from config.settings import settings
from context.task_manager import task_manager
from context.memory_distiller import MemoryDistiller

class Route(BaseModel):
    next: Literal[
        "goals_agent",
        "habits_agent",
        "health_agent",
        "therapy_agent",
        "__end__"
    ] = Field(description="The next specialized agent to route to, or __end__ if the request is completed or not related to life.")

SUPERVISOR_PROMPT = """You are the Life Supervisor Agent.
Your job is to manage the user's personal development requests by delegating tasks to specialized sub-agents.
You have access to the following sub-agents:
- goals_agent: Creates and tracks personal goals and progress.
- habits_agent: Designs habit formation plans and tracks streaks.
- health_agent: Builds fitness and wellness plans based on constraints.
- therapy_agent: Provides pure journaling prompts and coping exercises.

Analyze the conversation history. If the user's request is best handled by one of these agents, route to it.
If the sub-agent has already executed and returned a helpful response completing the user's intent, route to "__end__".
If the request is unrelated to life/health/goals/habits, route to "__end__".
"""

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model=settings.model_supervisors,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

llm_with_tools = llm.with_structured_output(Route)

def life_supervisor_node(state: AgentState) -> dict:
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
            pending_msg = AIMessage(content="[SYSTEM] Task is pending due to concurrency limits. Queued for later.", name="life_supervisor")
            pending_msg.additional_kwargs["force_end"] = True
            return {
                "messages": [pending_msg],
                "budget_stats": stats,
                "next": "__end__"
            }
        if task and task.status in ["completed", "failed", "cancelled"]:
            return {
                "budget_stats": stats,
                "next": "__end__"
            }

    messages = state.get("messages", [])
    memory = MemoryDistiller.load_summary()
    sys_msg = SystemMessage(content=f"{SUPERVISOR_PROMPT}\n\nCross-Domain Context:\n{memory}")
    formatted_messages = [sys_msg] + messages
    
    try:
        response = llm_with_tools.invoke(formatted_messages)
        next_node = response.next if response else "__end__"
    except Exception as e:
        print(f"[Life Supervisor] Structured output error: {e}")
        # fallback if gemini fails formatting
        next_node = "__end__"
    
    print(f"[Life Supervisor] Routing to: {next_node}")
    
    if next_node == "__end__" and task_id:
        t = task_manager.get_task(task_id)
        if t and t.status == "running":
            t.status = "completed"
            task_manager.update_task(t)
            
    stats["iterations"] += 1
    
    return {"budget_stats": stats, "next": next_node}
