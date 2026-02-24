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

PROMPT = """You are the LifeScouter Job Search Strategy Sub-Agent.
Your job is to formulate a targeted job search approach and find REAL job postings matching the user's profile.

You have access to tools:
- search_jobs: Search job boards (LinkedIn, Indeed, Glassdoor) for postings matching a query and location.
- tavily_search: General web search for any information.
- robust_web_scrape: Scrape a specific URL for detailed content.

WORKFLOW:
1. Analyze the user's profile and recent artifacts (e.g., resume) to understand their target roles and skills.
2. Use search_jobs to find REAL postings matching their profile and geographic constraints.
3. Optionally use robust_web_scrape to get more details from a promising job posting URL.
4. Compile your findings into a structured report.

Your FINAL output MUST be a strictly formatted Markdown document including:
| Target Role / Job Title | Company | Location | Why It's a Fit | Link | Next Action Step |
|-------------------------|---------|----------|----------------|------|------------------|
| ... | ... | ... | ... | ... | ... |

CRITICAL: All recommendations must be based on REAL search results, not hallucinated. Include actual URLs.
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

# Tools available to this agent
tools = [search_jobs, tavily_search, robust_web_scrape]

# Build the ReAct agent (autonomous reason-act-observe loop)
react_agent = create_react_agent(llm, tools)


def job_search_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("career")
    
    sys_content = f"{PROMPT}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}"
    
    # Run the ReAct agent with system context + conversation messages
    input_msgs = [SystemMessage(content=sys_content)] + messages
    
    try:
        result = react_agent.invoke({"messages": input_msgs})
        # Extract the final AI response
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content and not m.tool_calls]
        final_content = ai_messages[-1].content if ai_messages else "Job search completed but no results were found."
    except Exception as e:
        print(f"[Job Search Agent] ReAct execution error: {e}")
        final_content = f"Job search encountered an error: {str(e)}"
    
    # Save artifact
    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"job_search_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_content)
        
    return {"messages": [AIMessage(content=final_content, name="job_search_agent")]}
