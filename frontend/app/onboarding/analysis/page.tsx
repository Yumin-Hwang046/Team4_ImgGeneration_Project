'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getStoredLocation, getStoredCategory, getStoredStoreName } from '@/lib/auth'

export default function AnalysisPage() {
  const router = useRouter()
  const [location, setLocation] = useState('')
  const [category, setCategory] = useState('')
  const [storeName, setStoreName] = useState('')

  useEffect(() => {
    setLocation(getStoredLocation())
    setCategory(getStoredCategory())
    setStoreName(getStoredStoreName())

    const timer = setTimeout(() => router.push('/onboarding/report'), 4000)
    return () => clearTimeout(timer)
  }, [router])

  return (
    <div className="bg-surface text-on-surface font-body min-h-screen flex flex-col items-center justify-center px-6 relative overflow-hidden">
      <div className="absolute top-[-10%] right-[-5%] w-[40rem] h-[40rem] bg-primary-container/5 rounded-full blur-[100px]" />
      <div className="absolute bottom-[-10%] left-[-5%] w-[35rem] h-[35rem] bg-secondary-container/10 rounded-full blur-[100px]" />

      <div className="w-full max-w-2xl z-10">
        <div className="text-center mb-16">
          <span className="inline-block text-primary font-medium tracking-[0.2rem] mb-6 opacity-80 uppercase text-sm">
            더 디지털 큐레이터 AI 시스템
          </span>
          <h1 className="font-headline text-4xl md:text-5xl font-bold tracking-tight text-on-surface leading-[1.2]">
            반갑습니다{storeName ? `, ${storeName}` : ''}!<br />
            <span className="text-primary-container">분석을 시작합니다.</span>
          </h1>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-20">
          <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm flex flex-col gap-4 border border-outline-variant/30">
            <div className="flex items-center justify-between">
              <span className="text-on-secondary-container opacity-60 text-sm">선택한 지역</span>
              <span className="material-symbols-outlined text-primary-container">location_on</span>
            </div>
            <div className="text-3xl font-headline font-bold text-on-surface">
              {location || '—'}
            </div>
            <div className="h-1 w-12 bg-primary-container/30 rounded-full" />
          </div>
          <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm flex flex-col gap-4 border border-outline-variant/30">
            <div className="flex items-center justify-between">
              <span className="text-on-secondary-container opacity-60 text-sm">업종</span>
              <span className="material-symbols-outlined text-primary-container">storefront</span>
            </div>
            <div className="text-3xl font-headline font-bold text-on-surface">
              {category || '—'}
            </div>
            <div className="h-1 w-12 bg-primary-container/30 rounded-full" />
          </div>
        </div>

        <div className="flex flex-col items-center">
          <div className="relative w-32 h-32 mb-10">
            <div className="absolute inset-0 border-4 border-primary-container/20 rounded-full" />
            <div className="absolute inset-0 border-t-4 border-primary rounded-full animate-spin" />
            <div className="absolute inset-4 bg-gradient-to-br from-primary to-primary-container rounded-full animate-pulse-soft flex items-center justify-center">
              <span
                className="material-symbols-outlined text-white text-3xl"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                psychology
              </span>
            </div>
          </div>

          <div className="text-center space-y-4">
            <p className="text-lg font-medium text-secondary italic">
              AI가 {location || '해당 지역'} 최신 상권 트렌드를 분석 중입니다...
            </p>
            <div className="flex gap-2 justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-primary-container animate-bounce [animation-delay:-0.3s]" />
              <div className="w-1.5 h-1.5 rounded-full bg-primary-container animate-bounce [animation-delay:-0.15s]" />
              <div className="w-1.5 h-1.5 rounded-full bg-primary-container animate-bounce" />
            </div>
          </div>
        </div>
      </div>

      <footer className="absolute bottom-12 w-full text-center">
        <p className="text-xs tracking-widest text-on-surface/40 uppercase">
          EST. 2024 © THE DIGITAL CURATOR AI UNIT
        </p>
      </footer>
    </div>
  )
}
