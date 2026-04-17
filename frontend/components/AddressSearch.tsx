'use client'

import { useState, useRef, useEffect, useCallback } from 'react'

interface DaumPostcodeData {
  roadAddress: string
  jibunAddress: string
  autoJibunAddress: string
  zonecode: string
  sido: string
  sigungu: string
  hname: string
  bname: string
}

declare global {
  interface Window {
    daum: {
      Postcode: new (options: {
        oncomplete: (data: DaumPostcodeData) => void
        width?: string | number
        height?: string | number
      }) => { embed: (el: HTMLElement) => void }
    }
  }
}

interface Props {
  value: string
  onChange: (address: string, admCd: string, dongName: string, lat: string, lng: string) => void
  placeholder?: string
  className?: string
}

interface AddressResult {
  admCd: string
  lat: string
  lng: string
  dongNm: string
}

function loadDaumScript(): Promise<void> {
  return new Promise(resolve => {
    if (typeof window !== 'undefined' && window.daum) { resolve(); return }
    const script = document.createElement('script')
    script.src = 'https://t1.daumcdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js'
    script.onload = () => resolve()
    document.head.appendChild(script)
  })
}

// 행정동코드 + 좌표 + 정확한 행정동명을 함께 반환
async function fetchAddressData(jibunAddress: string): Promise<AddressResult> {
  const empty = { admCd: '', lat: '', lng: '', dongNm: '' }
  if (!jibunAddress) return empty
  try {
    const res = await fetch(`/api/address?query=${encodeURIComponent(jibunAddress)}`)
    const data = await res.json()
    return {
      admCd: data.documents?.[0]?.address?.h_code ?? '',
      lat: data.coords?.lat ?? '',
      lng: data.coords?.lng ?? '',
      dongNm: data.dongNm ?? '',
    }
  } catch {
    return empty
  }
}

export default function AddressSearch({ value, onChange, placeholder, className }: Props) {
  const [open, setOpen] = useState(false)
  const embedRef = useRef<HTMLDivElement>(null)
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  const handleComplete = useCallback(async (data: DaumPostcodeData) => {
    const address = data.roadAddress || data.jibunAddress
    const jibun = data.jibunAddress || data.autoJibunAddress
    setOpen(false)
    const result = await fetchAddressData(jibun)
    // coord2regioncode에서 가져온 정확한 행정동명 사용 (서울 API 매칭용)
    const dongName = result.dongNm || data.hname || data.bname
    onChangeRef.current(address, result.admCd, dongName, result.lat, result.lng)
  }, [])

  useEffect(() => {
    if (!open || !embedRef.current) return
    loadDaumScript().then(() => {
      if (!embedRef.current) return
      new window.daum.Postcode({
        oncomplete: handleComplete,
        width: '100%',
        height: '100%',
      }).embed(embedRef.current)
    })
  }, [open, handleComplete])

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`${className ?? ''} text-left`}
      >
        <span className={value ? 'text-on-surface' : 'text-outline/40'}>
          {value || (placeholder ?? '주소를 검색하세요')}
        </span>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl overflow-hidden w-full max-w-[500px] mx-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-stone-100">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-xl">location_on</span>
                <h3 className="font-semibold text-stone-800 text-sm">주소 검색</h3>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-stone-400 hover:text-stone-700 transition-colors"
              >
                <span className="material-symbols-outlined text-xl">close</span>
              </button>
            </div>
            <div ref={embedRef} style={{ height: 460 }} />
          </div>
        </div>
      )}
    </>
  )
}
