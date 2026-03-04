import json
import os
from pathlib import Path
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from config.settings import settings


class DistillationResult(BaseModel):
    career_insights: list[str] = Field(default_factory=list, description="Career-related facts, goals, skills, or constraints.")
    life_insights: list[str] = Field(default_factory=list, description="Life, health, habits, or personal goals.")
    learning_insights: list[str] = Field(default_factory=list, description="Learning targets, courses, or study plans.")
    cross_domain_goals: list[str] = Field(default_factory=list, description="Overaching goals that span multiple domains.")
    action_items: list[str] = Field(default_factory=list, description="Specific next steps the user or agent agreed on.")


class MemoryDistiller:
    STORE_PATH = Path(settings.data_dir) / "memory" / "context_store.json"
    MAX_ITEMS_PER_LIST = 15

    @staticmethod
    def _get_llm():
        return ChatGoogleGenerativeAI(
            model=settings.model_supervisors,
            api_key=settings.gemini_api_key if settings.gemini_api_key else None
        )

    @staticmethod
    def _read_store() -> dict:
        if not MemoryDistiller.STORE_PATH.exists():
            return {
                "career_insights": [],
                "life_insights": [],
                "learning_insights": [],
                "cross_domain_goals": [],
                "action_items": []
            }
        try:
            with open(MemoryDistiller.STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "career_insights": [],
                "life_insights": [],
                "learning_insights": [],
                "cross_domain_goals": [],
                "action_items": []
            }

    @staticmethod
    def _write_store(data: dict):
        MemoryDistiller.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MemoryDistiller.STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def distill(messages: list[BaseMessage], agent_group: str) -> None:
        """
        After each conversation, extract up to 5 bullet points of NEW facts
        and merge them into the persistent store.
        """
        if not messages:
            return

        # Simple heuristic: only distill if there was at least one human and one AI message recently
        recent_msgs = messages[-10:] # grab context from the recent tail
        
        # Don't distill if it's just a single greeting. 
        if len(recent_msgs) < 2:
            return

        # Format transcript
        transcript = []
        for m in recent_msgs:
            role = "User" if isinstance(m, HumanMessage) else "Agent"
            transcript.append(f"{role}: {m.content}")
        
        transcript_str = "\n".join(transcript)

        prompt = f"""You are a Memory Distillation system.
Your goal is to extract new, highly relevant facts from this recent conversation transcript and categorize them.
Focus on:
1. Concrete decisions or goals the user expressed.
2. Skills identified, gaps found, or constraints mentioned.
3. Specific action items agreed upon.

Do NOT simply summarize the conversation. Extract durable FACTS that should be remembered next session.
Keep bullet points very concise (under 15 words). Extract a maximum of 5 bullet points total across all categories.

Transcript:
{transcript_str}
"""
        
        try:
            llm = MemoryDistiller._get_llm()
            llm_structured = llm.with_structured_output(DistillationResult)
            
            result: DistillationResult = llm_structured.invoke([SystemMessage(content=prompt)])
            if not result:
                return
            
            store = MemoryDistiller._read_store()
            
            # Merge and cap lists
            def merge_list(key, new_items):
                existing = store.get(key, [])
                for item in new_items:
                    if item and item not in existing:
                        existing.append(item)
                # Keep only newest elements
                store[key] = existing[-MemoryDistiller.MAX_ITEMS_PER_LIST:]

            merge_list("career_insights", result.career_insights)
            merge_list("life_insights", result.life_insights)
            merge_list("learning_insights", result.learning_insights)
            merge_list("cross_domain_goals", result.cross_domain_goals)
            merge_list("action_items", result.action_items)
            
            MemoryDistiller._write_store(store)
            print(f"[MemoryDistiller] Successfully extracted {sum(len(getattr(result, k)) for k in result.model_fields)} facts.")
        except Exception as e:
            print(f"[MemoryDistiller] Distillation failed: {e}")

    @staticmethod
    def load_summary() -> str:
        """Returns all cross-domain context as a concise string (~300 tokens max)."""
        store = MemoryDistiller._read_store()
        
        lines = []
        for key, title in [
            ("career_insights", "Career"),
            ("life_insights", "Life"),
            ("learning_insights", "Learning"),
            ("cross_domain_goals", "Cross-Domain Goals"),
            ("action_items", "Action Items")
        ]:
            items = store.get(key, [])
            if items:
                lines.append(f"**{title}:**")
                for item in items:
                    lines.append(f"- {item}")
        
        if not lines:
            return "(No persistent memory facts extracted yet.)"
            
        return "\n".join(lines)
