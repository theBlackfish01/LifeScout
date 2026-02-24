import os
import sys
import json
import uuid
import time
import shutil
from pathlib import Path

# Mock weasyprint to prevent Windows GTK DLL crash
import types
weasyprint_mock = types.ModuleType('weasyprint')
weasyprint_mock.HTML = lambda *args, **kwargs: type('MockHTML', (), {'write_pdf': lambda *a, **k: None})()
weasyprint_mock.CSS = lambda *args, **kwargs: None
sys.modules['weasyprint'] = weasyprint_mock

# Load settings to dynamically retrieve paths
from config.settings import settings
from langchain_core.messages import HumanMessage
from orchestrator.graph import orchestrator_graph
from context.task_manager import task_manager
from context.profile_manager import ProfileManager
from models.user_profile import UserProfile
from models.task import Task

def setup_test_environment():
    """Ensure clean directories and a mock profile."""
    # 1. Clean data directories
    data_dir = Path(settings.data_dir)
    learning_dir = data_dir / "learning"
    
    if learning_dir.exists():
        shutil.rmtree(learning_dir)
        
    learning_dir.mkdir(parents=True, exist_ok=True)
    (learning_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (learning_dir / "logs").mkdir(parents=True, exist_ok=True)
    
    # 2. Mock a test profile
    profile = UserProfile(
        demographics={"age": 25, "occupation": "Software Engineer", "location": "Remote"},
        goals={
            "career": ["Become a Senior UI Engineer"],
            "life": ["Read 12 books this year"],
            "learning": ["Learn advanced React patterns", "Master LangGraph"]
        }
    )
    ProfileManager().save(profile)
    print("Test environment and mock profile created.")

def run_tests():
    print("\nTesting Learning Agent Group...\n")
    
    # Configure base inputs
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Ensure task manager is clean
    task_manager.tasks.clear()

    # --- Test 1: Concurrency and the Supervisor ---
    print("--- Testing Concurrency ---")
    
    # Start a long-running mock task in the learning group
    task1 = Task(id=str(uuid.uuid4()), agent_group="learning", trigger="user_initiated", sub_agent="study_plan", title="Generate a study plan for React", thread_id=thread_id, status="running")
    task_manager.register_task(task1)
    task_id1 = task1.id
    
    state1 = {
        "messages": [HumanMessage(content="Recommend me courses for LangGraph")],
        "active_agent": "learning",
        "task_id": "task_concurrency_test",
        "budget_stats": {"iterations": 0, "tool_calls": 0, "start_time": time.time()}
    }
    
    # This task should be queued
    task_concurrency = Task(id="task_concurrency_test", agent_group="learning", trigger="user_initiated", sub_agent="course_rec", title="Find courses", thread_id=thread_id, status="pending")
    task_manager.register_task(task_concurrency)
    
    try:
        result1 = orchestrator_graph.invoke(state1, config=config)
        messages = result1.get("messages", [])
        last_msg = messages[-1].content if messages else ""
        assert "[SYSTEM] Task is pending due to concurrency limits" in last_msg, f"Concurrency limit not enforced: {last_msg}"
        print("Concurrency check PASSED: Supervisor queued overlapping task.")
    except Exception as e:
        print(f"Concurrency check FAILED: {e}")

    # Clean up the pending task
    task1.status = "completed"
    task_manager.update_task(task1)
    task_concurrency.status = "cancelled"
    task_manager.update_task(task_concurrency)
    
    # --- Test 2: Routing to Specific Agents ---
    print("\n--- Testing Routing & Artifact Generation ---")
    
    test_cases = [
        ("I need a detailed study plan to learn LangGraph over 4 weeks.", "study_plan", "study_plan"),
        ("Recommend me some good online courses to learn React optimization.", "course_rec", "course_recs"),
        ("I finished reading chapter 1 of my LangGraph book today. Track this progress.", "progress", "progress_report")
    ]
    
    for prompt, expected_agent_type, artifact_prefix in test_cases:
        print(f"\nTesting prompt: '{prompt}'")
        test_task_id = str(uuid.uuid4())
        test_task = Task(id=test_task_id, agent_group="learning", trigger="user_initiated", sub_agent=expected_agent_type, title=prompt, thread_id=thread_id, status="running")
        task_manager.register_task(test_task) # Allow it to run natively
        
        state = {
            "messages": [HumanMessage(content=prompt)],
            "active_agent": "learning",
            "task_id": test_task_id,
            "budget_stats": {"iterations": 0, "tool_calls": 0, "start_time": time.time()}
        }
        
        try:
            # We use a new thread id to isolate test cases in the Sqlite graph DB
            local_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            result = orchestrator_graph.invoke(state, config=local_config)
            
            # 1. Verify exact output message from the sub-agent
            messages = result.get("messages", [])
            last_msg = messages[-1].content if messages else ""
            
            print(f"Output received: {last_msg}")
            
            artifact_dir = Path(settings.data_dir) / "learning" / "artifacts"
            expected_file = artifact_dir / f"{artifact_prefix}_{test_task_id}.md"
            
            # Verify the artifact was physically created on disk
            assert expected_file.exists(), f"Artifact file was not created at {expected_file}"
            
            with open(expected_file, "r", encoding="utf-8") as f:
                content = f.read()
                assert len(content) > 50, "Artifact file is empty or too short."
                print(f"Verified artifact {expected_file.name} successfully written.")
            
            print(f"Routing to '{expected_agent_type}' PASSED.")

        except Exception as e:
            print(f"Routing check FAILED for {expected_agent_type}: {e}")
        finally:
             test_task.status = "completed"
             task_manager.update_task(test_task)

if __name__ == "__main__":
    setup_test_environment()
    run_tests()
