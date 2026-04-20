import { getToken, removeToken } from './auth'

const API_BASE = '/api'

// ─── Error ────────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: number
  email: string
  name: string
  role: string
  is_active: boolean
}

export interface MeResponse extends UserResponse {
  instagram_username?: string | null
  created_at: string
  updated_at: string
}

export interface Token {
  access_token: string
  token_type: string
}

export interface GenerationListItem {
  id: number
  menu_name: string | null
  business_category: string | null
  generated_image_url: string | null
  generation_status: string | null
  created_at: string
}

export interface GeneratedImageItem {
  id: number
  image_url: string
  final_image_url: string | null
  prompt_used: string | null
  version_no: number
  image_type: string
  status: string
  created_at: string
}

export interface GenerationDetailResponse {
  id: number
  user_id: number
  purpose: string | null
  business_category: string | null
  menu_name: string | null
  mood: string | null
  location: string | null
  target_datetime: string | null
  extra_info: string | null
  generated_copy: string | null
  hashtags: string[] | null
  weather_summary: string | null
  recommended_concept: string | null
  original_image_url: string | null
  generated_image_url: string | null
  image_mode: string | null
  generation_status: string | null
  generated_images: GeneratedImageItem[] | null
  created_at: string
}

export interface RunGenerationRequest {
  purpose: string
  business_category: string
  menu_name: string
  location: string
  target_date: string
  target_time?: string
  mood?: string
  reference_preset?: string
  extra_prompt?: string
  channel?: string
  image_file?: File
}

export interface RunGenerationResponse {
  generation_id: number
  user_id: number
  status: string
  message: string
}

export interface RegenerateImageResponse {
  generation_id: number
  status: string
  message: string
}

export interface CalendarMonthDayItem {
  date: string
  weather_summary: string | null
  has_event: boolean
  has_generation: boolean
  has_schedule: boolean
}

export interface CalendarMonthResponse {
  year: number
  month: number
  days: CalendarMonthDayItem[]
}

export interface CalendarEventItem {
  id: number
  event_date: string
  title: string
  event_type: string
  location: string | null
  description: string | null
}

export interface CalendarEventCreate {
  event_date: string
  title: string
  event_type: string
  location?: string
  description?: string
}

export interface CalendarGenerationItem {
  id: number
  menu_name: string | null
  business_category: string | null
  generated_image_url: string | null
  generation_status: string | null
  created_at: string
}

export interface UploadScheduleItem {
  id: number
  generation_id: number
  scheduled_at: string
  channel: string
  status: string
  created_at: string
}

export interface UploadScheduleCreate {
  generation_id: number
  scheduled_at: string
  channel: string
}

export interface CalendarDayResponse {
  date: string
  weather: { summary: string }
  recommendation: {
    recommended_time: string
    recommended_channel: string
    recommended_purpose: string
    recommended_concept: string
  }
  events: CalendarEventItem[]
  generations: CalendarGenerationItem[]
  schedules: UploadScheduleItem[]
}

export interface InstagramUploadResponse {
  generation_id: number
  channel: string
  status: string
  message: string
}

export interface InstagramScheduleStatusResponse {
  schedule_id: number
  generation_id: number
  channel: string
  scheduled_at: string
  status: string
  message: string
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json()
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
      return data.detail.map((d: { msg?: string }) => d.msg ?? '').join(', ')
    }
    return res.statusText
  } catch {
    return res.statusText
  }
}

function handleUnauthorized(): never {
  removeToken()
  if (typeof window !== 'undefined') window.location.href = '/auth/login'
  throw new ApiError(401, '인증이 만료되었습니다.')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...authHeaders(),
    ...(options.headers as Record<string, string> ?? {}),
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401) return handleUnauthorized()

  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res))
  }

  return res.json() as Promise<T>
}

async function requestForm<T>(path: string, body: Record<string, string>): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      ...authHeaders(),
    },
    body: new URLSearchParams(body).toString(),
  })

  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res))
  }

  return res.json() as Promise<T>
}

async function requestMultipart<T>(path: string, formData: FormData): Promise<T> {
  // Do NOT set Content-Type — browser sets it with boundary automatically
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })

  if (res.status === 401) return handleUnauthorized()

  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res))
  }

  return res.json() as Promise<T>
}

// ─── API ──────────────────────────────────────────────────────────────────────

export const api = {
  auth: {
    signup: (email: string, password: string, name: string) =>
      requestForm<UserResponse>('/auth/signup', { email, password, name }),

    login: (email: string, password: string) =>
      requestForm<Token>('/auth/login', { email, password }),

    me: () => request<MeResponse>('/auth/me'),
  },

  generations: {
    run: (params: RunGenerationRequest) => {
      const fd = new FormData()
      fd.append('purpose', params.purpose)
      fd.append('business_category', params.business_category)
      fd.append('menu_name', params.menu_name)
      fd.append('location', params.location)
      fd.append('target_date', params.target_date)
      if (params.target_time) fd.append('target_time', params.target_time)
      if (params.mood) fd.append('mood', params.mood)
      if (params.reference_preset) fd.append('reference_preset', params.reference_preset)
      if (params.extra_prompt) fd.append('extra_prompt', params.extra_prompt)
      if (params.channel) fd.append('channel', params.channel)
      if (params.image_file) fd.append('image_file', params.image_file)
      return requestMultipart<RunGenerationResponse>('/generations/run', fd)
    },

    list: () => request<GenerationListItem[]>('/generations'),

    get: (id: number) => request<GenerationDetailResponse>(`/generations/${id}`),

    getImages: (id: number) => request<GeneratedImageItem[]>(`/generations/${id}/images`),

    update: (
      id: number,
      body: Partial<{
        purpose: string
        mood: string
        extra_info: string
        generated_copy: string
        hashtags: string[]
      }>
    ) =>
      request<GenerationDetailResponse>(`/generations/${id}`, {
        method: 'PUT',
        body: JSON.stringify(body),
      }),

    regenerate: (id: number) =>
      request<RegenerateImageResponse>(`/generations/${id}/regenerate`, { method: 'POST' }),

    delete: (id: number) =>
      request<{ message: string }>(`/generations/${id}`, { method: 'DELETE' }),
  },

  calendar: {
    getMonth: (year: number, month: number, location: string) => {
      const params = new URLSearchParams({ year: String(year), month: String(month), location })
      return request<CalendarMonthResponse>(`/calendar/month?${params}`)
    },

    getDay: (date: string, location: string) => {
      const params = new URLSearchParams({ date, location })
      return request<CalendarDayResponse>(`/calendar/day?${params}`)
    },

    getEvents: (year: number, month: number, location?: string) => {
      const params = new URLSearchParams({ year: String(year), month: String(month) })
      if (location) params.set('location', location)
      return request<CalendarEventItem[]>(`/calendar/events?${params}`)
    },

    createEvent: (body: CalendarEventCreate) =>
      request<CalendarEventItem>('/calendar/events', {
        method: 'POST',
        body: JSON.stringify(body),
      }),

    deleteEvent: (id: number) =>
      request<{ message: string }>(`/calendar/events/${id}`, { method: 'DELETE' }),

    createSchedule: (body: UploadScheduleCreate) =>
      request<UploadScheduleItem>('/calendar/schedules', {
        method: 'POST',
        body: JSON.stringify(body),
      }),

    getSchedules: () => request<UploadScheduleItem[]>('/calendar/schedules'),

    deleteSchedule: (id: number) =>
      request<{ message: string }>(`/calendar/schedules/${id}`, { method: 'DELETE' }),
  },

  instagram: {
    upload: (generation_id: number, channel: string) =>
      request<InstagramUploadResponse>('/instagram/upload', {
        method: 'POST',
        body: JSON.stringify({ generation_id, channel }),
      }),

    scheduleUpload: (generation_id: number, scheduled_at: string, channel: string) =>
      request<InstagramScheduleStatusResponse>('/instagram/schedule-upload', {
        method: 'POST',
        body: JSON.stringify({ generation_id, scheduled_at, channel }),
      }),

    getStatus: (schedule_id: number) =>
      request<InstagramScheduleStatusResponse>(`/instagram/status/${schedule_id}`),
  },
}
