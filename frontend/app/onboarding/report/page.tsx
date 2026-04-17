'use client'

import Link from 'next/link'
import { useState, useEffect } from 'react'
import { getStoredAdmCd, getStoredLocation, getStoredDongName, getStoredLat, getStoredLng, getStoredCategory } from '@/lib/auth'

const personas = [
  {
    id: 1,
    title: 'Warm',
    desc: '부드러운 베이지 톤과 따뜻한 질감으로 고객에게 정서적 안정감과 포근한 편안함을 선사하는 페르소나입니다.',
    label: '제안 01',
    bg: 'bg-amber-100',
    image: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=400&q=80',
  },
  {
    id: 2,
    title: 'Clean',
    desc: '불필요한 요소를 덜어낸 깔끔한 미니멀리즘으로 브랜드의 본질과 순수한 가치를 전달하는 페르소나입니다.',
    label: '제안 02',
    bg: 'bg-slate-100',
    image: 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?auto=format&fit=crop&w=400&q=80',
  },
  {
    id: 3,
    title: 'Trendy',
    desc: '최신 트렌드를 반영한 감각적이고 세련된 무드로 도시적인 젊은 감성을 전달하는 페르소나입니다.',
    label: '제안 03',
    bg: 'bg-rose-100',
    image: 'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=400&q=80',
  },
  {
    id: 4,
    title: 'Premium',
    desc: '고급스럽고 절제된 럭셔리 감성으로 브랜드의 품격과 깊은 신뢰감을 높여주는 페르소나입니다.',
    label: '제안 04',
    bg: 'bg-zinc-900',
    image: 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=400&q=80',
  },
]

interface DemoRank {
  rank: number
  demographic: string
  pct: number
  count: number
}

interface StoreRank {
  rank: number
  name: string
  count: number
  demographic: string
  pct: number
}

interface PersonaReasons {
  rank1: string | null
  rank2: string | null
}

interface CommercialData {
  demographics: {
    top3: DemoRank[]
    maleRatio: number
    femaleRatio: number
  } | null
  storeTop3: StoreRank[] | null
  total: number
  recommendedPersonas: number[]
  personaReasons: PersonaReasons | null
  strategyText: string | null
  keyInsight: string | null
}

const RANK_COLORS = ['bg-white', 'bg-white/60', 'bg-white/30']

export default function ReportPage() {
  const [data, setData] = useState<CommercialData | null>(null)
  const [loading, setLoading] = useState(true)
  const location = getStoredLocation()

  useEffect(() => {
    const admCd    = getStoredAdmCd()
    const dong     = getStoredDongName()
    const lat      = getStoredLat()
    const lng      = getStoredLng()
    const category = getStoredCategory()

    if (!admCd && !dong && !lat) { setLoading(false); return }

    const params = new URLSearchParams()
    if (admCd)    params.set('admCd', admCd)
    if (dong)     params.set('dong', dong)
    if (lat)      params.set('lat', lat)
    if (lng)      params.set('lng', lng)
    if (category) params.set('category', category)

    fetch(`/api/commercial?${params}`)
      .then(res => res.json())
      .then((json: CommercialData) => setData(json))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  // 서울 API 데이터 우선, 없으면 업종 기반 추정
  const displayTop3: DemoRank[] = data?.demographics?.top3 ??
    (data?.storeTop3?.map(s => ({
      rank: s.rank,
      demographic: s.demographic,
      pct: s.pct,
      count: s.count,
    })) ?? [])

  const top1 = displayTop3[0]
  const hasData = displayTop3.length > 0
  const isRealData = !!data?.demographics

  return (
    <div className="bg-surface text-on-surface pb-20">
      <nav className="bg-surface flex justify-between items-center px-8 py-6 w-full max-w-screen-2xl mx-auto">
        <div className="text-xl font-bold text-on-surface uppercase tracking-widest font-headline">
          The Digital Curator AI
        </div>
      </nav>

      <main className="max-w-screen-xl mx-auto px-6 pt-12 pb-16">
        <header className="mb-20">
          <span className="text-xs uppercase tracking-[0.3em] text-primary mb-4 block font-semibold">
            Intelligence Report
          </span>
          <h1 className="text-5xl font-bold tracking-tight text-on-surface max-w-3xl leading-[1.1] font-headline">
            데이터로 읽는<br />로컬 인구통계 인사이트
          </h1>
          {location && (
            <p className="mt-4 text-sm text-on-surface-variant flex items-center gap-1.5">
              <span className="material-symbols-outlined text-primary text-base">location_on</span>
              {location}
            </p>
          )}
        </header>

        {/* Demographics */}
        <section className="grid grid-cols-1 md:grid-cols-12 gap-6 mb-24">
          <div className="md:col-span-7 bg-surface-container-low rounded-xl p-10 flex flex-col justify-between border border-outline-variant/10">
            <div>
              <h3 className="text-2xl font-bold mb-8 font-headline">고객 인구통계 분석</h3>

              {loading && (
                <div className="space-y-4">
                  <div className="h-10 bg-surface-container rounded-lg animate-pulse w-3/4" />
                  <div className="h-6 bg-surface-container rounded-lg animate-pulse w-1/2" />
                </div>
              )}

              {!loading && hasData && (
                <div className="space-y-6">
                  <p className="text-4xl font-medium tracking-tight leading-snug">
                    {top1.demographic}이<br />
                    <span className="text-primary underline underline-offset-8">가장 활발한 지역</span>입니다.
                  </p>
                  <div className="flex flex-wrap gap-3 mt-8">
                    {isRealData && data?.demographics && (
                      <>
                        <span className="px-5 py-2.5 bg-white rounded-full text-on-surface shadow-sm border border-outline-variant/10 text-sm">
                          여성 {data.demographics.femaleRatio}%
                        </span>
                        <span className="px-5 py-2.5 bg-white rounded-full text-on-surface shadow-sm border border-outline-variant/10 text-sm">
                          남성 {data.demographics.maleRatio}%
                        </span>
                      </>
                    )}
                    {!isRealData && data?.storeTop3?.[0] && (
                      <span className="px-5 py-2.5 bg-white rounded-full text-on-surface shadow-sm border border-outline-variant/10 text-sm">
                        주요 업종: {data.storeTop3[0].name}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {!loading && !hasData && (
                <p className="text-2xl font-medium text-on-surface-variant">
                  상권 데이터를 불러오지 못했습니다.
                </p>
              )}
            </div>
            <p className="text-secondary mt-12 text-sm leading-relaxed max-w-md">
              {isRealData
                ? '서울시 생활인구 데이터(통신사 기반)를 분석하여 해당 행정동의 실제 유동인구 연령·성별 분포를 표시합니다.'
                : '소상공인시장진흥공단 상권정보 데이터를 기반으로 업종 분포에서 주요 고객층을 추정합니다.'}
            </p>
          </div>

          <div className="md:col-span-5 bg-primary text-white rounded-xl p-10 flex flex-col justify-center">
            <h3 className="text-xl font-bold mb-2 font-headline">
              {isRealData ? '연령별 유동인구 분포' : '주요 업종별 고객층'}
            </h3>
            {isRealData && (
              <p className="text-white/50 text-xs mb-8">실제 통신사 기반 데이터</p>
            )}
            {!isRealData && <div className="mb-8" />}

            {loading && (
              <div className="space-y-8">
                {[1, 2, 3].map(i => (
                  <div key={i} className="space-y-3">
                    <div className="h-4 bg-white/20 rounded animate-pulse w-full" />
                    <div className="h-1 bg-white/10 rounded-full w-full" />
                  </div>
                ))}
              </div>
            )}

            {!loading && displayTop3.length > 0 && (
              <div className="space-y-8">
                {displayTop3.map((item, i) => (
                  <div key={item.rank}>
                    <div className="flex justify-between mb-2 text-xs font-semibold text-white/70">
                      <span className="flex items-center gap-2">
                        <span className="text-white font-bold text-base">{item.rank}위</span>
                        <span className="text-white">{item.demographic}</span>
                      </span>
                      <span className="text-white">{item.pct}%</span>
                    </div>
                    <div className="w-full h-1 bg-white/10 rounded-full">
                      <div
                        className={`${RANK_COLORS[i]} h-full rounded-full transition-all duration-700`}
                        style={{ width: `${item.pct}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!loading && !hasData && (
              <p className="text-white/60 text-sm">
                주소 설정 후 상권 데이터를 불러올 수 있습니다.
              </p>
            )}
          </div>
        </section>

        {/* AI Strategy */}
        {(data?.strategyText || data?.keyInsight) && (
          <section className="mb-12">
            <div className="bg-surface-container-low rounded-2xl p-8 border border-outline-variant/10 space-y-4">
              <span className="text-xs uppercase tracking-[0.3em] text-primary font-semibold">AI Strategy</span>
              {data.keyInsight && (
                <div className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-primary text-xl shrink-0 mt-0.5">lightbulb</span>
                  <p className="font-bold text-on-surface text-lg leading-snug">{data.keyInsight}</p>
                </div>
              )}
              {data.strategyText && (
                <p className="text-on-surface-variant text-sm leading-relaxed pl-8">{data.strategyText}</p>
              )}
            </div>
          </section>
        )}

        {/* Personas */}
        <section className="mb-16">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6 border-b border-outline-variant/10 pb-8">
            <div>
              <span className="text-xs uppercase tracking-[0.3em] text-primary mb-3 block font-semibold">
                AI Recommendation
              </span>
              <h2 className="text-4xl font-bold tracking-tight font-headline">AI 추천 브랜드 페르소나</h2>
            </div>
            <p className="text-secondary max-w-sm text-sm leading-relaxed">
              지역 유동인구와 상권 분석을 바탕으로 AI가 추천하는 최적의 브랜드 페르소나입니다.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {personas.map((p) => {
              const recList = data?.recommendedPersonas ?? []
              const recRank = recList.indexOf(p.id)
              const isRec = recRank !== -1
              return (
                <div
                  key={p.id}
                  className={`group flex flex-col h-full rounded-2xl transition-all duration-300 ${
                    isRec ? 'ring-2 ring-primary ring-offset-4 scale-[1.02]' : ''
                  }`}
                >
                  {isRec && (
                    <div className="mb-3 px-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold shrink-0">
                          {recRank + 1}
                        </span>
                        <span className="text-xs font-bold text-primary uppercase tracking-widest">
                          {recRank === 0 ? 'AI 최우선 추천' : 'AI 추천'}
                        </span>
                      </div>
                      {data?.personaReasons && (
                        <p className="text-xs text-on-surface-variant leading-relaxed pl-8">
                          {recRank === 0 ? data.personaReasons.rank1 : data.personaReasons.rank2}
                        </p>
                      )}
                    </div>
                  )}
                  <div className={`relative aspect-[4/5] rounded-xl overflow-hidden mb-6 ${p.bg}`}>
                    <img src={p.image} alt={p.title} className="absolute inset-0 w-full h-full object-cover" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                    <div className="absolute bottom-6 left-6">
                      <span className="bg-white/20 backdrop-blur-md text-white px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider mb-2 inline-block">
                        {p.label}
                      </span>
                      <h3 className="text-white text-2xl font-bold font-headline">{p.title}</h3>
                    </div>
                  </div>
                  <p className="text-on-surface-variant text-sm leading-relaxed flex-grow">{p.desc}</p>
                  <Link
                    href="/dashboard"
                    className={`mt-6 w-full py-4 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all active:scale-[0.98] ${
                      isRec
                        ? 'bg-primary text-white hover:opacity-90'
                        : 'bg-surface-container-highest text-on-surface hover:bg-primary hover:text-white'
                    }`}
                  >
                    선택하기
                    <span className="material-symbols-outlined text-sm">arrow_forward</span>
                  </Link>
                </div>
              )
            })}
          </div>
        </section>

        <div className="flex justify-center mt-12 mb-20">
          <Link
            href="/onboarding/personas"
            className="px-12 py-4 rounded-full border border-outline text-on-surface text-sm font-bold uppercase tracking-widest hover:bg-on-surface hover:text-white transition-all flex items-center gap-2"
          >
            더보기
            <span className="material-symbols-outlined text-lg">expand_more</span>
          </Link>
        </div>
      </main>

      <footer className="max-w-screen-xl mx-auto px-6 py-12 border-t border-outline-variant/10 text-center">
        <p className="text-secondary text-[10px] uppercase tracking-[0.3em]">
          © 2024 THE DIGITAL CURATOR AI. ALL RIGHTS RESERVED.
        </p>
      </footer>
    </div>
  )
}
