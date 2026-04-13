const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface GenerateImageRequest {
  prompt: string
  style?: string
  type?: 'feed' | 'story'
  referenceImage?: string
}

export interface GenerateImageResponse {
  imageUrl: string
  caption: string
  processId: string
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }

  return res.json() as Promise<T>
}

export const api = {
  generateImage: (body: GenerateImageRequest) =>
    request<GenerateImageResponse>('/api/generate', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getGenerationStatus: (processId: string) =>
    request<{ status: string; progress: number; imageUrl?: string }>(
      `/api/generate/${processId}/status`
    ),
}
