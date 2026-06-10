<script setup lang="ts">
import {
  Activity,
  Bot,
  Check,
  CircleAlert,
  ClipboardList,
  Cpu,
  Image as ImageIcon,
  KeyRound,
  Loader2,
  LogIn,
  MessageSquareText,
  Play,
  Plug,
  RefreshCw,
  Send,
  Server,
  ShieldCheck,
  Square,
  TerminalSquare,
} from '@lucide/vue'
import { computed, onMounted, reactive, ref } from 'vue'

import {
  ApiError,
  checkHealth,
  checkReady,
  checkProvider,
  chat,
  generateImage,
  disablePlugin,
  enablePlugin,
  listPluginCommands,
  listPlugins,
  listPluginStatuses,
  listProviderCatalog,
  listProviderConfigs,
  listProviderModels,
  listProviderStatuses,
  login,
  logout,
  reloadPlugin,
  reloadProvider,
  runAgent,
  startProvider,
  stopProvider,
  type AgentRunResponse,
  type ChatResponse,
  type PluginCommandDefinition,
  type PluginDefinition,
  type PluginStatusReport,
  type ProviderAdminStatus,
  type ProviderConfigSummary,
  type ProviderInfo,
  type ProviderModel,
  type GeneratedImage,
} from './api'

type ViewKey = 'workspace' | 'plugins' | 'channels' | 'providers'

type ComposerMode = 'chat' | 'agent' | 'image'

type ToastLevel = 'info' | 'success' | 'error'

interface ToastMessage {
  id: number
  level: ToastLevel
  text: string
}

const views: Array<{
  key: ViewKey
  label: string
  icon: typeof Server
}> = [
  { key: 'workspace', label: '工作台', icon: MessageSquareText },
  { key: 'plugins', label: '插件', icon: Plug },
  { key: 'channels', label: '渠道', icon: Activity },
  { key: 'providers', label: '供应商管理', icon: Server },
]

const composerModes: Array<{
  key: ComposerMode
  label: string
  icon: typeof Server
}> = [
  { key: 'chat', label: '对话', icon: MessageSquareText },
  { key: 'agent', label: 'Agent', icon: Bot },
  { key: 'image', label: '图像', icon: ImageIcon },
]

const activeView = ref<ViewKey>('workspace')
const composerMode = ref<ComposerMode>('chat')
const loading = ref(false)
const providersLoading = ref(false)
const pluginsLoading = ref(false)
const submitting = ref(false)
const authOpen = ref(false)
const authBusy = ref(false)
const healthStatus = ref<'unknown' | 'ok' | 'error'>('unknown')
const readyStatus = ref<'unknown' | 'ready' | 'not_ready' | 'error'>('unknown')
const lastSyncedAt = ref<string | null>(null)
const toasts = ref<ToastMessage[]>([])

const providers = ref<ProviderAdminStatus[]>([])
const providerCatalog = ref<ProviderInfo[]>([])
const providerConfigs = ref<ProviderConfigSummary[]>([])
const providerModels = ref<Record<string, ProviderModel[]>>({})
const selectedProviderId = ref('')
const selectedModel = ref('')

const plugins = ref<PluginDefinition[]>([])
const pluginStatuses = ref<PluginStatusReport[]>([])
const pluginCommands = ref<PluginCommandDefinition[]>([])

const authForm = reactive({
  username: '',
  password: '',
})

const chatForm = reactive({
  sessionId: 'http',
  system: '',
  prompt: '',
  temperature: '',
  maxTokens: '',
  maxToolRounds: 1,
  allowTools: true,
})

interface FeedItem {
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
const feed = ref<FeedItem[]>([])

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
const previewImage = ref<GeneratedImage | null>(null)

const channelForm = reactive({
  channelId: 'memory',
  payload: '{\n  "text": "hello"\n}',
  responseMode: 'chat',
  triggerMode: 'always',
})

const chatResult = ref<ChatResponse | null>(null)
const channelPreviewError = ref('')

// feed 条目自增 ID，避免不同模式间 Date.now() 撞号。
let feedSeq = 0
function nextFeedId() {
  feedSeq += 1
  return feedSeq
}

const selectedProvider = computed(() =>
  providers.value.find((provider) => provider.provider_id === selectedProviderId.value)
)

const activeViewMeta = computed(() => views.find((view) => view.key === activeView.value))

const selectedProviderModels = computed(() => {
  if (!selectedProviderId.value) return []
  return providerModels.value[selectedProviderId.value] ?? []
})

const runnableProviders = computed(() =>
  providers.value.filter((provider) => provider.running || provider.configured)
)

const enabledPlugins = computed(
  () => plugins.value.filter((plugin) => plugin.enabled).length
)

const failedPlugins = computed(
  () =>
    pluginStatuses.value.filter((status) =>
      ['failed', 'error', 'disabled'].includes(String(status.status).toLowerCase())
    ).length
)

const providerSummary = computed(() => {
  const running = providers.value.filter((provider) => provider.running).length
  const configured = providers.value.filter((provider) => provider.configured).length
  return { running, configured, total: providers.value.length }
})

const composerModeMeta = computed(
  () => composerModes.find((mode) => mode.key === composerMode.value) ?? composerModes[0]
)

onMounted(() => {
  void refreshAll()
})

async function refreshAll() {
  loading.value = true
  try {
    await Promise.all([refreshHealth(), refreshProviders(), refreshPlugins()])
    lastSyncedAt.value = new Date().toLocaleTimeString()
  } finally {
    loading.value = false
  }
}

async function refreshHealth() {
  const [health, ready] = await Promise.allSettled([checkHealth(), checkReady()])
  healthStatus.value =
    health.status === 'fulfilled' && health.value.status === 'ok' ? 'ok' : 'error'
  readyStatus.value =
    ready.status === 'fulfilled'
      ? ready.value.status === 'ready'
        ? 'ready'
        : 'not_ready'
      : 'error'
}

async function refreshProviders() {
  providersLoading.value = true
  try {
    const [statuses, catalog, configs] = await Promise.all([
      listProviderStatuses(),
      listProviderCatalog(),
      listProviderConfigs(),
    ])
    providers.value = statuses.providers
    providerCatalog.value = catalog.providers
    providerConfigs.value = configs.configs
    ensureProviderSelection()
    await refreshSelectedProviderModels()
  } catch (error) {
    showApiError(error, '供应商刷新失败')
  } finally {
    providersLoading.value = false
  }
}

async function refreshSelectedProviderModels() {
  if (!selectedProviderId.value) return
  try {
    const result = await listProviderModels(selectedProviderId.value)
    providerModels.value = {
      ...providerModels.value,
      [selectedProviderId.value]: result.models,
    }
    if (!selectedModel.value && result.models.length > 0) {
      selectedModel.value = result.models[0].model_id
    }
  } catch {
    providerModels.value = {
      ...providerModels.value,
      [selectedProviderId.value]: [],
    }
  }
}

async function refreshPlugins() {
  pluginsLoading.value = true
  try {
    const [pluginList, statuses, commands] = await Promise.all([
      listPlugins(),
      listPluginStatuses(),
      listPluginCommands(),
    ])
    plugins.value = pluginList.plugins
    pluginStatuses.value = statuses.statuses
    pluginCommands.value = commands.commands
  } catch (error) {
    showApiError(error, '插件刷新失败')
  } finally {
    pluginsLoading.value = false
  }
}

function ensureProviderSelection() {
  if (
    selectedProviderId.value &&
    providers.value.some((provider) => provider.provider_id === selectedProviderId.value)
  ) {
    return
  }
  const preferred = providers.value.find((provider) => provider.running)
  selectedProviderId.value =
    preferred?.provider_id ?? providers.value[0]?.provider_id ?? ''
  selectedModel.value = ''
}

async function submitLogin() {
  authBusy.value = true
  try {
    await login(authForm.username, authForm.password)
    authOpen.value = false
    authForm.password = ''
    showToast('success', '已登录')
    await refreshAll()
  } catch (error) {
    showApiError(error, '登录失败')
  } finally {
    authBusy.value = false
  }
}

async function submitLogout() {
  try {
    await logout()
    showToast('info', '已退出登录')
  } catch (error) {
    showApiError(error, '退出登录失败')
  }
}

async function operateProvider(
  providerId: string,
  action: 'start' | 'stop' | 'reload' | 'check'
) {
  try {
    if (action === 'start') await startProvider(providerId)
    if (action === 'stop') await stopProvider(providerId)
    if (action === 'reload') await reloadProvider(providerId)
    if (action === 'check') {
      const result = await checkProvider(providerId)
      showToast(result.ok ? 'success' : 'error', result.detail ?? '供应商检查完成')
    } else {
      showToast('success', `供应商${actionLabel(action)}已提交`)
    }
    await refreshProviders()
  } catch (error) {
    showApiError(error, `供应商${actionLabel(action)}失败`)
  }
}

async function operatePlugin(
  pluginId: string,
  action: 'enable' | 'disable' | 'reload'
) {
  try {
    if (action === 'enable') await enablePlugin(pluginId)
    if (action === 'disable') await disablePlugin(pluginId)
    if (action === 'reload') await reloadPlugin(pluginId)
    showToast('success', `插件${actionLabel(action)}已提交`)
    await refreshPlugins()
  } catch (error) {
    showApiError(error, `插件${actionLabel(action)}失败`)
  }
}

// composer 统一分派：按当前模式调用对应提交逻辑。
function submitComposer() {
  if (submitting.value) return
  if (composerMode.value === 'chat') return submitChat()
  if (composerMode.value === 'agent') return submitAgent()
  return submitImage()
}

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

function addPreset(presetText: string) {
  if (imageForm.prompt) {
    imageForm.prompt += ', ' + presetText
  } else {
    imageForm.prompt = presetText
  }
}

function validateChannelPayload() {
  try {
    JSON.parse(channelForm.payload)
    channelPreviewError.value = ''
    showToast('success', '载荷 JSON 有效')
  } catch (error) {
    channelPreviewError.value =
      error instanceof Error ? error.message : '载荷 JSON 无效'
  }
}

function statusForPlugin(pluginId: string) {
  return pluginStatuses.value.find((status) => status.plugin_id === pluginId)
}

function commandsForPlugin(pluginId: string) {
  return pluginCommands.value.filter((command) => command.plugin_id === pluginId)
}

function actionLabel(action: string) {
  const labels: Record<string, string> = {
    start: '启动',
    stop: '停止',
    reload: '重载',
    check: '检查',
    enable: '启用',
    disable: '禁用',
  }
  return labels[action] ?? action
}

function statusLabel(status: string | null | undefined) {
  const labels: Record<string, string> = {
    ok: '正常',
    ready: '就绪',
    not_ready: '未就绪',
    unknown: '未知',
    error: '异常',
    enabled: '已启用',
    disabled: '已禁用',
    failed: '失败',
    running: '运行中',
    stopped: '已停止',
    configured: '已配置',
  }
  const raw = String(status ?? 'unknown')
  return labels[raw] ?? (raw === 'unknown' ? '未知' : raw)
}

function configFor(providerId: string) {
  return providerConfigs.value.find((config) => config.provider_id === providerId)
}

function setProvider(providerId: string) {
  selectedProviderId.value = providerId
  selectedModel.value = ''
  void refreshSelectedProviderModels()
}

function nullableNumber(value: unknown) {
  const text = optionalInputText(value)
  if (!text) return null
  const parsed = Number(text)
  return Number.isFinite(parsed) ? parsed : null
}

function nullableInteger(value: unknown) {
  const text = optionalInputText(value)
  if (!text) return null
  const parsed = Number.parseInt(text, 10)
  return Number.isFinite(parsed) ? parsed : null
}

function optionalInputText(value: unknown) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : ''
  if (typeof value === 'string') return value.trim()
  return String(value).trim()
}

function contentToText(content: unknown) {
  if (!Array.isArray(content)) return ''
  return content
    .map((part) => {
      if (part && typeof part === 'object' && 'text' in part) {
        const value = (part as { text?: unknown }).text
        return typeof value === 'string' ? value : ''
      }
      return ''
    })
    .filter(Boolean)
    .join('\n')
}

function showApiError(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    showToast('error', `${fallback}: ${error.message}`)
    if (error.status === 401 || error.status === 403) {
      authOpen.value = true
    }
    return
  }
  showToast('error', error instanceof Error ? error.message : fallback)
}

function showToast(level: ToastLevel, text: string) {
  const id = Date.now()
  toasts.value = [...toasts.value.slice(-3), { id, level, text }]
  window.setTimeout(() => {
    toasts.value = toasts.value.filter((toast) => toast.id !== id)
  }, 4200)
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">
          <Cpu :size="20" />
        </div>
        <div>
          <strong>CyreneBot</strong>
          <span>控制台</span>
        </div>
      </div>

      <button class="new-chat-button" type="button" @click="activeView = 'workspace'; clearFeed()">
        <MessageSquareText :size="18" />
        新对话
      </button>

      <nav class="nav-list" aria-label="主导航">
        <button
          v-for="view in views"
          :key="view.key"
          class="nav-item"
          :class="{ active: activeView === view.key }"
          type="button"
          @click="activeView = view.key"
        >
          <component :is="view.icon" :size="18" />
          <span>{{ view.label }}</span>
        </button>
      </nav>

      <div class="sidebar-block">
        <div class="block-title">运行状态</div>
        <div class="signal-row">
          <span class="status-dot" :class="healthStatus" />
          <span>API {{ statusLabel(healthStatus) }}</span>
        </div>
        <div class="signal-row">
          <span class="status-dot" :class="readyStatus" />
          <span>运行时 {{ statusLabel(readyStatus) }}</span>
        </div>
        <div class="signal-row">
          <span class="status-dot" :class="failedPlugins ? 'error' : 'ready'" />
          <span>插件 {{ enabledPlugins }}/{{ plugins.length }}</span>
        </div>
        <div class="signal-row" v-if="failedPlugins">
          <span class="status-dot error" />
          <span>异常 {{ failedPlugins }}</span>
        </div>
      </div>

      <div class="sidebar-actions">
        <button class="icon-button" type="button" title="刷新" @click="refreshAll">
          <RefreshCw :size="18" :class="{ spin: loading }" />
        </button>
        <button class="icon-button" type="button" title="登录" @click="authOpen = true">
          <KeyRound :size="18" />
        </button>
        <button class="icon-button" type="button" title="退出登录" @click="submitLogout">
          <Square :size="18" />
        </button>
      </div>
    </aside>

    <main class="workspace">
      <header class="topbar">
        <div class="topbar-title">
          <component :is="activeViewMeta?.icon" :size="20" />
          <div>
            <h1>{{ activeViewMeta?.label }}</h1>
            <p>
              {{ providerSummary.running }}/{{ providerSummary.total }} 个供应商运行中
              <span v-if="lastSyncedAt"> · 已同步 {{ lastSyncedAt }}</span>
            </p>
          </div>
        </div>

        <div class="provider-picker">
          <label>
            供应商
            <select :value="selectedProviderId" @change="setProvider(($event.target as HTMLSelectElement).value)">
              <option value="">选择供应商</option>
              <option
                v-for="provider in runnableProviders"
                :key="provider.provider_id"
                :value="provider.provider_id"
              >
                {{ provider.provider_id }}
              </option>
            </select>
          </label>
          <label>
            模型
            <select v-model="selectedModel">
              <option value="">选择模型</option>
              <option
                v-for="model in selectedProviderModels"
                :key="model.model_id"
                :value="model.model_id"
              >
                {{ model.name || model.model_id }}
              </option>
            </select>
          </label>
        </div>
      </header>

      <!-- 统一工作台：对话 / Agent / 图像 共用一条消息流 -->
      <section v-if="activeView === 'workspace'" class="chat-view">
        <div class="chat-thread">
          <div v-if="feed.length === 0" class="chat-empty">
            <div class="empty-mark">
              <component :is="composerModeMeta.icon" :size="28" />
            </div>
            <h2>今天想做点什么？</h2>
            <p>在下方切换对话、Agent 或图像模式，选择供应商和模型后直接输入。所有结果会汇总到这一条消息流里。</p>
          </div>

          <div v-for="item in feed" :key="item.id" class="message-row" :class="item.kind === 'user' ? 'user' : 'assistant'">
            <div class="message-avatar">
              <component v-if="item.kind === 'agent'" :is="Bot" :size="16" />
              <component v-else-if="item.kind === 'images'" :is="ImageIcon" :size="16" />
              <template v-else>{{ item.kind === 'user' ? '我' : 'A' }}</template>
            </div>
            <div class="message-body">
              <div class="message-role">
                {{ item.kind === 'user' ? '用户' : item.kind === 'agent' ? 'Agent' : item.kind === 'images' ? '图像' : '助手' }}
              </div>

              <!-- 文本内容（user / assistant / agent 最终回复） -->
              <div v-if="item.content" class="message-content">{{ item.content }}</div>

              <!-- 对话工具调用 -->
              <div v-if="item.toolCalls && item.toolCalls.length" class="tool-call-list">
                <div class="tool-call-title">工具调用</div>
                <div v-for="call in item.toolCalls" :key="call.id" class="tool-call-item">
                  <strong>{{ call.name }}</strong>({{ call.arguments }})
                </div>
              </div>

              <!-- Agent 执行轨迹 -->
              <div v-if="item.agentSteps && item.agentSteps.length" class="step-list" style="margin-top: 14px;">
                <div v-for="step in item.agentSteps" :key="step.index" class="step-item" style="display: flex; flex-direction: column; align-items: flex-start; gap: 8px;">
                  <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
                    <span style="font-weight: 700; color: var(--accent);">步骤 {{ step.index }}</span>
                    <span class="badge ok" v-if="step.response?.finish_reason">{{ step.response.finish_reason }}</span>
                  </div>
                  <div v-if="step.response?.message?.content" style="font-size: 13px; color: var(--muted); background: rgba(15,23,42,0.04); padding: 8px 12px; border-radius: 6px; width: 100%; border: 1px solid var(--border);">
                    <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; color: var(--muted);">思考 / 说明</div>
                    <div>{{ contentToText(step.response.message.content) }}</div>
                  </div>
                  <div v-if="step.tool_calls && step.tool_calls.length" style="width: 100%;">
                    <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--muted); margin-bottom: 4px;">工具调用</div>
                    <div v-for="call in step.tool_calls" :key="call.id" style="font-family: monospace; font-size: 12px; background: rgba(15,23,42,0.05); border: 1px solid var(--border); padding: 6px 10px; border-radius: 6px; margin-bottom: 4px; overflow-x: auto;">
                      <span style="color: var(--accent); font-weight: 600;">{{ call.name }}</span>({{ call.arguments }})
                    </div>
                  </div>
                  <div v-if="step.tool_results && step.tool_results.length" style="width: 100%;">
                    <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--muted); margin-bottom: 4px;">工具结果</div>
                    <div v-for="result in step.tool_results" :key="result.call_id" style="font-family: monospace; font-size: 11px; background: rgba(15,23,42,0.05); border: 1px solid var(--border); padding: 8px 12px; border-radius: 6px; margin-bottom: 4px;">
                      <div style="display: flex; justify-content: space-between; font-size: 10px; margin-bottom: 4px;">
                        <span style="color: var(--muted);">调用 ID：{{ result.call_id }}</span>
                        <span :style="{ color: result.success ? 'var(--ok)' : 'var(--danger)' }">
                          {{ result.success ? '成功' : '错误：' + result.error }}
                        </span>
                      </div>
                      <pre style="margin: 0; white-space: pre-wrap; word-break: break-all; color: var(--code-text); max-height: 120px; overflow-y: auto;">{{ result.content || result.error }}</pre>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 生成图库 -->
              <div v-if="item.images && item.images.length" class="image-gallery">
                <div v-for="(img, idx) in item.images" :key="idx" class="image-card" @click="previewImage = img">
                  <img :src="img.b64_json ? `data:${img.mime_type || 'image/png'};base64,${img.b64_json}` : (img.url || '')" alt="生成结果" />
                  <div class="image-card-overlay">
                    <p>{{ img.revised_prompt || item.prompt }}</p>
                  </div>
                </div>
              </div>

              <div class="chat-meta" v-if="item.time || item.model">
                <span v-if="item.time">{{ item.time }}</span>
                <span v-if="item.model">{{ item.model }}</span>
              </div>
            </div>
          </div>

          <div v-if="submitting" class="message-row assistant">
            <div class="message-avatar">
              <Loader2 :size="16" class="spin" />
            </div>
            <div class="message-body">
              <div class="message-content" style="color: var(--muted);">{{ composerModeMeta.label }}处理中…</div>
            </div>
          </div>
        </div>

        <form class="composer" @submit.prevent="submitComposer">
          <div class="composer-modes">
            <button
              v-for="mode in composerModes"
              :key="mode.key"
              type="button"
              class="composer-mode"
              :class="{ active: composerMode === mode.key }"
              @click="composerMode = mode.key"
            >
              <component :is="mode.icon" :size="15" />
              {{ mode.label }}
            </button>
          </div>

          <!-- 对话模式参数 -->
          <div v-if="composerMode === 'chat'" class="composer-options">
            <label>
              系统提示
              <input v-model="chatForm.system" type="text" placeholder="可选，例如：用简洁中文回答" />
            </label>
            <label>
              会话
              <input v-model="chatForm.sessionId" type="text" />
            </label>
            <label>
              温度
              <input v-model="chatForm.temperature" type="number" step="0.1" placeholder="默认" />
            </label>
            <label>
              最大 token
              <input v-model="chatForm.maxTokens" type="number" placeholder="默认" />
            </label>
          </div>

          <!-- Agent 模式参数 -->
          <div v-else-if="composerMode === 'agent'" class="composer-options agent-options">
            <label>
              会话
              <input v-model="agentForm.sessionId" type="text" />
            </label>
            <label>
              最大步数
              <input v-model.number="agentForm.maxSteps" type="number" min="1" />
            </label>
            <label>
              每步工具
              <input v-model="agentForm.maxToolCallsPerStep" type="number" placeholder="默认" />
            </label>
            <label>
              工具总数
              <input v-model="agentForm.maxTotalToolCalls" type="number" placeholder="默认" />
            </label>
            <div class="composer-toggles">
              <label class="mini-check"><input v-model="agentForm.planningEnabled" type="checkbox" /> 规划</label>
              <label class="mini-check"><input v-model="agentForm.replanningEnabled" type="checkbox" /> 重新规划</label>
              <label class="mini-check"><input v-model="agentForm.memoryEnabled" type="checkbox" /> 记忆</label>
            </div>
          </div>

          <!-- 图像模式参数 -->
          <div v-else class="composer-options">
            <label>
              数量
              <select v-model.number="imageForm.count">
                <option :value="1">1</option>
                <option :value="2">2</option>
                <option :value="3">3</option>
                <option :value="4">4</option>
              </select>
            </label>
            <label>
              尺寸
              <select v-model="imageForm.size">
                <option value="256x256">256x256</option>
                <option value="512x512">512x512</option>
                <option value="1024x1024">1024x1024</option>
              </select>
            </label>
            <label>
              质量
              <select v-model="imageForm.quality">
                <option value="standard">标准</option>
                <option value="hd">HD</option>
              </select>
            </label>
            <label>
              格式
              <select v-model="imageForm.responseFormat">
                <option value="b64_json">Base64 JSON</option>
                <option value="url">URL</option>
              </select>
            </label>
          </div>

          <div class="composer-box">
            <textarea
              v-if="composerMode === 'chat'"
              v-model="chatForm.prompt"
              rows="1"
              placeholder="给 CyreneBot 发送消息"
              @keydown.enter.ctrl.prevent="submitComposer"
            />
            <textarea
              v-else-if="composerMode === 'agent'"
              v-model="agentForm.goal"
              rows="1"
              placeholder="描述 Agent 应该达成的目标"
              @keydown.enter.ctrl.prevent="submitComposer"
            />
            <textarea
              v-else
              v-model="imageForm.prompt"
              rows="1"
              placeholder="描述想要生成的画面"
              @keydown.enter.ctrl.prevent="submitComposer"
            />
            <div class="composer-actions">
              <template v-if="composerMode === 'chat'">
                <label class="mini-check">
                  <input v-model="chatForm.allowTools" type="checkbox" />
                  工具
                </label>
                <input
                  v-model.number="chatForm.maxToolRounds"
                  class="tool-rounds-input"
                  type="number"
                  min="0"
                  title="工具轮次"
                />
              </template>
              <button class="send-button" type="submit" :disabled="submitting">
                <Loader2 v-if="submitting" :size="18" class="spin" />
                <Send v-else-if="composerMode === 'chat'" :size="18" />
                <Bot v-else-if="composerMode === 'agent'" :size="18" />
                <ImageIcon v-else :size="18" />
              </button>
            </div>
          </div>

          <div v-if="composerMode === 'image'" class="preset-prompts">
            <span class="preset-prompt-tag" @click="addPreset('cyberpunk style, neon glowing lights')">赛博朋克</span>
            <span class="preset-prompt-tag" @click="addPreset('photorealistic, 8k resolution, highly detailed')">写实</span>
            <span class="preset-prompt-tag" @click="addPreset('anime style, vibrant colors, studio ghibli aesthetic')">动漫</span>
            <span class="preset-prompt-tag" @click="addPreset('3D render, octane render, soft lighting, clay style')">3D 渲染</span>
            <span class="preset-prompt-tag" @click="addPreset('minimalist vector art, clean lines, flat colors')">极简</span>
          </div>

          <div class="composer-footer">
            <span>{{ chatResult?.stop_reason || chatResult?.response?.finish_reason || 'Ctrl+Enter 发送' }}</span>
            <button v-if="feed.length" class="text-button" type="button" @click="clearFeed">清空</button>
          </div>
        </form>
      </section>

      <!-- 插件视图 -->
      <section v-if="activeView === 'plugins'" class="content-grid providers-grid tool-view">
        <article class="panel span-2">
          <div class="panel-heading">
            <div>
              <h2>插件</h2>
              <p>已加载插件、命令面和运行状态。</p>
            </div>
            <button class="tool-button" type="button" @click="refreshPlugins">
              <RefreshCw :size="16" :class="{ spin: pluginsLoading }" />
              刷新
            </button>
          </div>

          <div class="plugin-list">
            <div v-for="plugin in plugins" :key="plugin.plugin_id" class="plugin-row">
              <div>
                <strong>{{ plugin.name || plugin.plugin_id }}</strong>
                <span>{{ plugin.plugin_id }} · {{ plugin.version }}</span>
                <small>{{ statusLabel(statusForPlugin(plugin.plugin_id)?.status) }}</small>
              </div>
              <div class="badge-group">
                <span class="badge" :class="{ ok: plugin.enabled }">
                  {{ plugin.enabled ? '已启用' : '已禁用' }}
                </span>
                <span class="badge">{{ commandsForPlugin(plugin.plugin_id).length }} 个命令</span>
              </div>
              <div class="row-actions">
                <button class="icon-button" type="button" title="启用" @click="operatePlugin(plugin.plugin_id, 'enable')">
                  <Check :size="16" />
                </button>
                <button class="icon-button" type="button" title="禁用" @click="operatePlugin(plugin.plugin_id, 'disable')">
                  <Square :size="16" />
                </button>
                <button class="icon-button" type="button" title="重载" @click="operatePlugin(plugin.plugin_id, 'reload')">
                  <RefreshCw :size="16" />
                </button>
              </div>
            </div>
          </div>
        </article>

        <article class="panel">
          <div class="panel-heading compact">
            <div>
              <h2>命令</h2>
              <p>已注册 {{ pluginCommands.length }} 个</p>
            </div>
          </div>
          <div class="compact-list">
            <div v-for="command in pluginCommands" :key="`${command.plugin_id}:${command.name}`">
              <strong>{{ command.name }}</strong>
              <span>{{ command.plugin_id }}</span>
              <small>{{ command.usage || command.description || '暂无用法说明' }}</small>
            </div>
          </div>
        </article>
      </section>

      <!-- 渠道视图 -->
      <section v-if="activeView === 'channels'" class="content-grid tool-view">
        <article class="panel">
          <div class="panel-heading">
            <div>
              <h2>Webhook 载荷</h2>
              <p>使用当前供应商和模型上下文准备渠道测试请求。</p>
            </div>
            <button class="tool-button" type="button" @click="validateChannelPayload">
              <ClipboardList :size="16" />
              校验
            </button>
          </div>

          <div class="form-grid">
            <label>
              渠道 ID
              <input v-model="channelForm.channelId" type="text" />
            </label>
            <label>
              回复模式
              <select v-model="channelForm.responseMode">
                <option value="chat">对话</option>
                <option value="agent">Agent</option>
              </select>
            </label>
            <label>
              触发模式
              <select v-model="channelForm.triggerMode">
                <option value="always">总是触发</option>
                <option value="keyword">关键词</option>
                <option value="mention">提及</option>
              </select>
            </label>
          </div>
          <label class="stacked">
            载荷 JSON
            <textarea v-model="channelForm.payload" rows="14" />
          </label>
          <p v-if="channelPreviewError" class="inline-error">{{ channelPreviewError }}</p>
        </article>

        <article class="panel response-panel">
          <div class="panel-heading compact">
            <div>
              <h2>请求结构</h2>
              <p>POST /channels/{{ channelForm.channelId || ':channel_id' }}/webhook</p>
            </div>
          </div>
          <pre class="response-text">{{ JSON.stringify({
            provider_id: selectedProviderId || '<供应商>',
            model: selectedModel || '<模型>',
            payload: channelForm.payload,
            message_response_mode: channelForm.responseMode,
            message_trigger_mode: channelForm.triggerMode
          }, null, 2) }}</pre>
        </article>
      </section>

      <!-- 供应商管理视图 -->
      <section v-if="activeView === 'providers'" class="provider-admin-view">
        <div class="management-hero">
          <div>
            <h2>供应商统一管理</h2>
            <p>集中查看配置、运行状态、模型列表和连接操作。</p>
          </div>
          <button class="tool-button" type="button" @click="refreshProviders">
            <RefreshCw :size="16" :class="{ spin: providersLoading }" />
            刷新供应商
          </button>
        </div>

        <section class="metric-strip">
          <div class="metric">
            <span>供应商</span>
            <strong>{{ providerSummary.total }}</strong>
          </div>
          <div class="metric">
            <span>已配置</span>
            <strong>{{ providerSummary.configured }}</strong>
          </div>
          <div class="metric">
            <span>运行中</span>
            <strong>{{ providerSummary.running }}</strong>
          </div>
          <div class="metric">
            <span>模型</span>
            <strong>{{ selectedProviderModels.length }}</strong>
          </div>
        </section>

        <div class="provider-admin-grid">
          <article class="panel provider-list-panel">
            <div class="panel-heading">
              <div>
                <h2>实例</h2>
                <p>选择一个供应商作为当前全局调用目标。</p>
              </div>
            </div>

            <div class="table-list">
              <div
                v-for="provider in providers"
                :key="provider.provider_id"
                class="provider-row"
                :class="{ selected: provider.provider_id === selectedProviderId }"
                @click="setProvider(provider.provider_id)"
              >
                <div class="row-main">
                  <span class="status-dot" :class="provider.running ? 'ready' : 'not_ready'" />
                  <div>
                    <strong>{{ provider.provider_id }}</strong>
                    <span>{{ provider.provider_type || provider.info?.provider_type || '未知类型' }}</span>
                  </div>
                </div>
                <div class="badge-group">
                  <span class="badge" :class="{ ok: provider.configured }">
                    {{ provider.configured ? '已配置' : '缺少配置' }}
                  </span>
                  <span class="badge" :class="{ ok: provider.running }">
                    {{ provider.running ? '运行中' : '已停止' }}
                  </span>
                </div>
                <div class="row-actions">
                  <button class="icon-button" type="button" title="启动" @click.stop="operateProvider(provider.provider_id, 'start')">
                    <Play :size="16" />
                  </button>
                  <button class="icon-button" type="button" title="停止" @click.stop="operateProvider(provider.provider_id, 'stop')">
                    <Square :size="16" />
                  </button>
                  <button class="icon-button" type="button" title="重载" @click.stop="operateProvider(provider.provider_id, 'reload')">
                    <RefreshCw :size="16" />
                  </button>
                  <button class="icon-button" type="button" title="检查连接" @click.stop="operateProvider(provider.provider_id, 'check')">
                    <ShieldCheck :size="16" />
                  </button>
                </div>
              </div>
            </div>
          </article>

          <aside class="provider-side">
            <article class="panel">
              <div class="panel-heading compact">
                <div>
                  <h2>当前目标</h2>
                  <p>{{ selectedProviderId || '尚未选择供应商' }}</p>
                </div>
              </div>
              <dl class="detail-list" v-if="selectedProvider">
                <div>
                  <dt>类型</dt>
                  <dd>{{ selectedProvider.provider_type || selectedProvider.info?.provider_type }}</dd>
                </div>
                <div>
                  <dt>运行中</dt>
                  <dd>{{ selectedProvider.running ? '是' : '否' }}</dd>
                </div>
                <div>
                  <dt>启用</dt>
                  <dd>{{ selectedProvider.enabled ? '是' : '否' }}</dd>
                </div>
                <div>
                  <dt>API 密钥</dt>
                  <dd>{{ configFor(selectedProvider.provider_id)?.has_api_key ? '已保存' : '未保存' }}</dd>
                </div>
                <div>
                  <dt>基础 URL</dt>
                  <dd>{{ configFor(selectedProvider.provider_id)?.base_url || '默认' }}</dd>
                </div>
              </dl>
            </article>

            <article class="panel">
              <div class="panel-heading compact">
                <div>
                  <h2>可用模型</h2>
                  <p>{{ selectedProviderModels.length }} 个模型</p>
                </div>
              </div>
              <div class="compact-list">
                <div v-if="selectedProviderModels.length === 0">
                  <strong>暂无模型</strong>
                  <span>选择运行中的供应商后刷新模型。</span>
                </div>
                <div v-for="model in selectedProviderModels" :key="model.model_id">
                  <strong>{{ model.name || model.model_id }}</strong>
                  <span>{{ model.model_id }}</span>
                </div>
              </div>
            </article>
          </aside>
        </div>

        <article class="panel provider-catalog-panel">
          <div class="panel-heading compact">
            <div>
              <h2>供应商目录</h2>
              <p>{{ providerCatalog.length }} 种供应商类型</p>
            </div>
          </div>
          <div class="catalog-grid">
            <div v-for="item in providerCatalog" :key="item.provider_type" class="catalog-card">
              <strong>{{ item.name }}</strong>
              <span>{{ item.provider_type }}</span>
              <small>{{ item.description || '暂无描述' }}</small>
              <div class="capability-row">
                <span v-for="capability in item.capabilities || []" :key="capability" class="badge ok">
                  {{ capability }}
                </span>
              </div>
            </div>
          </div>
        </article>
      </section>
    </main>

    <!-- 弹窗 -->
    <section v-if="authOpen" class="modal-backdrop" @click.self="authOpen = false">
      <form class="modal" @submit.prevent="submitLogin">
        <div class="panel-heading">
          <div>
            <h2>管理员登录</h2>
            <p>受保护接口使用会话 Cookie 鉴权。</p>
          </div>
          <KeyRound :size="20" />
        </div>
        <label>
          用户名
          <input v-model="authForm.username" autocomplete="username" type="text" />
        </label>
        <label>
          密码
          <input v-model="authForm.password" autocomplete="current-password" type="password" />
        </label>
        <div class="modal-actions">
          <button class="tool-button" type="button" @click="authOpen = false">取消</button>
          <button class="primary-button" type="submit" :disabled="authBusy">
            <Loader2 v-if="authBusy" :size="16" class="spin" />
            <LogIn v-else :size="16" />
            登录
          </button>
        </div>
      </form>
    </section>

    <!-- 图像预览弹窗 -->
    <section v-if="previewImage" class="modal-backdrop" @click.self="previewImage = null">
      <div class="image-preview-modal-content">
        <img :src="previewImage.b64_json ? `data:${previewImage.mime_type || 'image/png'};base64,${previewImage.b64_json}` : (previewImage.url || '')" alt="预览" />
        <div class="image-preview-details">
          <h2>修订后的提示词</h2>
          <p>{{ previewImage.revised_prompt || imageForm.prompt }}</p>
          <div class="image-preview-actions">
            <a :href="previewImage.b64_json ? `data:${previewImage.mime_type || 'image/png'};base64,${previewImage.b64_json}` : (previewImage.url || '')" :download="`generated_image_${Date.now()}.png`" class="primary-button" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center;">
              下载
            </a>
            <button class="tool-button" type="button" @click="previewImage = null">关闭</button>
          </div>
        </div>
      </div>
    </section>

    <div class="toast-stack" aria-live="polite">
      <div v-for="toast in toasts" :key="toast.id" class="toast" :class="toast.level">
        <CircleAlert v-if="toast.level === 'error'" :size="16" />
        <Check v-else-if="toast.level === 'success'" :size="16" />
        <TerminalSquare v-else :size="16" />
        <span>{{ toast.text }}</span>
      </div>
    </div>
  </div>
</template>
