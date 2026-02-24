import os
from models.user_profile import UserProfile
from models.task import Task
from context.profile_manager import ProfileManager
from context.task_manager import task_manager, TaskManager

def run_tests():
    # 1. Test Profile Manager
    print("Testing ProfileManager...")
    p = ProfileManager.load()
    print("Loaded profile id:", p.id)
    p.name = "Test User"
    ProfileManager.save(p)
    p2 = ProfileManager.load()
    assert p2.name == "Test User", "Profile save/load failed"
    print("ProfileManager OK")

    # 2. Test Task Manager Concurrency
    print("Testing TaskManager Concurrency...")
    t1 = Task(trigger="user_initiated", agent_group="career", sub_agent="resume", title="Resume 1", thread_id="test_1")
    t2 = Task(trigger="user_initiated", agent_group="career", sub_agent="resume", title="Resume 2", thread_id="test_2")
    
    task_manager.register_task(t1)
    task_manager.register_task(t2)
    
    # After register, t1 should be running, t2 should be pending
    assert task_manager.get_task(t1.id).status == "running", "t1 should be running"
    assert task_manager.get_task(t2.id).status == "pending", "t2 should be pending due to concurrency limit"
    print("Concurrency initial queue OK")

    # Finish t1
    t1.status = "completed"
    task_manager.update_task(t1)

    # Now t2 should be auto-started and set to running
    assert task_manager.get_task(t2.id).status == "running", "t2 should be running now"
    print("Concurrency queue auto-start OK")

    print("Checking stale tasks on init...")
    # Restart task manager artificially
    new_task_manager = TaskManager()
    
    # t2 should be found in logs with 'running', and will be updated to 'cancelled'
    with open(f"data/career/logs/{t2.id}.json", "r") as f:
        t2_json = f.read()
        assert '"status": "cancelled"' in t2_json, "Stale task should have been cancelled"
    print("Stale task cancellation OK")
    print("All tests passed.")

if __name__ == "__main__":
    run_tests()
