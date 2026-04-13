'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function GeneratingPage() {
  const router = useRouter()

  useEffect(() => {
    const timer = setTimeout(() => router.push('/studio'), 5000)
    return () => clearTimeout(timer)
  }, [router])

  return (
    <div className="bg-surface font-body text-on-surface overflow-hidden min-h-screen">
      <header className="flex justify-between items-center w-full px-12 py-6 fixed top-0 z-50">
        <div className="text-xl font-headline font-bold tracking-tight text-on-surface">
          The Digital Curator
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-on-secondary-container tracking-widest uppercase">
            Generation in progress
          </span>
        </div>
      </header>

      <main className="h-screen w-full flex flex-col items-center justify-center relative overflow-hidden">
        {/* Background blobs */}
        <div className="absolute inset-0 z-0">
          <div className="absolute top-[10%] left-[15%] w-96 h-96 bg-primary-container/10 rounded-full blur-[100px]" />
          <div className="absolute bottom-[20%] right-[10%] w-80 h-80 bg-secondary-container/30 rounded-full blur-[120px]" />
        </div>

        <div className="relative z-10 max-w-2xl w-full px-8 text-center">
          <div className="mb-12 flex justify-center">
            <div className="w-24 h-24 rounded-xl bg-surface-container-lowest shadow-sm flex items-center justify-center relative">
              <div className="absolute inset-0 bg-primary/5 rounded-xl animate-ping opacity-25" />
              <span
                className="material-symbols-outlined text-4xl text-primary"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                auto_awesome
              </span>
            </div>
          </div>

          <div className="mb-4">
            <span className="text-sm uppercase tracking-[0.2em] text-on-secondary-container/60">
              Creative Intelligence Pipeline
            </span>
          </div>

          <h1 className="font-headline text-3xl font-bold text-on-surface mb-6 leading-tight">
            AI가 브랜드 감성을 담은<br />콘텐츠를 생성 중입니다...
          </h1>

          <p className="text-lg text-on-surface-variant/80 mb-12 max-w-md mx-auto">
            잠시만 기다려 주세요. 최고의 결과물을 위해<br />정교하게 작업 중입니다.
          </p>

          <div className="w-full max-w-md mx-auto bg-surface-container-high h-[6px] rounded-full overflow-hidden mb-4">
            <div className="progress-pulse h-full rounded-full" />
          </div>

          <div className="flex justify-between items-start mt-8 max-w-md mx-auto">
            <div className="text-left">
              <span className="block text-[10px] uppercase text-on-secondary-container/50 tracking-widest mb-1">
                Process ID
              </span>
              <span className="block font-headline text-xs font-bold text-on-surface/70">DC-2024-X9</span>
            </div>
            <div className="text-right">
              <span className="block text-[10px] uppercase text-on-secondary-container/50 tracking-widest mb-1">
                Current Task
              </span>
              <span className="block font-headline text-xs font-bold text-on-surface/70">
                Synthesizing Aesthetics
              </span>
            </div>
          </div>
        </div>

        {/* Ghost cards */}
        <div className="absolute bottom-16 left-1/2 -translate-x-1/2 w-full max-w-4xl px-12 grid grid-cols-4 gap-6 opacity-30">
          {[0, 4, 0, 4].map((offset, i) => (
            <div
              key={i}
              className={`aspect-[4/5] bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/10 flex flex-col p-4 ${
                offset ? 'translate-y-4' : ''
              }`}
            >
              <div className="w-full h-2/3 bg-surface-container-low rounded-lg mb-4" />
              <div className="h-2 w-3/4 bg-surface-container-high rounded-full" />
            </div>
          ))}
        </div>
      </main>

      <div className="fixed bottom-12 right-12 flex items-center gap-3">
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:0s]" />
          <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:0.2s]" />
          <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:0.4s]" />
        </div>
        <span className="text-xs font-medium text-on-surface tracking-wider uppercase">SECURED BY AI ENGINE</span>
      </div>
    </div>
  )
}
