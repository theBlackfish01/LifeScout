from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, AIMessage

from config.settings import settings
from orchestrator.state import AgentState
from context.profile_manager import ProfileManager
from models.user_profile import UserProfile

# Define the conversational system prompt indicating the Onboarding objective
ONBOARDING_SYSTEM_PROMPT = """You are the LifeScouter AI Onboarding Manager.
Your goal is to collect information from the user to build a comprehensive UserProfile.
You need to iteratively ask questions to fill out the following schema:
- Demographics: Age, Occupation, Location (City/Country)
- Current Situation: Describe their current professional/personal standing over a paragraph.
- Goals: Determine their goals across 3 distinct domains: Career, Life, Learning.
- Constraints: Money constraints, Time limitations, Geographic anchors.
- Preferences: specific working styles, communication preferences.

DO NOT ask everything at once. Have a friendly, natural conversation.
Once you believe you have collected ALL information across these categories (or as much as the user is willing to share, but ensure you touch on each area), you should confirm the summary with the user.

CRITICAL: Once the user confirms the profile is accurate, you MUST output the final JSON payload matching the `UserProfile` schema. Do NOT return standard text responses once they confirm.
"""

def save_profile_tool(profile_dict: dict) -> str:
    """Saves the user profile dictionary into the system marking onboarding as complete."""
    try:
        # Construct and validate explicit types via Pydantic model
        profile = UserProfile(**profile_dict)
        profile.onboarding_complete = True
        manager = ProfileManager()
        manager.save(profile)
        return "SUCCESS: Profile saved to disk and onboarding complete."
    except Exception as e:
        return f"ERROR: Invalid profile dictionary format. {str(e)}"

# Define the exact tool binding schema for Gemini
# Define an explicit tool payload schema through typing
from typing import Dict, Any

def save_final_profile(profile_dict: UserProfile) -> str:
    """Saves the completed profile to the database. Call this ONLY after confirming the gathered details with the user.
    """
    return save_profile_tool(profile_dict.model_dump())


# 1. Initialize our LLM instances 
llm = ChatGoogleGenerativeAI(
    model=settings.model_onboarding, # gemini-2.0-flash
    api_key=settings.gemini_api_key if settings.gemini_api_key else None
)

# Bind the tool to the LLM explicitly using the function wrapper 
# We'll use bind_tools, but importantly we will check if the response parses to JSON manually 
# if the tool call fails to natively trigger, since Gemini flash is sometimes stubborn.
llm_with_tools = llm.bind_tools([save_final_profile])


def onboarding_agent_node(state: AgentState) -> dict:
    """
    The graph node for the Onboarding Agent.
    Evaluates standard chat history and responds or executes the tool.
    """
    messages = state.get("messages", [])
    
    # Check if there's no history (or just the initial prompt), inject the system prompt natively
    formatted_messages = []
    
    has_system = any(isinstance(m, SystemMessage) for m in messages)
    if not has_system:
        formatted_messages.append(SystemMessage(content=ONBOARDING_SYSTEM_PROMPT))
        
    formatted_messages.extend(messages)
    
    # 2. Invoke Gemini
    response = llm_with_tools.invoke(formatted_messages)

    # 3. Handle Node return payload
    final_messages = [response]
    next_node = "onboarding_agent" # default loop unless overwritten
    
    # Check for direct Tool Calls
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "save_final_profile":
                result = save_profile_tool(tool_call["args"])
                print(f"[Onboarding Agent] Tool Result: {result}")
                
                if "SUCCESS" in result:
                     # Onboarding is done! 
                     final_msg = AIMessage(content="Your profile has been fully set up! Redirecting...", name="onboarding")
                     final_messages.append(final_msg)
                     next_node = "__end__"
                else:
                     # Error validating schema, ask LLM to fix it
                     tool_msg = AIMessage(content=f"System Error: {result}. Please ask the user to clarify missing fields.", name="onboarding")
                     final_messages.append(tool_msg)
    else:
        # Fallback if Gemini returned raw JSON instead of using the tools native wrapper
        try:
             import json
             import re
             content = response.content
             
             # Locate possible JSON markdown blocks
             json_match = re.search(r'```(?:json)?\n(.*?)\n```', content, re.DOTALL)
             if json_match:
                 json_str = json_match.group(1)
             else:
                 # Fallback to crude bracket extraction if no markdown
                 start = content.find("{")
                 end = content.rfind("}") + 1
                 json_str = content[start:end]

             if json_str:
                  parsed = json.loads(json_str)
                  
                  if "demographics" in parsed or "goals" in parsed:
                       result = save_profile_tool(parsed)
                       print(f"[Onboarding Agent] JSON Fallback Result: {result}")
                       if "SUCCESS" in result:
                            final_msg = AIMessage(content="Your profile has been fully set up! Redirecting...", name="onboarding")
                            final_messages.append(final_msg)
                            next_node = "__end__"
        except Exception as e:
             print(f"[Onboarding Agent] Fallback parse failed: {e}")
             pass
                     
    return {"messages": final_messages, "next": next_node}
