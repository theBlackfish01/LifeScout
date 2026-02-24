from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from context.artifact_loader import ArtifactLoader
from tools.search import tavily_search

PROMPT = """You are the LifeScouter LinkedIn Strategy Sub-Agent.
Your job is to generate personal branding recommendations and outreach drafts optimized for LinkedIn.

You have access to tools:
- tavily_search: Search for LinkedIn best practices, industry trends, top-performing profile examples, and trending hashtags in the user's domain.

WORKFLOW:
1. Review the user's profile and recent career artifacts.
2. Use tavily_search to research current LinkedIn trends, optimal headline formats, and industry-specific keywords.
3. Generate high-quality recommendations.

Your FINAL output MUST be a strictly formatted Markdown document:
# LinkedIn Optimization Strategy

## 1. Headline Suggestions
[Provide 3 distinct, keyword-optimized headline options based on their goals and current trends found via search.]

## 2. 'About' Section Rewrite
[Provide a modern, engaging About section incorporating their background, goals, and trending industry keywords.]

## 3. Networking Outreach Templates
[Provide 3 distinct cold-outreach messaging templates tailored to their industry and target roles.]

## 4. Content Strategy
[Suggest 3 post ideas or topics they should write about based on trending industry discussions found via search.]
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

tools = [tavily_search]
react_agent = create_react_agent(llm, tools)


def linkedin_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("career")
    
    sys_content = f"{PROMPT}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}"
    input_msgs = [SystemMessage(content=sys_content)] + messages
    
    try:
        result = react_agent.invoke({"messages": input_msgs})
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content and not m.tool_calls]
        final_content = ai_messages[-1].content if ai_messages else "LinkedIn optimization completed."
    except Exception as e:
        print(f"[LinkedIn Agent] ReAct execution error: {e}")
        final_content = f"LinkedIn optimization encountered an error: {str(e)}"
    
    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"linkedin_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_content)
        
    return {"messages": [AIMessage(content=f"Generated LinkedIn optimization report and saved artifact to {file_path}", name="linkedin_agent")]}
