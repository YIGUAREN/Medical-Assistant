"""
模型工厂 - 集中管理所有 AI 模型的初始化
支持切换嵌入模型：DashScope API / Sentence-Transformer 本地模型
"""
import os
from abc import ABC, abstractmethod
from typing import Optional

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings

load_dotenv()


class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | ChatTongyi]:
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | ChatTongyi]:
        return ChatTongyi(
            model="qwen-max",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            streaming=True
        )


class DashScopeEmbeddingFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | ChatTongyi]:
        return DashScopeEmbeddings(
            model="text-embedding-v3",
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
        )


class SentenceTransformerEmbeddingFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | ChatTongyi]:
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            raise ImportError(
                "需要安装 langchain-huggingface 和 sentence-transformers：\n"
                "  pip install langchain-huggingface sentence-transformers"
            )

        model_name = os.getenv(
            "SENTENCE_TRANSFORMER_MODEL_NAME",
            "BAAI/bge-large-zh-v1.5"
        )
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )


class RerankFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | ChatTongyi]:
        from dashscope.rerank.text_rerank import TextReRank
        return TextReRank()


# ==================== 模型实例 ====================

chat_model = ChatModelFactory().generator()
rerank_model = RerankFactory().generator()

# 嵌入模型：根据环境变量切换
_embed_type = os.getenv("EMBED_MODEL_TYPE", "DASHSCOPE").upper()
if _embed_type == "SENTENCE_TRANSFORMER":
    embed_model = SentenceTransformerEmbeddingFactory().generator()
    print(f"[Model] 使用本地 Sentence-Transformer 嵌入模型")
else:
    embed_model = DashScopeEmbeddingFactory().generator()
    print(f"[Model] 使用 DashScope API 嵌入模型")
