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

PROMPT = """You are the LifeScout Interview Prep Coach Sub-Agent.
You are tough, analytical, but highly constructive. Your job is to simulate interview scenarios, generate specific Q&A, and identify skill gaps.

You have access to tools:
- tavily_search: Search for real interview questions from Glassdoor, Blind, or company-specific forums. Also useful for researching company culture and recent news.

WORKFLOW:
1. Review the user's profile and any recent career artifacts (resume, job search results).
2. Use tavily_search to find REAL interview questions for their target role/company.
3. Research the company's recent news, culture, and values if a specific company is mentioned.
4. Compile everything into a structured prep report.

Your FINAL output MUST be a strictly formatted Markdown document:
# Interview Preparation Report

## 1. Behavioral Questions & STAR Mapping
[List 3-5 behavioral questions sourced from real interviews. Provide STAR framework answers tailored to their experience.]

## 2. Technical / Domain Questions
[List specific technical questions found via search for their target role.]

## 3. Company Research
[Key facts about the target company found via search: recent news, culture, values.]

## 4. Identified Gap Areas
[Based on their profile vs. target role, list areas they should study.]
"""

llm = ChatGoogleGenerativeAI(
    model=settings.model_high_complexity,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

tools = [tavily_search]
react_agent = create_react_agent(llm, tools)


def interview_prep_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    artifacts = ArtifactLoader.load_recent("career")
    memory = MemoryDistiller.load_summary()
    
    sys_content = f"{PROMPT}\n\nCross-Domain Context:\n{memory}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}"
    input_msgs = [SystemMessage(content=sys_content)] + messages
    
    try:
        result = react_agent.invoke({"messages": input_msgs})
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content and not m.tool_calls]
        final_content = ai_messages[-1].content if ai_messages else "Interview prep completed."
    except Exception as e:
        print(f"[Interview Prep Agent] ReAct execution error: {e}")
        final_content = f"Interview prep encountered an error: {str(e)}"
    
    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"interview_prep_{task_id}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_content)
        
    return {"messages": [AIMessage(content=f"Generated Interview Prep report and saved artifact to {file_path}", name="interview_prep_agent")]}
