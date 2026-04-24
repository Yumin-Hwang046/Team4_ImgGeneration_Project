import Link from 'next/link'
import InstagramConnect from '@/components/InstagramConnect'

export default function LandingPage() {
  return (
    <div className="bg-background text-on-background min-h-screen flex flex-col">
      {/* TopNavBar */}
      <nav className="sticky top-0 w-full z-50 shrink-0 bg-surface-container-low border-b border-outline-variant/20 shadow-sm">
        <div className="flex justify-between items-center px-12 py-6 max-w-[1440px] mx-auto">
          <div className="text-2xl font-bold text-on-surface tracking-tighter font-headline">
            The Digital Curator
          </div>
          <div className="hidden md:flex items-center gap-10 font-headline font-semibold tracking-tight">
            <a className="text-on-surface/70 hover:text-primary transition-all duration-300 ease-out" href="#">Solutions</a>
            <a className="text-on-surface/70 hover:text-primary transition-all duration-300 ease-out" href="#">Pricing</a>
            <a className="text-on-surface/70 hover:text-primary transition-all duration-300 ease-out" href="#">Case Studies</a>
            <a className="text-on-surface/70 hover:text-primary transition-all duration-300 ease-out" href="#">Library</a>
          </div>
          <div className="flex items-center gap-6">
            <Link
              href="/auth/login"
              className="font-headline font-semibold text-on-surface/70 hover:text-primary active:scale-95 transition-all"
            >
              로그인
            </Link>
            <Link
              href="/auth/signup"
              className="cta-gradient px-8 py-2.5 rounded-full text-white font-headline font-semibold active:scale-95 transition-all shadow-md"
            >
              시작하기
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <main className="flex-grow flex items-center max-w-[1440px] mx-auto px-12 gap-16">
        {/* Left */}
        <div className="w-full md:w-1/2 flex flex-col items-start gap-10 py-12">
          <div className="space-y-4">
            <span className="text-xs font-medium uppercase tracking-[0.2em] text-primary/80">
              AI-Powered Social Curator
            </span>
            <h1 className="text-5xl md:text-6xl font-extrabold leading-[1.1] tracking-tight text-on-surface font-headline">
              SNS 마케팅의 <br />
              <span className="text-primary">완벽한 자동화</span>
            </h1>
            <p className="text-xl text-on-surface-variant leading-relaxed max-w-[480px]">
              당신의 브랜드를 위한 완벽한 비주얼과 카피라이팅.<br />
              클릭 한 번으로 생성부터 자동 업로드까지 해결하세요.
            </p>
          </div>

          <div className="flex flex-col gap-6 w-full">
            <div className="flex items-center gap-6">
              <Link
                href="/auth/signup"
                className="cta-gradient text-white px-10 py-5 rounded-xl text-lg font-bold shadow-xl hover:shadow-2xl transition-all duration-300 active:scale-95 font-headline"
              >
                지금 무료로 시작하기
              </Link>
              <div className="flex items-center gap-2 text-on-surface-variant text-sm font-medium">
                <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>
                  check_circle
                </span>
                카드 등록 없이 시작
              </div>
            </div>
            <div className="w-full max-w-[380px]">
              <InstagramConnect />
            </div>

            <div className="grid grid-cols-2 gap-4 mt-8 w-full max-w-[500px]">
              <div className="bg-surface-container-low p-6 rounded-xl space-y-2">
                <span className="material-symbols-outlined text-primary">auto_awesome</span>
                <h3 className="font-bold text-on-surface font-headline">자동 이미지 생성</h3>
                <p className="text-sm text-on-surface-variant">고급 AI 모델로 구현하는 프리미엄 브랜드 감성</p>
              </div>
              <div className="bg-surface-container-low p-6 rounded-xl space-y-2">
                <span className="material-symbols-outlined text-primary">schedule_send</span>
                <h3 className="font-bold text-on-surface font-headline">스마트 예약 업로드</h3>
                <p className="text-sm text-on-surface-variant">팔로워 활동 시간에 맞춰 자동으로 포스팅</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Phone Mockup */}
        <div className="hidden md:flex w-1/2 justify-center items-center relative">
          <div className="absolute -top-10 -right-10 w-64 h-64 bg-primary-container/20 rounded-full blur-3xl" />
          <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-secondary-container/30 rounded-full blur-3xl" />

          <div className="relative z-10 w-[340px] bg-white rounded-[3rem] p-4 shadow-2xl border-[8px] border-on-background/5">
            <div className="bg-white h-full w-full rounded-[2.2rem] overflow-hidden flex flex-col">
              <div className="px-4 py-4 flex items-center justify-between border-b border-surface-container">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-surface-container-high" />
                  <span className="text-xs font-bold">digital_curator_official</span>
                </div>
                <span className="material-symbols-outlined text-sm">more_horiz</span>
              </div>

              <div className="aspect-square bg-gradient-to-br from-primary/20 to-primary-container/30 relative overflow-hidden flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-6xl opacity-30">image</span>
                <div className="absolute top-4 right-4 bg-black/40 backdrop-blur-md px-3 py-1 rounded-full text-[10px] text-white flex items-center gap-1">
                  <span className="material-symbols-outlined text-[10px]" style={{ fontVariationSettings: "'FILL' 1" }}>bolt</span>
                  AI Generated
                </div>
              </div>

              <div className="p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <div className="flex gap-4">
                    <span className="material-symbols-outlined">favorite</span>
                    <span className="material-symbols-outlined">mode_comment</span>
                    <span className="material-symbols-outlined">send</span>
                  </div>
                  <span className="material-symbols-outlined">bookmark</span>
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-bold">좋아요 1,284개</p>
                  <p className="text-[13px] leading-snug">
                    <span className="font-bold">digital_curator_official</span>{' '}
                    오늘 아침, 완벽한 라떼 한 잔의 여유. AI가 제안하는 오늘의 무드.
                  </p>
                  <p className="text-[11px] text-on-surface-variant pt-1">2분 전</p>
                </div>
              </div>
            </div>
          </div>

          {/* Floating status */}
          <div className="absolute -right-12 top-1/4 glass-card p-6 rounded-2xl shadow-xl border border-white/50 z-20 space-y-3">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <span className="material-symbols-outlined text-primary">upload_file</span>
              </div>
              <div>
                <p className="text-xs font-bold">업로드 준비 완료</p>
                <p className="text-[10px] text-on-surface-variant">오후 2:30 (예약됨)</p>
              </div>
            </div>
            <div className="h-[2px] w-full bg-surface-container">
              <div className="h-full bg-primary w-2/3" />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full shrink-0 bg-surface-container-low">
        <div className="py-8 px-12 flex flex-col md:flex-row justify-between items-center max-w-[1440px] mx-auto text-sm tracking-wide">
          <div className="flex items-center gap-8">
            <div className="text-lg font-bold text-on-surface font-headline">The Digital Curator</div>
            <p className="text-on-surface/60">© 2024 The Digital Curator. All rights reserved.</p>
          </div>
          <div className="flex gap-8 mt-4 md:mt-0">
            <a className="text-on-surface/60 hover:text-primary transition-colors" href="#">Privacy</a>
            <a className="text-on-surface/60 hover:text-primary transition-colors" href="#">Terms</a>
            <a className="text-on-surface/60 hover:text-primary transition-colors" href="#">LinkedIn</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
