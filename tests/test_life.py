import os
import shutil
from pathlib import Path
from langchain_core.messages import HumanMessage
from orchestrator.graph import orchestrator_graph
from models.task import Task
from context.task_manager import task_manager
from config.settings import settings

def run_tests():
    print("Testing Life Agent Group...")
    
    # Clean previous artifacts if any
    artifact_dir = Path(settings.data_dir) / "life" / "artifacts"
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
        
    # 1. Test Concurrency
    print("\n--- Testing Concurrency ---")
    t1 = Task(trigger="user_initiated", agent_group="life", sub_agent="health", title="Health 1", thread_id="t1")
    t2 = Task(trigger="user_initiated", agent_group="life", sub_agent="health", title="Health 2", thread_id="t2")
    
    task_manager.register_task(t1)
    task_manager.register_task(t2)
    
    state2 = {
        "messages": [HumanMessage(content="Give me a gym routine")],
        "active_agent": "life",
        "task_id": t2.id
    }
    config2 = {"configurable": {"thread_id": "life_t2"}}
    result2 = orchestrator_graph.invoke(state2, config=config2)
    
    messages = result2.get("messages", [])
    concurrency_met = False
    for msg in messages:
        if hasattr(msg, "name") and msg.name == "life_supervisor":
            if "pending due to concurrency limits" in msg.content:
                concurrency_met = True
                print(f"Concurrent submission result: {msg.content}")
                
    assert concurrency_met, "Concurrency guard failed. Second task was not queued."
    
    # Finish T1 manually so T2 can run
    t1.status = "completed"
    task_manager.update_task(t1)
    
    # 2. Test Routing and Artifact Generation
    print("\n--- Testing Routing & Artifact Generation ---")
    state_valid = {
        "messages": [HumanMessage(content="Build me a marathon training health routine.")],
        "active_agent": "life",
        "task_id": t2.id
    }
    
    result_valid = orchestrator_graph.invoke(state_valid, config=config2)
    final_messages = result_valid.get("messages", [])
    
    found_health = False
    for msg in final_messages:
        if hasattr(msg, "name") and msg.name == "health_agent":
            print(f"Agent response: {msg.content}")
            found_health = True
            
    assert found_health, "Life supervisor failed to route to health_agent natively."
    
    # Assert artifact exists
    assert artifact_dir.exists(), "Artifacts directory not created."
    files = list(artifact_dir.glob(f"health_{t2.id}.md"))
    assert len(files) == 1, "Health plan artifact file was not serialized."
    print("Routing and Artifacts verified.")

    # 3. Test Therapy Disclaimer 
    print("\n--- Testing Therapy Disclaimer Safety Requirement ---")
    state_therapy = {
         "messages": [HumanMessage(content="I am feeling extremely stressed from work, can you give me some journaling tips?")],
         "active_agent": "life",
         "task_id": t2.id
    }
    
    result_therapy = orchestrator_graph.invoke(state_therapy, config=config2)
    therapy_messages = result_therapy.get("messages", [])
    
    disclaimer_found = False
    for msg in therapy_messages:
         if hasattr(msg, "name") and msg.name == "therapy_agent":
              print(f"Therapy Agent Response:\n{msg.content[:150]}...\n")
              if "I am not a professional therapist" in msg.content:
                  disclaimer_found = True
                  
    assert disclaimer_found, "CRITICAL ERROR: Therapy Sub-Agent failed to prepend the mandatory safety disclaimer!"
    print("Therapy Disclaimer Verified.")

    print("\nAll Life Agent Validations Passed Successfully.")

if __name__ == "__main__":
    run_tests()
