'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { setStoredLocation, setStoredCategory, setStoredStoreName, setStoredAdmCd, setStoredDongName } from '@/lib/auth'
import AddressSearch from '@/components/AddressSearch'

const CATEGORY_OPTIONS = [
  '카페&베이커리',
  '한식당',
  '주점',
  '양식',
  '일식&아시안',
  '분식&패스트푸드',
  '고기&구이',
]

export default function SetupPage() {
  const router = useRouter()
  const [storeName, setStoreName] = useState('')
  const [category, setCategory] = useState('')
  const [location, setLocation] = useState('')
  const [admCd, setAdmCd] = useState('')
  const [error, setError] = useState<string | null>(null)

  const [dongName, setDongName] = useState('')

  const handleAddressChange = (address: string, code: string, dong: string) => {
    setLocation(address)
    setAdmCd(code)
    setDongName(dong)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!storeName.trim()) {
      setError('매장 이름을 입력해주세요.')
      return
    }
    if (!category) {
      setError('업종 카테고리를 선택해주세요.')
      return
    }
    if (!location.trim()) {
      setError('매장 위치를 입력해주세요.')
      return
    }

    setStoredStoreName(storeName.trim())
    setStoredCategory(category)
    setStoredLocation(location.trim())
    if (admCd) setStoredAdmCd(admCd)
    if (dongName) setStoredDongName(dongName)

    router.push('/onboarding/confirm')
  }

  return (
    <div className="bg-surface text-on-surface min-h-screen flex flex-col items-center justify-center p-6">
      <main className="w-full max-w-md">
        <div className="bg-surface-container-lowest rounded-xl shadow-editorial p-10 md:p-12">
          <div className="mb-8 text-center">
            <span className="text-[10px] tracking-widest text-primary uppercase mb-3 block font-label">
              Step 1 of 2
            </span>
            <h1 className="font-headline text-2xl font-bold text-on-surface tracking-tight mb-2">
              매장 정보를 입력해주세요
            </h1>
            <p className="text-on-surface-variant text-xs leading-relaxed opacity-80">
              입력하신 정보를 바탕으로 맞춤 콘텐츠를 생성합니다.
            </p>
          </div>

          {error && (
            <div className="mb-6 px-4 py-3 rounded-lg bg-error/10 border border-error/20 text-error text-sm text-center">
              {error}
            </div>
          )}

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                매장 이름
              </label>
              <input
                type="text"
                value={storeName}
                onChange={e => setStoreName(e.target.value)}
                placeholder="운영하시는 매장명을 입력하세요"
                className="w-full px-4 py-3 bg-surface-container-low border-none rounded-xl focus:ring-2 focus:ring-primary-container text-sm text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                업종 카테고리
              </label>
              <div className="relative">
                <select
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                  className="w-full px-4 py-3 bg-surface-container-low border-none rounded-xl focus:ring-2 focus:ring-primary-container text-sm text-on-surface appearance-none transition-all duration-200 outline-none"
                >
                  <option value="" disabled>업종을 선택해주세요</option>
                  {CATEGORY_OPTIONS.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
                <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none text-xl">
                  expand_more
                </span>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                매장 위치
              </label>
              <AddressSearch
                value={location}
                onChange={handleAddressChange}
                placeholder="도로명 주소로 검색 (예: 성수이로 78)"
                className="w-full px-4 py-3 bg-surface-container-low border-none rounded-xl focus:ring-2 focus:ring-primary-container text-sm text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
              />
            </div>

            <button
              type="submit"
              className="w-full py-4 px-6 rounded-xl text-white font-semibold tracking-wide cta-gradient hover:opacity-90 active:scale-[0.98] transition-all duration-200 shadow-md font-headline mt-2"
            >
              다음 단계로
            </button>
          </form>
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
