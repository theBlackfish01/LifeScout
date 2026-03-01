from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader
from context.memory_distiller import MemoryDistiller
from tools.search import tavily_search

RESUME_PROMPT = """You are the LifeScout Resume Sub-Agent.
Your job is to generate and optimize CVs based on the user's profile and requests.

You have access to tools:
- tavily_search: Search the web for job description keywords, industry trends, or best practices for resume formatting.

WORKFLOW:
1. Review the user's profile and any recent artifacts (prior resumes, job search results).
2. If the user mentions a specific target role or company, use tavily_search to find the actual job description or industry keywords.
3. Generate a polished, keyword-optimized resume.

Your final output MUST be a strictly formatted Markdown resume:
# [User Name] - Resume
[Contact Info Block]

## Summary
[Targeted summary incorporating keywords from real job descriptions if searched]

## Experience
[List roles. CRITICAL: Focus on action verbs and quantify achievements.]

## Education
[Education details]

## Skills
[Extract and categorize grouped technical and soft skills]
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

tools = [tavily_search]
react_agent = create_react_agent(llm, tools)


def resume_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("career")
    memory = MemoryDistiller.load_summary()
    
    sys_content = f"{RESUME_PROMPT}\n\nCross-Domain Context:\n{memory}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}"
    input_msgs = [SystemMessage(content=sys_content)] + messages
    
    try:
        result = react_agent.invoke({"messages": input_msgs})
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content and not m.tool_calls]
        final_content = ai_messages[-1].content if ai_messages else "Resume generation completed."
    except Exception as e:
        print(f"[Resume Agent] ReAct execution error: {e}")
        final_content = f"Resume generation encountered an error: {str(e)}"
    
    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"resume_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_content)
        
    return {"messages": [AIMessage(content=f"Generated resume and saved artifact to {file_path}\n\n{final_content[:500]}...", name="resume_agent")]}
