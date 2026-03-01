import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, AIMessage

from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager

SETTINGS_SYSTEM_PROMPT = """You are the LifeScout AI Settings Manager.
You are interacting with the user to manage their `UserProfile`.

Here is their current profile stored in the system:
{current_profile}

Your Goal:
You must determine what the user wants to change (single fields or entire categories). 
1. Acknowledge their requested change.
2. If the user's intent is unclear, ask for clarification.
3. Critically: Before pushing `execute_profile_update`, you MUST verbally confirm the exact changes you are about to make and receive their final "yes" or consent. 
   Additionally, briefly summarize the *impact* of this change. For example: "Changing your constraint from 20 hours to 5 hours will require us to rethink your learning plan. I am going to update your available hours to 5, is that correct?"
4. If they agree to the changes, use the `execute_profile_update` tool passing the ENTIRE updated profile JSON object (not just the delta).
"""

from models.user_profile import UserProfile

def execute_profile_update(updated_profile_dict: UserProfile) -> str:
    """Updates the UserProfile on disk. Submit the complete, updated profile dictionary. Do not submit partial deltas."""
    manager = ProfileManager()
    manager.save(updated_profile_dict)
    return "SUCCESS: User profile updated successfully."

llm = ChatGoogleGenerativeAI(
    model=settings.model_settings,
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

llm_with_tools = llm.bind_tools([execute_profile_update])

def settings_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    
    # 1. Fetch current live profile
    manager = ProfileManager()
    current_profile = manager.load()
    profile_json = current_profile.model_dump_json(indent=2) if current_profile else "{}"
    
    # 2. Inject Dynamic system prompt keeping memory fresh
    sys_prompt = SETTINGS_SYSTEM_PROMPT.format(current_profile=profile_json)
    
    formatted_messages = []
    
    # Update or add system message (Replacing the first message if it's already a system message, else inserting)
    if messages and isinstance(messages[0], SystemMessage):
         formatted_messages.append(SystemMessage(content=sys_prompt))
         formatted_messages.extend(messages[1:])
    else:
         formatted_messages.append(SystemMessage(content=sys_prompt))
         formatted_messages.extend(messages)

    # 3. LLM Invoke
    response = llm_with_tools.invoke(formatted_messages)

    final_messages = [response]
    next_node = "settings_agent"
    
    # 4. Handle Actions
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "execute_profile_update":
                try:
                    from models.user_profile import UserProfile
                    args = tool_call["args"]
                    
                    # Unpack if nested inside updated_profile_dict
                    if "updated_profile_dict" in args:
                         prof_obj = UserProfile(**args["updated_profile_dict"])
                    else:
                         prof_obj = UserProfile(**args)
                    
                    result = execute_profile_update(prof_obj)
                    print(f"[Settings Agent] Tool Result: {result}")
                    
                    if "SUCCESS" in result:
                        # After saving successfully, drop connection to the settings node and finish cycle.
                        success_msg = AIMessage(content="Profile updated successfully!", name="settings")
                        final_messages.append(success_msg)
                        next_node = "__end__"
                    else:
                        error_msg = AIMessage(content=f"System failed to save. Error: {result}", name="settings")
                        final_messages.append(error_msg)
                except Exception as e:
                    error_msg = AIMessage(content=f"System failed to save format. Error: {str(e)}", name="settings")
                    final_messages.append(error_msg)
    else:
        # Fallback if Gemini returned raw JSON instead of using the tools native wrapper
        try:
             import json
             import re
             content = response.content
             
             json_match = re.search(r'```(?:json)?\n(.*?)\n```', content, re.DOTALL)
             if json_match:
                 json_str = json_match.group(1)
             else:
                 start = content.find("{")
                 end = content.rfind("}") + 1
                 json_str = content[start:end]

             if json_str:
                  parsed = json.loads(json_str)
                  from models.user_profile import UserProfile
                  # Unpack if nested inside updated_profile_dict
                  if "updated_profile_dict" in parsed:
                       prof_obj = UserProfile(**parsed["updated_profile_dict"])
                  else:
                       prof_obj = UserProfile(**parsed)
                  
                  result = execute_profile_update(prof_obj)
                  print(f"[Settings Agent] JSON Fallback Result: {result}")
                  if "SUCCESS" in result:
                       success_msg = AIMessage(content="Profile updated successfully!", name="settings")
                       final_messages.append(success_msg)
                       next_node = "__end__"
        except Exception as e:
             print(f"[Settings Agent] Fallback parse failed: {e}")
             pass

    return {"messages": final_messages, "next": next_node}
