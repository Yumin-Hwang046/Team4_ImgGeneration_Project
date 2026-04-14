import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'
const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? 'http://localhost:3000'

async function exchangeCodeWithBackend(code: string): Promise<string | null> {
  const res = await fetch(`${BACKEND_URL}/auth/instagram/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  })

  if (!res.ok) return null

  const data = await res.json() as { token?: string }
  return data.token ?? null
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const code = searchParams.get('code')
  const error = searchParams.get('error')

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
    const token = await exchangeCodeWithBackend(code)

    if (token) {
      return NextResponse.redirect(
        `${APP_URL}/auth/instagram/success?token=${encodeURIComponent(token)}`
      )
    }

    return NextResponse.redirect(`${APP_URL}/auth/login?error=auth_failed`)
  } catch {
    return NextResponse.redirect(`${APP_URL}/auth/login?error=auth_failed`)
  }
}
