import { computed, reactive, ref, type Component } from 'vue'

import { Bot, Image as ImageIcon, MessageSquareText } from '@lucide/vue'

import {
  chat,
  generateImage,
  runAgent,
  type AgentRunResponse,
  type ChatResponse,
  type GeneratedImage,
} from '../api'
import { contentToText, nullableInteger, nullableNumber } from '../utils/format'
import { useNotify } from './useNotify'
import { useProviders } from './useProviders'

export type ComposerMode = 'chat' | 'agent' | 'image'

export const composerModes: Array<{ key: ComposerMode; label: string; icon: Component }> = [
  { key: 'chat', label: '对话', icon: MessageSquareText },
  { key: 'agent', label: 'Agent', icon: Bot },
  { key: 'image', label: '图像', icon: ImageIcon },
]

export interface FeedItem {
  id: number
  kind: 'user' | 'assistant' | 'agent' | 'images'
  // 通用文本内容（user/assistant 用；agent 存最终回复）
  content?: string
  model?: string
  time?: string
  toolCalls?: any[]
  // agent 模式专属
  agentSteps?: AgentRunResponse['steps']
  agentStopReason?: string
  // image 模式专属
  images?: GeneratedImage[]
  prompt?: string
  // 进行中标记（用于流式占位/loading）
  pending?: boolean
}

const composerMode = ref<ComposerMode>('chat')
const submitting = ref(false)
const feed = ref<FeedItem[]>([])
const chatResult = ref<ChatResponse | null>(null)
const previewImage = ref<GeneratedImage | null>(null)

const chatForm = reactive({
  sessionId: 'http',
  system: '',
  prompt: '',
  temperature: '',
  maxTokens: '',
  maxToolRounds: 1,
  allowTools: true,
})

const agentForm = reactive({
  sessionId: 'http',
  goal: '',
  message: '',
  maxSteps: 4,
  planningEnabled: true,
  replanningEnabled: true,
  memoryEnabled: false,
  maxToolCallsPerStep: '',
  maxTotalToolCalls: '',
})

const imageForm = reactive({
  prompt: '',
  count: 1,
  size: '1024x1024',
  quality: 'standard',
  responseFormat: 'b64_json' as 'b64_json' | 'url',
})

// feed 条目自增 ID，避免不同模式间 Date.now() 撞号。
let feedSeq = 0
function nextFeedId() {
  feedSeq += 1
  return feedSeq
}

const { showToast, showApiError } = useNotify()
const { selectedProviderId, selectedModel } = useProviders()

function clearFeed() {
  feed.value = []
  chatResult.value = null
}

// 收集 feed 里的对话消息，作为多轮上下文回传后端。
function chatContextMessages() {
  const messages: Array<{ role: string; content: string }> = []
  feed.value.forEach((item) => {
    if (item.kind === 'user' && item.content) {
      messages.push({ role: 'user', content: item.content })
    } else if (item.kind === 'assistant' && item.content) {
      messages.push({ role: 'assistant', content: item.content })
    }
  })
  return messages
}

async function submitChat() {
  if (!selectedProviderId.value || !selectedModel.value || !chatForm.prompt.trim()) {
    showToast('error', '请选择供应商、模型，并填写提示词')
    return
  }
  const userPrompt = chatForm.prompt.trim()
  feed.value.push({ id: nextFeedId(), kind: 'user', content: userPrompt })
  chatForm.prompt = ''
  submitting.value = true
  try {
    const messages: Array<{ role: string; content: string }> = []
    if (chatForm.system.trim()) {
      messages.push({ role: 'system', content: chatForm.system.trim() })
    }
    messages.push(...chatContextMessages())

    chatResult.value = await chat({
      provider_id: selectedProviderId.value,
      model: selectedModel.value,
      messages,
      temperature: nullableNumber(chatForm.temperature),
      max_tokens: nullableInteger(chatForm.maxTokens),
      max_tool_rounds: chatForm.allowTools ? chatForm.maxToolRounds : 0,
      metadata: {
        session_id: chatForm.sessionId || 'http',
        source: 'frontend-console',
      },
    })

    const replyText = contentToText(chatResult.value?.response?.message?.content) || ''
    feed.value.push({
      id: nextFeedId(),
      kind: 'assistant',
      content: replyText,
      model: chatResult.value?.response?.model,
      time: new Date().toLocaleTimeString(),
      toolCalls: chatResult.value?.response?.tool_calls || [],
    })

    showToast('success', '已收到模型回复')
  } catch (error) {
    showApiError(error, '对话请求失败')
  } finally {
    submitting.value = false
  }
}

async function submitAgent() {
  if (!selectedProviderId.value || !selectedModel.value || !agentForm.goal.trim()) {
    showToast('error', '请选择供应商、模型，并填写目标')
    return
  }
  feed.value.push({ id: nextFeedId(), kind: 'user', content: agentForm.goal.trim() })
  submitting.value = true
  try {
    const result = await runAgent({
      provider_id: selectedProviderId.value,
      model: selectedModel.value,
      goal: agentForm.goal.trim(),
      messages: agentForm.message.trim()
        ? [{ role: 'user', content: agentForm.message.trim() }]
        : [],
      max_steps: agentForm.maxSteps,
      planning: {
        enabled: agentForm.planningEnabled,
        replanning_enabled: agentForm.replanningEnabled,
      },
      memory_retrieval: agentForm.memoryEnabled
        ? {
            enabled: true,
            max_results: 4,
          }
        : null,
      max_tool_calls_per_step: nullableInteger(agentForm.maxToolCallsPerStep),
      max_total_tool_calls: nullableInteger(agentForm.maxTotalToolCalls),
      metadata: {
        session_id: agentForm.sessionId || 'http',
        source: 'frontend-console',
      },
    })
    feed.value.push({
      id: nextFeedId(),
      kind: 'agent',
      content: contentToText(result.response?.message?.content) || '',
      model: result.response?.model,
      time: new Date().toLocaleTimeString(),
      agentSteps: result.steps ?? [],
      agentStopReason: result.stop_reason,
    })
    showToast('success', 'Agent 运行完成')
  } catch (error) {
    showApiError(error, 'Agent 运行失败')
  } finally {
    submitting.value = false
  }
}

async function submitImage() {
  if (!selectedProviderId.value || !selectedModel.value || !imageForm.prompt.trim()) {
    showToast('error', '请选择供应商、模型，并填写提示词')
    return
  }
  const prompt = imageForm.prompt.trim()
  feed.value.push({ id: nextFeedId(), kind: 'user', content: prompt })
  submitting.value = true
  try {
    const res = await generateImage({
      provider_id: selectedProviderId.value,
      model: selectedModel.value,
      prompt,
      count: Number(imageForm.count),
      size: imageForm.size,
      quality: imageForm.quality,
      response_format: imageForm.responseFormat,
      metadata: {
        session_id: 'http-image',
        source: 'frontend-console',
      },
    })
    feed.value.push({
      id: nextFeedId(),
      kind: 'images',
      images: res.response.images || [],
      prompt,
      time: new Date().toLocaleTimeString(),
    })
    showToast('success', '图像生成完成')
  } catch (error) {
    showApiError(error, '图像生成失败')
  } finally {
    submitting.value = false
  }
}

// composer 统一分派：按当前模式调用对应提交逻辑。
function submitComposer() {
  if (submitting.value) return
  if (composerMode.value === 'chat') return submitChat()
  if (composerMode.value === 'agent') return submitAgent()
  return submitImage()
}

function addPreset(presetText: string) {
  if (imageForm.prompt) {
    imageForm.prompt += ', ' + presetText
  } else {
    imageForm.prompt = presetText
  }
}

const composerFooter = computed(
  () =>
    chatResult.value?.stop_reason ||
    chatResult.value?.response?.finish_reason ||
    'Ctrl+Enter 发送'
)

const composerModeMeta = computed(
  () => composerModes.find((mode) => mode.key === composerMode.value) ?? composerModes[0]
)

export function useFeed() {
  return {
    composerMode,
    composerModeMeta,
    submitting,
    feed,
    chatResult,
    previewImage,
    chatForm,
    agentForm,
    imageForm,
    composerFooter,
    clearFeed,
    submitComposer,
    addPreset,
  }
}
