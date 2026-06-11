import { ref } from 'vue'

import { checkHealth, checkReady } from '../api'

export type HealthStatus = 'unknown' | 'ok' | 'error'
export type ReadyStatus = 'unknown' | 'ready' | 'not_ready' | 'error'

const healthStatus = ref<HealthStatus>('unknown')
const readyStatus = ref<ReadyStatus>('unknown')

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

export function useHealth() {
  return { healthStatus, readyStatus, refreshHealth }
}
