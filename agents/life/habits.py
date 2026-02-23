from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader

PROMPT = """You are the LifeScouter Behavioral Habits Sub-Agent.
Your job is to design habit formation plans based on the user's profile using behavioral psychology strategies (like habit stacking or implementation intentions).

Your output MUST be a strictly formatted Markdown document including a tracking matrix:
# Habit Formation Plan

## Core Habits
1. **[Habit Name]**: [Trigger/Cue] -> [Routine] -> [Reward].

## Weekly Tracker
| Habit | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|-------|-----|-----|-----|-----|-----|-----|-----|
| ...   | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_low_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def habits_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("life")
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    artifact_dir = Path(settings.data_dir) / "life" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"habits_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.content)
        
    return {
        "messages": [AIMessage(content=f"Generated habits plan and saved artifact to {file_path}", name="habits_agent")],
        "next": "__end__"
    }
