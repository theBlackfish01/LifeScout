import os
import shutil
from pathlib import Path
from langchain_core.messages import HumanMessage
from orchestrator.graph import orchestrator_graph
from models.task import Task
from context.task_manager import task_manager

def run_tests():
    print("Testing Career Agent Group...")
    
    # Clean previous artifacts if any
    artifact_dir = Path("data/career/artifacts")
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
        
    # 1. Test Concurrency
    print("\n--- Testing Concurrency ---")
    t1 = Task(trigger="user_initiated", agent_group="career", sub_agent="resume", title="Resume 1", thread_id="t1")
    t2 = Task(trigger="user_initiated", agent_group="career", sub_agent="resume", title="Resume 2", thread_id="t2")
    
    task_manager.register_task(t1)
    task_manager.register_task(t2)
    
    state2 = {
        "messages": [HumanMessage(content="Rewrite my resume")],
        "active_agent": "career",
        "task_id": t2.id
    }
    config2 = {"configurable": {"thread_id": "t2"}}
    result2 = orchestrator_graph.invoke(state2, config=config2)
    
    msg2 = result2.get("messages", [])[-1].content
    print(f"Concurrent submission result: {msg2}")
    assert "pending due to concurrency limits" in msg2, "Concurrency guard failed. Second task was not queued."
    
    # Finish T1 manually so T2 can run
    t1.status = "completed"
    task_manager.update_task(t1)
    
    # 2. Test Routing and Artifact Generation
    print("\n--- Testing Routing & Artifact Generation ---")
    state_valid = {
        "messages": [HumanMessage(content="Rewrite my resume tailored for an Engineering Manager position.")],
        "active_agent": "career",
        "task_id": t2.id
    }
    
    result_valid = orchestrator_graph.invoke(state_valid, config=config2)
    final_messages = result_valid.get("messages", [])
    
    found_resume = False
    for msg in final_messages:
        if hasattr(msg, "name") and msg.name == "resume_agent":
            print(f"Agent response: {msg.content}")
            found_resume = True
            
    assert found_resume, "Career supervisor failed to route to resume_agent natively."
    
    # Assert artifact exists
    assert artifact_dir.exists(), "Artifacts directory not created."
    files = list(artifact_dir.glob(f"resume_{t2.id}.md"))
    assert len(files) == 1, "Resume artifact file was not serialized."
    print("Routing and Artifacts verified.")

    # 3. Test Budget Guard (Mock iteration loop)
    print("\n--- Testing Career Budget Guard ---")
    state_budget = {
        "messages": [HumanMessage(content="Hello career agent")],
        "active_agent": "career",
        "budget_stats": {"iterations": 5, "tool_calls": 0, "start_time": 0.0}
    }
    
    result_budget = orchestrator_graph.invoke(state_budget, config={"configurable": {"thread_id": "budget_test"}})
    msg_budget = result_budget.get("messages", [])[-1].content
    print(f"Budget test result: {msg_budget}")
    assert "Budget Exceeded" in msg_budget, "Supervisor failed to respect strict iteration budget constraints."
    
    print("\nAll Career Agent Validations Passed Successfully.")

if __name__ == "__main__":
    run_tests()
