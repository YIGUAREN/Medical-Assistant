from backend.model.factory import rerank_model
from langchain_chroma import Chroma
from backend.utils.config_handler import chroma_config
from langchain_core.documents import Document

def rerank_documents(query: str, documents: list[Document], top_n: int = 5):
    if not documents:
        return []
    doc_texts = [doc.page_content for doc in documents]
    response = rerank_model.call(
        model=chroma_config["rerank_model"],
        query=query,
        documents=doc_texts,
        top_n=min(top_n, len(doc_texts)),
    )
    results = response.output.results
    sorted_docs = [documents[result.index] for result in results]
    return sorted_docs

class MedicalRetriever:
    def __init__(self, vectorstore: Chroma, search_k: int = 20):
        self.vectorstore = vectorstore
        self.search_k = search_k

    def retrieve(self, query: str, top_n: int = 5) -> list[Document]:
        candidates = self.vectorstore.similarity_search(query, k=self.search_k)
        return rerank_documents(query, candidates, top_n=top_n)
