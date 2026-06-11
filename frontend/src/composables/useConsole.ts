import { computed, ref, type Component } from 'vue'

import {
  Activity,
  MessageSquareText,
  Plug,
  Server,
} from '@lucide/vue'

import { useHealth } from './useHealth'
import { usePlugins } from './usePlugins'
import { useProviders } from './useProviders'

export type ViewKey = 'workspace' | 'plugins' | 'channels' | 'providers'

export const views: Array<{ key: ViewKey; label: string; icon: Component }> = [
  { key: 'workspace', label: '工作台', icon: MessageSquareText },
  { key: 'plugins', label: '插件', icon: Plug },
  { key: 'channels', label: '渠道', icon: Activity },
  { key: 'providers', label: '供应商管理', icon: Server },
]

const activeView = ref<ViewKey>('workspace')
const loading = ref(false)
const lastSyncedAt = ref<string | null>(null)

const activeViewMeta = computed(() => views.find((view) => view.key === activeView.value))

const { refreshHealth } = useHealth()
const { refreshProviders } = useProviders()
const { refreshPlugins } = usePlugins()

async function refreshAll() {
  loading.value = true
  try {
    await Promise.all([refreshHealth(), refreshProviders(), refreshPlugins()])
    lastSyncedAt.value = new Date().toLocaleTimeString()
  } finally {
    loading.value = false
  }
}

export function useConsole() {
  return { activeView, loading, lastSyncedAt, activeViewMeta, refreshAll }
}
