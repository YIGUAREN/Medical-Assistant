"""
SQLite 会话记忆存储
保存和管理会话历史记录
"""
import sqlite3
import json
import os
from typing import Optional
from backend.utils.path_tool import get_abs_path


DB_PATH = get_abs_path("data/sessions.db")


def _get_connection():
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表"""
    conn = _get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT DEFAULT '新会话',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            log_type TEXT NOT NULL,
            log_data TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_agent_logs_session ON agent_logs(session_id);
    """)
    conn.commit()
    conn.close()


class SessionMemory:
    """会话记忆管理"""

    @staticmethod
    def create_session(session_id: str, title: str = "新会话") -> dict:
        """创建新会话"""
        conn = _get_connection()
        conn.execute(
            "INSERT OR IGNORE INTO sessions (session_id, title) VALUES (?, ?)",
            (session_id, title)
        )
        conn.commit()
        conn.close()
        return {"session_id": session_id, "title": title}

    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        """获取会话信息"""
        conn = _get_connection()
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    @staticmethod
    def get_all_sessions(limit: int = 50) -> list[dict]:
        """获取所有会话列表"""
        conn = _get_connection()
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def add_message(session_id: str, role: str, content: str):
        """添加消息记录"""
        conn = _get_connection()
        # 更新会话时间
        conn.execute(
            "UPDATE sessions SET updated_at = datetime('now') WHERE session_id = ?",
            (session_id,)
        )
        # 插入消息
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_messages(session_id: str, limit: int = 50) -> list[dict]:
        """获取会话消息历史"""
        conn = _get_connection()
        rows = conn.execute(
            """SELECT role, content, created_at FROM messages
               WHERE session_id = ? ORDER BY id ASC LIMIT ?""",
            (session_id, limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def add_agent_log(session_id: str, log_type: str, log_data: dict):
        """添加Agent日志"""
        conn = _get_connection()
        conn.execute(
            "INSERT INTO agent_logs (session_id, log_type, log_data) VALUES (?, ?, ?)",
            (session_id, log_type, json.dumps(log_data, ensure_ascii=False))
        )
        conn.commit()
        conn.close()

    @staticmethod
    def delete_session(session_id: str):
        """删除会话"""
        conn = _get_connection()
        conn.execute("DELETE FROM agent_logs WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def format_history_for_prompt(session_id: str, max_turns: int = 5) -> str:
        """将历史消息格式化为对话上下文文本"""
        messages = SessionMemory.get_messages(session_id, limit=max_turns * 2)
        if not messages:
            return ""

        parts = []
        for msg in messages:
            role_name = "用户" if msg["role"] == "user" else "助手"
            parts.append(f"{role_name}: {msg['content'][:200]}")
        return "\n".join(parts)


# 启动时初始化数据库
init_db()
