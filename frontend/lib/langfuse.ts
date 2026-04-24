import { randomBytes } from 'crypto'

type TraceValue = string | number | boolean | null | undefined | TraceValue[] | { [key: string]: TraceValue }

function isEnabled() {
  return Boolean(process.env.LANGFUSE_PUBLIC_KEY && process.env.LANGFUSE_SECRET_KEY)
}

function toHex(bytes: number) {
  return randomBytes(bytes).toString('hex')
}

function nowNano() {
  return `${BigInt(Date.now()) * 1000000n}`
}

function truncate(value: string, limit = 1000) {
  return value.length > limit ? `${value.slice(0, limit)}...(truncated)` : value
}

function sanitize(value: unknown): TraceValue {
  const sensitive = ['authorization', 'token', 'api_key', 'apikey', 'secret', 'password', 'cookie', 'servicekey']

  if (value === null || value === undefined) return value as null | undefined
  if (typeof value === 'string') return truncate(value)
  if (typeof value === 'number' || typeof value === 'boolean') return value
  if (Array.isArray(value)) return value.map(sanitize)

  if (typeof value === 'object') {
    const out: Record<string, TraceValue> = {}
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      const lower = key.toLowerCase()
      out[key] = sensitive.some(token => lower.includes(token)) ? '***' : sanitize(item)
    }
    return out
  }

  return String(value)
}

function attr(key: string, value: TraceValue) {
  if (value === null || value === undefined) {
    return { key, value: { stringValue: '' } }
  }
  if (typeof value === 'boolean') return { key, value: { boolValue: value } }
  if (typeof value === 'number') {
    return Number.isInteger(value)
      ? { key, value: { intValue: String(value) } }
      : { key, value: { doubleValue: value } }
  }
  return { key, value: { stringValue: typeof value === 'string' ? value : JSON.stringify(value) } }
}

export async function traceFrontendApiCall(input: {
  name: string
  method: string
  url: string
  request?: Record<string, unknown>
  response?: { status?: number; ok?: boolean; text?: string; url?: string }
  error?: string
  tags?: string[]
}) {
  if (!isEnabled()) return

  try {
    const publicKey = process.env.LANGFUSE_PUBLIC_KEY!
    const secretKey = process.env.LANGFUSE_SECRET_KEY!
    const baseUrl = process.env.LANGFUSE_BASE_URL || process.env.LANGFUSE_HOST || 'https://cloud.langfuse.com'
    const traceId = toHex(16)
    const spanId = toHex(8)
    const start = nowNano()
    const end = nowNano()

    const attributes = [
      attr('langfuse.name', input.name),
      attr('http.method', input.method),
      attr('http.url', input.url),
      attr('request', sanitize(input.request || {})),
      attr('response.status_code', input.response?.status ?? ''),
      attr('response.ok', input.response?.ok ?? ''),
      attr('response.url', input.response?.url ?? ''),
      attr('response.text_preview', truncate(input.response?.text || '', 800)),
      attr('error', input.error || ''),
      attr('tags', input.tags || []),
      attr('runtime', 'next-route-handler'),
    ]

    await fetch(`${baseUrl}/api/public/otel/v1/traces`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Basic ${Buffer.from(`${publicKey}:${secretKey}`).toString('base64')}`,
      },
      body: JSON.stringify({
        resourceSpans: [{
          resource: {
            attributes: [
              attr('service.name', 'frontend-route-handlers'),
            ],
          },
          scopeSpans: [{
            scope: { name: 'frontend.langfuse.manual' },
            spans: [{
              traceId,
              spanId,
              name: input.name,
              kind: 1,
              startTimeUnixNano: start,
              endTimeUnixNano: end,
              attributes,
            }],
          }],
        }],
      }),
      cache: 'no-store',
    })
  } catch (error) {
    console.error('[langfuse] frontend trace failed:', error)
  }
}
