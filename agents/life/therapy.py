from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager

# The prompt strictly enforces the therapist disclaimer mandate natively on the language model node
PROMPT = """You are the Life Therapy Sub-Agent.
Your job is to provide journaling prompts and coping exercises.
You output a Markdown-formatted session notes artifact.

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
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    
    content = response.content
    
    # Redundancy check enforcing the disclaimer if the LLM hallucinated past the prompt bounds.
    if "I am not a professional therapist" not in content:
        content = "**I am not a professional therapist.**\n\n" + content
    
    artifact_dir = Path(settings.data_dir) / "life" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"therapy_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return {
        "messages": [AIMessage(content=content, name="therapy_agent")],
        "next": "__end__"
    }
