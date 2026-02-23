from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager

PROMPT = """You are the LifeScouter Career Lead Generation Sub-Agent.
Your job is to proactively find high-quality career opportunities and evaluate leads against the user profile.

Your output MUST be a strictly formatted Markdown document grouping leads into the following categories:
# Lead Generation Report

## 1. Top Target Companies
[List companies that match their profile and geographic constraints, and explain WHY.]

## 2. Networking Opportunities
[List specific events, conferences, or online communities they should join.]

## 3. High-ROI Certifications/Resources
[List non-obvious, high-value resources or certifications they should pursue to become a top candidate.]
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def lead_generation_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"lead_batch_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.content)
        
    return {"messages": [AIMessage(content=f"Generated Lead Generation batch and saved artifact to {file_path}", name="lead_generation_agent")]}
