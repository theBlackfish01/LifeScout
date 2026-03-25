from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader
from context.memory_distiller import MemoryDistiller
from tools.save_artifact import save_artifact

PROMPT = """You are the LifeScout Learning Progress & Reflection Sub-Agent.
Your job is to track the user's learning progress, implement spaced repetition reminders, and reflect on their educational milestones.

Your output MUST be a strictly formatted Markdown document structured as an "End of Cycle Review":
# Learning Progress Review

## 1. Wins & Milestones
[Highlight areas where they are succeeding based on their history]

## 2. Blockers & Adjustments
[Identify what they are struggling with and how to adjust the plan]

## 3. Spaced Repetition Focus
[Based on their past learning topics, explicitly list 3 concepts they need to review *this week* to ensure retention]
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_low_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def progress_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("learning")
    memory = MemoryDistiller.load_summary()
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCross-Domain Context:\n{memory}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    task_id = state.get("task_id", "manual")
    file_path = save_artifact("learning", "progress_report", task_id, response.content)

    return {
        "messages": [AIMessage(content=f"Learning progress report saved to {file_path}", name="progress_agent")],
        "next": "__end__",
        "termination_signal": True
    }
