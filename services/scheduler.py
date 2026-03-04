from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from api.routes.notifications import create_notification
from context.memory_distiller import MemoryDistiller

class ProactiveScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
    def start(self):
        # Schedule the daily career scan
        self.scheduler.add_job(
            self.daily_career_scan,
            'interval',
            hours=24,
            next_run_time=datetime.now(), # Run immediately on startup once for demo
            id='daily_career_scan',
            replace_existing=True
        )
        
        # Schedule the daily habit nudge
        self.scheduler.add_job(
            self.daily_habit_nudge,
            'interval',
            hours=24,
            id='daily_habit_nudge',
            replace_existing=True
        )
        
        self.scheduler.start()
        print("[Scheduler] Started background jobs.")
        
    def shutdown(self):
        self.scheduler.shutdown()
        print("[Scheduler] Shutdown complete.")

    async def daily_career_scan(self):
        """Simulates scanning for career opportunities based on memory."""
        print("[Scheduler] Running daily_career_scan...")
        try:
            # Check if user has career goals
            memory = MemoryDistiller.load_summary()
            if "career" in memory.lower() or "job" in memory.lower():
                # In a real app, this would trigger the actual LangGraph job_search_agent.
                # For Sprint 8, we simply generate a notification to prove the pipeline works.
                create_notification(
                    title="New Job Match Found",
                    message="I found 2 new remote AI opportunities matching your extracted resume skills from last week's search.",
                    notif_type="career"
                )
        except Exception as e:
            print(f"[Scheduler] Error in daily_career_scan: {e}")

    async def daily_habit_nudge(self):
        """Simulates encouraging the user based on Life goals."""
        print("[Scheduler] Running daily_habit_nudge...")
        try:
            memory = MemoryDistiller.load_summary()
            if "habit" in memory.lower() or "health" in memory.lower() or "goal" in memory.lower():
                create_notification(
                    title="Habit Check-in",
                    message="Don't forget to review your weekly health goals. You're doing great!",
                    notif_type="life"
                )
        except Exception as e:
            print(f"[Scheduler] Error in daily_habit_nudge: {e}")

# Global instance
scheduler_service = ProactiveScheduler()
