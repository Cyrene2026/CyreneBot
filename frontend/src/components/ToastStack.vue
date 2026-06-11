<script setup lang="ts">
import { Check, CircleAlert, TerminalSquare } from '@lucide/vue'

import { useNotify } from '../composables/useNotify'

const { toasts } = useNotify()
</script>

<template>
  <div class="toast-stack" aria-live="polite">
    <div v-for="toast in toasts" :key="toast.id" class="toast" :class="toast.level">
      <CircleAlert v-if="toast.level === 'error'" :size="16" />
      <Check v-else-if="toast.level === 'success'" :size="16" />
      <TerminalSquare v-else :size="16" />
      <span>{{ toast.text }}</span>
    </div>
  </div>
</template>
