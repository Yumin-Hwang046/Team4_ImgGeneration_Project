'use client'

import { Suspense, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { setToken } from '@/lib/auth'

interface AccountOption {
  id: string
  name: string
  username?: string
}

function SelectAccountContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const selectionToken = searchParams.get('selection_token') ?? ''
  const accountsRaw = searchParams.get('accounts') ?? '[]'

  let accounts: AccountOption[] = []
  try {
    accounts = JSON.parse(decodeURIComponent(accountsRaw))
  } catch {
    accounts = []
  }

  const handleSelect = async (account: AccountOption) => {
    setLoading(account.id)
    setError(null)

    try {
      const res = await fetch('/api/auth/instagram/select-account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          selection_token: decodeURIComponent(selectionToken),
          account_id: account.id,
          account_name: account.name,
        }),
      })

      if (!res.ok) {
        setError('계정 선택에 실패했습니다. 다시 시도해주세요.')
        return
      }

      const data = await res.json() as { token?: string }
      if (data.token) {
        setToken(data.token)
        router.replace('/onboarding/setup')
      } else {
        setError('토큰을 받지 못했습니다.')
      }
    } catch {
      setError('오류가 발생했습니다. 다시 시도해주세요.')
    } finally {
      setLoading(null)
    }
  }

  if (accounts.length === 0) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-error">연결된 Instagram 계정을 찾을 수 없습니다.</p>
          <button
            onClick={() => router.replace('/auth/login')}
            className="text-primary underline text-sm"
          >
            로그인으로 돌아가기
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-surface-container-lowest rounded-xl shadow-editorial p-8 space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-extrabold text-on-surface font-headline">
            Instagram 계정 선택
          </h1>
          <p className="text-sm text-on-surface-variant">
            연결할 Instagram 비즈니스 계정을 선택해주세요.
          </p>
        </div>

        {error && (
          <div className="px-4 py-3 rounded-lg bg-error/10 border border-error/20 text-error text-sm text-center">
            {error}
          </div>
        )}

        <div className="space-y-3">
          {accounts.map((account) => (
            <button
              key={account.id}
              onClick={() => handleSelect(account)}
              disabled={loading !== null}
              className="w-full flex items-center gap-4 p-4 rounded-xl border border-outline-variant/30 hover:border-primary hover:bg-primary/5 active:scale-[0.98] transition-all duration-200 disabled:opacity-60 text-left"
            >
              <div className="w-10 h-10 rounded-full instagram-gradient flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 fill-white" viewBox="0 0 24 24">
                  <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-on-surface truncate">{account.name}</p>
                {account.username && (
                  <p className="text-sm text-on-surface-variant">@{account.username}</p>
                )}
              </div>
              {loading === account.id ? (
                <span className="material-symbols-outlined text-primary animate-spin text-xl">
                  progress_activity
                </span>
              ) : (
                <span className="material-symbols-outlined text-outline text-xl">
                  chevron_right
                </span>
              )}
            </button>
          ))}
        </div>

        <button
          onClick={() => router.replace('/auth/login')}
          className="w-full text-center text-sm text-on-surface-variant hover:text-primary transition-colors"
        >
          취소하고 돌아가기
        </button>
      </div>
    </div>
  )
}

export default function SelectAccountPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">
          progress_activity
        </span>
      </div>
    }>
      <SelectAccountContent />
    </Suspense>
  )
}
