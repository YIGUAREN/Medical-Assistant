"""
LangGraph 工作流定义
节点：开始 → 计划 → 工具调用 → 自我反省 → END
"""
from langgraph.graph import StateGraph, END
from backend.agent.state import MedicalState, get_initial_state
from backend.agent.nodes import (
    start_node, plan_node, tool_call_node,
    self_reflect_node, final_node, should_continue
)


def build_medical_agent():
    workflow = StateGraph(MedicalState)

    workflow.add_node("start", start_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("tool_call", tool_call_node)
    workflow.add_node("self_reflect", self_reflect_node)
    workflow.add_node("final", final_node)

    workflow.set_entry_point("start")

    workflow.add_edge("start", "plan")
    workflow.add_edge("plan", "tool_call")
    workflow.add_edge("tool_call", "self_reflect")

    workflow.add_conditional_edges(
        "self_reflect",
        should_continue,
        {"end": "final", "tool_call": "tool_call"}
    )

    workflow.add_edge("final", END)

    agent = workflow.compile()
    return agent


medical_agent = build_medical_agent()
