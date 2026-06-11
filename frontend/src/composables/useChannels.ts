import { computed, reactive, ref } from 'vue'

import { useNotify } from './useNotify'
import { useProviders } from './useProviders'

const channelForm = reactive({
  channelId: 'memory',
  payload: '{\n  "text": "hello"\n}',
  responseMode: 'chat',
  triggerMode: 'always',
})
const channelPreviewError = ref('')

const { showToast } = useNotify()
const { selectedProviderId, selectedModel } = useProviders()

function validateChannelPayload() {
  try {
    JSON.parse(channelForm.payload)
    channelPreviewError.value = ''
    showToast('success', '载荷 JSON 有效')
  } catch (error) {
    channelPreviewError.value =
      error instanceof Error ? error.message : '载荷 JSON 无效'
  }
}

const requestPreview = computed(() =>
  JSON.stringify(
    {
      provider_id: selectedProviderId.value || '<供应商>',
      model: selectedModel.value || '<模型>',
      payload: channelForm.payload,
      message_response_mode: channelForm.responseMode,
      message_trigger_mode: channelForm.triggerMode,
    },
    null,
    2
  )
)

export function useChannels() {
  return {
    channelForm,
    channelPreviewError,
    requestPreview,
    validateChannelPayload,
  }
}
