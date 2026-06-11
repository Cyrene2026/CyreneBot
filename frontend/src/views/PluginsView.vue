<script setup lang="ts">
import { Check, RefreshCw, Square } from '@lucide/vue'

import { usePlugins } from '../composables/usePlugins'
import { statusLabel } from '../utils/format'

const {
  plugins,
  pluginCommands,
  pluginsLoading,
  refreshPlugins,
  statusForPlugin,
  commandsForPlugin,
  operatePlugin,
} = usePlugins()
</script>

<template>
  <section class="content-grid providers-grid tool-view">
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
</template>
