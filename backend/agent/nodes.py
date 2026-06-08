"""
Agent节点实现 - 开始 → 计划 → 工具调用 → 自我反省 → END
"""
import json
import asyncio
from backend.model.factory import chat_model
from backend.mcp.tools_mcp import tools_mcp
from backend.mcp.medical_db_mcp import medical_db_mcp
from backend.mcp.base import MCPClient
from backend.utils.config_handler import prompts_config
from backend.utils.logger_handler import logger
from backend.stream_queue import push_token, push_end
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

llm = chat_model
tools_client = MCPClient(tools_mcp)
db_client = MCPClient(medical_db_mcp)


async def start_node(state):
    """开始节点：解析用户问题，提取症状信息"""
    user_query = state["user_query"]
    logger.info(f"[Node:Start] 开始处理 - {user_query[:50]}...")

    prompt_text = prompts_config.get("start_prompt", "")
    prompt = ChatPromptTemplate.from_template(prompt_text)
    chain = prompt | llm

    try:
        resp = await chain.ainvoke({"user_query": user_query})
        result = json.loads(resp.content)

        symptoms = result.get("symptoms", [])
        severity = result.get("severity", "unknown")
        age_group = result.get("age_group", "unknown")

        logger.info(f"[Node:Start] 提取到 {len(symptoms)} 个症状，严重程度: {severity}")
        return {
            "extracted_symptoms": symptoms,
            "severity": severity,
            "age_group": age_group,
            "current_step": state["current_step"] + 1
        }
    except Exception as e:
        logger.error(f"[Node:Start] 解析失败: {e}")
        return {
            "extracted_symptoms": [user_query],
            "severity": "unknown",
            "age_group": "unknown",
            "current_step": state["current_step"] + 1
        }


async def plan_node(state):
    """计划节点：制定诊断和回答计划"""
    user_query = state["user_query"]
    symptoms = state["extracted_symptoms"]
    severity = state["severity"]
    logger.info(f"[Node:Plan] 开始制定计划 - 严重程度: {severity}")

    prompt_text = prompts_config.get("plan_prompt", "")
    prompt = ChatPromptTemplate.from_template(prompt_text)
    chain = prompt | llm

    try:
        resp = await chain.ainvoke({
            "user_query": user_query,
            "symptom_analysis": f"症状: {', '.join(symptoms)}，严重程度: {severity}"
        })
        result = json.loads(resp.content)

        return {
            "plan_steps": result.get("plan_steps", []),
            "required_agents": result.get("required_agents", []),
            "need_knowledge_retrieval": result.get("need_knowledge_retrieval", True),
            "urgency_level": result.get("urgency_level", "normal"),
            "current_step": state["current_step"] + 1
        }
    except Exception as e:
        logger.error(f"[Node:Plan] 失败: {e}")
        return {
            "plan_steps": [
                {"step": 1, "action": "retrieve_knowledge", "reason": "检索相关知识"},
                {"step": 2, "action": "analyze_symptoms", "reason": "分析症状"},
                {"step": 3, "action": "diagnose", "reason": "诊断"},
                {"step": 4, "action": "medicine_advice", "reason": "用药建议"}
            ],
            "required_agents": ["symptom_analyzer", "diagnosis_assistant", "medicine_adviser"],
            "need_knowledge_retrieval": True,
            "urgency_level": "normal",
            "current_step": state["current_step"] + 1
        }


async def tool_call_node(state):
    """工具调用节点：调用多Agent工具"""
    if state.get("is_cancelled", False):
        logger.info("[Node:ToolCall] 用户已取消")
        return {"is_finished": True, "final_response": "已取消处理"}

    user_query = state["user_query"]
    logger.info(f"[Node:ToolCall] 开始工具调用")

    # 1. 检索知识
    retrieved_knowledge = state.get("retrieved_knowledge", "")
    if state.get("need_knowledge_retrieval", True) and not retrieved_knowledge:
        try:
            knowledge_results = await db_client.call("search_knowledge", query=user_query, top_n=5)
            retrieved_knowledge = "\n\n---\n\n".join([
                f"【{k['disease']}】\n{k['content']}" for k in knowledge_results
            ])
        except Exception as e:
            logger.warning(f"[Node:ToolCall] 检索失败: {e}")

    # 2. 症状分析
    symptom_result = state.get("symptom_result")
    if not symptom_result:
        try:
            result = await tools_client.call("analyze_symptoms", user_query=user_query)
            symptom_result = result.get("analysis", "")
        except Exception as e:
            logger.error(f"[Node:ToolCall] 症状分析失败: {e}")
            symptom_result = f"初步分析用户可能有与「{user_query}」相关的健康问题。"

    # 3. 诊断
    diagnosis_result = state.get("diagnosis_result")
    if not diagnosis_result:
        try:
            result = await tools_client.call("diagnose", user_query=user_query, symptom_analysis=symptom_result)
            diagnosis_result = result.get("diagnosis", "")
        except Exception as e:
            logger.error(f"[Node:ToolCall] 诊断失败: {e}")
            diagnosis_result = f"基于症状分析，可能与「{user_query}」相关的疾病需要进一步确认。"

    # 4. 用药建议
    medicine_result = state.get("medicine_result")
    if not medicine_result:
        try:
            result = await tools_client.call("medicine_advice", user_query=user_query, diagnosis=diagnosis_result)
            medicine_result = result.get("advice", "")
        except Exception as e:
            logger.error(f"[Node:ToolCall] 用药建议失败: {e}")
            medicine_result = "用药建议需要根据具体诊断结果给出，请咨询医生。"

    return {
        "symptom_result": symptom_result,
        "diagnosis_result": diagnosis_result,
        "medicine_result": medicine_result,
        "retrieved_knowledge": retrieved_knowledge,
        "current_step": state["current_step"] + 1
    }


async def self_reflect_node(state):
    """自我反省节点：检查结果是否完整合理"""
    user_query = state["user_query"]
    symptom_result = state.get("symptom_result", "")
    diagnosis_result = state.get("diagnosis_result", "")
    medicine_result = state.get("medicine_result", "")
    retrieved_knowledge = state.get("retrieved_knowledge", "")

    logger.info("[Node:SelfReflect] 开始自我反省")

    prompt_text = prompts_config.get("self_reflect_prompt", "")
    prompt = ChatPromptTemplate.from_template(prompt_text)
    chain = prompt | llm

    try:
        resp = await chain.ainvoke({
            "user_query": user_query,
            "symptom_result": symptom_result[:500] if symptom_result else "无",
            "diagnosis_result": diagnosis_result[:500] if diagnosis_result else "无",
            "medicine_result": medicine_result[:500] if medicine_result else "无",
            "retrieved_knowledge": retrieved_knowledge[:500] if retrieved_knowledge else "无"
        })
        result = json.loads(resp.content)

        is_complete = result.get("is_complete", False)
        verdict = result.get("final_verdict", "pass")
        supplement_queries = result.get("supplement_queries", [])

        logger.info(f"[Node:SelfReflect] 审查结论: {verdict}, 完整: {is_complete}")

        # 如果需要补充检索
        if verdict == "need_supplement" and supplement_queries:
            for query in supplement_queries:
                try:
                    results = await db_client.call("search_knowledge", query=query, top_n=2)
                    extra_text = "\n\n".join([f"【{k['disease']}补充】\n{k['content']}" for k in results])
                    retrieved_knowledge = retrieved_knowledge + "\n\n" + extra_text if retrieved_knowledge else extra_text
                except:
                    pass

        return {
            "reflection_result": result,
            "is_complete": is_complete or (verdict == "pass"),
            "retrieved_knowledge": retrieved_knowledge,
            "current_step": state["current_step"] + 1
        }
    except Exception as e:
        logger.error(f"[Node:SelfReflect] 失败: {e}")
        return {
            "reflection_result": {"is_complete": True, "issues": [], "final_verdict": "pass", "should_redirect_to_doctor": False},
            "is_complete": True,
            "current_step": state["current_step"] + 1
        }


async def final_node(state):
    """最终节点：生成回答（流式输出到队列）"""
    if state.get("is_cancelled", False):
        return {"final_response": "已取消生成。如果您有健康问题，随时可以再次咨询我。", "is_finished": True}

    user_query = state["user_query"]
    session_id = state.get("session_id", "")
    diagnosis_result = state.get("diagnosis_result", "")
    medicine_result = state.get("medicine_result", "")
    retrieved_knowledge = state.get("retrieved_knowledge", "")
    reflection = state.get("reflection_result", {})

    logger.info(f"[Node:Final] 开始流式生成 - session: {session_id[:8]}")

    should_redirect = reflection.get("should_redirect_to_doctor", False)

    # 构建prompt
    prompt_text = prompts_config.get("final_response_prompt", "")
    prompt = ChatPromptTemplate.from_template(prompt_text)
    chain = prompt | llm

    try:
        full_response = ""
        async for chunk in chain.astream({
            "user_query": user_query,
            "diagnosis": diagnosis_result or "暂无明确诊断",
            "medicine_advice": medicine_result or "暂无用药建议",
            "knowledge": retrieved_knowledge[:800] if retrieved_knowledge else "无相关检索结果",
            "reflection": json.dumps(reflection, ensure_ascii=False)
        }):
            if chunk.content:
                full_response += chunk.content
                if session_id:
                    await push_token(session_id, chunk.content)

        if should_redirect:
            redirect_msg = "\n\n⚠️ **建议就医**：根据评估，建议您尽快就医以获得专业诊疗。"
            full_response += redirect_msg
            if session_id:
                await push_token(session_id, redirect_msg)

        if session_id:
            await push_end(session_id)

        logger.info(f"[Node:Final] 流式生成完成，共 {len(full_response)} 字符")
        return {"final_response": full_response, "is_finished": True, "message": [AIMessage(content=full_response)]}

    except Exception as e:
        logger.error(f"[Node:Final] 流式生成失败: {e}")
        fallback = (
            f"您好！关于您描述的「{user_query}」，以下是我的分析：\n\n"
            f"{diagnosis_result or '需要更多信息来进行准确判断。'}\n\n"
            f"{medicine_result or ''}\n\n"
            f"⚠️ **免责声明**：以上内容仅为AI助手提供的一般性参考，不能替代专业医疗建议。"
            f"如果症状持续或加重，请及时就医。"
        )
        if session_id:
            for ch in fallback:
                await push_token(session_id, ch)
                await asyncio.sleep(0.02)
            await push_end(session_id)
        return {"final_response": fallback, "is_finished": True, "message": [AIMessage(content=fallback)]}


def should_continue(state):
    """判断流程走向"""
    if state.get("is_cancelled", False):
        return "end"
    if state.get("current_step", 0) >= state.get("max_steps", 10):
        return "end"
    if state.get("is_complete", False):
        return "end"
    if state.get("reflection_result", {}).get("final_verdict") in ["pass", "redirect_hospital"]:
        return "end"
    return "tool_call"
