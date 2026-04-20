'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { getStoredLocation, getStoredCategory, getStoredStoreName } from '@/lib/auth'

export default function ConfirmPage() {
  const router = useRouter()
  const [storeName, setStoreName] = useState('')
  const [category, setCategory] = useState('')
  const [location, setLocation] = useState('')

  useEffect(() => {
    const name = getStoredStoreName()
    const cat = getStoredCategory()
    const loc = getStoredLocation()

    if (!name || !cat || !loc) {
      router.replace('/onboarding/setup')
      return
    }

    setStoreName(name)
    setCategory(cat)
    setLocation(loc)
  }, [router])

  if (!storeName) return null

  return (
    <div className="bg-surface text-on-surface min-h-screen flex flex-col items-center justify-center px-6 py-12">
      <div className="text-center mb-12 max-w-2xl">
        <span className="text-[10px] tracking-widest text-primary uppercase mb-3 block font-label">
          Step 2 of 2
        </span>
        <h1 className="font-headline text-3xl md:text-4xl font-bold text-on-surface tracking-tight mb-4">
          정보를 확인해주세요
        </h1>
      </div>

      <div className="w-full max-w-lg bg-surface-container-lowest rounded-xl shadow-editorial p-8 mb-10">
        <div className="space-y-6">
          <div className="flex items-center justify-between border-b border-surface-container pb-6">
            <div>
              <span className="text-[10px] tracking-widest text-primary uppercase mb-1 block font-label">
                Store Name
              </span>
              <span className="font-headline text-xl font-semibold">{storeName}</span>
            </div>
            <div className="w-10 h-10 rounded-full bg-surface-container-low flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                storefront
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between border-b border-surface-container pb-6">
            <div>
              <span className="text-[10px] tracking-widest text-primary uppercase mb-1 block font-label">
                Business Category
              </span>
              <span className="font-headline text-xl font-semibold">{category}</span>
            </div>
            <div className="w-10 h-10 rounded-full bg-surface-container-low flex items-center justify-center">
              <span className="material-symbols-outlined text-secondary text-xl">category</span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <span className="text-[10px] tracking-widest text-primary uppercase mb-1 block font-label">
                Location
              </span>
              <span className="font-headline text-xl font-semibold">{location}</span>
            </div>
            <div className="w-10 h-10 rounded-full bg-surface-container-low flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                location_on
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col items-center gap-6">
        <Link
          href="/onboarding/analysis"
          className="cta-gradient text-white font-headline text-lg font-bold px-12 py-5 rounded-xl shadow-lg hover:scale-[0.98] transition-all duration-300 ease-out flex items-center gap-3"
        >
          분석 시작하기
          <span className="material-symbols-outlined">arrow_forward</span>
        </Link>
        <Link
          href="/onboarding/setup"
          className="text-on-surface-variant font-medium text-sm hover:underline underline-offset-8 transition-all opacity-60"
        >
          정보 수정하기
        </Link>
      </div>
    </div>
  )
}
