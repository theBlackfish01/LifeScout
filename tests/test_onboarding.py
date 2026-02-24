import os
import json
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from orchestrator import orchestrator_graph, get_checkpoint_config
from context.profile_manager import ProfileManager

def run_tests():
    print("Testing Onboarding & Settings Logic...")
    
    # Ensure a clean slate for the test
    profile_path = Path("data/user_profile.json")
    if profile_path.exists():
        profile_path.unlink()
        
    print("\n--- Testing Onboarding Agent Logic ---")
    config = get_checkpoint_config("onboarding", "test_onboard_v1")
    
    # 1. Trigger Initial System Prompt Response (asking for details)
    initial_state = {
        "messages": [HumanMessage(content="Hi there, I am here to setup my profile.")],
        "active_agent": "onboarding",
        "task_id": "test_setup_1"
    }

    result1 = orchestrator_graph.invoke(initial_state, config=config)
    messages1 = result1.get("messages", [])
    
    # Check that Gemini responded asking for info (it shouldn't have fired the setup tool immediately)
    assert len(messages1) > 1, "Graph didn't route to onboarding branch properly"
    ai_response = messages1[-1].content
    print(f"[Onboarding Intro] Gemini says: {ai_response[:100]}...")
    assert "age" in ai_response.lower() or "goals" in ai_response.lower() or "profile" in ai_response.lower(), "AI didn't ask for profile details."

    # 2. Trigger explicit setup matching the structured JSON format
    # Instead of doing 10 cycles, we feed it a mega-response.
    mega_prompt = """
    My name is Alice. My profile ID should be left blank for the system to generate.
    My age is 35, I am a software engineer living in New York. 
    My current situation is stable, but looking for new challenges.
    My career goal is to become an Engineering Director.
    My life goal is to buy a house in the suburbs.
    My learning goal is to learn Spanish fluently.
    My constraints: I have a budget constraint of $100 a month, a time constraint of 5 hours a week, and a geographic constraint of staying in New York.
    My preferences: I prefer formal communication style and direct bullet points.
    I do not want to share anything else. Please save this exact profile now.
    """
    
    follow_up_state = {
        "messages": [HumanMessage(content=mega_prompt)],
        "active_agent": "onboarding",
    }
    
    result2 = orchestrator_graph.invoke(follow_up_state, config=config)
    messages2 = result2.get("messages", [])
    
    # We should see tool triggers and a physical save.
    print(f"\n[Onboarding Pre-Save Check] Gemini says: {messages2[-1].content}")
    assert "yes" in messages2[-1].content.lower() or "save" in messages2[-1].content.lower() or "look good" in messages2[-1].content.lower() or "correct" in messages2[-1].content.lower(), "AI failed to ask for permission to save the profile."

    # 3. Explicitly confirm the save
    confirm_state = {
        "messages": [
            HumanMessage(content="Yes, that looks perfect. Please save it.")
        ],
        "active_agent": "onboarding"
    }

    result3 = orchestrator_graph.invoke(confirm_state, config=config)
    messages3 = result3.get("messages", [])
    
    print(f"\n[Onboarding Confirmation Save] Gemini says: {messages3[-1].content}")
    assert profile_path.exists(), "Profile was NOT dumped to disk by the setup_tool after confirmation."
    manager = ProfileManager()
    assert manager.load().onboarding_complete is True, "ProfileManager did not register onboarding_complete=True"
    print("Onboarding flow verified.")


    print("\n--- Testing Settings Agent Logic ---")
    config_setting = get_checkpoint_config("settings", "test_settings_v1")
    
    settings_state = {
        "messages": [HumanMessage(content="Update my age to 99 please.")],
        "active_agent": "settings",
        "task_id": "test_settings_1"
    }
    
    result3 = orchestrator_graph.invoke(settings_state, config=config_setting)
    messages3 = result3.get("messages", [])
    
    # 1. It must confirm FIRST before updating
    ai_response_setting = messages3[-1].content
    print(f"\n[Settings Propose] Gemini says: {ai_response_setting}")
    
    # Ensure profile age wasn't instantly modified yet
    current_age = manager.load().age
    assert current_age != 99, "AI executed the tool without confirming first! Budget guard failed."
    assert "?" in ai_response_setting or "confirm" in ai_response_setting.lower() or "correct" in ai_response_setting.lower(), "AI failed to ask for permission to update."
    
    # 2. Assert Confirmation runs the tool
    settings_confirm = {
         "messages": [
             HumanMessage(content="Yes, please go ahead and save that exact change."),
             SystemMessage(content="The user has confirmed. YOU MUST NOW output the JSON payload to update the profile. Do not ask any more questions or return conversational text.")
         ],
         "active_agent": "settings"
    }

    result4 = orchestrator_graph.invoke(settings_confirm, config=config_setting)
    messages4 = result4.get("messages", [])
    
    final_age = manager.load().age
    print(f"\n[Settings Save] Action Finalized.")
    assert final_age == 99, f"Settings tool completely failed to write the update to disk. Age is {final_age}"

    # Clean up
    profile_path.unlink()
    
    print("\nAll Standalone Setup Tests Passed Successfully.")

if __name__ == "__main__":
    run_tests()
