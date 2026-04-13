import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'

const COOKIE_OPTS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
}

async function exchangeCodeWithBackend(code: string): Promise<string | null> {
  const res = await fetch(`${BACKEND_URL}/api/auth/instagram/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  })

  if (!res.ok) return null

  const data = await res.json() as { token?: string }
  return data.token ?? null
}

export async function GET(req: NextRequest) {
  const { searchParams, origin } = new URL(req.url)
  const code = searchParams.get('code')
  const error = searchParams.get('error')

  if (error) {
    const reason = searchParams.get('error_reason') ?? error
    return NextResponse.redirect(
      new URL(`/auth/login?error=instagram_denied&reason=${encodeURIComponent(reason)}`, origin)
    )
  }

  if (!code) {
    return NextResponse.redirect(new URL('/auth/login?error=missing_code', origin))
  }

  try {
    const token = await exchangeCodeWithBackend(code)

    if (token) {
      // 백엔드 정상 응답 — 토큰 쿠키 저장 후 온보딩으로 이동
      const response = NextResponse.redirect(new URL('/onboarding/confirm', origin))
      response.cookies.set('auth_token', token, {
        ...COOKIE_OPTS,
        maxAge: 60 * 60 * 24 * 7, // 7일
      })
      return response
    }

    // 백엔드 응답은 왔지만 토큰이 없는 경우
    return NextResponse.redirect(new URL('/auth/login?error=auth_failed', origin))
  } catch {
    // 백엔드 미준비 상태 — code를 임시 쿠키에 보관 후 온보딩 진행
    const response = NextResponse.redirect(new URL('/onboarding/confirm', origin))
    response.cookies.set('ig_pending_code', code, {
      ...COOKIE_OPTS,
      maxAge: 60 * 10, // 10분 (백엔드 준비 후 교환용)
    })
    return response
  }
}
