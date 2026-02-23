from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager

PROMPT = """You are the LifeScouter LinkedIn Strategy Sub-Agent.
Your job is to generate personal branding recommendations and outreach drafts.

Your output MUST be a strictly formatted Markdown document adhering to the following structure:
# LinkedIn Optimization Strategy

## 1. Headline Suggestions
[Provide 3 distinct, keyword-optimized headline options based on their goals.]

## 2. 'About' Section Rewrite
[Provide a modern, engaging About section incorporating their background and goals from their profile.]

## 3. Networking Outreach Templates
[Provide 3 distinct cold-outreach messaging templates tailored to their specific industry and target roles.]
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def linkedin_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"linkedin_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.content)
        
    return {"messages": [AIMessage(content=f"Generated LinkedIn optimization report and saved artifact to {file_path}", name="linkedin_agent")]}
