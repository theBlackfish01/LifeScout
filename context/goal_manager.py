import json
from pathlib import Path
from typing import List, Optional
from models.goal import Goal
from config.settings import settings

class GoalManager:
    @staticmethod
    def _get_path(agent_group: str) -> Path:
        return Path(settings.data_dir) / agent_group / "goals" / "goals.json"

    @staticmethod
    def _load_all(agent_group: str) -> List[Goal]:
        path = GoalManager._get_path(agent_group)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Goal(**item) for item in data]
        except Exception as e:
            print(f"Error loading goals for {agent_group}: {e}")
            return []

    @staticmethod
    def _save_all(agent_group: str, goals: List[Goal]) -> None:
        path = GoalManager._get_path(agent_group)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps([json.loads(g.model_dump_json()) for g in goals], indent=2))

    @staticmethod
    def list_goals(agent_group: str) -> List[Goal]:
        return GoalManager._load_all(agent_group)

    @staticmethod
    def get_goal(agent_group: str, goal_id: str) -> Optional[Goal]:
        goals = GoalManager._load_all(agent_group)
        for g in goals:
            if g.id == goal_id:
                return g
        return None

    @staticmethod
    def create(goal: Goal) -> None:
        goals = GoalManager._load_all(goal.agent_group)
        goals.append(goal)
        GoalManager._save_all(goal.agent_group, goals)

    @staticmethod
    def update(goal: Goal) -> None:
        goals = GoalManager._load_all(goal.agent_group)
        for i, g in enumerate(goals):
            if g.id == goal.id:
                goals[i] = goal
                GoalManager._save_all(goal.agent_group, goals)
                return
        # If not found, create it
        GoalManager.create(goal)

    @staticmethod
    def delete(agent_group: str, goal_id: str) -> None:
        goals = GoalManager._load_all(agent_group)
        goals = [g for g in goals if g.id != goal_id]
        GoalManager._save_all(agent_group, goals)
