<template>
  <el-container class="app-container">
    <el-aside width="280px" class="sidebar">
      <div class="logo-section">
        智能医疗助手
      </div>

      <el-button type="success" class="new-chat-btn" @click="startNewChat" size="large">
        <el-icon><Plus /></el-icon>
        新建咨询
      </el-button>

      <el-divider content-position="left">常见问题</el-divider>

      <div class="quick-questions">
        <el-card shadow="hover" class="quick-card" @click="sendQuickMessage('我发烧38.5度，头痛，怎么办？')">
          <span>发烧38.5度</span>
        </el-card>
        <el-card shadow="hover" class="quick-card" @click="sendQuickMessage('感冒流鼻涕打喷嚏，吃什么药？')">
          <span>感冒流鼻涕</span>
        </el-card>
        <el-card shadow="hover" class="quick-card" @click="sendQuickMessage('拉肚子呕吐，可能吃坏东西了')">
          <span>腹泻呕吐</span>
        </el-card>
        <el-card shadow="hover" class="quick-card" @click="sendQuickMessage('咳嗽一周了，晚上咳得厉害')">
          <span>持续咳嗽</span>
        </el-card>
        <el-card shadow="hover" class="quick-card" @click="sendQuickMessage('皮肤起红疹很痒，是过敏吗？')">
          <span>皮肤过敏</span>
        </el-card>
        <el-card shadow="hover" class="quick-card" @click="sendQuickMessage('头晕乏力好几天了')">
          <span>头晕乏力</span>
        </el-card>
      </div>
    </el-aside>

    <el-main class="main-content">
      <el-header class="chat-header">
        <div class="header-left">
          <el-icon size="24" color="#67C23A"><FirstAidKit /></el-icon>
          <span class="header-title">医疗健康咨询</span>
          <el-tag size="small" type="warning" effect="plain">AI辅助，仅供参考</el-tag>
        </div>
        <div class="header-right">
          <el-tooltip content="新建会话" placement="bottom">
            <el-button :icon="Plus" circle @click="startNewChat" />
          </el-tooltip>
        </div>
      </el-header>

      <el-card class="messages-container" shadow="never">
        <div class="messages-scroll" ref="messagesContainer">
          <div class="welcome-message" v-if="messages.length === 0">
            <el-icon size="80" color="#67C23A" class="welcome-icon"><Plus /></el-icon>
            <h2>欢迎使用智能医疗助手</h2>
            <p>我可以帮您分析症状、提供健康建议、解答用药疑问</p>
            <div class="welcome-notice">
              <el-alert title="温馨提示" type="warning" description="我是一个AI医疗助手，提供的信息仅供一般性参考。如果症状严重或持续不缓解，请及时就医。紧急情况请拨打120。" :closable="false" show-icon />
            </div>
          </div>

          <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.role">
            <el-avatar :size="40" :class="msg.role === 'user' ? 'user-avatar' : 'assistant-avatar'">
              {{ msg.role === 'user' ? '👤' : '🏥' }}
            </el-avatar>
            <div class="message-bubble">
              <div class="message-content" v-html="msg.content"></div>
              <div class="message-time"><el-icon><Clock /></el-icon> {{ msg.time }}</div>
            </div>
          </div>

          <div v-if="isGenerating && !streamingContent" class="generating-status">
            <div class="generating-indicator">
              <el-icon class="loading-icon" :size="20"><Loading /></el-icon>
              <span>{{ thinkingText }}</span>
            </div>
            <el-button type="danger" size="small" round class="cancel-btn" @click="cancelGeneration">
              <el-icon><Close /></el-icon> 停止生成
            </el-button>
          </div>

          <div v-if="streamingContent" class="message-item assistant">
            <el-avatar :size="40" class="assistant-avatar">🏥</el-avatar>
            <div class="message-bubble">
              <div class="message-content" v-html="streamingContent"></div>
              <div class="message-time"><el-icon><Clock /></el-icon> 正在生成...</div>
            </div>
          </div>
        </div>
      </el-card>

      <el-footer class="input-footer">
        <el-input v-model="inputMessage" type="textarea" :rows="1"
          :autosize="{ minRows: 1, maxRows: 4 }" placeholder="描述您的症状或健康问题..."
          @keydown="handleKeyDown" class="chat-input" :disabled="isGenerating">
          <template #append>
            <el-button :icon="Promotion" type="success" @click="sendMessage"
              :loading="isGenerating" :disabled="!inputMessage.trim()">咨询</el-button>
          </template>
        </el-input>
        <div class="input-disclaimer">💡 本服务为AI辅助，不构成医疗诊断。紧急情况请拨打120。</div>
      </el-footer>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { marked } from 'marked'
import { Plus, Clock, Loading, Promotion, Close } from '@element-plus/icons-vue'

const messages = ref([])
const inputMessage = ref('')
const isGenerating = ref(false)
const streamingContent = ref('')
const thinkingText = ref('正在分析您的问题...')
const messagesContainer = ref(null)

let sessionId = null
let abortController = null

const getCurrentTime = () => {
  const now = new Date()
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
}

const scrollToBottom = () => nextTick(() => {
  if (messagesContainer.value) messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
})

const formatMarkdown = (content) => {
  try { return marked.parse(content) } catch { return content }
}

const addMessage = (role, content) => {
  messages.value.push({ role, content: formatMarkdown(content), time: getCurrentTime() })
  scrollToBottom()
}

const startNewChat = async () => {
  messages.value = []
  sessionId = null
  streamingContent.value = ''
  try {
    const resp = await fetch('/api/chat/new', { method: 'POST' })
    const data = await resp.json()
    sessionId = data.session_id
  } catch { sessionId = crypto.randomUUID() }
}

const sendQuickMessage = (msg) => { inputMessage.value = msg; sendMessage() }

const cancelGeneration = async () => {
  if (!sessionId) return
  try {
    await fetch('/api/chat/cancel', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sessionId }) })
  } catch {}
  if (abortController) { abortController.abort(); abortController = null }
  isGenerating.value = false
  streamingContent.value = ''
  addMessage('assistant', '⏹️ **已取消生成**')
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isGenerating.value) return
  const query = inputMessage.value.trim()
  addMessage('user', query)
  inputMessage.value = ''

  if (!sessionId) {
    try {
      const resp = await fetch('/api/chat/new', { method: 'POST' })
      const data = await resp.json()
      sessionId = data.session_id
    } catch { sessionId = crypto.randomUUID() }
  }

  isGenerating.value = true
  streamingContent.value = ''
  thinkingText.value = '正在分析您的问题...'
  abortController = new AbortController()

  try {
    const interval = setInterval(() => {
      const stages = ['正在检索医疗知识...', '正在分析症状...', '正在生成诊断建议...', '正在整理最终回答...']
      thinkingText.value = stages[Math.floor(Math.random() * stages.length)]
    }, 2000)

    const response = await fetch('/api/chat/stream', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_query: query, session_id: sessionId }),
      signal: abortController.signal
    })
    clearInterval(interval)

    if (!response.ok) throw new Error('请求失败')

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let fullContent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      while (buffer.includes('\n\n')) {
        const [event, rest] = buffer.split('\n\n', 2)
        buffer = rest
        if (event.startsWith('data: ')) {
          try {
            const data = JSON.parse(event.slice(6))
            if (data.type === 'stream') {
              fullContent += data.content
              streamingContent.value = formatMarkdown(fullContent)
              scrollToBottom()
            } else if (data.type === 'end') {
              if (data.session_id) sessionId = data.session_id
              if (fullContent) addMessage('assistant', fullContent)
              streamingContent.value = ''
              isGenerating.value = false
              break
            } else if (data.type === 'cancelled') {
              streamingContent.value = ''
              isGenerating.value = false
              addMessage('assistant', '⏹️ 已取消生成。')
              break
            } else if (data.type === 'error') {
              streamingContent.value = ''
              isGenerating.value = false
              addMessage('assistant', `❌ ${data.content}`)
              break
            }
          } catch (e) { console.error('解析数据失败:', e) }
        }
      }
    }
    if (isGenerating.value && fullContent) addMessage('assistant', fullContent)
    isGenerating.value = false
    streamingContent.value = ''
  } catch (error) {
    if (error.name === 'AbortError') return
    isGenerating.value = false
    streamingContent.value = ''
    addMessage('assistant', `❌ 抱歉，发生了错误: ${error.message}。请稍后重试。`)
  }
}

const handleKeyDown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
}

onMounted(() => { startNewChat(); scrollToBottom() })
</script>

<style scoped>
.app-container { height: 100vh; background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); }
.sidebar { background: rgba(255, 255, 255, 0.95); box-shadow: 2px 0 10px rgba(0,0,0,0.1); padding: 20px; display: flex; flex-direction: column; overflow-y: auto; }
.logo-section { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.logo-text { font-size: 20px; font-weight: 700; color: #2e7d32; margin: 0; }
.new-chat-btn { width: 100%; margin-bottom: 16px; }
.quick-questions { display: flex; flex-direction: column; gap: 8px; }
.quick-card { cursor: pointer; transition: all 0.3s ease; display: flex; align-items: center; gap: 10px; }
.quick-card:hover { transform: translateX(4px); border-color: #67C23A; }
.main-content { padding: 0; display: flex; flex-direction: column; background: #f1f8e9; }
.chat-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; background: white; border-bottom: 1px solid #e4e7ed; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.header-left { display: flex; align-items: center; gap: 12px; }
.header-title { font-size: 18px; font-weight: 600; color: #2e7d32; }
.header-right { display: flex; gap: 8px; }
.messages-container { flex: 1; overflow: hidden; border-radius: 0; background: #f1f8e9; }
.messages-scroll { height: 100%; overflow-y: auto; padding: 24px; }
.welcome-message { text-align: center; padding: 60px 20px; }
.welcome-icon { margin-bottom: 20px; animation: bounce 2s ease-in-out infinite; }
@keyframes bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
.welcome-message h2 { font-size: 26px; margin-bottom: 12px; color: #2e7d32; }
.welcome-message p { color: #666; font-size: 16px; margin-bottom: 24px; }
.welcome-notice { max-width: 500px; margin: 0 auto; }
.message-item { display: flex; gap: 14px; margin-bottom: 20px; animation: slideIn 0.3s ease-out; }
@keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.message-item.user { flex-direction: row-reverse; }
.user-avatar { background: linear-gradient(135deg, #43a047 0%, #66bb6a 100%); }
.assistant-avatar { background: linear-gradient(135deg, #00897b 0%, #26a69a 100%); }
.message-bubble { max-width: 70%; }
.message-content { padding: 14px 18px; background: white; border-radius: 16px; border-bottom-left-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); line-height: 1.7; font-size: 14px; }
.message-item.user .message-content { background: linear-gradient(135deg, #43a047 0%, #66bb6a 100%); color: white; border-bottom-left-radius: 16px; border-bottom-right-radius: 4px; }
.message-content :deep(p) { margin: 8px 0; }
.message-content :deep(code) { background: rgba(0,0,0,0.08); padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
.message-item.user .message-content :deep(code) { background: rgba(255,255,255,0.2); }
.message-content :deep(ul), .message-content :deep(ol) { padding-left: 20px; margin: 8px 0; }
.message-content :deep(li) { margin: 4px 0; }
.message-content :deep(strong) { font-weight: 600; }
.message-time { font-size: 12px; color: #999; margin-top: 6px; display: flex; align-items: center; gap: 4px; padding: 0 4px; }
.message-item.user .message-time { text-align: right; justify-content: flex-end; }
.generating-status { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; background: #e8f5e9; border-radius: 12px; margin-bottom: 16px; }
.generating-indicator { display: flex; align-items: center; gap: 10px; color: #2e7d32; font-size: 14px; }
.loading-icon { animation: rotate 1s linear infinite; color: #43a047; }
@keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.cancel-btn { flex-shrink: 0; }
.input-footer { padding: 16px 24px; background: white; border-top: 1px solid #e4e7ed; }
.chat-input { width: 100%; }
.input-disclaimer { font-size: 11px; color: #999; text-align: center; margin-top: 8px; }
</style>
