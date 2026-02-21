import json
from pathlib import Path
from typing import Dict, List, Optional
from models.task import Task
from config.settings import settings

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._init_data_dirs()
        self._cancel_stale_tasks()

    def _init_data_dirs(self):
        # Ensure log directories exist
        for group in ["career", "life", "learning"]:
            path = Path(settings.data_dir) / group / "logs"
            path.mkdir(parents=True, exist_ok=True)

    def _cancel_stale_tasks(self):
        # Scan data/*/logs/*.json, if status == "running", set to "cancelled"
        base_path = Path(settings.data_dir)
        for group in ["career", "life", "learning"]:
            log_dir = base_path / group / "logs"
            if log_dir.exists():
                for log_file in log_dir.glob("*.json"):
                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            
                        if data.get("status") == "running":
                            data["status"] = "cancelled"
                            with open(log_file, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=2)
                    except Exception as e:
                        print(f"Error checking stale task {log_file}: {e}")

    def _get_log_path(self, agent_group: str, task_id: str) -> Path:
        return Path(settings.data_dir) / agent_group / "logs" / f"{task_id}.json"

    def _save_task_log(self, task: Task):
        path = self._get_log_path(task.agent_group, task.id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(task.model_dump_json(indent=2))

    def _get_running_task(self, agent_group: str) -> Optional[Task]:
        for t in self.tasks.values():
            if t.agent_group == agent_group and t.status == "running":
                return t
        return None

    def register_task(self, task: Task) -> None:
        """Register a new task and evaluate start condition."""
        if task.status != "pending" and task.status != "running":
            # Start off any new task evaluating cleanly
            task.status = "pending"
            
        self.tasks[task.id] = task
        self._save_task_log(task)
        self._evaluate_queue(task.agent_group)

    def update_task(self, task: Task) -> None:
        """Update task and save log."""
        self.tasks[task.id] = task
        self._save_task_log(task)
        
        # If task just completed/failed/cancelled, check queue
        if task.status in ["completed", "failed", "cancelled"]:
            self._evaluate_queue(task.agent_group)

    def _evaluate_queue(self, agent_group: str):
        """Check if we can transition a pending task to running."""
        running_task = self._get_running_task(agent_group)
        if running_task is not None:
            # Concurrency limit reached for this group
            return

        # Find the oldest pending task
        pending_tasks = [t for t in self.tasks.values() if t.agent_group == agent_group and t.status == "pending"]
        if pending_tasks:
            # Sort by created_at
            pending_tasks.sort(key=lambda t: t.created_at)
            next_task = pending_tasks[0]
            next_task.status = "running"
            self.update_task(next_task)
            # Downstream components will trigger the background execution logic based on this status

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def get_tasks_by_group(self, agent_group: str) -> List[Task]:
        return [t for t in self.tasks.values() if t.agent_group == agent_group]

# Singleton instance exported for application-wide use
task_manager = TaskManager()
