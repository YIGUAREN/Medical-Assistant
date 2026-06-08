"""
MCP基础实现 - 作为内部通信协议
MCP Server和Client基类，用于Agent内部组件间的通信
"""
import asyncio
from typing import Any, Callable, Optional
from backend.utils.logger_handler import logger


class MCPMessage:
    def __init__(self, method: str, params: dict, msg_id: Optional[str] = None):
        self.id = msg_id or str(id(self))
        self.method = method
        self.params = params


class MCPResponse:
    def __init__(self, msg_id: str, result: Any = None, error: Optional[str] = None):
        self.id = msg_id
        self.result = result
        self.error = error

    def to_dict(self) -> dict:
        resp = {"id": self.id}
        if self.error:
            resp["error"] = self.error
        else:
            resp["result"] = self.result
        return resp


class MCPServer:
    def __init__(self, name: str):
        self.name = name
        self._handlers: dict[str, Callable] = {}
        logger.info(f"[MCP] 服务器 '{name}' 已创建")

    def register(self, method: str, handler: Callable = None):
        """注册方法处理器，支持装饰器和直接调用两种用法"""
        if handler is None:
            def decorator(actual_handler):
                self._handlers[method] = actual_handler
                logger.info(f"[MCP] 服务器 '{self.name}' 注册方法: {method}")
                return actual_handler
            return decorator
        self._handlers[method] = handler
        logger.info(f"[MCP] 服务器 '{self.name}' 注册方法: {method}")
        return handler

    async def handle_message(self, message: MCPMessage) -> MCPResponse:
        method = message.method
        params = message.params
        if method not in self._handlers:
            return MCPResponse(msg_id=message.id, error=f"未知方法: {method}")
        try:
            handler = self._handlers[method]
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**params)
            else:
                result = handler(**params)
            return MCPResponse(msg_id=message.id, result=result)
        except Exception as e:
            logger.error(f"[MCP] 方法 '{method}' 执行失败: {e}")
            return MCPResponse(msg_id=message.id, error=str(e))

    def list_methods(self) -> list[str]:
        return list(self._handlers.keys())


class MCPClient:
    def __init__(self, server: MCPServer):
        self.server = server

    async def call(self, method: str, **params) -> Any:
        message = MCPMessage(method=method, params=params)
        response = await self.server.handle_message(message)
        if response.error:
            raise MCPError(f"MCP调用 '{method}' 失败: {response.error}")
        return response.result


class MCPError(Exception):
    pass
