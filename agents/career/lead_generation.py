from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader
from tools.search import tavily_search, search_jobs
from tools.web_scraper import robust_web_scrape

PROMPT = """You are the LifeScouter Career Lead Generation Sub-Agent.
Your job is to proactively find high-quality career opportunities and evaluate leads against the user profile.

You have access to tools:
- search_jobs: Search job boards (LinkedIn, Indeed, Glassdoor) for postings.
- tavily_search: General web search for companies, events, certifications.
- robust_web_scrape: Scrape a specific URL for company info or event details.

WORKFLOW:
1. Analyze the user's profile, skills, and career goals.
2. Use search_jobs to find matching opportunities.
3. Use tavily_search to research target companies, networking events, and certifications.
4. Optionally use robust_web_scrape to deep-dive into company career pages.
5. Compile everything into a structured report.

Your FINAL output MUST be a strictly formatted Markdown document:
# Lead Generation Report

## 1. Top Target Companies
[List companies found via search that match their profile. Include WHY and a link.]

## 2. Active Job Postings
[List specific real postings found. Include URLs.]

## 3. Networking Opportunities
[Events, conferences, or communities found via search.]

## 4. High-ROI Certifications/Resources
[Non-obvious certifications or resources that would make them a top candidate.]

CRITICAL: All leads must come from REAL search results, not hallucinated data. Include actual URLs.
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

tools = [search_jobs, tavily_search, robust_web_scrape]
react_agent = create_react_agent(llm, tools)


def lead_generation_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("career")
    
    sys_content = f"{PROMPT}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}"
    input_msgs = [SystemMessage(content=sys_content)] + messages
    
    try:
        result = react_agent.invoke({"messages": input_msgs})
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content and not m.tool_calls]
        final_content = ai_messages[-1].content if ai_messages else "Lead generation completed but no results found."
    except Exception as e:
        print(f"[Lead Gen Agent] ReAct execution error: {e}")
        final_content = f"Lead generation encountered an error: {str(e)}"
    
    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"lead_batch_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_content)
        
    return {"messages": [AIMessage(content=final_content, name="lead_generation_agent")]}
