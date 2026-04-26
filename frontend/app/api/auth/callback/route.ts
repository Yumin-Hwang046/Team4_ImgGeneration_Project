import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL =
  process.env.BACKEND_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  'http://localhost:8000'
const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? 'http://localhost:3000'

interface CallbackResult {
  token?: string
  is_new_user?: boolean
  needs_selection?: boolean
  selection_token?: string
  accounts?: { id: string; name: string; username?: string }[]
}

async function exchangeCodeWithBackend(code: string, existingToken?: string): Promise<CallbackResult | null> {
  const body: Record<string, string> = { code }
  if (existingToken) body.existing_token = existingToken

  const res = await fetch(`${BACKEND_URL}/auth/instagram/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) return null
  return res.json() as Promise<CallbackResult>
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const code = searchParams.get('code')
  const error = searchParams.get('error')

  // state에 기존 JWT가 담겨 있으면 계정 연동 모드
  const state = searchParams.get('state')
  const existingToken = state?.startsWith('link:') ? state.slice(5) : undefined

  if (error) {
    const reason = searchParams.get('error_reason') ?? error
    return NextResponse.redirect(
      `${APP_URL}/auth/login?error=instagram_denied&reason=${encodeURIComponent(reason)}`
    )
  }

  if (!code) {
    return NextResponse.redirect(`${APP_URL}/auth/login?error=missing_code`)
  }

  try {
    const result = await exchangeCodeWithBackend(code, existingToken)

    if (result?.needs_selection && result.selection_token && result.accounts) {
      // 계정 여러 개 → 선택 화면으로
      const accounts = encodeURIComponent(JSON.stringify(result.accounts))
      const selToken = encodeURIComponent(result.selection_token)
      return NextResponse.redirect(
        `${APP_URL}/auth/instagram/select?selection_token=${selToken}&accounts=${accounts}`
      )
    }

    if (result?.token) {
      const isNew = result.is_new_user ? '&new=true' : ''
      const isLinked = existingToken ? '&linked=true' : ''
      return NextResponse.redirect(
        `${APP_URL}/auth/instagram/success?token=${encodeURIComponent(result.token)}${isNew}${isLinked}`
      )
    }

    return NextResponse.redirect(`${APP_URL}/auth/login?error=auth_failed`)
  } catch {
    return NextResponse.redirect(`${APP_URL}/auth/login?error=auth_failed`)
  }
}
