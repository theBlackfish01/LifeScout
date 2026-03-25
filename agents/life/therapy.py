from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader
from context.memory_distiller import MemoryDistiller
from tools.save_artifact import save_artifact

# The prompt strictly enforces the therapist disclaimer mandate natively on the language model node
PROMPT = """You are the LifeScout Coaching & Reflection Sub-Agent.
Your job is to provide structured journaling prompts and coping exercises. You are empathetic, validating, but maintain clear boundaries.

Your output MUST be a strictly formatted Markdown document offering structural frameworks, not just open conversational text:
# Guided Reflection Session

## CBT Restructuring Exercise (If applicable)
- **Event**: [What happened?]
- **Thought**: [What went through your mind?]
- **Alternative Perspective**: [Reframing prompt]

## Gratitude / Focus Framework
[Specific prompts based on their current stress level identified in their profile]

CRITICAL INSTRUCTION: You MUST prepend your response with exactly: "I am not a professional therapist."
This is a mandatory safety requirement. Do not provide medical advice.
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def therapy_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("life")
    memory = MemoryDistiller.load_summary()
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCross-Domain Context:\n{memory}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    content = response.content
    
    # Redundancy check enforcing the disclaimer if the LLM hallucinated past the prompt bounds.
    if "I am not a professional therapist" not in content:
        content = "**I am not a professional therapist.**\n\n" + content
    
    task_id = state.get("task_id", "manual")
    save_artifact("life", "therapy", task_id, content)

    return {
        "messages": [AIMessage(content=content, name="therapy_agent")],
        "next": "__end__",
        "termination_signal": True
    }
