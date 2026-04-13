import Link from 'next/link'
import SideBar from '@/components/SideBar'

const recentContents = [
  { id: 1, title: '여름 시즌 채소 프로모션', time: 'Created 2h ago', img: 'https://images.unsplash.com/photo-1540420773420-3366772f4999?w=400&h=500&fit=crop&auto=format&q=80' },
  { id: 2, title: '오후의 휴식 커피 원두', time: 'Created Yesterday', img: 'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&h=500&fit=crop&auto=format&q=80' },
  { id: 3, title: '봄맞이 인테리어 소품', time: 'Created 3d ago', img: 'https://images.unsplash.com/photo-1490750967868-88df5691cc07?w=400&h=500&fit=crop&auto=format&q=80' },
  { id: 4, title: '매일 아침 갓 구운 빵', time: 'Created 1w ago', img: 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=500&fit=crop&auto=format&q=80' },
]

export default function DashboardPage() {
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

          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {recentContents.map((item) => (
              <div key={item.id} className="group cursor-pointer">
                <div className="aspect-[4/5] rounded-2xl overflow-hidden mb-4 relative bg-stone-200">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={item.img}
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <div className="absolute inset-0 bg-black/5 group-hover:bg-black/0 transition-colors" />
                </div>
                <p className="text-sm font-medium text-on-surface/90 truncate">{item.title}</p>
                <p className="text-[10px] text-on-surface-variant/50 mt-1.5 uppercase tracking-wider">
                  {item.time}
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}
