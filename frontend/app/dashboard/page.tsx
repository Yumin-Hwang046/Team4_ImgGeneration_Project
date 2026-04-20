'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import SideBar from '@/components/SideBar'
import { api, GenerationListItem } from '@/lib/api'

const BACKEND_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

function validImgSrc(url: string | null): string | null {
  if (!url) return null
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  if (url.startsWith('/media/')) return `${BACKEND_ORIGIN}${url}`
  return null
}

function formatRelativeDate(dateStr: string): string {
  const now = new Date()
  const date = new Date(dateStr)
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffHours < 1) return '방금 전'
  if (diffHours < 24) return `${diffHours}시간 전`
  if (diffDays === 1) return '어제'
  if (diffDays < 7) return `${diffDays}일 전`
  return date.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
}

function RecentCard({ item }: { item: GenerationListItem }) {
  const src = validImgSrc(item.generated_image_url)
  const title = item.menu_name ?? item.business_category ?? '콘텐츠'

  return (
    <div className="group cursor-pointer">
      <div className="aspect-[4/5] rounded-2xl overflow-hidden mb-4 relative bg-stone-200">
        {src ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={src}
            alt={title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            {item.generation_status === 'PENDING' ? (
              <span className="material-symbols-outlined text-stone-400 text-3xl animate-spin">progress_activity</span>
            ) : (
              <span className="material-symbols-outlined text-stone-300 text-3xl">image</span>
            )}
          </div>
        )}
        <div className="absolute inset-0 bg-black/5 group-hover:bg-black/0 transition-colors" />
      </div>
      <p className="text-sm font-medium text-on-surface/90 truncate">{title}</p>
      <p className="text-[10px] text-on-surface-variant/50 mt-1.5 uppercase tracking-wider">
        {formatRelativeDate(item.created_at)}
      </p>
    </div>
  )
}

export default function DashboardPage() {
  const [recentItems, setRecentItems] = useState<GenerationListItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.generations.list()
      .then(list => setRecentItems(list.slice(0, 4)))
      .catch(() => setRecentItems([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex min-h-screen bg-surface text-on-surface">
      <SideBar />

      <main className="ml-64 flex-1 min-h-screen p-12 lg:px-24 bg-surface">
        <header className="flex justify-between items-end mb-16">
          <div>
            <span className="text-[10px] font-label tracking-[0.25em] text-primary/70 uppercase mb-4 block">
              Dashboard Overview
            </span>
          </div>
        </header>

        {/* Hero Banner */}
        <section className="mb-24">
          <div className="relative w-full aspect-[21/9] rounded-[3rem] overflow-hidden shadow-editorial-lg group bg-gradient-to-br from-stone-800 to-stone-950">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=1400&h=600&fit=crop&auto=format&q=80"
              alt="hero"
              className="absolute inset-0 w-full h-full object-cover opacity-60 group-hover:scale-105 transition-transform duration-700"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-black/40 via-transparent to-transparent" />

            <div className="absolute inset-0 flex flex-col justify-center px-16 md:px-24">
              <div className="max-w-3xl">
                <div className="mb-8">
                  <h3 className="flex flex-col gap-1">
                    <span
                      className="block mb-2 text-7xl md:text-8xl font-medium transition-transform duration-700 group-hover:-translate-y-1"
                      style={{
                        fontFamily: 'Instrument Serif, serif',
                        fontStyle: 'italic',
                        background: 'linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                      }}
                    >
                      Instagram
                    </span>
                    <span
                      className="text-white text-5xl md:text-6xl tracking-tight leading-none"
                      style={{ fontFamily: 'Instrument Serif, serif', fontStyle: 'italic', fontWeight: 300 }}
                    >
                      게시물 만들기
                    </span>
                  </h3>
                </div>
                <p className="text-white/90 font-light text-xl tracking-tight leading-relaxed max-w-sm border-l-2 border-white/20 pl-6 py-1">
                  당신의 브랜드에 감성을 더하는<br />가장 완벽한 디자인 큐레이션.
                </p>
              </div>

              <div className="absolute bottom-12 right-16">
                <Link
                  href="/studio"
                  className="group/link flex items-center gap-4 text-white transition-all px-6 py-3 rounded-full border border-white/20 hover:border-white/60 bg-white/5 backdrop-blur-md"
                >
                  <span className="text-sm font-medium tracking-widest uppercase">지금 바로 제작하기</span>
                  <span className="material-symbols-outlined text-2xl transition-transform duration-500 group-hover/link:translate-x-1.5">
                    arrow_forward
                  </span>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Recent content grid */}
        <section>
          <div className="flex justify-between items-center mb-10">
            <h4 className="text-2xl font-headline text-on-surface">최근 생성한 콘텐츠</h4>
            <Link
              href="/archive"
              className="text-xs uppercase tracking-widest text-primary/80 hover:text-primary transition-all border-b border-transparent hover:border-primary/40 pb-0.5"
            >
              View Archive
            </Link>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <span className="material-symbols-outlined text-primary text-3xl animate-spin">progress_activity</span>
            </div>
          ) : recentItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-4 text-on-surface-variant/40">
              <span className="material-symbols-outlined text-5xl">image_search</span>
              <p className="text-sm font-medium">아직 생성된 콘텐츠가 없습니다</p>
              <Link href="/studio" className="mt-2 px-6 py-3 rounded-xl bg-primary text-white text-sm font-bold hover:opacity-90 transition-opacity">
                첫 콘텐츠 만들기
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              {recentItems.map(item => <RecentCard key={item.id} item={item} />)}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
