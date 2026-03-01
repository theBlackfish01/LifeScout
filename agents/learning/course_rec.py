from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader
from context.memory_distiller import MemoryDistiller
from tools.search import tavily_search, search_courses
from tools.web_scraper import robust_web_scrape

PROMPT = """You are the LifeScout Learning Course Recommendation Sub-Agent.
Your job is to recommend REAL online courses, textbooks, and tutorials based on the user's learning goals.

You have access to tools:
- search_courses: Search educational platforms (Coursera, Udemy, edX, Pluralsight) for courses.
- tavily_search: General web search for tutorials, books, or learning resources.
- robust_web_scrape: Scrape a specific course URL for detailed info (syllabus, price, duration).

WORKFLOW:
1. Analyze the user's profile and learning goals.
2. Use search_courses to find matching courses on major platforms.
3. Optionally use robust_web_scrape to get detailed course info from promising results.
4. Compile verified recommendations with real links.

Your FINAL output MUST be a strictly formatted Markdown document:
# Course Recommendations

## [Course/Resource Name]
* **Provider**: [e.g., Coursera, Udemy, Book]
* **Estimated Cost**: [$]
* **Estimated Duration**: [Time]
* **Why it fits**: [Exact reason based on their profile and goals]
* **Link**: [REAL URL from search results]

CRITICAL: All recommendations must come from REAL search results. Include actual URLs. Never hallucinate links.
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_low_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

tools = [search_courses, tavily_search, robust_web_scrape]
react_agent = create_react_agent(llm, tools)


def course_rec_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("learning")
    memory = MemoryDistiller.load_summary()
    
    sys_content = f"{PROMPT}\n\nCross-Domain Context:\n{memory}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}"
    input_msgs = [SystemMessage(content=sys_content)] + messages
    
    try:
        result = react_agent.invoke({"messages": input_msgs})
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content and not m.tool_calls]
        final_content = ai_messages[-1].content if ai_messages else "Course search completed but no results found."
    except Exception as e:
        print(f"[Course Rec Agent] ReAct execution error: {e}")
        final_content = f"Course recommendation encountered an error: {str(e)}"
    
    artifact_dir = Path(settings.data_dir) / "learning" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"course_recs_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_content)
        
    return {
        "messages": [AIMessage(content=final_content, name="course_rec_agent")],
        "next": "__end__"
    }
