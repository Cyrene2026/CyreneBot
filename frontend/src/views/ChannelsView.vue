<script setup lang="ts">
import { ClipboardList } from '@lucide/vue'

import { useChannels } from '../composables/useChannels'

const { channelForm, channelPreviewError, requestPreview, validateChannelPayload } =
  useChannels()
</script>

<template>
  <section class="content-grid tool-view">
    <article class="panel">
      <div class="panel-heading">
        <div>
          <h2>Webhook 载荷</h2>
          <p>使用当前供应商和模型上下文准备渠道测试请求。</p>
        </div>
        <button class="tool-button" type="button" @click="validateChannelPayload">
          <ClipboardList :size="16" />
          校验
        </button>
      </div>

      <div class="form-grid">
        <label>
          渠道 ID
          <input v-model="channelForm.channelId" type="text" />
        </label>
        <label>
          回复模式
          <select v-model="channelForm.responseMode">
            <option value="chat">对话</option>
            <option value="agent">Agent</option>
          </select>
        </label>
        <label>
          触发模式
          <select v-model="channelForm.triggerMode">
            <option value="always">总是触发</option>
            <option value="keyword">关键词</option>
            <option value="mention">提及</option>
          </select>
        </label>
      </div>
      <label class="stacked">
        载荷 JSON
        <textarea v-model="channelForm.payload" rows="14" />
      </label>
      <p v-if="channelPreviewError" class="inline-error">{{ channelPreviewError }}</p>
    </article>

    <article class="panel response-panel">
      <div class="panel-heading compact">
        <div>
          <h2>请求结构</h2>
          <p>POST /channels/{{ channelForm.channelId || ':channel_id' }}/webhook</p>
        </div>
      </div>
      <pre class="response-text">{{ requestPreview }}</pre>
    </article>
  </section>
</template>
