from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager

PROMPT = """You are the LifeScouter Goals & OKR Sub-Agent.
Your job is to create and track personal goals and progress based on the user's profile and requests.

Your output MUST be a strictly formatted Markdown document using the OKR (Objectives and Key Results) framework:
# Personal Goals Tracker

## Objective: [High-level inspiring goal]
* **Key Result 1**: [Specific, Measurable, Achievable, Relevant, Time-Bound (S.M.A.R.T) metric to track]
* **Key Result 2**: [Another S.M.A.R.T metric]

CRITICAL: All goals must explicitly factor in the time and money constraints listed in the user's profile.
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_low_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def goals_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    artifact_dir = Path(settings.data_dir) / "life" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"goals_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.content)
        
    return {
        "messages": [AIMessage(content=f"Generated goals tracker and saved artifact to {file_path}", name="goals_agent")],
        "next": "__end__"
    }
