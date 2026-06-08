from dotenv import load_dotenv
import os
from abc import ABC, abstractmethod
from typing import Optional
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

class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | ChatTongyi]:
        return DashScopeEmbeddings(
            model="text-embedding-v3",
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
        )

class RerankFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | ChatTongyi]:
        from dashscope.rerank.text_rerank import TextReRank
        return TextReRank()

chat_model = ChatModelFactory().generator()
embed_model = EmbeddingsFactory().generator()
rerank_model = RerankFactory().generator()
