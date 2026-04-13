'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import SideBar from '@/components/SideBar'

const weatherOptions = [
  {
    id: 'sunny',
    label: '맑은 날씨',
    icon: 'wb_sunny',
    gradient: 'from-sky-300 via-yellow-200 to-amber-100',
    iconColor: 'text-yellow-500',
  },
  {
    id: 'cloudy',
    label: '흐린 날씨',
    icon: 'cloud',
    gradient: 'from-slate-400 via-gray-300 to-slate-200',
    iconColor: 'text-gray-500',
  },
  {
    id: 'rainy',
    label: '비 오는 배경',
    icon: 'rainy',
    gradient: 'from-slate-700 via-slate-500 to-blue-400',
    iconColor: 'text-blue-200',
  },
  {
    id: 'warm',
    label: '따뜻한 조명',
    icon: 'light_mode',
    gradient: 'from-amber-500 via-orange-300 to-yellow-200',
    iconColor: 'text-amber-100',
  },
]

export default function StudioPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<'feed' | 'story'>('feed')
  const [selectedWeather, setSelectedWeather] = useState('sunny')
  const [prompt, setPrompt] = useState('')
  const [uploadedImage, setUploadedImage] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const url = URL.createObjectURL(file)
    setUploadedImage(url)
  }

  const handleGenerate = () => {
    if (!prompt.trim() && !uploadedImage) return
    router.push('/generating')
  }

  return (
    <div className="flex min-h-screen bg-background text-on-surface overflow-hidden">
      <SideBar />

      <main className="ml-64 flex-1 flex flex-col h-screen overflow-hidden relative bg-background">
        {/* Top Bar */}
        <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl flex justify-between items-center px-12 py-8 w-full border-b border-outline-variant/10">
          <div className="flex flex-col gap-4">
            <h1
              className="text-3xl text-on-surface tracking-tight"
              style={{ fontFamily: 'Instrument Serif, serif', fontStyle: 'italic' }}
            >
              생성 페이지
            </h1>
            <nav className="flex gap-8">
              <button
                onClick={() => setActiveTab('feed')}
                className={`mt-4 font-bold tracking-tight text-base pb-1 transition-all duration-200 ${
                  activeTab === 'feed' ? 'active-tab' : 'text-stone-400 hover:text-stone-600'
                }`}
              >
                피드
              </button>
              <button
                onClick={() => setActiveTab('story')}
                className={`mt-4 font-medium tracking-tight text-base pb-1 transition-all duration-200 ${
                  activeTab === 'story' ? 'active-tab' : 'text-stone-400 hover:text-stone-600'
                }`}
              >
                스토리
              </button>
            </nav>
          </div>
        </header>

        {/* Content */}
        <div className="px-12 pb-12 overflow-y-auto w-full flex-1">
          <div className="max-w-[1400px] mx-auto flex flex-col lg:flex-row gap-16 pt-8">
            {/* Left: Config */}
            <div className="flex-1 space-y-10 pb-20">
              {/* Step 1: Upload */}
              <section className="space-y-6">
                <div className="flex items-center gap-4 mb-2">
                  <span className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container text-[14px] font-bold">
                    1
                  </span>
                  <h3 className="text-[15px] font-label uppercase tracking-widest text-on-surface-variant">
                    Image Upload
                  </h3>
                </div>
                <div
                  onClick={() => fileRef.current?.click()}
                  className="w-full h-36 rounded-2xl bg-surface-container-low border-2 border-dashed border-outline-variant flex flex-col items-center justify-center cursor-pointer hover:bg-surface-container-high transition-colors"
                >
                  {uploadedImage ? (
                    <img src={uploadedImage} alt="uploaded" className="h-full w-full object-cover rounded-2xl" />
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-primary text-2xl mb-2">
                        add_photo_alternate
                      </span>
                      <p className="text-xs text-stone-500 font-medium">이미지 업로드</p>
                    </>
                  )}
                </div>
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </section>

              {/* Step 2: Weather/context reference */}
              <section className="space-y-6">
                <div className="flex items-center gap-4 mb-2">
                  <span className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container text-[14px] font-bold">
                    2
                  </span>
                  <h3 className="text-[15px] font-label uppercase tracking-widest text-on-surface-variant">
                    Contextual Reference
                  </h3>
                </div>
                <div className="grid grid-cols-4 gap-3">
                  {weatherOptions.map((opt) => (
                    <button
                      key={opt.id}
                      onClick={() => setSelectedWeather(opt.id)}
                      className={`relative aspect-[4/5] rounded-xl overflow-hidden transition-all duration-300 bg-gradient-to-b ${opt.gradient} ${
                        selectedWeather === opt.id ? 'ring-2 ring-primary ring-offset-2 scale-[1.03]' : 'hover:scale-[1.02]'
                      }`}
                    >
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
                        <span
                          className={`material-symbols-outlined text-4xl ${opt.iconColor} drop-shadow`}
                          style={{ fontVariationSettings: "'FILL' 1" }}
                        >
                          {opt.icon}
                        </span>
                      </div>
                      <div className="absolute bottom-0 inset-x-0 pb-2 flex items-end justify-center bg-gradient-to-t from-black/30 to-transparent pt-6">
                        <span className="text-[12px] font-bold text-white drop-shadow">
                          {opt.label}
                        </span>
                      </div>
                      {selectedWeather === opt.id && (
                        <div className="absolute inset-0 bg-primary/20" />
                      )}
                    </button>
                  ))}
                </div>
              </section>

              {/* Step 3: Prompt */}
              <section className="space-y-6">
                <div className="flex items-center gap-4 mb-2">
                  <span className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container text-[14px] font-bold">
                    3
                  </span>
                  <h3 className="text-[15px] font-label uppercase tracking-widest text-on-surface-variant">
                    Copywriting
                  </h3>
                </div>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="생성하고 싶은 문구의 분위기나 키워드를 입력하세요..."
                  className="w-full h-32 bg-surface-container-low border-none rounded-2xl p-6 text-sm text-on-surface placeholder:text-stone-400 focus:ring-1 focus:ring-primary transition-all resize-none shadow-sm outline-none"
                />
              </section>

              <button
                onClick={handleGenerate}
                className="w-full py-4 px-6 bg-primary text-white font-bold text-base uppercase tracking-widest rounded-2xl flex items-center justify-center gap-2 shadow-xl shadow-primary/10 hover:-translate-y-0.5 active:translate-y-0 transition-all"
              >
                <span className="material-symbols-outlined text-lg">auto_awesome</span>
                생성하기
              </button>
            </div>

            {/* Right: Preview */}
            <div className="w-full lg:w-[480px]">
              <div className="glass-card sticky top-8 p-10 rounded-[3rem] shadow-2xl shadow-stone-200/50 border border-white/60">
                <div className="flex items-center justify-between mb-8">
                  <span className="text-[10px] uppercase tracking-[0.25em] text-stone-400">Live Preview</span>
                  <div className="flex gap-2.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-secondary-container" />
                    <div className="w-2.5 h-2.5 rounded-full bg-outline-variant" />
                    <div className="w-2.5 h-2.5 rounded-full bg-primary" />
                  </div>
                </div>

                {activeTab === 'feed' ? (
                  <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-stone-100">
                    <div className="p-4 flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-yellow-400 to-purple-600 p-[1.5px]">
                        <div className="w-full h-full rounded-full border-2 border-white bg-stone-200" />
                      </div>
                      <span className="text-xs font-bold text-on-surface">the_digital_curator</span>
                      <span className="material-symbols-outlined ml-auto text-stone-400">more_horiz</span>
                    </div>
                    <div className="aspect-square bg-surface-container-low relative flex items-center justify-center">
                      {uploadedImage ? (
                        <img src={uploadedImage} alt="preview" className="w-full h-full object-cover" />
                      ) : (
                        <span className="material-symbols-outlined text-outline/30 text-6xl">image</span>
                      )}
                    </div>
                    <div className="p-5 space-y-4">
                      <div className="flex gap-4 text-stone-700">
                        <span className="material-symbols-outlined">favorite</span>
                        <span className="material-symbols-outlined">chat_bubble</span>
                        <span className="material-symbols-outlined">send</span>
                        <span className="material-symbols-outlined ml-auto">bookmark</span>
                      </div>
                      <div className="space-y-1">
                        <p className="text-[11px] font-bold">좋아요 1,248개</p>
                        <p className="text-[11px] leading-relaxed text-stone-700">
                          <span className="font-bold text-black">the_digital_curator</span>{' '}
                          {prompt || '오늘의 공간. 빛과 그림자가 만들어내는 완벽한 조형미. #minimalism #curation #aesthetic'}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="aspect-[9/16] bg-stone-900 rounded-3xl overflow-hidden shadow-2xl relative border border-white/20 mx-auto max-w-[280px]">
                    {uploadedImage ? (
                      <img src={uploadedImage} alt="story preview" className="absolute inset-0 w-full h-full object-cover opacity-80" />
                    ) : (
                      <div className="absolute inset-0 bg-gradient-to-br from-primary/40 to-primary-container/20" />
                    )}
                    <div className="absolute inset-0 flex flex-col justify-center items-center p-8 text-center">
                      <h2
                        className="text-white text-3xl mb-4 drop-shadow-lg"
                        style={{ fontFamily: 'Instrument Serif, serif', fontStyle: 'italic' }}
                      >
                        Nordic Studio
                      </h2>
                      <p className="text-white/90 text-sm font-medium tracking-tight drop-shadow-md">
                        {prompt || '당신의 일상을 더 미니멀하게'}
                      </p>
                    </div>
                    <div className="absolute top-0 left-0 right-0 p-4 space-y-4 bg-gradient-to-b from-black/40 to-transparent">
                      <div className="flex gap-1 h-0.5">
                        <div className="flex-1 bg-white rounded-full" />
                        <div className="flex-1 bg-white/30 rounded-full" />
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full border border-white/50 bg-stone-300" />
                        <span className="text-xs font-bold text-white">the_digital_curator</span>
                        <span className="text-[10px] text-white/70">2h</span>
                      </div>
                    </div>
                    <div className="absolute bottom-0 left-0 right-0 p-4 flex items-center gap-4 bg-gradient-to-t from-black/40 to-transparent">
                      <div className="flex-1 h-10 rounded-full border border-white/50 px-4 flex items-center">
                        <span className="text-white/70 text-xs">메시지 보내기...</span>
                      </div>
                      <span className="material-symbols-outlined text-white">favorite</span>
                      <span className="material-symbols-outlined text-white">send</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
