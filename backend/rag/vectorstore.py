from langchain_chroma import Chroma
from langchain_core.documents import Document
from backend.model.factory import embed_model
from backend.utils.config_handler import chroma_config

def create_vectorstore(documents: list[Document]):
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embed_model,
        persist_directory=chroma_config["persist_directory"],
        collection_name=chroma_config.get("collection_name", "medical_knowledge")
    )
    return vectorstore

def load_vectorstore():
    return Chroma(
        embedding_function=embed_model,
        persist_directory=chroma_config["persist_directory"],
        collection_name=chroma_config.get("collection_name", "medical_knowledge")
    )
