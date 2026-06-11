import type { GeneratedImage } from '../api'

const ACTION_LABELS: Record<string, string> = {
  start: '启动',
  stop: '停止',
  reload: '重载',
  check: '检查',
  enable: '启用',
  disable: '禁用',
}

const STATUS_LABELS: Record<string, string> = {
  ok: '正常',
  ready: '就绪',
  not_ready: '未就绪',
  unknown: '未知',
  error: '异常',
  enabled: '已启用',
  disabled: '已禁用',
  failed: '失败',
  running: '运行中',
  stopped: '已停止',
  configured: '已配置',
}

export function actionLabel(action: string) {
  return ACTION_LABELS[action] ?? action
}

export function statusLabel(status: string | null | undefined) {
  const raw = String(status ?? 'unknown')
  return STATUS_LABELS[raw] ?? (raw === 'unknown' ? '未知' : raw)
}

function optionalInputText(value: unknown) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : ''
  if (typeof value === 'string') return value.trim()
  return String(value).trim()
}

export function nullableNumber(value: unknown) {
  const text = optionalInputText(value)
  if (!text) return null
  const parsed = Number(text)
  return Number.isFinite(parsed) ? parsed : null
}

export function nullableInteger(value: unknown) {
  const text = optionalInputText(value)
  if (!text) return null
  const parsed = Number.parseInt(text, 10)
  return Number.isFinite(parsed) ? parsed : null
}

export function contentToText(content: unknown) {
  if (!Array.isArray(content)) return ''
  return content
    .map((part) => {
      if (part && typeof part === 'object' && 'text' in part) {
        const value = (part as { text?: unknown }).text
        return typeof value === 'string' ? value : ''
      }
      return ''
    })
    .filter(Boolean)
    .join('\n')
}

// 把生成图统一解析为可直接用于 <img src> 的字符串。
export function imageSrc(image: Pick<GeneratedImage, 'b64_json' | 'mime_type' | 'url'>) {
  if (image.b64_json) {
    return `data:${image.mime_type || 'image/png'};base64,${image.b64_json}`
  }
  return image.url || ''
}
