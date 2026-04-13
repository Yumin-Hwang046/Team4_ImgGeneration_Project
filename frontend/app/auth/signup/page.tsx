import Link from 'next/link'
import InstagramConnect from '@/components/InstagramConnect'

export default function SignupPage() {
  return (
    <div className="bg-surface text-on-surface min-h-screen flex flex-col items-center justify-center p-6">
      <main className="w-full max-w-md">
        <div className="bg-surface-container-lowest rounded-xl shadow-editorial">
          <div className="px-8 py-6 md:px-10">
            <div className="text-center mb-6">
              <h1 className="text-2xl font-extrabold text-on-background tracking-tight font-headline mb-1">
                회원가입
              </h1>
              <p className="text-on-surface-variant text-xs leading-relaxed opacity-80">
                디지털 큐레이터와 함께 매장의 고유한 페르소나를 구축해보세요.
              </p>
            </div>

            <form className="space-y-3" action="/onboarding/confirm">
              <div className="space-y-1">
                <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                  아이디
                </label>
                <input
                  type="text"
                  placeholder="사용하실 아이디를 입력하세요"
                  className="w-full px-4 py-2.5 bg-surface-container-low border-none rounded-lg focus:ring-2 focus:ring-primary-container text-sm text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                    비밀번호
                  </label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 bg-surface-container-low border-none rounded-lg focus:ring-2 focus:ring-primary-container text-sm text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                    비밀번호 확인
                  </label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 bg-surface-container-low border-none rounded-lg focus:ring-2 focus:ring-primary-container text-sm text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                  매장 이름
                </label>
                <input
                  type="text"
                  placeholder="운영하시는 매장명을 입력하세요"
                  className="w-full px-4 py-2.5 bg-surface-container-low border-none rounded-lg focus:ring-2 focus:ring-primary-container text-sm text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                  카테고리 선택
                </label>
                <div className="relative">
                  <select className="w-full px-4 py-2.5 bg-surface-container-low border-none rounded-lg focus:ring-2 focus:ring-primary-container text-sm text-on-surface appearance-none transition-all duration-200 outline-none">
                    <option value="" disabled>업종을 선택해주세요</option>
                    <option value="cafe&bakery">카페&베이커리 (Cafe&Bakery)</option>
                    <option value="korean restaurant">한식당 (Korean Restaurant)</option>
                    <option value="pub & bar">주점 (Pub & Bar)</option>
                    <option value="western cuisine">양식 (Western Cuisine)</option>
                    <option value="japanese & asian cuisine">일식&아시안 (Japanese & Asian Cuisine)</option>
                    <option value="snack & fast food">분식 & 패스트푸드 (Snack & Fast food)</option>
                    <option value="bbq & grill">고기 & 구이 (BBQ & Grill)</option>
                  </select>
                  <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none text-xl">
                    expand_more
                  </span>
                </div>
              </div>

              <div className="space-y-1">
                <label className="block text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider px-1">
                  위치 검색
                </label>
                <div className="relative">
                  <input
                    type="text"
                    placeholder="매장 위치를 검색하세요"
                    className="w-full pl-4 pr-10 py-2.5 bg-surface-container-low border-none rounded-lg focus:ring-2 focus:ring-primary-container text-sm text-on-surface placeholder:text-outline/40 transition-all duration-200 outline-none"
                  />
                  <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-xl">
                    search
                  </span>
                </div>
              </div>

              <div className="pt-2">
                <InstagramConnect variant="signup" />
                <p className="text-[9px] text-center text-on-surface-variant/60 mt-1.5 uppercase tracking-wider font-bold">
                  인스타그램 연동 시 매장 정보가 자동으로 최적화됩니다.
                </p>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  className="w-full py-3.5 px-6 rounded-lg text-white font-semibold text-sm tracking-wide cta-gradient hover:opacity-90 active:scale-[0.98] transition-all duration-200 shadow-sm font-headline"
                >
                  회원가입 완료하기
                </button>
              </div>
            </form>

            <div className="mt-4 text-center">
              <p className="text-[11px] text-on-secondary-fixed-variant font-medium">
                이미 계정이 있으신가요?{' '}
                <Link className="text-primary hover:underline underline-offset-4 transition-colors" href="/auth/login">
                  로그인하기
                </Link>
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 text-center opacity-40">
          <p className="text-[9px] tracking-[0.2em] text-on-surface-variant font-medium uppercase">
            Curated by Digital Archive Dept.
          </p>
        </div>
      </main>

      <footer className="w-full py-6 px-8 mt-6 flex flex-col md:flex-row justify-between items-center max-w-md border-t border-outline-variant/10">
        <p className="text-[11px] tracking-wide text-on-secondary-container mb-2 md:mb-0 opacity-80">
          © 2024 Digital Curator. The Human Archive.
        </p>
        <div className="flex gap-6">
          <a className="text-[11px] text-on-secondary-container hover:underline opacity-60 hover:opacity-100 transition-all" href="#">Privacy Policy</a>
          <a className="text-[11px] text-on-secondary-container hover:underline opacity-60 hover:opacity-100 transition-all" href="#">Terms</a>
        </div>
      </footer>
    </div>
  )
}
