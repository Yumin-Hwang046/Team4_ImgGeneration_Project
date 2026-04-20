'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import InstagramConnect from '@/components/InstagramConnect'
import { api } from '@/lib/api'
import { setToken } from '@/lib/auth'

export default function SignupPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.')
      return
    }

    setLoading(true)

    try {
      await api.auth.signup(email, password, '')
      const { access_token } = await api.auth.login(email, password)
      setToken(access_token)
      router.push('/onboarding/setup')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-surface text-on-surface min-h-screen flex flex-col items-center justify-center p-6">
      <main className="w-full max-w-md">
        <div className="bg-surface-container-lowest rounded-xl shadow-editorial">
          <div className="px-8 py-6 md:px-10">
            <div className="text-center mb-6">
              <h1 className="text-2xl font-extrabold text-on-background tracking-tight font-headline mb-1">
                회원가입
              </h1>
              <p className="text-on-surface-variant text-xs leading-relaxed opacity-80">
                디지털 큐레이터와 함께 매장의 고유한 페르소나를 구축해보세요.
              </p>
            </div>

            {error && (
              <div className="mb-4 px-4 py-3 rounded-lg bg-error/10 border border-error/20 text-error text-sm text-center">
                {error}
              </div>
            )}

            <form className="space-y-3" onSubmit={handleSubmit}>
              <div className="space-y-1">
                <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                  이메일 (아이디)
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="이메일을 입력하세요"
                  required
                  className="w-full px-4 py-2.5 bg-surface-container-low border-none rounded-lg focus:ring-2 focus:ring-primary-container text-sm text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                    비밀번호
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full px-4 py-2.5 bg-surface-container-low border-none rounded-lg focus:ring-2 focus:ring-primary-container text-sm text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                    비밀번호 확인
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full px-4 py-2.5 bg-surface-container-low border-none rounded-lg focus:ring-2 focus:ring-primary-container text-sm text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
                  />
                </div>
              </div>

              <div className="pt-2">
                <InstagramConnect variant="signup" />
                <p className="text-[9px] text-center text-on-surface-variant/60 mt-1.5 uppercase tracking-wider font-bold">
                  인스타그램 연동 시 매장 정보가 자동으로 최적화됩니다.
                </p>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3.5 px-6 rounded-lg text-white font-semibold text-sm tracking-wide cta-gradient hover:opacity-90 active:scale-[0.98] transition-all duration-200 shadow-sm font-headline disabled:opacity-60"
                >
                  {loading ? '처리 중...' : '회원가입 완료하기'}
                </button>
              </div>
            </form>

            <div className="mt-4 text-center">
              <p className="text-[11px] text-on-secondary-fixed-variant font-medium">
                이미 계정이 있으신가요?{' '}
                <Link className="text-primary hover:underline underline-offset-4 transition-colors" href="/auth/login">
                  로그인하기
                </Link>
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 text-center opacity-40">
          <p className="text-[9px] tracking-[0.2em] text-on-surface-variant font-medium uppercase">
            Curated by Digital Archive Dept.
          </p>
        </div>
      </main>
    </div>
  )
}
