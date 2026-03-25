from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader
from context.memory_distiller import MemoryDistiller
from tools.save_artifact import save_artifact

PROMPT = """You are the LifeScout Learning Study Plan Sub-Agent.
Your job is to create highly structured study schedules with clear milestones based on the user's Profile goals.

Your output MUST be a strictly formatted Markdown document structured as a Syllabus:
# Custom Study Syllabus

## Overview & Expectations
[High level summary of the learning path]

## Weekly Plan
* **Week 1**: [Topic] - [Specific Actionable Task] - [Estimated Time, which MUST fit within their week constraints]
* **Week 2**: ...
* **Week 3**: ...

CRITICAL: Emphasize "active recall" techniques in the actionable tasks rather than just passive reading.
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def study_plan_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("learning")
    memory = MemoryDistiller.load_summary()
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCross-Domain Context:\n{memory}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    task_id = state.get("task_id", "manual")
    file_path = save_artifact("learning", "study_plan", task_id, response.content)

    return {
        "messages": [AIMessage(content=f"Study plan saved to {file_path}", name="study_plan_agent")],
        "next": "__end__",
        "termination_signal": True
    }
