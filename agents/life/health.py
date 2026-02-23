from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager

PROMPT = """You are the LifeScouter Health & Wellness Sub-Agent.
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
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    artifact_dir = Path(settings.data_dir) / "life" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"health_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.content)
        
    return {
        "messages": [AIMessage(content=f"Generated health plan and saved artifact to {file_path}", name="health_agent")],
        "next": "__end__"
    }
