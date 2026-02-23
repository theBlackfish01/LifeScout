from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager

PROMPT = """You are the LifeScouter Strategic Career Advisor Sub-Agent.
Your job is to build a highly actionable, multi-step career roadmap and set specific milestones based on the user's profile and constraints.

Your output MUST be a strictly formatted Markdown document adhering to the following structure:
# Career Development Roadmap
## Executive Summary
[A brief synthesized summary of their overall goal and its feasibility based on their background.]

## Phase 1: 3-6 Month Milestones
[Actionable, specific short-term goals. E.g., "Complete Course X", "Build Portfolio Project Y", "Attend 3 Networking Events".]

## Phase 2: 1-Year Goals
[Broader objectives showing the transition into the target role/level.]

## Skill Acquisition Plan
[Specific skills to learn, why they are needed, and how to learn them within their time/budget constraints.]

CRITICAL: You MUST explicitly reference their available hours per week and budget constraints in the Skill Acquisition Plan to ensure the roadmap is realistic.
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def career_planning_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"career_planning_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.content)
        
    return {"messages": [AIMessage(content=f"Generated Career Planning roadmap and saved artifact to {file_path}", name="career_planning_agent")]}
