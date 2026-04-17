'use client'

import { Suspense, useEffect, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import SideBar from '@/components/SideBar'
import { api, GenerationDetailResponse } from '@/lib/api'

const POLL_INTERVAL_MS = 2000
const MAX_POLLS = 60

// ─── Schedule Modal ────────────────────────────────────────────────────────────

type Channel = 'instagram_feed' | 'instagram_story'

function ScheduleModal({
  onClose,
  onConfirm,
  defaultChannel = 'instagram_feed',
}: {
  onClose: () => void
  onConfirm: (scheduledAt: string, channel: Channel) => void
  defaultChannel?: Channel
}) {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const [selectedDay, setSelectedDay] = useState(today.getDate())
  const [ampm, setAmpm] = useState<'AM' | 'PM'>('AM')
  const [hour, setHour] = useState(10)
  const [minute, setMinute] = useState(0)
  const [channel, setChannel] = useState<Channel>(defaultChannel)

  const MONTH_LABELS = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월']
  const DAY_LABELS = ['Su','Mo','Tu','We','Th','Fr','Sa']

  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const prevMonthDays = new Date(year, month, 0).getDate()

  const prevMonth = () => {
    if (month === 0) { setMonth(11); setYear(y => y - 1) }
    else setMonth(m => m - 1)
  }
  const nextMonth = () => {
    if (month === 11) { setMonth(0); setYear(y => y + 1) }
    else setMonth(m => m + 1)
  }

  const handleConfirm = () => {
    const h24 = ampm === 'PM'
      ? (hour === 12 ? 12 : hour + 12)
      : (hour === 12 ? 0 : hour)
    const pad = (n: number) => String(n).padStart(2, '0')
    const scheduledAt = `${year}-${pad(month + 1)}-${pad(selectedDay)}T${pad(h24)}:${pad(minute)}:00`
    onConfirm(scheduledAt, channel)
  }

  const handleMinuteWheel = (e: React.WheelEvent<HTMLInputElement>) => {
    e.preventDefault()
    setMinute(m => Math.max(0, Math.min(59, m + (e.deltaY < 0 ? 1 : -1))))
  }

  const cells: { day: number; current: boolean }[] = []
  for (let i = firstDay - 1; i >= 0; i--) cells.push({ day: prevMonthDays - i, current: false })
  for (let d = 1; d <= daysInMonth; d++) cells.push({ day: d, current: true })
  while (cells.length % 7 !== 0) cells.push({ day: cells.length - daysInMonth - firstDay + 1, current: false })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-stone-900/40 backdrop-blur-sm" />
      <div
        className="relative bg-surface w-full max-w-md rounded-3xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-6 border-b border-stone-100 flex items-center justify-between">
          <h3 className="text-xl font-bold text-on-surface tracking-tight">예약 설정</h3>
          <button onClick={onClose} className="p-2 hover:bg-stone-100 rounded-full transition-colors">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Calendar */}
          <section>
            <div className="flex items-center justify-between mb-4 px-2">
              <span className="text-sm font-bold text-on-surface">{year}년 {MONTH_LABELS[month]}</span>
              <div className="flex gap-1">
                <button onClick={prevMonth} className="p-1 hover:bg-stone-100 rounded-md">
                  <span className="material-symbols-outlined text-sm">chevron_left</span>
                </button>
                <button onClick={nextMonth} className="p-1 hover:bg-stone-100 rounded-md">
                  <span className="material-symbols-outlined text-sm">chevron_right</span>
                </button>
              </div>
            </div>
            <div className="grid grid-cols-7 text-center text-[10px] font-bold text-on-surface-variant/60 uppercase mb-2">
              {DAY_LABELS.map(d => <span key={d}>{d}</span>)}
            </div>
            <div className="grid grid-cols-7 gap-1 text-center">
              {cells.map((cell, i) => {
                const isSelected = cell.current && cell.day === selectedDay
                return (
                  <span
                    key={i}
                    onClick={() => cell.current && setSelectedDay(cell.day)}
                    className={`py-2 text-xs rounded-lg transition-colors ${
                      !cell.current
                        ? 'text-stone-300'
                        : isSelected
                        ? 'bg-primary text-white font-bold cursor-pointer'
                        : 'text-on-surface font-medium hover:bg-stone-100 cursor-pointer'
                    }`}
                  >
                    {cell.day}
                  </span>
                )
              })}
            </div>
          </section>

          {/* Channel */}
          <section className="pt-4 border-t border-stone-100">
            <label className="block text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-3">
              채널 선택
            </label>
            <div className="flex bg-stone-100 p-1 rounded-xl">
              {([
                { value: 'instagram_feed', label: '피드' },
                { value: 'instagram_story', label: '스토리' },
              ] as { value: Channel; label: string }[]).map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setChannel(opt.value)}
                  className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                    channel === opt.value ? 'bg-white text-on-surface shadow-sm' : 'text-on-surface-variant'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </section>

          {/* Time */}
          <section className="pt-4 border-t border-stone-100">
            <label className="block text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-4">
              Time Selection
            </label>
            <div className="flex items-center gap-4">
              <div className="flex bg-stone-100 p-1 rounded-xl shrink-0">
                {(['AM', 'PM'] as const).map(v => (
                  <button
                    key={v}
                    onClick={() => setAmpm(v)}
                    className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
                      ampm === v ? 'bg-white text-on-surface shadow-sm' : 'text-on-surface-variant'
                    }`}
                  >
                    {v}
                  </button>
                ))}
              </div>
              <div className="flex-1 flex items-center gap-2">
                <div className="relative flex-1">
                  <select
                    value={hour}
                    onChange={e => setHour(Number(e.target.value))}
                    className="w-full appearance-none bg-stone-50 border border-stone-200 rounded-xl px-4 py-3 text-sm outline-none"
                  >
                    {Array.from({ length: 12 }, (_, i) => i + 1).map(h => (
                      <option key={h} value={h}>{String(h).padStart(2, '0')}</option>
                    ))}
                  </select>
                  <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none text-sm">
                    keyboard_arrow_down
                  </span>
                </div>
                <span className="font-bold">:</span>
                <input
                  type="number"
                  min={0}
                  max={59}
                  value={String(minute).padStart(2, '0')}
                  onChange={e => {
                    const v = Math.max(0, Math.min(59, Number(e.target.value)))
                    setMinute(isNaN(v) ? 0 : v)
                  }}
                  onWheel={handleMinuteWheel}
                  className="flex-1 bg-stone-50 border border-stone-200 rounded-xl px-4 py-3 text-sm outline-none text-center [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                />
              </div>
            </div>
          </section>
        </div>

        <div className="p-6 bg-stone-50/50 flex flex-col gap-3">
          <button
            onClick={handleConfirm}
            className="w-full py-4 bg-primary text-white font-bold rounded-xl shadow-lg hover:bg-primary/90 transition-all"
          >
            확인 및 예약 완료
          </button>
          <button
            onClick={onClose}
            className="w-full py-4 text-on-surface-variant font-medium hover:bg-stone-100 rounded-xl transition-all"
          >
            취소
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Result Page ───────────────────────────────────────────────────────────────

function ResultPage({ data }: { data: GenerationDetailResponse }) {
  const router = useRouter()
  const [showScheduleModal, setShowScheduleModal] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [scheduling, setScheduling] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  const imageUrl = data.generated_image_url ?? null

  const handleUpload = async () => {
    setUploading(true)
    setMsg(null)
    try {
      await api.instagram.upload(data.id, 'instagram_feed')
      setMsg({ text: '인스타그램 업로드 완료!', ok: true })
    } catch (err) {
      setMsg({ text: (err as Error).message, ok: false })
    } finally {
      setUploading(false)
    }
  }

  const handleSchedule = async (scheduledAt: string, channel: Channel) => {
    setShowScheduleModal(false)
    setScheduling(true)
    setMsg(null)
    try {
      await api.instagram.scheduleUpload(data.id, scheduledAt, channel)
      setMsg({ text: '예약이 완료되었습니다!', ok: true })
    } catch (err) {
      setMsg({ text: (err as Error).message, ok: false })
    } finally {
      setScheduling(false)
    }
  }

  const handleRegenerate = async () => {
    setRegenerating(true)
    try {
      await api.generations.regenerate(data.id)
      router.push(`/generating?id=${data.id}`)
    } catch (err) {
      setMsg({ text: (err as Error).message, ok: false })
      setRegenerating(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-background text-on-surface">
      <SideBar />

      {showScheduleModal && (
        <ScheduleModal
          onClose={() => setShowScheduleModal(false)}
          onConfirm={handleSchedule}
          defaultChannel="instagram_feed"
        />
      )}

      <main className="ml-64 flex-1 p-12">
        <div className="mb-8">
          <p className="text-[10px] font-medium text-on-secondary-container tracking-widest uppercase mb-2">
            RESULT PREVIEW
          </p>
          <h2 className="text-3xl font-bold text-on-surface tracking-tight">
            ✨ 콘텐츠 생성이 완료되었습니다!
          </h2>
        </div>

        {msg && (
          <div className={`mb-6 px-4 py-3 rounded-xl text-sm font-medium border ${
            msg.ok
              ? 'bg-primary/10 border-primary/20 text-primary'
              : 'bg-error/10 border-error/20 text-error'
          }`}>
            {msg.text}
          </div>
        )}

        <div className="flex flex-col lg:flex-row gap-12 h-[calc(100vh-260px)] min-h-[600px]">
          {/* Left: Generated Image */}
          <div className="w-full lg:w-3/5 h-full">
            <div className="relative w-full h-full bg-surface-container-low rounded-[2rem] p-8 flex items-center justify-center overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 to-transparent pointer-events-none" />
              <div className="relative z-10 w-full h-full max-w-2xl max-h-[80%] bg-white p-4 rounded-xl shadow-2xl hover:scale-[1.02] transition-transform duration-500">
                {imageUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={imageUrl} alt="Generated" className="w-full h-full object-cover rounded-lg" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <span className="material-symbols-outlined text-outline/30 text-6xl">image</span>
                  </div>
                )}
                <div className="absolute top-8 right-8 bg-white/90 backdrop-blur-md p-3 rounded-full shadow-lg">
                  <span
                    className="material-symbols-outlined text-primary"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    verified
                  </span>
                </div>
              </div>

              <div className="absolute bottom-8 left-12 right-12 flex justify-between items-end">
                <div>
                  <span className="text-[0.65rem] font-bold text-on-surface-variant uppercase tracking-widest block mb-1">
                    Curation ID: GEN-{data.id}
                  </span>
                  <span className="text-sm font-medium text-on-surface opacity-60">
                    Generated via Editorial V3 Engine
                  </span>
                </div>
                <div className="flex gap-2">
                  <button className="p-3 bg-surface-container-lowest/80 backdrop-blur rounded-full hover:bg-white transition-colors shadow-sm">
                    <span className="material-symbols-outlined text-on-surface">zoom_in</span>
                  </button>
                  {imageUrl && (
                    <a
                      href={imageUrl}
                      download
                      className="p-3 bg-surface-container-lowest/80 backdrop-blur rounded-full hover:bg-white transition-colors shadow-sm"
                    >
                      <span className="material-symbols-outlined text-on-surface">download</span>
                    </a>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right: Instagram mockup + actions */}
          <div className="w-full lg:w-2/5 flex flex-col gap-4 h-full">
            <div className="flex-grow bg-surface-container-lowest border border-outline-variant/10 rounded-[2rem] shadow-sm flex flex-col overflow-hidden">
              {/* Mockup header */}
              <div className="p-5 border-b border-surface-container flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 p-[2px]">
                    <div className="w-full h-full rounded-full border-2 border-white bg-stone-200" />
                  </div>
                  <span className="text-sm font-bold text-on-surface">the_digital_curator</span>
                </div>
                <span className="material-symbols-outlined">more_horiz</span>
              </div>

              {/* Mockup content */}
              <div className="overflow-y-auto p-5 flex-grow" style={{ scrollbarWidth: 'thin' }}>
                <div className="aspect-square w-full rounded-xl overflow-hidden mb-4 bg-surface-container-low">
                  {imageUrl && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={imageUrl} alt="Instagram preview" className="w-full h-full object-cover" />
                  )}
                </div>
                <div className="space-y-3">
                  <div className="flex gap-4 text-stone-700">
                    <span className="material-symbols-outlined">favorite</span>
                    <span className="material-symbols-outlined">chat_bubble</span>
                    <span className="material-symbols-outlined">send</span>
                    <span className="material-symbols-outlined ml-auto">bookmark</span>
                  </div>
                  {data.generated_copy && (
                    <p className="text-sm text-on-surface-variant leading-relaxed">{data.generated_copy}</p>
                  )}
                  {data.hashtags && data.hashtags.length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {data.hashtags.map(tag => (
                        <span
                          key={tag}
                          className="px-3 py-1 bg-secondary-container text-on-secondary-container text-xs rounded-full font-medium"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex flex-col gap-3">
              <div className="flex gap-3">
                <button
                  onClick={handleUpload}
                  disabled={uploading}
                  className="flex-grow py-4 px-6 bg-gradient-to-r from-[#6BA4B8] to-[#296678] text-white rounded-xl font-bold shadow-lg hover:opacity-95 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
                >
                  <span className="material-symbols-outlined">upload_file</span>
                  {uploading ? '업로드 중...' : '인스타 업로드'}
                </button>
                <button
                  onClick={handleRegenerate}
                  disabled={regenerating}
                  title="다시 생성하기"
                  className="w-14 h-14 flex items-center justify-center bg-slate-200/50 text-slate-700 rounded-xl hover:bg-slate-200 transition-colors active:scale-95 disabled:opacity-60"
                >
                  <span className={`material-symbols-outlined ${regenerating ? 'animate-spin' : ''}`}>
                    refresh
                  </span>
                </button>
              </div>
              <button
                onClick={() => setShowScheduleModal(true)}
                disabled={scheduling}
                className="w-full py-4 px-6 bg-slate-200/50 text-slate-700 rounded-xl font-bold hover:bg-slate-200 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
              >
                <span className="material-symbols-outlined">calendar_today</span>
                {scheduling ? '예약 처리 중...' : '인스타 예약'}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

// ─── Generating Content ────────────────────────────────────────────────────────

function GeneratingContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const generationId = searchParams.get('id')

  const [genStatus, setGenStatus] = useState<'PENDING' | 'SUCCESS' | 'FAILED'>('PENDING')
  const [genData, setGenData] = useState<GenerationDetailResponse | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const pollCount = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!generationId) {
      router.replace('/studio')
      return
    }

    const id = Number(generationId)

    const poll = async () => {
      try {
        const data = await api.generations.get(id)
        const st = data.generation_status

        if (st === 'SUCCESS') {
          setGenData(data)
          setGenStatus('SUCCESS')
          return
        }

        if (st === 'FAILED') {
          setGenStatus('FAILED')
          setErrorMsg('콘텐츠 생성에 실패했습니다. 다시 시도해주세요.')
          return
        }

        pollCount.current += 1
        if (pollCount.current >= MAX_POLLS) {
          setGenStatus('FAILED')
          setErrorMsg('처리 시간이 초과되었습니다. 보관함에서 결과를 확인해주세요.')
          return
        }

        timerRef.current = setTimeout(poll, POLL_INTERVAL_MS)
      } catch {
        setGenStatus('FAILED')
        setErrorMsg('상태 조회 중 오류가 발생했습니다.')
      }
    }

    timerRef.current = setTimeout(poll, POLL_INTERVAL_MS)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [generationId, router])

  if (genStatus === 'SUCCESS' && genData) {
    return <ResultPage data={genData} />
  }

  if (genStatus === 'FAILED') {
    return (
      <div className="min-h-screen bg-surface flex flex-col items-center justify-center gap-6 p-8">
        <div className="w-16 h-16 rounded-full bg-error/10 flex items-center justify-center">
          <span className="material-symbols-outlined text-error text-3xl">error</span>
        </div>
        <h1 className="font-headline text-2xl font-bold text-on-surface text-center">생성 실패</h1>
        <p className="text-on-surface-variant text-center max-w-sm">{errorMsg}</p>
        <div className="flex gap-3">
          <button
            onClick={() => router.push('/studio')}
            className="px-6 py-3 rounded-xl border border-outline text-on-surface font-semibold hover:bg-surface-container-low transition-colors"
          >
            다시 시도
          </button>
          <button
            onClick={() => router.push('/archive')}
            className="px-6 py-3 rounded-xl bg-primary text-white font-semibold hover:opacity-90 transition-opacity"
          >
            보관함 확인
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-surface font-body text-on-surface overflow-hidden min-h-screen">
      <header className="flex justify-between items-center w-full px-12 py-6 fixed top-0 z-50">
        <div className="text-xl font-headline font-bold tracking-tight text-on-surface">
          The Digital Curator
        </div>
        <span className="text-sm font-medium text-on-secondary-container tracking-widest uppercase">
          Generation in progress
        </span>
      </header>

      <main className="h-screen w-full flex flex-col items-center justify-center relative overflow-hidden">
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
              <span className="block text-[10px] uppercase text-on-secondary-container/50 tracking-widest mb-1">Process ID</span>
              <span className="block font-headline text-xs font-bold text-on-surface/70">
                {generationId ? `GEN-${generationId}` : '—'}
              </span>
            </div>
            <div className="text-right">
              <span className="block text-[10px] uppercase text-on-secondary-container/50 tracking-widest mb-1">Current Task</span>
              <span className="block font-headline text-xs font-bold text-on-surface/70">
                Synthesizing Aesthetics
              </span>
            </div>
          </div>
        </div>

        <div className="absolute bottom-16 left-1/2 -translate-x-1/2 w-full max-w-4xl px-12 grid grid-cols-4 gap-6 opacity-30">
          {[0, 4, 0, 4].map((offset, i) => (
            <div
              key={i}
              className={`aspect-[4/5] bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/10 flex flex-col p-4 ${offset ? 'translate-y-4' : ''}`}
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

export default function GeneratingPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
      </div>
    }>
      <GeneratingContent />
    </Suspense>
  )
}
