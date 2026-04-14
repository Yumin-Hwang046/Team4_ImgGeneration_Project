'use client'

import { Suspense, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { setToken } from '@/lib/auth'

function InstagramSuccessContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    const token = searchParams.get('token')

    if (token) {
      setToken(token)
      router.replace('/onboarding/setup')
    } else {
      router.replace('/auth/login?error=auth_failed')
    }
  }, [searchParams, router])

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center">
      <span className="material-symbols-outlined text-primary text-4xl animate-spin">
        progress_activity
      </span>
    </div>
  )
}

export default function InstagramSuccessPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">
          progress_activity
        </span>
      </div>
    }>
      <InstagramSuccessContent />
    </Suspense>
  )
}
