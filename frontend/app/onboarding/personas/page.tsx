import Link from 'next/link'

const personas = [
  {
    id: 1,
    title: 'Warm',
    tag: '따뜻한',
    desc: '부드러운 베이지 톤과 따뜻한 질감으로 고객에게 정서적 안정감과 포근한 편안함을 선사하는 페르소나입니다.',
    bg: 'bg-amber-100',
    image: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=600&q=80',
  },
  {
    id: 2,
    title: 'Clean',
    tag: '깔끔한',
    desc: '불필요한 요소를 덜어낸 깔끔한 미니멀리즘으로 브랜드의 본질과 순수한 가치를 전달하는 페르소나입니다.',
    bg: 'bg-slate-100',
    image: 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?auto=format&fit=crop&w=600&q=80',
  },
  {
    id: 3,
    title: 'Trendy',
    tag: '트렌디',
    desc: '최신 트렌드를 반영한 감각적이고 세련된 무드로 도시적인 젊은 감성을 전달하는 페르소나입니다.',
    bg: 'bg-rose-100',
    image: 'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=600&q=80',
  },
  {
    id: 4,
    title: 'Premium',
    tag: '프리미엄',
    desc: '고급스럽고 절제된 럭셔리 감성으로 브랜드의 품격과 깊은 신뢰감을 높여주는 페르소나입니다.',
    bg: 'bg-zinc-900',
    image: 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=600&q=80',
  },
]

export default function PersonasPage() {
  return (
    <div className="bg-surface text-on-surface min-h-screen">
      <main className="max-w-screen-2xl mx-auto px-8 py-12">
        <header className="mb-16 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4">
            <span className="text-on-secondary-container text-sm tracking-[0.05rem] uppercase">
              브랜드 페르소나 라이브러리
            </span>
            <h1 className="text-5xl font-extrabold tracking-tight text-on-surface font-headline">
              모든 브랜드 무드 탐색
            </h1>
            <p className="text-on-surface-variant max-w-xl text-lg leading-relaxed">
              The Digital Curator AI가 분석한 열 가지 이상의 고유한 브랜드 페르소나를 탐색해보세요.
            </p>
          </div>
          <Link
            href="/onboarding/report"
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-surface-container-high text-on-surface font-medium hover:bg-surface-container-highest transition-colors duration-200"
          >
            <span className="material-symbols-outlined text-xl">arrow_back</span>
            <span>뒤로가기</span>
          </Link>
        </header>

        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {personas.map((p) => (
            <article
              key={p.id}
              className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden flex flex-col hover:shadow-md transition-shadow duration-300"
            >
              <div className={`relative h-56 w-full ${p.bg} overflow-hidden flex items-end p-4`}>
                <img
                  src={p.image}
                  alt={p.title}
                  className="absolute inset-0 w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
                <span className="relative z-10 bg-white/20 backdrop-blur-md text-white px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider">
                  {p.tag}
                </span>
              </div>
              <div className="p-6 flex flex-col flex-grow">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-bold font-headline">{p.title}</h3>
                </div>
                <p className="text-on-surface-variant text-sm mb-8 flex-grow">{p.desc}</p>
                <Link
                  href="/dashboard"
                  className="w-full py-4 rounded-xl cta-gradient text-white font-bold text-center hover:opacity-90 transition-opacity block"
                >
                  선택하기
                </Link>
              </div>
            </article>
          ))}
        </section>

        <footer className="mt-20 pt-10 border-t border-outline-variant/20 flex justify-between items-center text-on-surface-variant">
          <p className="text-xs tracking-wider uppercase">© 2024 THE DIGITAL CURATOR AI · CURATED PERSONAS</p>
          <div className="flex gap-6">
            <button className="text-sm font-medium hover:text-primary transition-colors">이용약관</button>
            <button className="text-sm font-medium hover:text-primary transition-colors">개인정보처리방침</button>
          </div>
        </footer>
      </main>
    </div>
  )
}
