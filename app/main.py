import os
import json
import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from server.host_agent.adk_host_manager import ADKHostManager
from a2a_types import Message, TextPart
from server.host_agent.utils import get_agent_card
from app.task_queue import task_queue

# FastAPI 앱 인스턴스 생성
app = FastAPI()

# 정적 파일(HTML, JS, CSS 등) 서빙을 위한 디렉토리 마운트
STATIC_DIR = Path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 환경 변수에서 API 키를 읽어옴. 없으면 예외 발생
api_key = os.environ.get("GOOGLE_API_KEY", "")
if not api_key:
    raise RuntimeError("GOOGLE_API_KEY environment variable is required. Please set it in your environment or .env file.")

# ADK Host Manager 인스턴스 생성 (에이전트 관리)
host_manager = ADKHostManager(api_key)

# 에이전트 정보 저장용 리스트
agent_infos = []

# 루트 엔드포인트: index.html 반환
@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# WebSocket 엔드포인트: 클라이언트와 실시간 메시지 통신
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    print(f"Client #{session_id} connected")
    conversation = host_manager.create_conversation()
    print(f"Created conversation: {conversation.conversation_id}")

    async def send_task_results():
        while True:
            item = await task_queue.get()
            # If the item is a dict with 'type', treat as new protocol
            if isinstance(item, dict) and 'type' in item:
                if item['type'] == 'request':
                    # Send the request as a user message
                    req = item['request']
                    text = None
                    if hasattr(req, 'message') and hasattr(req.message, 'parts') and req.message.parts:
                        part = req.message.parts[0]
                        text = getattr(part, 'text', str(part))
                    await websocket.send_text(json.dumps({
                        "type": "message",
                        "source": "host_request",
                        "content": {
                            "text": text or "[no message]",
                            "role": "host",
                            "taskId": item.get('task_id')
                        }
                    }))
                elif item['type'] == 'response':
                    task = item['task']
                    message_text = None
                    name = "agent"
                    if task and hasattr(task, 'status') and getattr(task.status, 'message', None) and task.status.message.parts:
                        msg = task.status.message
                        if hasattr(msg, 'parts') and msg.parts:
                            message_text = msg.parts[0].text if hasattr(msg.parts[0], 'text') else str(msg.parts[0])
                    if not message_text and hasattr(task, 'artifacts') and task.artifacts:
                        for artifact in task.artifacts:
                            if hasattr(artifact, 'parts') and artifact.parts:
                                message_text = artifact.parts[0].text if hasattr(artifact.parts[0], 'text') else str(artifact.parts[0])
                                name = getattr(artifact, 'name', "agent")
                                break
                    if not message_text:
                        message_text = "[no message]"
                    await websocket.send_text(json.dumps({
                        "type": "message",
                        "source": "task",
                        "content": {
                            "text": message_text,
                            "role": name,
                            "taskId": getattr(task, 'id', None)
                        }
                    }))
                continue
            # Legacy: handle as task
            task = item
            message_text = None
            name = "agent"
            if task and hasattr(task, 'status') and getattr(task.status, 'message', None):
                msg = task.status.message
                if hasattr(msg, 'parts') and msg.parts:
                    message_text = msg.parts[0].text if hasattr(msg.parts[0], 'text') else str(msg.parts[0])
            if not message_text and hasattr(task, 'artifacts') and task.artifacts:
                for artifact in task.artifacts:
                    if hasattr(artifact, 'parts') and artifact.parts:
                        message_text = artifact.parts[0].text if hasattr(artifact.parts[0], 'text') else str(artifact.parts[0])
                        name = getattr(artifact, 'name', "agent")
                        break
            if not message_text:
                message_text = "[no message]"
            await websocket.send_text(json.dumps({
                "type": "message",
                "source": "task",
                "content": {
                    "text": message_text,
                    "role": name,
                    "taskId": getattr(task, 'id', None)
                }
            }))

    send_task_task = asyncio.create_task(send_task_results())

    try:
        while True:
            user_input = await websocket.receive_text()
            for agent_url in [agent['url'] for agent in agent_infos]:
                host_manager.register_agent(agent_url)
            
            # 유저 메시지 전송
            await websocket.send_text(json.dumps({
                "type": "message",
                "source": "user",
                "content": {
                    "text": user_input,
                    "role": "user"
                }
            }))

            # Message 객체 생성 시 TextPart 직렬화
            message = Message(
                parts=[{"text": user_input}],
                role="user",
                metadata={"conversation_id": conversation.conversation_id}
            )
            await host_manager.process_message(message)
            
            # 에이전트 메시지 처리
            agent_messages = [
                m for m in host_manager._messages
                if m.role != "user" and m.metadata and m.metadata.get("conversation_id") == conversation.conversation_id
            ]
            if agent_messages:
                last_agent_msg = agent_messages[-1]
                part = last_agent_msg.parts[0]
                text = part["text"] if isinstance(part, dict) and "text" in part else (part.text if hasattr(part, "text") else str(part))
                await websocket.send_text(json.dumps({
                    "type": "message",
                    "source": "host_agent",
                    "content": {
                        "text": text,
                        "role": last_agent_msg.role
                    }
                }))
            else:
                await websocket.send_text(json.dumps({
                    "type": "message",
                    "source": "system",
                    "content": {
                        "text": "[No agent response yet]",
                        "role": "system"
                    }
                }))
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        send_task_task.cancel()
        print(f"Client #{session_id} disconnected")

@app.get("/agents")
async def get_agents():
    return {"agents": agent_infos}

@app.post("/agents")
async def add_agent(request: Request):
    data = await request.json()
    url = data.get("url")
    if url not in [agent['url'] for agent in agent_infos]:
        card = get_agent_card(url)
        if card:
            name = card.model_dump().get('name')
            agent_infos.append({"name": name, "url": url})
            return {"success": True, "agents": agent_infos}
        else:
            return {"fail": False, "error": "Invalid or unreachable agent URL"}
    else:
        return {"fail": False, "error": "Invalid or duplicate URL"}

@app.delete("/agents")
async def delete_agent(request: Request):
    data = await request.json()
    url = data.get("url")
    before_count = len(agent_infos)
    agent_infos[:] = [agent for agent in agent_infos if agent["url"] != url]
    after_count = len(agent_infos)
    if before_count > after_count:
        return {"success": True, "agents": agent_infos}
    else:
        return {"fail": False, "error": "Agent not found"}

@app.post("/agent_card_preview")
async def agent_card_preview(request: Request):
    data = await request.json()
    url = data.get("url")
    card = get_agent_card(url)
    if card:
        return JSONResponse(content=card.model_dump())
    else:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "type": "AgentConnectionError",
                    "message": "Invalid agent or unreachable"
                }
            }
        )

def task_to_dict(task):
    # task 객체를 dict로 변환
    return {
        "id": getattr(task, "id", None),
        "status": getattr(task, "status", None),
        "message": getattr(task, "status", {}).get("message", None) if hasattr(task, "status") else None,
    }
