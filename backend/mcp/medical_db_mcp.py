"""
医疗数据库MCP Server
提供医疗知识的查询、检索功能
"""
from backend.mcp.base import MCPServer
from backend.rag.vectorstore import load_vectorstore
from backend.rag.retriever import MedicalRetriever
from backend.utils.logger_handler import logger
from backend.utils.config_handler import chroma_config

class MedicalDatabaseMCP(MCPServer):
    def __init__(self):
        super().__init__(name="medical_database")
        self._retriever = None
        self._init_retriever()
        self._register_methods()

    def _init_retriever(self):
        try:
            vectorstore = load_vectorstore()
            self._retriever = MedicalRetriever(vectorstore=vectorstore, search_k=chroma_config.get("search_k", 20))
            logger.info("[MCP/DB] 医疗知识检索器初始化成功")
        except Exception as e:
            logger.warning(f"[MCP/DB] 检索器初始化失败（知识库可能尚未创建）: {e}")
            self._retriever = None

    def _register_methods(self):
        @self.register("search_knowledge")
        async def search_knowledge(query: str, top_n: int = 5):
            if not self._retriever:
                raise RuntimeError("知识库尚未初始化，请先运行 init_knowledge.py")
            docs = self._retriever.retrieve(query, top_n=top_n)
            return [
                {"content": doc.page_content, "disease": doc.metadata.get("disease", ""),
                 "category": doc.metadata.get("category", ""), "score": 0.0}
                for doc in docs
            ]

        @self.register("health_check")
        async def health_check():
            return {"status": "ok" if self._retriever else "no_knowledge_base", "name": self.name, "methods": self.list_methods()}

medical_db_mcp = MedicalDatabaseMCP()
