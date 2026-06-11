import { reactive, ref } from 'vue'

import { login, logout } from '../api'
import { useConsole } from './useConsole'
import { useNotify } from './useNotify'

const authForm = reactive({
  username: '',
  password: '',
})
const authBusy = ref(false)

const { authOpen, showToast, showApiError } = useNotify()
const { refreshAll } = useConsole()

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

export function useAuth() {
  return { authForm, authBusy, authOpen, submitLogin, submitLogout }
}
