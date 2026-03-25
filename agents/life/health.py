from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader
from context.memory_distiller import MemoryDistiller
from tools.save_artifact import save_artifact

PROMPT = """You are the LifeScout Health & Wellness Sub-Agent.
Your job is to build fitness and wellness plans based on the user's profile and constraints.

Your output MUST be a strictly formatted Markdown document divided into clear domains:
# Wellness & Fitness Plan

> [!WARNING]
> Consult a physician before starting any new diet or exercise regimen.

## 1. Nutrition Principles
[Core guidelines tailored to their objectives]

## 2. Activity / Training Routine
[Specific exercises strictly mapped to their weekly time constraints]

## 3. Recovery & Mental Hygiene
[Sleep and stress management protocols]
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_low_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def health_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("life")
    memory = MemoryDistiller.load_summary()
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCross-Domain Context:\n{memory}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    task_id = state.get("task_id", "manual")
    file_path = save_artifact("life", "health", task_id, response.content)

    return {
        "messages": [AIMessage(content=f"Health plan saved to {file_path}", name="health_agent")],
        "next": "__end__",
        "termination_signal": True
    }
