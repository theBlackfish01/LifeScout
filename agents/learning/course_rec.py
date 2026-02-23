from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader

PROMPT = """You are the LifeScouter Learning Course Recommendation Sub-Agent.
Your job is to recommend specific online courses, textbooks, tutorials, or educational resources based on the user's Profile goals.

Your output MUST be a strictly formatted Markdown document. For EACH recommendation, you MUST provide:
# Course Recommendations

## [Course/Resource Name]
* **Provider**: [e.g., Coursera, Udemy, Book]
* **Estimated Cost**: [$]
* **Estimated Duration**: [Time]
* **Why it fits**: [Exact reason based on their profile data]
* **Link**: [URL]
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_low_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

def course_rec_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("learning")
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = llm.invoke(formatted)
    content = response.content
    
    artifact_dir = Path(settings.data_dir) / "learning" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"course_recs_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return {
        "messages": [AIMessage(content=f"Generated course recommendations and saved artifact to {file_path}", name="course_rec_agent")],
        "next": "__end__"
    }
