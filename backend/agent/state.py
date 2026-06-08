from typing import Optional, Annotated, List, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MedicalState(TypedDict):
    message: Annotated[list[BaseMessage], add_messages]
    user_query: str
    session_id: str
    extracted_symptoms: list[str]
    severity: str
    age_group: str
    plan_steps: list[dict]
    required_agents: list[str]
    need_knowledge_retrieval: bool
    urgency_level: str
    symptom_result: Optional[str]
    diagnosis_result: Optional[str]
    medicine_result: Optional[str]
    retrieved_knowledge: str
    reflection_result: Optional[dict]
    is_complete: bool
    final_response: Optional[str]
    current_step: int
    max_steps: int
    is_finished: bool
    is_cancelled: bool

def get_initial_state():
    return {
        "message": [],
        "user_query": "",
        "session_id": "",
        "extracted_symptoms": [],
        "severity": "unknown",
        "age_group": "unknown",
        "plan_steps": [],
        "required_agents": [],
        "need_knowledge_retrieval": False,
        "urgency_level": "normal",
        "symptom_result": None,
        "diagnosis_result": None,
        "medicine_result": None,
        "retrieved_knowledge": "",
        "reflection_result": None,
        "is_complete": False,
        "final_response": None,
        "current_step": 0,
        "max_steps": 10,
        "is_finished": False,
        "is_cancelled": False,
    }
