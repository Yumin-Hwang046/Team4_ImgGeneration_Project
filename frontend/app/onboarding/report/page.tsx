import Link from 'next/link'

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

export default function ReportPage() {
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
        </header>

        {/* Demographics */}
        <section className="grid grid-cols-1 md:grid-cols-12 gap-6 mb-24">
          <div className="md:col-span-7 bg-surface-container-low rounded-xl p-10 flex flex-col justify-between border border-outline-variant/10">
            <div>
              <h3 className="text-2xl font-bold mb-8 font-headline">고객 인구통계 분석</h3>
              <div className="space-y-6">
                <p className="text-4xl font-medium tracking-tight leading-snug">
                  20-30대 여성이 <br />
                  <span className="text-primary underline underline-offset-8">가장 활발한 지역</span>입니다.
                </p>
                <div className="flex gap-3 mt-8">
                  <span className="px-6 py-3 bg-white rounded-full text-on-surface shadow-sm border border-outline-variant/10 text-sm">
                    주말 유동인구 최대
                  </span>
                  <span className="px-6 py-3 bg-white rounded-full text-on-surface shadow-sm border border-outline-variant/10 text-sm">
                    여성 비율 62%
                  </span>
                </div>
              </div>
            </div>
            <p className="text-secondary mt-12 text-sm leading-relaxed max-w-md">
              해당 지역은 트렌드에 민감한 2030 여성층의 방문 빈도가 전국 평균 대비 1.5배 높게 측정되었습니다.
            </p>
          </div>

          <div className="md:col-span-5 bg-primary text-white rounded-xl p-10 flex flex-col justify-center">
            <h3 className="text-xl font-bold mb-10 font-headline">연령별 인구 분포</h3>
            <div className="space-y-8">
              {[
                { label: '2030 Millennials & Gen Z', pct: 68, opacity: 'bg-white' },
                { label: '4050 Generation', pct: 24, opacity: 'bg-white/40' },
                { label: 'Others', pct: 8, opacity: 'bg-white/40' },
              ].map(({ label, pct, opacity }) => (
                <div key={label}>
                  <div className="flex justify-between mb-3 text-xs uppercase tracking-widest font-semibold text-white/70">
                    <span>{label}</span>
                    <span className="text-white">{pct}%</span>
                  </div>
                  <div className="w-full h-1 bg-white/10 rounded-full">
                    <div className={`${opacity} h-full rounded-full`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

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
              브랜드의 핵심 가치와 시장 트렌드를 결합하여 AI가 도출한 최적의 4가지 무드보드와 페르소나 제안입니다.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {personas.map((p) => (
              <div key={p.id} className="group flex flex-col h-full">
                <div className={`relative aspect-[4/5] rounded-xl overflow-hidden mb-6 ${p.bg}`}>
                  <img
                    src={p.image}
                    alt={p.title}
                    className="absolute inset-0 w-full h-full object-cover"
                  />
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
                  className="mt-6 w-full py-4 rounded-xl bg-surface-container-highest text-on-surface font-semibold flex items-center justify-center gap-2 transition-all hover:bg-primary hover:text-white active:scale-[0.98]"
                >
                  선택하기
                  <span className="material-symbols-outlined text-sm">arrow_forward</span>
                </Link>
              </div>
            ))}
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
