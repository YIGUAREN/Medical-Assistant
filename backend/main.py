"""
FastAPI 后端入口 - 医疗助手 API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import uuid
import json
import asyncio
from langchain_core.messages import HumanMessage, AIMessage

from backend.agent.graph import medical_agent, get_initial_state
from backend.utils.logger_handler import logger
from backend.mcp.medical_db_mcp import medical_db_mcp
from backend.mcp.tools_mcp import tools_mcp
from backend.mcp.base import MCPMessage
from backend.storage.sqlite_memory import SessionMemory
from backend.stream_queue import get_queue, remove_queue

app = FastAPI(title="智能医疗助手 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str, dict] = {}
cancel_events: dict[str, asyncio.Event] = {}


class ChatRequest(BaseModel):
    user_query: str
    session_id: Optional[str] = None


class CancelRequest(BaseModel):
    session_id: str


@app.get("/")
async def read_root():
    return {"message": "智能医疗助手 API 服务", "version": "1.0.0"}


@app.get("/api/mcp/status")
async def mcp_status():
    db_health = await medical_db_mcp.handle_message(MCPMessage(method="health_check", params={}))
    tools_health = await tools_mcp.handle_message(MCPMessage(method="health_check", params={}))
    return {
        "medical_db": db_health.to_dict() if hasattr(db_health, 'to_dict') else str(db_health.__dict__),
        "tools": tools_health.to_dict() if hasattr(tools_health, 'to_dict') else str(tools_health.__dict__),
        "active_sessions": len(sessions)
    }


async def stream_medical_response(session_id: str, user_query: str):
    """流式响应生成器：Agent运行与队列消费并发执行，实现真正的实时流式输出"""
    if session_id not in sessions:
        initial_state = get_initial_state()
        sessions[session_id] = {"config": {"configurable": {"thread_id": session_id}}, "state": initial_state}
        SessionMemory.create_session(session_id)

    # 保存用户消息到SQLite
    SessionMemory.add_message(session_id, "user", user_query)

    session = sessions[session_id]
    config = session["config"]
    current_state = session["state"]

    current_state["user_query"] = user_query
    current_state["session_id"] = session_id
    current_state["is_cancelled"] = False
    current_state["is_finished"] = False
    current_state["current_step"] = 0

    cancel_event = asyncio.Event()
    cancel_events[session_id] = cancel_event

    if "message" not in current_state:
        current_state["message"] = []
    current_state["message"].append(HumanMessage(content=user_query))

    # 预创建队列，确保Agent推送时队列已就绪
    get_queue(session_id)

    full_text = ""
    agent_result = None

    try:
        yield f'data: {json.dumps({"type": "thinking", "content": "正在分析您的问题..."})}\n\n'

        async def run_agent():
            """后台运行Agent，final_node会向流式队列推送token"""
            nonlocal agent_result
            try:
                agent_result = await medical_agent.ainvoke(current_state, config)
            except Exception as e:
                logger.error(f"[Agent] 运行失败: {e}")
                agent_result = {"final_response": f"处理请求时出错: {str(e)}", "is_finished": True}

        agent_task = asyncio.create_task(run_agent())

        # 并发消费流式队列：Agent运行的同时向SSE推送token
        # 使用 asyncio.create_task 并发执行Agent，主协程消费队列
        end_received = False
        while True:
            # 检查取消事件
            if cancel_event.is_set():
                logger.info(f"[API] 用户取消了会话 {session_id}")
                current_state["is_cancelled"] = True
                yield f'data: {json.dumps({"type": "cancelled", "content": "已取消生成"})}\n\n'
                agent_task.cancel()
                break

            # 已经收到结束信号 -> 等待Agent最终完成即可
            if end_received:
                if agent_task.done():
                    break
                await asyncio.sleep(0.05)
                continue

            # 尝试从队列获取token（等待100ms超时）
            try:
                token = await asyncio.wait_for(
                    _get_token_or_none(session_id), timeout=0.1
                )
                if token is None:
                    # final_node推送了push_end()，标记结束信号，不再等待新token
                    end_received = True
                    continue
                full_text += token
                yield f"data: {json.dumps({"type": "stream", "content": token}, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                # 队列暂无数据，继续轮询（如果Agent已完成但队列还有数据，会在下次循环获取）
                if agent_task.done():
                    # Agent已完成但队列可能还有残留数据，再尝试一次非阻塞读取
                    try:
                        token = await asyncio.wait_for(
                            _get_token_or_none(session_id), timeout=0.3
                        )
                        if token is None:
                            break
                        full_text += token
                        yield f"data: {json.dumps({"type": "stream", "content": token}, ensure_ascii=False)}\n\n"
                    except asyncio.TimeoutError:
                        break
                continue

        # Agent已完成，保存结果
        if agent_result:
            session["state"] = agent_result

        # 保存助手回复到SQLite
        if full_text:
            SessionMemory.add_message(session_id, "assistant", full_text)

        if not cancel_event.is_set():
            yield f'data: {json.dumps({"type": "end", "content": "", "session_id": session_id}, ensure_ascii=False)}\n\n'

    except asyncio.CancelledError:
        yield f'data: {json.dumps({"type": "cancelled", "content": "请求被取消"})}\n\n'
    except Exception as e:
        logger.error(f"[API] 流式响应失败: {e}")
        yield f"data: {json.dumps({"type": "error", "content": f"处理请求时出错: {str(e)}"}, ensure_ascii=False)}\n\n"
    finally:
        remove_queue(session_id)
        cancel_events.pop(session_id, None)


async def _get_token_or_none(session_id: str) -> Optional[str]:
    """从队列获取一个token，返回None表示结束信号"""
    from backend.stream_queue import _stream_queues
    q = _stream_queues.get(session_id)
    if q is None:
        raise asyncio.TimeoutError
    token = await q.get()
    if token is None:
        return None
    if isinstance(token, str) and token.startswith("__ERROR__:"):
        return token[len("__ERROR__:"):]
    return token


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    if not request.session_id:
        request.session_id = str(uuid.uuid4())
    return StreamingResponse(
        stream_medical_response(request.session_id, request.user_query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache", "Connection": "keep-alive",
            "X-Accel-Buffering": "no", "X-Session-Id": request.session_id
        }
    )


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not request.session_id:
        request.session_id = str(uuid.uuid4())

    if request.session_id not in sessions:
        sessions[request.session_id] = {"config": {"configurable": {"thread_id": request.session_id}}, "state": get_initial_state()}
        SessionMemory.create_session(request.session_id)

    # 保存用户消息到SQLite
    SessionMemory.add_message(request.session_id, "user", request.user_query)

    session = sessions[request.session_id]
    current_state = session["state"]
    current_state["user_query"] = request.user_query
    current_state["session_id"] = request.session_id
    current_state["is_cancelled"] = False
    current_state["is_finished"] = False
    current_state["current_step"] = 0
    if "message" not in current_state:
        current_state["message"] = []
    current_state["message"].append(HumanMessage(content=request.user_query))

    try:
        result = await medical_agent.ainvoke(current_state, session["config"])
        session["state"] = result
        final_response = result.get("final_response", "处理完成")
        SessionMemory.add_message(request.session_id, "assistant", str(final_response))
        return {"session_id": request.session_id, "status": "success", "response": str(final_response)}
    except Exception as e:
        return {"session_id": request.session_id, "status": "error", "response": f"处理请求时出错: {str(e)}"}


@app.post("/api/chat/cancel")
async def cancel_chat(request: CancelRequest):
    session_id = request.session_id
    if session_id in cancel_events:
        cancel_events[session_id].set()
        return {"status": "success", "message": "已取消生成"}
    return {"status": "warning", "message": "没有正在进行的生成任务"}


@app.post("/api/chat/new")
async def new_chat():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"config": {"configurable": {"thread_id": session_id}}, "state": get_initial_state()}
    SessionMemory.create_session(session_id)
    return {"session_id": session_id, "message": "新会话已创建"}


@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    messages = SessionMemory.get_messages(session_id)
    return {"session_id": session_id, "messages": messages}


@app.get("/api/chat/sessions")
async def list_sessions():
    return {"sessions": SessionMemory.get_all_sessions()}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    logger.info(f"启动医疗助手API服务: http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)
