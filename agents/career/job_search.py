from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader

PROMPT = """You are the LifeScouter Job Search Strategy Sub-Agent.
Your job is to formulate a targeted job search approach and evaluate potential role types/postings matching the user's profile and geographic constraints.

Your output MUST be a strictly formatted Markdown document including the following structured list or table:
| Target Role / Job Title | Why It's a Fit (Based on Profile) | Gaps to Address | Next Action Step |
|-------------------------|-----------------------------------|-----------------|------------------|
| ... | ... | ... | ... |

CRITICAL: You MUST explicitly filter recommendations based on their geographic location or remote work preferences listed in their constraints. Ensure all "Next Action Steps" are highly specific (avoid generic advice like "apply online").
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def job_search_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("career")
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"job_search_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.content)
        
    return {"messages": [AIMessage(content=f"Generated Job Search report and saved artifact to {file_path}", name="job_search_agent")]}
