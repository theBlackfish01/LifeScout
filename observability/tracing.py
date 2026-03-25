"""
LangSmith tracing configuration.

LangChain automatically traces every LLM call, chain invocation, and tool
execution when the LANGCHAIN_TRACING_V2 environment variable is set.  This
module translates the LifeScouter settings into those environment variables at
startup so no per-file changes are needed.
"""
import os


def configure_tracing() -> bool:
    """
    Set LangChain tracing env vars from application settings.

    Call once at server startup (before any LLM is instantiated).
    Returns True if tracing was enabled, False if skipped.
    """
    from config.settings import settings

    if not settings.langsmith_api_key:
        print("[Tracing] LANGSMITH_API_KEY not set — tracing disabled.")
        return False

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)

    print(f"[Tracing] LangSmith enabled — project={settings.langsmith_project}")
    return True
