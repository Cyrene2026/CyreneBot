<script setup lang="ts">
import { onMounted } from 'vue'

import AppSidebar from './components/AppSidebar.vue'
import AppTopbar from './components/AppTopbar.vue'
import AuthModal from './components/AuthModal.vue'
import ImagePreviewModal from './components/ImagePreviewModal.vue'
import ToastStack from './components/ToastStack.vue'
import { useConsole } from './composables/useConsole'
import ChannelsView from './views/ChannelsView.vue'
import PluginsView from './views/PluginsView.vue'
import ProvidersView from './views/ProvidersView.vue'
import WorkspaceView from './views/WorkspaceView.vue'

const { activeView, refreshAll } = useConsole()

onMounted(() => {
  void refreshAll()
})
</script>

<template>
  <div class="shell">
    <AppSidebar />

    <main class="workspace">
      <AppTopbar />

      <WorkspaceView v-if="activeView === 'workspace'" />
      <PluginsView v-else-if="activeView === 'plugins'" />
      <ChannelsView v-else-if="activeView === 'channels'" />
      <ProvidersView v-else-if="activeView === 'providers'" />
    </main>

    <AuthModal />
    <ImagePreviewModal />
    <ToastStack />
  </div>
</template>
