"""
工具层MCP Server - 多Agent协作工具
"""
from backend.mcp.base import MCPServer, MCPClient
from backend.mcp.medical_db_mcp import medical_db_mcp
from backend.model.factory import chat_model
from backend.utils.config_handler import prompts_config
from backend.utils.logger_handler import logger
from langchain_core.prompts import ChatPromptTemplate

class ToolsMCP(MCPServer):
    def __init__(self):
        super().__init__(name="medical_tools")
        self.db_client = MCPClient(medical_db_mcp)
        self._register_methods()

    def _register_methods(self):
        llm = chat_model

        @self.register("analyze_symptoms")
        async def analyze_symptoms(user_query: str):
            knowledge_results = await self.db_client.call("search_knowledge", query=user_query, top_n=3)
            knowledge_text = "\n\n".join([f"[{k['disease']}] {k['content'][:300]}" for k in knowledge_results])
            prompt_text = prompts_config.get("symptom_analyzer_prompt", "")
            prompt = ChatPromptTemplate.from_template(prompt_text)
            chain = prompt | llm
            resp = await chain.ainvoke({"user_query": user_query, "knowledge": knowledge_text})
            return {"analysis": resp.content, "related_knowledge": knowledge_results}

        @self.register("diagnose")
        async def diagnose(user_query: str, symptom_analysis: str):
            knowledge_results = await self.db_client.call("search_knowledge", query=user_query, top_n=3)
            knowledge_text = "\n\n".join([f"[{k['disease']}] {k['content']}" for k in knowledge_results])
            prompt_text = prompts_config.get("diagnosis_assistant_prompt", "")
            prompt = ChatPromptTemplate.from_template(prompt_text)
            chain = prompt | llm
            resp = await chain.ainvoke({"user_query": user_query, "symptom_analysis": symptom_analysis, "knowledge": knowledge_text})
            return {"diagnosis": resp.content, "supporting_knowledge": knowledge_results}

        @self.register("medicine_advice")
        async def medicine_advice(user_query: str, diagnosis: str):
            prompt_text = prompts_config.get("medicine_adviser_prompt", "")
            prompt = ChatPromptTemplate.from_template(prompt_text)
            chain = prompt | llm
            resp = await chain.ainvoke({"user_query": user_query, "diagnosis": diagnosis})
            return {"advice": resp.content}

        @self.register("health_check")
        async def health_check():
            db_health = await self.db_client.call("health_check")
            return {"status": "ok", "name": self.name, "database": db_health, "methods": self.list_methods()}

tools_mcp = ToolsMCP()
