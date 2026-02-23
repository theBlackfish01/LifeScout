from pathlib import Path
from langchain_core.messages import SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from tools.search import SearchTool

PROMPT = """You are the LifeScouter Learning Course Recommendation Sub-Agent.
Your job is to recommend specific online courses, textbooks, tutorials, or educational resources based on the user's Profile goals.
You have access to a web search tool to find up-to-date links and course information.

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

# Bind the search tool
agent_executor = llm.bind_tools([SearchTool.search])

def course_rec_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    profile_json = profile.model_dump_json(indent=2) if profile else "{}"
    
    sys_msg = SystemMessage(content=f"{PROMPT}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages
    
    response = agent_executor.invoke(formatted)
    
    # If the LLM decided to use a tool, we need to handle it. For this simplified implementation,
    # we'll assume a single pass where we either get a direct answer or it hallucinates a tool call format.
    # In a real LangGraph setup, tool calls would route to a ToolNode. To keep the mock simple and robust
    # like the others, we'll force it to answer directly if it tries to use a tool without a ToolNode loop,
    # or we just take its direct text response.
    
    # If it returns tool calls, we execute them manually here for simplicity in this agent.
    if hasattr(response, 'tool_calls') and response.tool_calls:
         tool_responses = []
         for tool_call in response.tool_calls:
             if tool_call['name'] == 'SearchTool':
                 query = tool_call['args'].get('query', '')
                 print(f"[Course Rec] Searching for: {query}")
                 try:
                     search_result = SearchTool.search.invoke({"query": query})
                     tool_responses.append(f"Search Results for '{query}':\n{search_result}")
                 except Exception as e:
                     tool_responses.append(f"Search failed for '{query}': {e}")
         
         # Re-prompt with search results
         follow_up_msg = AIMessage(content="I need to use my search results to formulate the final recommendations.")
         result_msg = SystemMessage(content="\n\n".join(tool_responses))
         final_response = llm.invoke(formatted + [response, result_msg])
         content = final_response.content
    else:
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
