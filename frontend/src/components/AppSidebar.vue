<script setup lang="ts">
import { Cpu, KeyRound, MessageSquareText, RefreshCw, Square } from '@lucide/vue'

import { useAuth } from '../composables/useAuth'
import { useConsole, views } from '../composables/useConsole'
import { useFeed } from '../composables/useFeed'
import { useHealth } from '../composables/useHealth'
import { usePlugins } from '../composables/usePlugins'
import { statusLabel } from '../utils/format'

const { activeView, loading, refreshAll } = useConsole()
const { clearFeed } = useFeed()
const { healthStatus, readyStatus } = useHealth()
const { plugins, enabledPlugins, failedPlugins } = usePlugins()
const { authOpen, submitLogout } = useAuth()

function startNewChat() {
  activeView.value = 'workspace'
  clearFeed()
}
</script>

<template>
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

    <button class="new-chat-button" type="button" @click="startNewChat">
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
</template>
