'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import SideBar from '@/components/SideBar'
import InstagramConnect from '@/components/InstagramConnect'
import { api, MeResponse } from '@/lib/api'

export default function SettingsPage() {
  const router = useRouter()
  const [user, setUser] = useState<MeResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.auth.me()
      .then(setUser)
      .catch(() => router.push('/auth/login'))
      .finally(() => setLoading(false))
  }, [router])

  if (loading) {
    return (
      <div className="flex min-h-screen bg-surface items-center justify-center">
        <span className="material-symbols-outlined text-primary text-3xl animate-spin">progress_activity</span>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-surface text-on-surface">
      <SideBar />

      <main className="ml-64 flex-1 min-h-screen p-12 lg:px-24 bg-surface">
        <header className="mb-12">
          <span className="text-[10px] font-label tracking-[0.25em] text-primary/70 uppercase mb-4 block">
            Account Settings
          </span>
          <h1 className="text-4xl font-headline text-on-surface" style={{ fontFamily: 'Instrument Serif, serif', fontStyle: 'italic' }}>
            설정
          </h1>
        </header>

        <div className="max-w-2xl space-y-8">
          {/* 프로필 섹션 */}
          <section className="bg-white/60 rounded-2xl p-8 border border-stone-200/60">
            <h2 className="text-xs uppercase tracking-[0.2em] text-on-surface-variant/60 mb-6">프로필</h2>
            <div className="flex items-center gap-5">
              <div className="w-14 h-14 rounded-full bg-stone-200 flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-stone-400 text-2xl">person</span>
              </div>
              <div>
                <p className="font-semibold text-on-surface text-lg">{user?.name}</p>
                <p className="text-sm text-on-surface-variant/60 mt-0.5">{user?.email}</p>
              </div>
            </div>
          </section>

          {/* Instagram 연동 섹션 */}
          <section className="bg-white/60 rounded-2xl p-8 border border-stone-200/60">
            <h2 className="text-xs uppercase tracking-[0.2em] text-on-surface-variant/60 mb-2">Instagram 연동</h2>
            <p className="text-sm text-on-surface-variant/60 mb-6">
              Instagram Business 계정을 연동하면 생성한 콘텐츠를 바로 업로드할 수 있습니다.
            </p>

            {user?.instagram_username ? (
              <div className="flex items-center gap-4 p-4 bg-stone-50 rounded-xl border border-stone-200/60">
                <div className="w-10 h-10 rounded-full instagram-gradient flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5 fill-white" viewBox="0 0 24 24">
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-on-surface">@{user.instagram_username}</p>
                  <p className="text-xs text-on-surface-variant/50 mt-0.5">Instagram Business 계정 연동됨</p>
                </div>
                <div className="flex items-center gap-1.5 text-green-600">
                  <span className="material-symbols-outlined text-lg">check_circle</span>
                  <span className="text-xs font-medium">연동됨</span>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-start gap-3 p-4 bg-amber-50 rounded-xl border border-amber-200/60">
                  <span className="material-symbols-outlined text-amber-500 text-lg mt-0.5">info</span>
                  <p className="text-sm text-amber-700">
                    아직 Instagram 계정이 연동되지 않았습니다. 아래 버튼으로 연동하세요.
                  </p>
                </div>
                <InstagramConnect variant="signup" label="으로 연동하기" linkMode />
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}
