'use client'

import { getToken } from '@/lib/auth'

const INSTAGRAM_SVG_PATH =
  'M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z'

function buildMetaAuthUrl(linkMode: boolean): string {
  const appId = process.env.NEXT_PUBLIC_META_APP_ID
  const redirectUri = process.env.NEXT_PUBLIC_META_REDIRECT_URI

  if (!appId || !redirectUri) {
    throw new Error('NEXT_PUBLIC_META_APP_ID 또는 NEXT_PUBLIC_META_REDIRECT_URI 환경변수가 없습니다.')
  }

  const scope = 'instagram_basic,instagram_content_publish,pages_show_list,business_management'

  const existingToken = linkMode ? getToken() : null
  const params = new URLSearchParams({
    client_id: appId,
    redirect_uri: redirectUri,
    scope,
    response_type: 'code',
    ...(existingToken ? { state: `link:${existingToken}` } : {}),
  })

  return `https://www.facebook.com/dialog/oauth?${params.toString()}`
}

interface InstagramConnectProps {
  variant?: 'login' | 'signup'
  label?: string
  linkMode?: boolean  // true면 기존 로그인 계정에 Instagram 연동
}

export default function InstagramConnect({ variant = 'login', label, linkMode = false }: InstagramConnectProps) {
  const handleLogin = () => {
    try {
      const url = buildMetaAuthUrl(linkMode)
      window.location.href = url
    } catch (err) {
      alert((err as Error).message)
    }
  }

  if (variant === 'signup') {
    return (
      <button
        type="button"
        onClick={handleLogin}
        className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium text-white instagram-gradient hover:opacity-90 active:scale-[0.98] transition-all duration-200 shadow-sm"
      >
        <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path d={INSTAGRAM_SVG_PATH} />
        </svg>
        <span style={{ fontFamily: 'Lobster, cursive', fontSize: '1.1rem' }}>Instagram</span>
        <span className="font-semibold text-sm">{label ?? '과 연동하기'}</span>
      </button>
    )
  }

  return (
    <button
      type="button"
      onClick={handleLogin}
      className="w-full flex items-center justify-center gap-3 py-4 px-6 rounded-xl font-medium text-white transition-all duration-200 instagram-gradient hover:opacity-90 active:scale-[0.98]"
    >
      <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d={INSTAGRAM_SVG_PATH} />
      </svg>
      <span style={{ fontFamily: 'Lobster, cursive', fontSize: '1.25rem' }}>Instagram</span>
      <span className="font-semibold">{label ?? '으로 로그인'}</span>
    </button>
  )
}
