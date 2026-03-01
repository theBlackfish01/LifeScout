from typing import Annotated
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.task_manager import task_manager
from context.memory_distiller import MemoryDistiller

PROMPT = """You are the Learning Supervisor Agent.
Your job is to route user requests regarding education, courses, study planning, or progress tracking to the correct specialized sub-agent.

Available Sub-Agents:
1. 'study_plan_agent': For creating structured study schedules, curriculum milestones, or learning paths based on goals.
2. 'course_rec_agent': For recommending specific online courses, textbooks, or learning resources.
3. 'progress_agent': For tracking learning progress, logging completed milestones, or spaced repetition schedules.

You MUST choose one of these sub-agents if the request fits. If the request does not fit any of these, or if the user is explicitly ending the conversation, output '__end__'.
"""

class Route(BaseModel):
    next: str = Field(description="The name of the next agent to route to, or '__end__' to terminate.")

llm = ChatGoogleGenerativeAI(
    model=settings.model_low_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
).with_structured_output(Route)

def learning_supervisor_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    task_id = state.get("task_id")
    stats = state.get("budget_stats", {"iterations": 0, "tool_calls": 0, "start_time": 0.0})
    
    # Budget Check
    stats["iterations"] = stats.get("iterations", 0) + 1
    if stats["iterations"] > 5:
        msg = AIMessage(content="[SYSTEM] Budget Exceeded for Learning Group.", name="learning_supervisor")
        msg.additional_kwargs["force_end"] = True
        return {"messages": [msg], "budget_stats": stats, "next": "__end__"}

    # Concurrency Check
    if task_id:
        task = task_manager.get_task(task_id)
        if task and task.status == "pending":
            pending_msg = AIMessage(content="[SYSTEM] Task is pending due to concurrency limits. Queued for later.", name="learning_supervisor")
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
            
    memory = MemoryDistiller.load_summary()
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCross-Domain Context:\n{memory}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    return {
        "budget_stats": stats,
        "next": response.next
    }
