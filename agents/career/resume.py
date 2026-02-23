from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager

RESUME_PROMPT = """You are the LifeScouter Resume Sub-Agent.
Your job is to generate and optimize CVs based on the user's profile and requests.

Your output MUST be a strictly formatted Markdown document formatted as a ready-to-use resume:
# [User Name] - Resume
[Contact Info Block]

## Summary
[Targeted summary based on their profile goals]

## Experience
[List roles. CRITICAL: Focus on action verbs and quantify achievements if data is provided in their profile.]

## Education
[Education details]

## Skills
[Extract and categorize grouped technical and soft skills]
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def resume_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    
    sys_msg = SystemMessage(content=f"{RESUME_PROMPT}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"resume_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.content)
        
    return {"messages": [AIMessage(content=f"Generated resume and saved artifact to {file_path}\n\n{response.content[:200]}...", name="resume_agent")]}
