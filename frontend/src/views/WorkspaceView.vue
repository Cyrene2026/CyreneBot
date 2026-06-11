<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Loader2 } from '@lucide/vue'

import ChatComposer from '../components/ChatComposer.vue'
import FeedMessage from '../components/FeedMessage.vue'
import { useFeed } from '../composables/useFeed'

const { feed, submitting, composerModeMeta } = useFeed()
const threadRef = ref<HTMLElement | null>(null)
const hasPendingFeedItem = computed(() => feed.value.some((item) => item.pending))

watch(
  feed,
  () => {
    void nextTick(() => {
      const thread = threadRef.value
      if (thread) thread.scrollTop = thread.scrollHeight
    })
  },
  { deep: true, flush: 'post' }
)
</script>

<template>
  <!-- 统一工作台：对话 / Agent / 图像 共用一条消息流 -->
  <section class="chat-view">
    <div ref="threadRef" class="chat-thread">
      <div v-if="feed.length === 0" class="chat-empty">
        <div class="empty-mark">
          <component :is="composerModeMeta.icon" :size="28" />
        </div>
        <h2>今天想做点什么？</h2>
        <p>在下方切换对话、Agent 或图像模式，选择供应商和模型后直接输入。所有结果会汇总到这一条消息流里。</p>
      </div>

      <FeedMessage v-for="item in feed" :key="item.id" :item="item" />

      <div v-if="submitting && !hasPendingFeedItem" class="message-row assistant">
        <div class="message-avatar">
          <Loader2 :size="16" class="spin" />
        </div>
        <div class="message-body">
          <div class="message-content message-pending">{{ composerModeMeta.label }}处理中…</div>
        </div>
      </div>
    </div>

    <ChatComposer />
  </section>
</template>
