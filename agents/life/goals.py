from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader
from context.memory_distiller import MemoryDistiller
from tools.save_artifact import save_artifact

PROMPT = """You are the LifeScout Goals & OKR Sub-Agent.
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
    artifacts = ArtifactLoader.load_recent("life")
    memory = MemoryDistiller.load_summary()
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCross-Domain Context:\n{memory}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    task_id = state.get("task_id", "manual")
    file_path = save_artifact("life", "goals", task_id, response.content)

    return {
        "messages": [AIMessage(content=f"Goals tracker saved to {file_path}", name="goals_agent")],
        "next": "__end__",
        "termination_signal": True
    }
