import { ref } from 'vue'

import { ApiError } from '../api'

export type ToastLevel = 'info' | 'success' | 'error'

export interface ToastMessage {
  id: number
  level: ToastLevel
  text: string
}

// 模块级单例：所有组件共享同一份提示与登录弹窗状态。
const toasts = ref<ToastMessage[]>([])
const authOpen = ref(false)

function showToast(level: ToastLevel, text: string) {
  const id = Date.now()
  toasts.value = [...toasts.value.slice(-3), { id, level, text }]
  window.setTimeout(() => {
    toasts.value = toasts.value.filter((toast) => toast.id !== id)
  }, 4200)
}

function showApiError(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    showToast('error', `${fallback}: ${error.message}`)
    // 鉴权失败时自动弹出登录框。
    if (error.status === 401 || error.status === 403) {
      authOpen.value = true
    }
    return
  }
  showToast('error', error instanceof Error ? error.message : fallback)
}

export function useNotify() {
  return { toasts, authOpen, showToast, showApiError }
}
