from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader

PROMPT = """You are the LifeScouter Interview Prep Coach Sub-Agent.
You are tough, analytical, but highly constructive. Your job is to simulate interview scenarios, generate specific Q&A, and identify skill gaps for the user's target roles based on their profile.

Your output MUST be a strictly formatted Markdown document adhering to the following structure:
# Interview Preparation Report

## 1. Behavioral Questions & STAR Mapping
[List 3-5 likely behavioral questions. Provide a framework for how they should answer using the STAR (Situation, Task, Action, Result) method specifically tailored to the experience listed in their profile.]

## 2. Technical / Domain Content Questions
[List specific technical, domain, or situational questions common for their target role.]

## 3. Identified Gap Areas
[Based on their profile vs. the target role expectations, list specific areas where their answers might currently be weak and what they should study to close the gap.]
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def interview_prep_agent_node(state: AgentState) -> dict:
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
    file_path = artifact_dir / f"interview_prep_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.content)
        
    return {"messages": [AIMessage(content=f"Generated Interview Prep report and saved artifact to {file_path}", name="interview_prep_agent")]}
