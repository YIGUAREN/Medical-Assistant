# 🏥 智能医疗助手 (Medical Assistant)

Stars Forks Python

AI 驱动的智能医疗咨询助手，融合 **LangGraph Agent 工作流 + RAG 医疗知识库 + 流式对话**，解决"身体不适时快速获取专业、可靠的医疗参考建议"的问题。

## 📋 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [Agent 工作流](#agent-工作流)
- [快速开始](#快速开始)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [API 文档](#api-文档)
- [配置说明](#配置说明)
- [医疗知识库](#医疗知识库)
- [免责声明](#免责声明)

## 项目简介

基于 **FastAPI + Vue 3 + LangGraph + 通义千问** 构建的智能医疗咨询助手，核心能力包括：

- **💬 Agent 智能问诊**：多节点 LangGraph 工作流（症状解析 → 诊断计划 → 多工具调用 → 自我审查 → 流式回答），模拟医生问诊逻辑
- **⚡ 流式对话**：基于 SSE 的实时流式输出，逐 token 展示 AI 回答，支持随时中断
- **📚 RAG 医疗知识库**：内置 30+ 种常见疾病的专业知识，基于 Chroma 向量检索增强生成，回答有据可依
- **🔧 MCP 模块通信**：基于 MCP 协议的模块间通信，知识检索与多 Agent 协作分离，架构清晰可扩展

## 核心特性

| 功能模块 | 说明 |
|---------|------|
| **🧠 LangGraph 工作流** | 五节点 Agent 流程：start → plan → tool_call → self_reflect → final，模拟临床推理链路 |
| **⚡ SSE 流式输出** | 基于 asyncio.Queue + StreamingResponse 的逐 token 实时推送 |
| **📚 RAG 知识库** | Chroma 向量数据库 + 重排序，检索 30+ 种常见疾病的症状、用药、护理知识 |
| **🔧 MCP 内部通信** | 自研轻量级 MCP 协议，知识库服务与工具服务解耦 |
| **🔄 自我审查机制** | self_reflect 节点自动检查诊断完整性，可触发补充检索或建议就医 |
| **🛑 取消生成** | 支持用户随时中断 AI 回复 |
| **💾 会话持久化** | SQLite 存储对话历史，支持多会话管理 |
| **🏷️ 快速问诊** | 前端预设 6 种常见症状一键咨询 |
| **🎨 友好界面** | Vue 3 + Element Plus，Markdown 渲染，移动端适配 |

## Agent 工作流

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户输入症状描述                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  🟢 start_node                                                 │
│  解析症状、严重程度、年龄段 → {"symptoms": [...], "severity": "..."} │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  🔵 plan_node                                                 │
│  制定诊断计划 → 需要哪些 Agent、是否需要知识检索、紧急程度评估      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  🟠 tool_call_node (并发调用)                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 知识检索(RAG) │  │ 症状分析Agent │  │ 诊断Agent     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐                                              │
│  │ 用药建议Agent │                                              │
│  └──────────────┘                                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  🟣 self_reflect_node                                           │
│  自我审查：结果是否完整？是否需要补充检索？是否需要建议就医？      │
│  ┌──────────────┐              ┌──────────────┐                │
│  │ 通过 → final  │              │ 不通过 → 补充  │                │
│  └──────────────┘              └──────────────┘                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  🔴 final_node (流式生成)                                       │
│  chain.astream() → push_token() → asyncio.Queue → SSE → 前端    │
│  逐 token 实时推送，支持取消                                      │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

| 环境 | 版本 |
|------|------|
| Python | 3.13+ |
| uv | 0.5+ |
| Node.js | 18+ |

### 安装依赖

```bash
# 克隆项目
git clone <your-repo-url>
cd Medical-Assistant

# 后端依赖
uv sync

# 前端依赖
cd frontend && npm install
cd ..
```

### 环境配置

在项目根目录创建 `.env` 文件：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
```

### 初始化医疗知识库（首次运行）

```bash
uv run python -m backend.data.init_knowledge
```

### 启动服务

| 服务 | 命令 | 端口 |
|------|------|------|
| 后端服务 | `uv run uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload` | 8001 |
| 前端服务 | `cd frontend && npm run dev` | 5173 |

打开浏览器访问 `http://localhost:5173`

### 直接调用 API

```bash
# 流式聊天
curl -N -X POST http://localhost:8001/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"user_query":"感冒了怎么办","session_id":"test1"}'

# 非流式聊天
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_query":"发烧38度，头痛"}'

# 查看系统状态
curl http://localhost:8001/api/mcp/status
```

## 技术栈

### 后端技术

| 技术 | 说明 |
|------|------|
| **FastAPI** | 高性能异步 Web 框架（StreamingResponse SSE） |
| **LangGraph** | Agent 工作流框架（StateGraph 多节点编排） |
| **LangChain** | LLM 调用链（ChatPromptTemplate + Runnable） |
| **ChromaDB** | 轻量级向量数据库（医疗知识库存储） |
| **通义千问 (DashScope)** | LLM 服务（qwen-max 对话 / text-embedding-v3 嵌入 / qwen3-rerank 重排序） |
| **Sentence-Transformers** | 可选本地嵌入模型（BAAI/bge-large-zh-v1.5），替代 DashScope 嵌入 |
| **SQLite** | 会话记忆持久化 |
| **MCP 协议** | 自研轻量级模块间通信协议 |

### 前端技术

| 技术 | 说明 |
|------|------|
| **Vue 3** | Composition API |
| **Vite** | 构建工具 |
| **Element Plus** | UI 组件库 |
| **marked** | Markdown 渲染 |
| **Fetch API** | SSE 流式消费（ReadableStream） |

## 项目结构

```
Medical-Assistant/
├── backend/                          # FastAPI 后端服务
│   ├── agent/                        # LangGraph Agent 工作流
│   │   ├── graph.py                  #   StateGraph 工作流图定义
│   │   ├── nodes.py                  #   五节点实现（start → plan → tool_call → self_reflect → final）
│   │   └── state.py                  #   Agent 状态 TypedDict + 初始状态
│   ├── config/                       # 配置文件
│   │   ├── prompts.yml               #   提示词模板（8个节点/Agent 提示词）
│   │   └── chroma.yml                #   向量数据库配置（collection / persist_directory / rerank_model）
│   ├── mcp/                          # MCP 内部通信协议
│   │   ├── base.py                   #   MCPServer / MCPClient / MCPMessage / MCPResponse
│   │   ├── medical_db_mcp.py         #   医疗知识库服务（search_knowledge / health_check）
│   │   └── tools_mcp.py              #   多 Agent 工具服务（analyze_symptoms / diagnose / medicine_advice）
│   ├── model/                        # 模型工厂
│   │   └── factory.py                #   ChatTongyi / DashScopeEmbeddings / TextReRank 初始化
│   ├── rag/                          # RAG 检索增强
│   │   ├── vectorstore.py            #   Chroma 向量库创建与加载
│   │   └── retriever.py              #   检索器（向量检索 + 重排序）
│   ├── storage/                      # 持久化存储
│   │   └── sqlite_memory.py          #   SQLite 会话记忆（CRUD + 历史格式化）
│   ├── utils/                        # 工具函数
│   │   ├── config_handler.py         #   YAML 配置加载（prompts_config / chroma_config）
│   │   ├── logger_handler.py         #   日志配置（文件 + 控制台）
│   │   └── path_tool.py              #   项目根目录路径解析
│   ├── data/                         # 医疗知识数据
│   │   ├── medical_knowledge.py      #   30+ 种常见疾病原始知识（症状/用药/护理）
│   │   └── init_knowledge.py         #   知识库初始化脚本（文档 → Chroma）
│   ├── stream_queue.py               # 流式队列（asyncio.Queue 封装，Agent → SSE）
│   └── main.py                       # FastAPI 入口 + SSE 流式生成器 + REST 端点
├── frontend/                         # Vue 3 前端项目
│   ├── src/
│   │   ├── App.vue                   #   主聊天界面（SSE ReadableStream 消费 + Markdown 渲染）
│   │   └── main.js                   #   Vue 入口 + Element Plus 注册
│   ├── index.html                    # HTML 入口
│   ├── vite.config.js                # Vite 配置（/api → localhost:8001 代理）
│   └── package.json                  # 前端依赖
├── data/                             # 运行时数据目录（Chroma / SQLite）
├── logs/                             # 日志目录
├── pyproject.toml                    # Python 依赖声明
└── .env                              # API 密钥配置
```

## API 文档

完整 API 端点列表。启动服务后也可访问交互式文档：`http://localhost:8001/docs`

| 端点 | 方法 | 说明 | 请求体 |
|------|------|------|--------|
| `/` | GET | 服务健康检查 | - |
| `/api/chat/stream` | POST | **流式**聊天（SSE） | `{"user_query": str, "session_id": str?}` |
| `/api/chat` | POST | 非流式聊天 | `{"user_query": str, "session_id": str?}` |
| `/api/chat/cancel` | POST | 取消正在生成的回复 | `{"session_id": str}` |
| `/api/chat/new` | POST | 创建新会话 | - |
| `/api/chat/history/{session_id}` | GET | 获取会话历史 | - |
| `/api/chat/sessions` | GET | 获取所有会话列表 | - |
| `/api/mcp/status` | GET | MCP 服务状态 | - |

### SSE 事件格式

流式端点 `/api/chat/stream` 返回 `text/event-stream`，事件格式如下：

```
data: {"type": "thinking", "content": "正在分析您的问题..."}

data: {"type": "stream", "content": "根据您的描述"}

data: {"type": "stream", "content": "，可能是普通感冒"}

data: {"type": "end", "content": "", "session_id": "xxx"}

data: {"type": "error", "content": "错误信息"}

data: {"type": "cancelled", "content": "已取消生成"}
```

| 事件类型 | 说明 |
|---------|------|
| `thinking` | Agent 正在思考阶段 |
| `stream` | 逐 token 流式内容 |
| `end` | 生成完成 |
| `error` | 发生错误 |
| `cancelled` | 用户取消生成 |

## 配置说明

### LLM 模型配置

在 `backend/model/factory.py` 中配置：

| 模型 | 用途 | 类型 | 配置项 |
|------|------|------|--------|
| `qwen-max` | 对话/诊断/分析 | `ChatTongyi` | `DASHSCOPE_API_KEY` |
| `text-embedding-v3` | 向量嵌入（DashScope） | `DashScopeEmbeddings` | `DASHSCOPE_API_KEY` |
| `BAAI/bge-large-zh-v1.5` | 向量嵌入（本地） | `HuggingFaceEmbeddings` | 自动下载到本地缓存 |
| `qwen3-rerank` | 检索重排序 | `TextReRank` | `DASHSCOPE_API_KEY` |

### 嵌入模型切换

通过环境变量 `EMBED_MODEL_TYPE` 切换：

```env
# 使用阿里云 DashScope API（默认）
EMBED_MODEL_TYPE=DASHSCOPE

# 使用本地 Sentence-Transformer（无需 API Key）
EMBED_MODEL_TYPE=SENTENCE_TRANSFORMER
SENTENCE_TRANSFORMER_MODEL_NAME=BAAI/bge-large-zh-v1.5
```

首次切换到 `SENTENCE_TRANSFORMER` 时会自动下载模型到 HuggingFace 缓存目录，之后离线可用。

### 向量数据库配置

在 `backend/config/chroma.yml` 中配置：

```yaml
collection_name: medical_knowledge
persist_directory: chroma_db
rerank_model: "qwen3-rerank"
```

### 提示词模板

在 `backend/config/prompts.yml` 中配置 7 个提示词模板，分别对应各 Agent 节点和工具的行为。

## 医疗知识库

内置 **30+ 种常见疾病** 的专业知识数据，覆盖 10 大类别：

| 类别 | 疾病 |
|------|------|
| 🫁 呼吸道疾病 | 普通感冒、流行性感冒、急性咽炎、急性扁桃体炎、急性支气管炎、肺炎 |
| 🤒 全身症状 | 发热（发烧） |
| 🫃 消化系统疾病 | 急性肠胃炎、消化不良、食物中毒 |
| 🤕 神经系统 | 紧张性头痛、偏头痛 |
| 👃 耳鼻喉科 | 鼻窦炎 |
| 🤧 过敏性疾病 | 过敏性鼻炎、荨麻疹、过敏性休克 |
| 🩹 皮肤疾病 | 湿疹、带状疱疹 |
| 👶 儿科 | 小儿发热（幼儿急疹）、小儿手足口病 |
| 🆘 急救 | 烫伤急救、鼻出血急救 |
| 😴 其他 | 中暑、失眠 |

每条知识记录包含：疾病名称、分类、症状、病因、判断方式、治疗、用药、何时就医、预防、注意事项。

## 免责声明

本项目为 **AI 辅助医疗咨询工具**，提供的信息仅供一般性参考。**不能替代专业医疗诊断**。如果症状严重或持续不缓解，请及时就医。紧急情况请拨打 120。
