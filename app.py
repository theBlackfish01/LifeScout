import asyncio
import uuid
import sys
import types

# Mock weasyprint natively bypassing Windows GTK DLL crashes for development
weasyprint_mock = types.ModuleType('weasyprint')
weasyprint_mock.HTML = lambda *args, **kwargs: type('MockHTML', (), {'write_pdf': lambda *a, **k: None})()
weasyprint_mock.CSS = lambda *args, **kwargs: None
sys.modules['weasyprint'] = weasyprint_mock

import chainlit as cl
from langchain_core.messages import HumanMessage, AIMessage

from orchestrator.graph import orchestrator_graph
from context.profile_manager import ProfileManager
from context.task_manager import task_manager
from config.settings import settings
from models.task import Task
import time
import os
from pathlib import Path

@cl.set_chat_profiles
async def chat_profile():
    return [
        cl.ChatProfile(
            name="Career Agent",
            markdown_description="Optimize resumes, prep for interviews, search jobs.",
            icon="https://cdn-icons-png.flaticon.com/512/3281/3281289.png",
        ),
        cl.ChatProfile(
            name="Life Agent",
            markdown_description="Set goals, track habits, get mental & physical health plans.",
            icon="https://cdn-icons-png.flaticon.com/512/2966/2966327.png",
        ),
        cl.ChatProfile(
            name="Learning Agent",
            markdown_description="Build study schedules, track progress, recommend courses.",
            icon="https://cdn-icons-png.flaticon.com/512/2436/2436636.png",
        ),
        cl.ChatProfile(
            name="Settings",
            markdown_description="Manage your global user profile context manually.",
            icon="https://cdn-icons-png.flaticon.com/512/3524/3524659.png",
        ),
    ]

@cl.on_chat_start
async def on_chat_start():
    profile_name = cl.user_session.get("chat_profile")
    if not profile_name:
        profile_name = "Career Agent" # Default fallback
        cl.user_session.set("chat_profile", profile_name)
    
    # 1. Start background poll checking task completions natively 
    cl.user_session.set("notified_tasks", set())
    cl.run_sync(poll_tasks())
    
    # Simple mapping logic for group constants
    active_agent = "career"
    if "life" in profile_name.lower(): active_agent = "life"
    elif "learning" in profile_name.lower(): active_agent = "learning"
    elif "settings" in profile_name.lower(): active_agent = "settings"
    
    # Store dynamic thread identifier uniquely locking chat states
    cl.user_session.set("thread_id", str(uuid.uuid4()))
    cl.user_session.set("active_agent", active_agent)

    # 2. Onboarding Gate
    profile_mgr = ProfileManager()
    profile = profile_mgr.load()
    if not profile.onboarding_complete:
         # Hard-override to Onboarding Agent if profile setup is missing
         cl.user_session.set("active_agent", "onboarding")
         await cl.Message(content="Welcome to Life Scouter! I noticed your profile isn't setup. Let's get began right now. What's your current situation like?").send()
    else:
         await cl.Message(content=f"Welcome back to your **{profile_name}** workspace! How can I assist you today?").send()

async def poll_tasks():
    """Background polling loop injecting notifications per session."""
    while True:
        notified = cl.user_session.get("notified_tasks", set())
        if notified is None:
             break # Session terminated
             
        for task_id, task in task_manager.tasks.items():
            if task.status == "completed" and task_id not in notified:
                notified.add(task_id)
                # Ensure we push notifications to the active Chainlit context implicitly
                cl.user_session.set("notified_tasks", notified)
                
                # We use simple string concatenation as a banner representation natively
                banner = f"✅ **Task Completed in Background**: {task.title}\n"
                if task.result.summary:
                     banner += f"\n*Result Summary*: {task.result.summary}"
                     
                await cl.Message(content=banner).send()
        
        await asyncio.sleep(5)  # Poll every 5 seconds

@cl.action_callback("approve_plan")
async def on_action_approve_plan(action: cl.Action):
    """
    Receives an action from the UI representing a Plan Approval.
    Creates an asynchronous Task for the Orchestrator loop natively.
    """
    await cl.Message(content=f"Submitting '{action.value}' into background execution...").send()
    
    active_agent = cl.user_session.get("active_agent", "career")
    
    # Register the native physical Task model triggering async pipelines internally
    new_task = Task(
        agent_group=active_agent,
        trigger="user_initiated",
        sub_agent="generic_workflow", # Fallback, ideally parsed dynamically
        title=f"Executing Approved Plan: {action.value}",
        thread_id=cl.user_session.get("thread_id")
    )
    task_manager.register_task(new_task)
    
    # Remove action button securely reflecting confirmation
    await action.remove()
    return "Plan Executing Natively"

@cl.action_callback("provide_feedback")
async def on_action_provide_feedback(action: cl.Action):
     """
     Placeholder for inline feedback forms mapping inputs safely to Task results.
     For MVP flow, triggers a simulated 'revision workflow'.
     """
     await cl.Message(content=f"Opening feedback loop for '{action.value}'... Please describe the issue.").send()
     await action.remove()
     return "Awaiting Revision Inputs"

@cl.on_message
async def on_message(message: cl.Message):
    active_agent = cl.user_session.get("active_agent", "career")
    thread_id = cl.user_session.get("thread_id")
    
    # Check for basic UI commands bypassing the AI
    payload = message.content.strip().lower()
    if payload == "/dashboard":
        content = "## Active Task Dashboard\n\n"
        tasks = task_manager.get_tasks_by_group(active_agent)
        if not tasks:
            content += "No active or pending tasks for this workspace."
        else:
            for t in tasks:
                 content += f"- **{t.title}** [`{t.status.upper()}`] (Sub-agent: {t.sub_agent})\n"
        await cl.Message(content=content).send()
        return
        
    if payload == "/library":
        content = f"## Artifact Library ({active_agent.title()})\n\n"
        artifact_dir = Path(settings.data_dir) / active_agent / "artifacts"
        if not artifact_dir.exists():
            content += "No artifacts generated yet."
        else:
            files = list(artifact_dir.glob("*.md")) + list(artifact_dir.glob("*.pdf")) + list(artifact_dir.glob("*.docx"))
            if not files:
                 content += "No artifacts generated yet."
            else:
                 # Provide explicit Chainlit file representations for native download links
                 elements = []
                 for f in files:
                      content += f"- {f.name}\n"
                      elements.append(cl.File(name=f.name, path=str(f), display="inline"))
                 await cl.Message(content=content, elements=elements).send()
                 return
        await cl.Message(content=content).send()
        return

    if payload == "/profile":
        content = "## User Profile Context\n\n"
        profile = ProfileManager().load()
        content += f"**Demographics**: {profile.demographics}\n"
        content += f"**Current Situation**: {profile.current_situation}\n"
        content += f"**Goals**: {profile.goals}\n"
        content += f"**Constraints**: {profile.constraints}\n"
        content += f"**Preferences**: {profile.preferences}\n"
        await cl.Message(content=content).send()
        return
    
    
    # 2. Extract elements attached to message adding content bounds
    if message.elements:
        payload += "\n\n[Attached Files Content]:\n"
        for element in message.elements:
            try:
                if element.path and os.path.exists(element.path):
                    with open(element.path, "r", encoding="utf-8") as f:
                         payload += f"--- {element.name} ---\n{f.read()}\n"
            except Exception as e:
                payload += f"--- {element.name} (Error reading file: {e}) ---\n"
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Build the standard AgentState payload expected by Orchestrator Graph
    state = {
        "messages": [HumanMessage(content=payload)],
        "active_agent": active_agent,
        "task_id": "interactive_session", # Default generic task for live chats unless overridden by actions
    }
    
    # Yield loading spinner in UI
    msg = cl.Message(content="")
    await msg.send()
    
    # Call Orchestrator natively utilizing Async streams (simulated sync currently via native LangGraph execution loops)
    try:
        # Note: LangGraph v0 generally runs async via ainvoke, but we use invoke. 
        # Chainlit runs it on a separate thread effectively avoiding blocking WS.
        result = await cl.make_async(orchestrator_graph.invoke)(state, config=config)
        
        # Parse output appending elements cleanly to UI
        if "messages" in result and len(result["messages"]) > 0:
            last_msg = result["messages"][-1]
            if isinstance(last_msg, AIMessage):
                msg.content = last_msg.content
                await msg.update()
                return

        # Failsafe
        msg.content = "[System] Processing complete, but no output generated."
        await msg.update()
        
    except Exception as e:
        msg.content = f"An error occurred routing through the orchestration graph: {str(e)}"
        await msg.update()
