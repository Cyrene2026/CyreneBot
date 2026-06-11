import { computed, ref } from 'vue'

import {
  disablePlugin,
  enablePlugin,
  listPluginCommands,
  listPlugins,
  listPluginStatuses,
  reloadPlugin,
  type PluginCommandDefinition,
  type PluginDefinition,
  type PluginStatusReport,
} from '../api'
import { actionLabel } from '../utils/format'
import { useNotify } from './useNotify'

const plugins = ref<PluginDefinition[]>([])
const pluginStatuses = ref<PluginStatusReport[]>([])
const pluginCommands = ref<PluginCommandDefinition[]>([])
const pluginsLoading = ref(false)

const enabledPlugins = computed(
  () => plugins.value.filter((plugin) => plugin.enabled).length
)

const failedPlugins = computed(
  () =>
    pluginStatuses.value.filter((status) =>
      ['failed', 'error', 'disabled'].includes(String(status.status).toLowerCase())
    ).length
)

const { showToast, showApiError } = useNotify()

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

function statusForPlugin(pluginId: string) {
  return pluginStatuses.value.find((status) => status.plugin_id === pluginId)
}

function commandsForPlugin(pluginId: string) {
  return pluginCommands.value.filter((command) => command.plugin_id === pluginId)
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

export function usePlugins() {
  return {
    plugins,
    pluginStatuses,
    pluginCommands,
    pluginsLoading,
    enabledPlugins,
    failedPlugins,
    refreshPlugins,
    statusForPlugin,
    commandsForPlugin,
    operatePlugin,
  }
}
