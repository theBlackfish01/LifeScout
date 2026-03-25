"""
Onboarding and Settings agent tests.
All tests require a live LLM (GEMINI_API_KEY).
"""
import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from orchestrator import orchestrator_graph, get_checkpoint_config
from context.profile_manager import ProfileManager


# ---------------------------------------------------------------------------
# Onboarding agent
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_onboarding_agent_asks_for_profile_details(require_gemini_key, tmp_profile_path):
    config = get_checkpoint_config("onboarding", "integ_onboarding_intro")
    state = {
        "messages": [HumanMessage(content="Hi, I want to set up my profile.")],
        "active_agent": "onboarding",
        "task_id": "ob_intro",
    }
    result = orchestrator_graph.invoke(state, config=config)
    messages = result.get("messages", [])
    assert len(messages) > 1

    response_text = messages[-1].content.lower()
    # Agent should be asking for info — age, goals, or profile details
    assert any(kw in response_text for kw in ("age", "goal", "profile", "tell me", "occupation")), (
        f"Expected onboarding intro question, got: {messages[-1].content[:200]}"
    )


@pytest.mark.integration
def test_onboarding_saves_profile_after_confirmation(require_gemini_key, tmp_profile_path):
    """Multi-turn: provide info, then confirm to trigger profile save."""
    config = get_checkpoint_config("onboarding", "integ_onboarding_save")

    # Turn 1: provide profile details
    orchestrator_graph.invoke(
        {
            "messages": [HumanMessage(content="Hi, I want to set up my profile.")],
            "active_agent": "onboarding",
            "task_id": "ob_save",
        },
        config=config,
    )

    # Turn 2: supply full details
    orchestrator_graph.invoke(
        {
            "messages": [HumanMessage(
                content=(
                    "I'm Alice, age 35, Software Engineer in New York. "
                    "Career goal: Engineering Director. Life goal: buy a house. "
                    "Learning goal: learn Spanish. Budget $100/month, 5 hours/week. "
                    "Please save this profile now."
                )
            )],
            "active_agent": "onboarding",
        },
        config=config,
    )

    # Turn 3: confirm
    result = orchestrator_graph.invoke(
        {
            "messages": [HumanMessage(content="Yes, that looks correct. Please save it.")],
            "active_agent": "onboarding",
        },
        config=config,
    )

    assert tmp_profile_path.exists(), "Profile was not written to disk"
    profile = ProfileManager.load()
    assert profile.onboarding_complete is True


# ---------------------------------------------------------------------------
# Settings agent
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_settings_agent_confirms_before_updating(require_gemini_key, tmp_profile_path):
    """Settings agent should ask for confirmation before applying a change."""
    # Seed a profile so the agent has something to work with
    profile = ProfileManager.load()
    profile.age = 30
    profile.onboarding_complete = True
    ProfileManager.save(profile)

    config = get_checkpoint_config("settings", "integ_settings_confirm")
    result = orchestrator_graph.invoke(
        {
            "messages": [HumanMessage(content="Update my age to 99 please.")],
            "active_agent": "settings",
            "task_id": "settings_1",
        },
        config=config,
    )
    messages = result.get("messages", [])
    response_text = messages[-1].content.lower()

    # Age must NOT have changed yet — agent should ask first
    assert ProfileManager.load().age != 99, "Agent updated profile without confirmation"
    assert any(kw in response_text for kw in ("confirm", "correct", "?", "sure")), (
        f"Expected confirmation prompt, got: {messages[-1].content[:200]}"
    )


@pytest.mark.integration
def test_settings_agent_applies_update_after_confirmation(require_gemini_key, tmp_profile_path):
    """Settings agent saves change after explicit user confirmation."""
    profile = ProfileManager.load()
    profile.age = 30
    profile.onboarding_complete = True
    ProfileManager.save(profile)

    config = get_checkpoint_config("settings", "integ_settings_apply")

    # Turn 1: request change
    orchestrator_graph.invoke(
        {
            "messages": [HumanMessage(content="Update my age to 99 please.")],
            "active_agent": "settings",
            "task_id": "settings_apply",
        },
        config=config,
    )

    # Turn 2: confirm with explicit instruction override
    orchestrator_graph.invoke(
        {
            "messages": [
                HumanMessage(content="Yes, please go ahead and save that change."),
                SystemMessage(content=(
                    "The user has confirmed. Output the JSON payload to update the profile. "
                    "Do not ask any more questions."
                )),
            ],
            "active_agent": "settings",
        },
        config=config,
    )

    assert ProfileManager.load().age == 99, "Settings agent did not persist the age update"
