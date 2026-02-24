"""
WebSocket Chat endpoint.
Handles bidirectional communication: receives user messages and streams
back LangGraph execution results (AI responses, status updates) in real-time.
"""
import asyncio
import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage, AIMessage

from api.connection_manager import manager
from orchestrator.graph import orchestrator_graph
from context.profile_manager import ProfileManager

router = APIRouter(tags=["Chat"])

profile_mgr = ProfileManager()


@router.websocket("/api/chat/{thread_id}")
async def websocket_chat(websocket: WebSocket, thread_id: str):
    """
    Bidirectional WebSocket for chat.

    Client sends JSON:
        {"message": "...", "active_agent": "career|life|learning|onboarding|settings"}

    Server streams back JSON events:
        {"type": "status", "content": "processing"}
        {"type": "ai_message", "content": "...", "agent_name": "..."}
        {"type": "error", "content": "..."}
        {"type": "done"}
    """
    await manager.connect(websocket, thread_id)
    try:
        while True:
            # 1. Receive a message from the client
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            active_agent = data.get("active_agent", "career")

            if not user_message:
                await websocket.send_json({"type": "error", "content": "Empty message received."})
                continue

            # 2. Send a processing status
            await websocket.send_json({"type": "status", "content": "processing"})

            # 3. Build the LangGraph state
            config = {"configurable": {"thread_id": thread_id}}
            input_messages = [HumanMessage(content=user_message)]
            input_count = len(input_messages)

            state = {
                "messages": input_messages,
                "active_agent": active_agent,
                "task_id": "interactive_session",
            }

            # 4. Invoke the orchestrator graph asynchronously
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: orchestrator_graph.invoke(state, config=config)
                )

                # 5. Extract only NEW AI messages (skip the input messages we sent in)
                ai_found = False
                if "messages" in result:
                    new_messages = result["messages"][input_count:]  # Skip input messages
                    for msg in new_messages:
                        if isinstance(msg, AIMessage):
                            ai_found = True
                            await websocket.send_json({
                                "type": "ai_message",
                                "content": msg.content,
                                "agent_name": getattr(msg, "name", None) or "assistant",
                            })

                # 6. If no AI message was produced, send a helpful fallback
                if not ai_found:
                    await websocket.send_json({
                        "type": "ai_message",
                        "content": f"I'm your **{active_agent.title()} Agent**. How can I help you today? Try asking me something specific about your {active_agent} goals.",
                        "agent_name": f"{active_agent}_agent",
                    })

                # 7. Signal completion
                await websocket.send_json({"type": "done"})

            except Exception as e:
                error_detail = traceback.format_exc()
                print(f"[Chat WS] Error during graph invocation: {error_detail}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Agent execution failed: {str(e)}"
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket, thread_id)
        print(f"[Chat WS] Client disconnected from thread: {thread_id}")
    except Exception as e:
        print(f"[Chat WS] Unexpected error: {e}")
        await manager.disconnect(websocket, thread_id)
