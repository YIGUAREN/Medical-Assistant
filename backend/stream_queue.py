"""
全局流式队列 - 用于Agent节点向SSE推送流式token
"""
import asyncio

# 全局队列: session_id -> asyncio.Queue
_stream_queues: dict[str, asyncio.Queue] = {}


def get_queue(session_id: str) -> asyncio.Queue:
    """获取或创建会话的流式队列"""
    if session_id not in _stream_queues:
        _stream_queues[session_id] = asyncio.Queue()
    return _stream_queues[session_id]


def remove_queue(session_id: str):
    """移除会话的流式队列"""
    _stream_queues.pop(session_id, None)


async def push_token(session_id: str, token: str):
    """向队列推送一个token"""
    q = get_queue(session_id)
    await q.put(token)


async def push_end(session_id: str):
    """推送结束信号"""
    q = get_queue(session_id)
    await q.put(None)


async def push_error(session_id: str, error_msg: str):
    """推送错误信号"""
    q = get_queue(session_id)
    await q.put(f"__ERROR__:{error_msg}")
