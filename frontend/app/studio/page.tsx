'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import SideBar from '@/components/SideBar'
import { api } from '@/lib/api'
import { getStoredCategory, getStoredLocation, getStoredMood } from '@/lib/auth'

type MoodKey = 'warm' | 'clean' | 'trendy' | 'premium'

type ReferenceOption = {
  id: string
  label: string
  filename: string
  gradient: string
}

const BACKEND_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

const MOOD_LABELS: Record<MoodKey, string> = {
  warm: 'Warm',
  clean: 'Clean',
  trendy: 'Trendy',
  premium: 'Premium',
}

const REFERENCE_OPTIONS_BY_MOOD: Record<MoodKey, ReferenceOption[]> = {
  warm: [
    { id: 'warm-1', label: 'Warm #1', filename: '1.png', gradient: 'from-amber-500 via-orange-300 to-yellow-200' },
    { id: 'warm-2', label: 'Warm #2', filename: '2.png', gradient: 'from-amber-500 via-orange-300 to-yellow-200' },
    { id: 'warm-3', label: 'Warm #3', filename: '3.png', gradient: 'from-amber-500 via-orange-300 to-yellow-200' },
    { id: 'warm-4', label: 'Warm #4', filename: '4.png', gradient: 'from-amber-500 via-orange-300 to-yellow-200' },
  ],
  clean: [
    { id: 'clean-1', label: 'Clean #1', filename: '1.png', gradient: 'from-slate-300 via-gray-200 to-zinc-100' },
    { id: 'clean-2', label: 'Clean #2', filename: '2.png', gradient: 'from-slate-300 via-gray-200 to-zinc-100' },
    { id: 'clean-3', label: 'Clean #3', filename: '3.png', gradient: 'from-slate-300 via-gray-200 to-zinc-100' },
    { id: 'clean-4', label: 'Clean #4', filename: '4.png', gradient: 'from-slate-300 via-gray-200 to-zinc-100' },
  ],
  trendy: [
    { id: 'trendy-1', label: 'Trendy #1', filename: '1.png', gradient: 'from-rose-500 via-fuchsia-300 to-orange-200' },
    { id: 'trendy-2', label: 'Trendy #2', filename: '2.png', gradient: 'from-rose-500 via-fuchsia-300 to-orange-200' },
    { id: 'trendy-3', label: 'Trendy #3', filename: '3.png', gradient: 'from-rose-500 via-fuchsia-300 to-orange-200' },
    { id: 'trendy-4', label: 'Trendy #4', filename: '4.png', gradient: 'from-rose-500 via-fuchsia-300 to-orange-200' },
  ],
  premium: [
    { id: 'premium-1', label: 'Premium #1', filename: '1.png', gradient: 'from-zinc-800 via-stone-600 to-amber-400' },
    { id: 'premium-2', label: 'Premium #2', filename: '2.png', gradient: 'from-zinc-800 via-stone-600 to-amber-400' },
    { id: 'premium-3', label: 'Premium #3', filename: '3.png', gradient: 'from-zinc-800 via-stone-600 to-amber-400' },
    { id: 'premium-4', label: 'Premium #4', filename: '4.png', gradient: 'from-zinc-800 via-stone-600 to-amber-400' },
  ],
}

function normalizeMood(value: string): MoodKey {
  const raw = value.trim().toLowerCase()
  if (raw === 'warm' || raw === '따뜻한') return 'warm'
  if (raw === 'clean' || raw === '깔끔한') return 'clean'
  if (raw === 'trendy' || raw === '트렌디') return 'trendy'
  if (raw === 'premium' || raw === '프리미엄') return 'premium'
  return 'warm'
}

function StepLabel({ step, label }: { step: number; label: string }) {
  return (
    <div className="flex items-center gap-4 mb-2">
      <span className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container text-[14px] font-bold shrink-0">
        {step}
      </span>
      <h3 className="text-[15px] font-label uppercase tracking-widest text-on-surface-variant">{label}</h3>
    </div>
  )
}

export default function StudioPage() {
  const router = useRouter()
  const fileRef = useRef<HTMLInputElement>(null)

  const [activeTab, setActiveTab] = useState<'feed' | 'story'>('feed')

  const [uploadedImage, setUploadedImage] = useState<string | null>(null)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [selectedMood, setSelectedMood] = useState<MoodKey>('warm')
  const [selectedReference, setSelectedReference] = useState('1.png')
  const [extraPrompt, setExtraPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const moodFromSignup = normalizeMood(getStoredMood())
    setSelectedMood(moodFromSignup)
    setSelectedReference('1.png')
  }, [])
  const referenceOptions = REFERENCE_OPTIONS_BY_MOOD[selectedMood]

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImageFile(file)
    setUploadedImage(URL.createObjectURL(file))
  }

  const handleGenerate = async () => {
    setError(null)

    if (!imageFile) {
      setError('원본 이미지를 먼저 업로드해주세요. (Case4 모델 필수)')
      return
    }

    setLoading(true)

    try {
      const result = await api.generations.run({
        purpose: '매장 홍보',
        business_category: getStoredCategory() || '카페&베이커리',
        menu_name: '',
        location: getStoredLocation() || '서울',
        target_date: new Date().toISOString().split('T')[0],
        mood: selectedMood,
        reference_preset: selectedReference,
        extra_prompt: extraPrompt || undefined,
        channel: activeTab === 'story' ? 'story' : 'feed',
        image_file: imageFile,
      })
      router.push(`/generating?id=${result.generation_id}`)
    } catch (err) {
      setError((err as Error).message)
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-background text-on-surface overflow-hidden">
      <SideBar />

      <main className="ml-64 flex-1 flex flex-col h-screen overflow-hidden relative bg-background">
        <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl flex justify-between items-center px-12 py-8 w-full border-b border-outline-variant/10">
          <div className="flex flex-col gap-4">
            <h1 className="text-3xl text-on-surface tracking-tight" style={{ fontFamily: 'Instrument Serif, serif', fontStyle: 'italic' }}>
              생성 페이지
            </h1>
            <nav className="flex gap-8">
              {(['feed', 'story'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`mt-4 font-bold tracking-tight text-base pb-1 transition-all duration-200 ${
                    activeTab === tab ? 'active-tab' : 'text-stone-400 hover:text-stone-600'
                  }`}
                >
                  {tab === 'feed' ? '피드' : '스토리'}
                </button>
              ))}
            </nav>
          </div>
        </header>

        <div className="px-12 pb-12 overflow-y-auto w-full flex-1">
          <div className="max-w-[1400px] mx-auto flex flex-col lg:flex-row gap-16 pt-8">
            <div className="flex-1 space-y-10 pb-20">


              {/* Step 1: Image Upload */}
              <section className="space-y-4">
                <StepLabel step={1} label="Image Upload" />
                <div
                  onClick={() => fileRef.current?.click()}
                  className="w-full h-36 rounded-2xl bg-surface-container-low border-2 border-dashed border-outline-variant flex flex-col items-center justify-center cursor-pointer hover:bg-surface-container-high transition-colors"
                >
                  {uploadedImage ? (
                    <img src={uploadedImage} alt="uploaded" className="h-full w-full object-cover rounded-2xl" />
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-primary text-2xl mb-2">add_photo_alternate</span>
                      <p className="text-xs text-stone-500 font-medium">이미지 업로드 (필수)</p>
                    </>
                  )}
                </div>
                <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
              </section>

              {/* Step 2: Contextual Reference */}
              <section className="space-y-4">
                <StepLabel step={2} label="Contextual Reference" />
                <p className="text-sm text-on-surface-variant">
                  회원가입에서 선택한 페르소나: <span className="font-bold text-on-surface">{MOOD_LABELS[selectedMood]}</span>
                </p>
                <div className="grid grid-cols-4 gap-3">
                  {referenceOptions.map(opt => (
                    <button
                      key={opt.id}
                      onClick={() => setSelectedReference(opt.filename)}
                      className={`relative aspect-[4/5] rounded-xl overflow-hidden transition-all duration-300 ${
                        selectedReference === opt.filename ? 'ring-2 ring-primary ring-offset-2 scale-[1.03]' : 'hover:scale-[1.02]'
                      }`}
                    >
                      <div
                        className={`absolute inset-0 bg-gradient-to-b ${opt.gradient}`}
                        style={{
                          backgroundImage: `linear-gradient(to bottom, rgba(0,0,0,0.06), rgba(0,0,0,0.2)), url(${BACKEND_ORIGIN}/media/reference_presets/${selectedMood}/${opt.filename})`,
                          backgroundSize: 'cover',
                          backgroundPosition: 'center',
                        }}
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/35 to-transparent" />
                      <div className="absolute bottom-0 inset-x-0 pb-2 flex items-end justify-center pt-6">
                        <span className="text-[12px] font-bold text-white drop-shadow">{opt.label}</span>
                      </div>
                      {selectedReference === opt.filename && <div className="absolute inset-0 bg-primary/20" />}
                    </button>
                  ))}
                </div>
              </section>

              {/* Step 4: Extra Prompt */}
              <section className="space-y-4">
                <StepLabel step={3} label="Copywriting Hint" />
                <textarea
                  value={extraPrompt}
                  onChange={e => setExtraPrompt(e.target.value)}
                  placeholder="생성하고 싶은 문구의 분위기나 키워드를 입력하세요... (선택)"
                  className="w-full h-32 bg-surface-container-low border-none rounded-2xl p-6 text-sm text-on-surface placeholder:text-stone-400 focus:ring-1 focus:ring-primary transition-all resize-none shadow-sm outline-none"
                />
              </section>

              {error && (
                <div className="px-4 py-3 rounded-xl bg-error/10 border border-error/20 text-error text-sm">
                  {error}
                </div>
              )}

              <button
                onClick={handleGenerate}
                disabled={loading}
                className="w-full py-4 px-6 bg-primary text-white font-bold text-base uppercase tracking-widest rounded-2xl flex items-center justify-center gap-2 shadow-xl shadow-primary/10 hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-60 disabled:translate-y-0"
              >
                <span className="material-symbols-outlined text-lg">auto_awesome</span>
                {loading ? '처리 중...' : '생성하기'}
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
                      <span className="text-xs font-bold text-on-surface">{'the_digital_curator'}</span>
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
                        <p className="text-[11px] font-bold">좋아요 —</p>
                        <p className="text-[11px] leading-relaxed text-stone-700">
                          <span className="font-bold text-black">the_digital_curator</span>{' '}
                          {extraPrompt || '콘텐츠가 생성되면 여기에 표시됩니다.'}
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
                      <h2 className="text-white text-3xl mb-4 drop-shadow-lg" style={{ fontFamily: 'Instrument Serif, serif', fontStyle: 'italic' }}>
                        {'Digital Curator'}
                      </h2>
                      <p className="text-white/90 text-sm font-medium tracking-tight drop-shadow-md">
                        {extraPrompt || '당신의 일상을 더 미니멀하게'}
                      </p>
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
