<script setup lang="ts">
import { useConsole } from '../composables/useConsole'
import { useProviders } from '../composables/useProviders'

const { activeViewMeta, lastSyncedAt } = useConsole()
const {
  selectedProviderId,
  selectedModel,
  runnableProviders,
  selectedProviderModels,
  providerSummary,
  setProvider,
} = useProviders()
</script>

<template>
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
</template>
