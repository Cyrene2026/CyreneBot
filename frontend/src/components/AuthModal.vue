<script setup lang="ts">
import { KeyRound, Loader2, LogIn } from '@lucide/vue'

import { useAuth } from '../composables/useAuth'

const { authForm, authBusy, authOpen, submitLogin } = useAuth()
</script>

<template>
  <section v-if="authOpen" class="modal-backdrop" @click.self="authOpen = false">
    <form class="modal" @submit.prevent="submitLogin">
      <div class="panel-heading">
        <div>
          <h2>管理员登录</h2>
          <p>受保护接口使用会话 Cookie 鉴权。</p>
        </div>
        <KeyRound :size="20" />
      </div>
      <label>
        用户名
        <input v-model="authForm.username" autocomplete="username" type="text" />
      </label>
      <label>
        密码
        <input v-model="authForm.password" autocomplete="current-password" type="password" />
      </label>
      <div class="modal-actions">
        <button class="tool-button" type="button" @click="authOpen = false">取消</button>
        <button class="primary-button" type="submit" :disabled="authBusy">
          <Loader2 v-if="authBusy" :size="16" class="spin" />
          <LogIn v-else :size="16" />
          登录
        </button>
      </div>
    </form>
  </section>
</template>
