"""
ArtifactLoader: Injects recent artifacts into agent system prompts,
enabling cross-session context retention (e.g., resume → job search).
"""
import os
from pathlib import Path
from typing import Optional
from config.settings import settings


class ArtifactLoader:
    @staticmethod
    def load_recent(group: str, limit: int = 3, max_chars: int = 4000) -> str:
        """
        Reads the N most recent artifact files from a given agent group
        and returns their contents as a formatted string.

        Args:
            group: Agent group ("career", "life", "learning").
            limit: Max number of files to load.
            max_chars: Max total characters across all files.

        Returns:
            Combined artifact text, or "(no prior artifacts)" if none exist.
        """
        artifact_dir = Path(settings.data_dir) / group / "artifacts"
        if not artifact_dir.exists():
            return "(no prior artifacts)"

        # Get markdown and text artifacts, sorted most recent first
        files = sorted(
            [f for f in artifact_dir.iterdir() if f.suffix in (".md", ".txt") and f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        if not files:
            return "(no prior artifacts)"

        content = []
        total = 0
        for f in files[:limit]:
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue

            remaining = max_chars - total
            if remaining <= 0:
                break
            if len(text) > remaining:
                text = text[:remaining] + "\n[... truncated]"

            content.append(f"--- {f.name} ---\n{text}")
            total += len(text)

        return "\n\n".join(content) if content else "(no prior artifacts)"

    @staticmethod
    def load_specific(group: str, filename: str) -> Optional[str]:
        """Load a specific artifact by filename."""
        path = Path(settings.data_dir) / group / "artifacts" / filename
        if path.exists() and path.is_file():
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                return None
        return None
