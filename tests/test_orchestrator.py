import time
from langchain_core.messages import HumanMessage
from orchestrator import orchestrator_graph, get_checkpoint_config

def run_tests():
    print("Testing Orchestrator Router & Supervisor mechanics...")
    
    # 1. Test Router (Career)
    print("\n--- Testing Career Routing ---")
    config = get_checkpoint_config("career", "test_thread_v2")
    
    initial_state = {
        "messages": [HumanMessage(content="Hello career agent")],
        "active_agent": "career",
        "task_id": "task_career_1"
    }

    # Run the graph
    print("Invoking graph...")
    result1 = orchestrator_graph.invoke(initial_state, config=config)
    messages1 = result1.get("messages", [])
    
    # Career routing should hit: Router -> Supervisor -> Career Agent -> END
    assert len(messages1) > 1, "Graph didn't route to branch properly"
    assert any("[career Sub-Agent]" in m.content for m in messages1), "Did not reach career dummy agent"
    print("Career Routing OK")

    # 2. Test Checkpointing (Restore State)
    print("\n--- Testing State Restoration (Checkpointing) ---")
    # Sending a second message to the exact same thread
    follow_up_state = {
        "messages": [HumanMessage(content="Here is a follow up")],
        "active_agent": "career", 
        # Crucial for checkpoint tests: graph.invoke automatically merges messages!
    }
    result2 = orchestrator_graph.invoke(follow_up_state, config=config)
    messages2 = result2.get("messages", [])
    
    # The returned state should contain ALL messages from result1 AND the new follow-ups
    assert len(messages2) > len(messages1), "State was not restored from SQLite checkpoint!"
    print(f"State Restored OK. Total messages in thread: {len(messages2)}")

    # 3. Test Budget Supervisor Limits
    print("\n--- Testing Extraneous Budget Limits ---")
    config_life = get_checkpoint_config("life", "test_budget_thread_v2")
    
    # Mocking a state where an agent has been running in loops and blowing iterations
    budget_blown_state = {
        "messages": [HumanMessage(content="Help me with life")],
        "active_agent": "life",
        "task_id": "task_life_1",
        "budget_stats": {
            "iterations": 6,  # Over the limit (5)
            "tool_calls": 0,
            "start_time": time.time()
        }
    }
    
    result3 = orchestrator_graph.invoke(budget_blown_state, config=config_life)
    messages3 = result3.get("messages", [])
    stats3 = result3.get("budget_stats", {})
    
    # We expect the state returned to have the budget message. Let's see what got pushed.
    print(f"Messages in budget state: {[m.content for m in messages3]}")
    
    # Supervisor should intercept this BEFORE hitting the life agent
    assert any("[SYSTEM] Budget Exceeded" in m.content for m in messages3), "Supervisor failed to enforce budget limit"
    
    # Check that NO new life_agent messages were appended AFTER the budget check.
    # The initial message was "Help me with life". The second should be the budget exceed message.
    # The life Sub-Agent should not have been called.
    has_sub_agent_run = any("[life Sub-Agent]" in m.content for m in messages3[1:])
    assert not has_sub_agent_run, "Agent executed despite blown budget"
    print("Budget Enforcement OK")
    
    # 4. Standalone Routes
    print("\n--- Testing Standalone Routes ---")
    config_onboard = get_checkpoint_config("onboarding", "test_onboard_v2")
    res_ob = orchestrator_graph.invoke({"messages": [HumanMessage(content="hi")], "active_agent": "onboarding", "task_id": "1"}, config=config_onboard)
    assert any("[Onboarding] Complete." in m.content for m in res_ob.get("messages", [])), "Onboarding route failed"
    print("Standalone Edge OK")

    print("\nAll Orchestrator Tests Passed Successfully.")

if __name__ == "__main__":
    run_tests()
