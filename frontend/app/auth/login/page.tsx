'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import InstagramConnect from '@/components/InstagramConnect'
import { api } from '@/lib/api'
import { setToken } from '@/lib/auth'

const PARAM_ERROR_MESSAGES: Record<string, string> = {
  instagram_denied: '인스타그램 로그인을 취소했습니다.',
  missing_code: '인증 코드를 받지 못했습니다. 다시 시도해주세요.',
  auth_failed: '인증에 실패했습니다. 잠시 후 다시 시도해주세요.',
}

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const paramError = searchParams.get('error')
    ? PARAM_ERROR_MESSAGES[searchParams.get('error')!] ?? null
    : null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const { access_token } = await api.auth.login(email, password)
      setToken(access_token)
      router.push('/dashboard')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-surface text-on-surface min-h-screen flex flex-col items-center justify-center p-6">
      <main className="w-full max-w-md mt-16">
        <div className="bg-surface-container-lowest rounded-xl shadow-editorial p-10 md:p-12">
          <div className="mb-10">
            <h1 className="text-3xl font-extrabold text-primary tracking-tight font-headline text-center mb-1">
              The Digital Curator
            </h1>
            <p className="text-on-surface-variant text-[10px] text-center uppercase tracking-[0.3em] font-bold opacity-60">
              Premium Archive Access
            </p>
          </div>

          {(paramError || error) && (
            <div className="mb-6 px-4 py-3 rounded-lg bg-error/10 border border-error/20 text-error text-sm text-center">
              {paramError ?? error}
            </div>
          )}

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label className="block text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider mb-2">
                이메일
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="이메일을 입력하세요"
                required
                className="w-full px-5 py-4 bg-surface-container-low border-none rounded-xl focus:ring-2 focus:ring-primary-container text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider mb-2">
                비밀번호
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full px-5 py-4 bg-surface-container-low border-none rounded-xl focus:ring-2 focus:ring-primary-container text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 px-6 rounded-xl text-white font-semibold tracking-wide cta-gradient hover:opacity-90 active:scale-[0.98] transition-all duration-200 shadow-md font-headline disabled:opacity-60"
            >
              {loading ? '로그인 중...' : '로그인'}
            </button>
          </form>

          <div className="mt-8 flex justify-center items-center space-x-4 text-[13px] text-on-secondary-fixed-variant font-medium">
            <a className="hover:text-primary transition-colors" href="#">아이디 찾기</a>
            <span className="w-1 h-1 bg-outline-variant/30 rounded-full" />
            <a className="hover:text-primary transition-colors" href="#">비밀번호 찾기</a>
            <span className="w-1 h-1 bg-outline-variant/30 rounded-full" />
            <Link className="hover:text-primary transition-colors" href="/auth/signup">회원가입</Link>
          </div>

          <div className="relative my-10">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-outline-variant/20" />
            </div>
            <div className="relative flex justify-center text-[11px] uppercase tracking-widest">
              <span className="bg-surface-container-lowest px-4 text-outline">또는</span>
            </div>
          </div>

          <InstagramConnect />
        </div>

        <div className="mt-10 text-center opacity-40">
          <p className="text-[11px] tracking-widest text-on-surface-variant font-medium uppercase">
            Curated by Digital Archive Dept.
          </p>
        </div>
      </main>

      <footer className="w-full py-10 px-8 mt-auto flex flex-col md:flex-row justify-between items-center max-w-md">
        <p className="text-sm tracking-wide text-on-secondary-container mb-4 md:mb-0">
          © 2024 Digital Curator. The Human Archive.
        </p>
        <div className="flex gap-6">
          <a className="text-sm text-on-secondary-container hover:underline opacity-80 hover:opacity-100 transition-all" href="#">Privacy</a>
          <a className="text-sm text-on-secondary-container hover:underline opacity-80 hover:opacity-100 transition-all" href="#">Terms</a>
        </div>
      </footer>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
      </div>
    }>
      <LoginForm />
    </Suspense>
  )
}
