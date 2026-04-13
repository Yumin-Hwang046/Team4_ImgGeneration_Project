'use client'

import { useState } from 'react'
import SideBar from '@/components/SideBar'

type Tag = '완료' | '예약' | '행사' | '기타'
type ViewMode = '월간' | '주간' | '리스트'

type CalEvent = {
  id: number
  date: number
  title: string
  time: string
  tag: Tag
  colorClass: string
}

type ModalState =
  | { mode: 'add'; date: number }
  | { mode: 'edit'; event: CalEvent }
  | null

const TAG_COLORS: Record<Tag, string> = {
  '완료': 'bg-stone-100 border-stone-300 text-stone-500',
  '예약': 'bg-blue-50 border-blue-400 text-blue-600',
  '행사': 'bg-red-50 border-red-400 text-red-600',
  '기타': 'bg-amber-50 border-amber-400 text-amber-600',
}

const INITIAL_EVENTS: CalEvent[] = [
  { id: 1, date: 3,  title: '성수동 팝업 마켓', time: '10:00', tag: '행사', colorClass: TAG_COLORS['행사'] },
  { id: 2, date: 9,  title: '모닝 라떼',        time: '09:00', tag: '완료', colorClass: TAG_COLORS['완료'] },
  { id: 3, date: 18, title: '신규 메뉴',         time: '14:00', tag: '예약', colorClass: TAG_COLORS['예약'] },
  { id: 4, date: 25, title: '크리스마스',        time: '종일',  tag: '행사', colorClass: TAG_COLORS['행사'] },
]

const DAYS_EN = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const DAYS_KO = ['일', '월', '화', '수', '목', '금', '토']

function isPast(year: number, month: number, day: number) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return new Date(year, month, day) < today
}

function effectiveColor(ev: CalEvent, year: number, month: number) {
  return isPast(year, month, ev.date) ? TAG_COLORS['완료'] : ev.colorClass
}

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate()
}
function getFirstDayOfMonth(year: number, month: number) {
  return new Date(year, month, 1).getDay()
}
function getDaysInPrevMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate()
}
function getWeekDates(year: number, month: number, day: number) {
  const base = new Date(year, month, day)
  const dow = base.getDay()
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(base)
    d.setDate(base.getDate() - dow + i)
    return d
  })
}

// ─── TimePicker ──────────────────────────────────────────────────────────────
function TimePicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const parse = (v: string) => {
    const [h, m] = v.split(':').map(Number)
    const h24 = isNaN(h) ? 9 : h
    return { period: h24 < 12 ? '오전' : '오후', hour: h24 % 12 || 12, minute: isNaN(m) ? 0 : m }
  }
  const { period, hour, minute } = parse(value.includes(':') ? value : '09:00')
  const [open, setOpen] = useState<'period' | 'hour' | 'minute' | null>(null)

  const commit = (p: string, h: number, m: number) => {
    let h24 = h % 12
    if (p === '오후') h24 += 12
    onChange(`${String(h24).padStart(2, '0')}:${String(m).padStart(2, '0')}`)
  }

  const handleHourInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseInt(e.target.value)
    if (!isNaN(v) && v >= 1 && v <= 12) commit(period, v, minute)
  }

  const handleMinuteInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseInt(e.target.value)
    if (!isNaN(v) && v >= 0 && v <= 59) commit(period, hour, v)
  }

  const hours   = Array.from({ length: 12 }, (_, i) => i + 1)
  const minutes = Array.from({ length: 12 }, (_, i) => i * 5)

  const DropDown = ({ items, current, onSelect }: { items: (string | number)[]; current: string | number; onSelect: (v: string | number) => void }) => (
    <>
      <div className="fixed inset-0 z-40" onClick={() => setOpen(null)} />
      <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 bg-white rounded-xl shadow-xl border border-stone-100 z-50 overflow-y-auto max-h-44 min-w-[3.5rem]">
        {items.map(item => (
          <button
            key={item}
            onClick={() => { onSelect(item); setOpen(null) }}
            className={`w-full px-3 py-2 text-sm text-center transition-colors hover:bg-stone-50 ${current === item ? 'text-primary font-bold' : 'text-on-surface font-medium'}`}
          >
            {typeof item === 'number' ? String(item).padStart(2, '0') : item}
          </button>
        ))}
      </div>
    </>
  )

  const inputCls = "w-8 bg-transparent text-center text-sm font-bold outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none hover:bg-stone-100 rounded focus:bg-white focus:ring-1 focus:ring-primary/40 transition-colors"

  return (
    <div className="flex items-center gap-0.5 bg-stone-50 border border-stone-200 rounded-xl px-3 py-2.5">
      {/* 오전/오후 */}
      <div className="relative">
        <button onClick={() => setOpen(open === 'period' ? null : 'period')} className="px-2 py-1 rounded-lg hover:bg-stone-100 text-sm font-bold text-primary transition-colors">
          {period}
        </button>
        {open === 'period' && <DropDown items={['오전', '오후']} current={period} onSelect={v => commit(v as string, hour, minute)} />}
      </div>

      {/* 시 */}
      <div className="relative flex items-center">
        <input
          type="number"
          min={1}
          max={12}
          value={hour}
          onChange={handleHourInput}
          className={inputCls}
        />
        <button
          onClick={() => setOpen(open === 'hour' ? null : 'hour')}
          className="text-stone-400 font-bold text-sm hover:text-primary transition-colors px-1"
        >
          시
        </button>
        {open === 'hour' && <DropDown items={hours} current={hour} onSelect={v => commit(period, v as number, minute)} />}
      </div>

      {/* 분 */}
      <div className="relative flex items-center">
        <input
          type="number"
          min={0}
          max={59}
          value={String(minute).padStart(2, '0')}
          onChange={handleMinuteInput}
          className={inputCls}
        />
        <button
          onClick={() => setOpen(open === 'minute' ? null : 'minute')}
          className="text-stone-400 font-bold text-sm hover:text-primary transition-colors px-1"
        >
          분
        </button>
        {open === 'minute' && <DropDown items={minutes} current={minute} onSelect={v => commit(period, hour, v as number)} />}
      </div>
    </div>
  )
}

// ─── Modal ───────────────────────────────────────────────────────────────────
function EventModal({
  state,
  onClose,
  onSave,
  onDelete,
}: {
  state: NonNullable<ModalState>
  onClose: () => void
  onSave: (data: Omit<CalEvent, 'id' | 'colorClass'>) => void
  onDelete: (id: number) => void
}) {
  const isEdit = state.mode === 'edit'
  const date = state.mode === 'add' ? state.date : state.event.date
  const [title, setTitle] = useState(isEdit ? state.event.title : '')
  const [time, setTime]   = useState(isEdit ? state.event.time  : '09:00')
  const [tag, setTag]     = useState<Tag>(isEdit ? state.event.tag : '예약')

  const handleSave = () => {
    if (!title.trim()) return
    onSave({ date, title, time, tag })
    onClose()
  }

  const handleDelete = () => {
    if (isEdit) onDelete(state.event.id)
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm mx-4"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-bold font-headline">
            {isEdit ? '일정 수정' : `${date}일 일정 추가`}
          </h3>
          <button onClick={onClose} className="text-stone-400 hover:text-stone-600 transition-colors">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-stone-500 uppercase tracking-widest mb-1.5 block">제목</label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSave()}
              placeholder="일정 제목을 입력하세요"
              autoFocus
              className="w-full px-4 py-3 rounded-xl bg-stone-50 border border-stone-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-stone-500 uppercase tracking-widest mb-1.5 block">시간</label>
            <TimePicker value={time} onChange={setTime} />
          </div>

          <div>
            <label className="text-xs font-semibold text-stone-500 uppercase tracking-widest mb-1.5 block">태그</label>
            <div className="flex gap-2">
              {(['예약', '행사', '완료', '기타'] as Tag[]).map(t => (
                <button
                  key={t}
                  onClick={() => setTag(t)}
                  className={`flex-1 py-2.5 rounded-xl text-xs font-bold border transition-all ${
                    tag === t ? TAG_COLORS[t] : 'bg-stone-50 border-stone-200 text-stone-400 hover:bg-stone-100'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-8">
          {isEdit && (
            <button
              onClick={handleDelete}
              className="px-4 py-3 rounded-xl bg-error/10 text-error text-sm font-semibold hover:bg-error/20 transition-colors"
            >
              삭제
            </button>
          )}
          <button
            onClick={onClose}
            className="flex-1 py-3 rounded-xl bg-stone-100 text-stone-600 text-sm font-semibold hover:bg-stone-200 transition-colors"
          >
            취소
          </button>
          <button
            onClick={handleSave}
            className="flex-1 py-3 rounded-xl bg-primary text-white text-sm font-bold hover:opacity-90 transition-opacity"
          >
            {isEdit ? '수정 완료' : '추가하기'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── CalendarGrid ─────────────────────────────────────────────────────────────
function CalendarGrid({
  year, month, events, onDayClick, onEventClick,
}: {
  year: number
  month: number
  events: CalEvent[]
  onDayClick: (date: number) => void
  onEventClick: (ev: CalEvent, e: React.MouseEvent) => void
}) {
  const today = new Date()
  const daysInMonth  = getDaysInMonth(year, month)
  const firstDay     = getFirstDayOfMonth(year, month)
  const prevMonthDays = getDaysInPrevMonth(year, month)
  const totalCells   = Math.ceil((firstDay + daysInMonth) / 7) * 7

  const cells = Array.from({ length: totalCells }, (_, i) => {
    if (i < firstDay) return { day: prevMonthDays - firstDay + i + 1, current: false }
    if (i >= firstDay + daysInMonth) return { day: i - firstDay - daysInMonth + 1, current: false }
    return { day: i - firstDay + 1, current: true }
  })

  return (
    <div className="flex-1 grid grid-cols-7 gap-px bg-stone-100 overflow-hidden rounded-xl border border-stone-100">
      {DAYS_EN.map((d, i) => (
        <div key={d} className={`bg-surface py-2 text-center text-xs font-bold tracking-widest uppercase ${i === 0 ? 'text-error' : 'text-stone-400'}`}>
          {d}
        </div>
      ))}
      {cells.map((cell, idx) => {
        const isToday  = cell.current && cell.day === today.getDate() && month === today.getMonth() && year === today.getFullYear()
        const isSunday = idx % 7 === 0
        const dayEvents = cell.current ? events.filter(s => s.date === cell.day) : []

        return (
          <div
            key={idx}
            onClick={() => cell.current && onDayClick(cell.day)}
            className={`bg-surface p-2.5 min-h-[90px] cursor-pointer hover:bg-surface-container-low transition-colors ${!cell.current ? 'opacity-30 cursor-default' : ''} ${isToday ? 'ring-2 ring-primary/30 ring-inset z-10' : ''}`}
          >
            <div className={`w-7 h-7 flex items-center justify-center rounded-full mb-1 text-sm font-bold ${
              isToday ? 'bg-primary text-white' : isSunday && cell.current ? 'text-error' : 'text-on-surface'
            }`}>
              {cell.day}
            </div>
            <div className="space-y-0.5">
              {dayEvents.map((ev, i) => (
                <div
                  key={i}
                  onClick={e => onEventClick(ev, e)}
                  className={`px-1.5 py-0.5 border-l-2 text-[11px] font-semibold truncate rounded-sm hover:opacity-75 transition-opacity ${effectiveColor(ev, year, month)}`}
                >
                  {ev.title}
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── WeekView ─────────────────────────────────────────────────────────────────
function WeekView({
  year, month, baseDay, events, onDayClick, onEventClick,
}: {
  year: number
  month: number
  baseDay: number
  events: CalEvent[]
  onDayClick: (date: number) => void
  onEventClick: (ev: CalEvent, e: React.MouseEvent) => void
}) {
  const today = new Date()
  const weekDates = getWeekDates(year, month, baseDay)

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="grid grid-cols-7 gap-px bg-stone-100 rounded-t-xl border border-stone-100 border-b-0 shrink-0">
        {weekDates.map((date, i) => {
          const isToday = date.toDateString() === today.toDateString()
          return (
            <div key={i} className={`bg-surface py-3 flex flex-col items-center gap-1 ${i === 0 ? 'rounded-tl-xl' : ''} ${i === 6 ? 'rounded-tr-xl' : ''}`}>
              <span className={`text-xs font-bold tracking-widest uppercase ${i === 0 ? 'text-error' : 'text-stone-400'}`}>{DAYS_KO[i]}</span>
              <span className={`w-8 h-8 flex items-center justify-center rounded-full text-sm font-bold transition-colors ${isToday ? 'bg-primary text-white' : 'text-on-surface hover:bg-surface-container-low'}`}>
                {date.getDate()}
              </span>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-7 gap-px bg-stone-100 flex-1 overflow-y-auto rounded-b-xl border border-stone-100 border-t-0">
        {weekDates.map((date, i) => {
          const dayEvents = events.filter(s => new Date(year, month, s.date).toDateString() === date.toDateString())
          const isToday   = date.toDateString() === today.toDateString()
          return (
            <div
              key={i}
              onClick={() => onDayClick(date.getDate())}
              className={`bg-surface p-2 min-h-[200px] cursor-pointer hover:bg-surface-container-low transition-colors ${isToday ? 'bg-primary/[0.02]' : ''}`}
            >
              {dayEvents.length === 0 ? (
                <div className="h-full flex items-center justify-center">
                  <span className="text-xs text-stone-300">+</span>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {dayEvents.map((ev, j) => (
                    <div
                      key={j}
                      onClick={e => onEventClick(ev, e)}
                      className={`p-2 rounded-lg border-l-2 text-xs font-semibold leading-tight cursor-pointer hover:opacity-80 transition-opacity ${effectiveColor(ev, year, month)}`}
                    >
                      <div className="text-[10px] opacity-70 mb-0.5">{ev.time}</div>
                      {ev.title}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── ListView ─────────────────────────────────────────────────────────────────
function ListView({
  year, month, events, onEventClick, onAddNew,
}: {
  year: number
  month: number
  events: CalEvent[]
  onEventClick: (ev: CalEvent, e: React.MouseEvent) => void
  onAddNew: () => void
}) {
  const sorted = events.slice().sort((a, b) => a.date - b.date)
  const accentOf = (ev: CalEvent) => {
    if (isPast(year, month, ev.date)) return 'bg-stone-300'
    if (ev.tag === '행사') return 'bg-red-400'
    if (ev.tag === '예약') return 'bg-blue-400'
    if (ev.tag === '완료') return 'bg-stone-300'
    return 'bg-amber-400'
  }

  if (sorted.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 text-on-surface-variant/40">
        <span className="material-symbols-outlined text-5xl">event_busy</span>
        <p className="text-sm font-medium">이번 달 예약된 포스팅이 없습니다</p>
        <button onClick={onAddNew} className="mt-2 px-6 py-3 rounded-xl bg-primary text-white text-sm font-bold hover:opacity-90 transition-opacity">
          일정 추가하기
        </button>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto space-y-3 pr-1">
      {sorted.map((ev, i) => (
        <div key={i} onClick={e => onEventClick(ev, e)} className="flex items-stretch gap-4 group cursor-pointer">
          <div className="flex flex-col items-center w-14 shrink-0 pt-1">
            <span className="text-xs font-bold text-on-surface-variant">{month + 1}월</span>
            <span className="text-2xl font-extrabold font-headline text-on-surface leading-none">{ev.date}</span>
            <span className="text-[11px] text-on-surface-variant/50">{DAYS_KO[new Date(2024, month, ev.date).getDay()]}</span>
          </div>
          <div className={`w-0.5 self-stretch rounded-full ${accentOf(ev)}`} />
          <div className={`flex-1 p-4 rounded-2xl border ${effectiveColor(ev, year, month)} flex items-center justify-between group-hover:shadow-sm transition-shadow`}>
            <div>
              <p className="text-sm font-bold">{ev.title}</p>
              <p className="text-xs opacity-70 mt-0.5">{ev.time}</p>
            </div>
            <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-white/60">{ev.tag}</span>
          </div>
        </div>
      ))}
      <button
        onClick={onAddNew}
        className="w-full py-4 rounded-2xl border-2 border-dashed border-outline-variant/30 text-on-surface-variant/60 text-sm font-medium hover:bg-surface-container-low transition-colors flex items-center justify-center gap-2 mt-4"
      >
        <span className="material-symbols-outlined text-lg">add</span>
        새 포스팅 예약
      </button>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function CalendarPage() {
  const today = new Date()
  const [year,   setYear]   = useState(today.getFullYear())
  const [month,  setMonth]  = useState(today.getMonth())
  const [view,   setView]   = useState<ViewMode>('월간')
  const [events, setEvents] = useState<CalEvent[]>(INITIAL_EVENTS)
  const [modal,  setModal]  = useState<ModalState>(null)

  const prevMonth = () => { if (month === 0) { setMonth(11); setYear(y => y - 1) } else setMonth(m => m - 1) }
  const nextMonth = () => { if (month === 11) { setMonth(0); setYear(y => y + 1) } else setMonth(m => m + 1) }

  const openAdd  = (date: number) => setModal({ mode: 'add', date })
  const openEdit = (ev: CalEvent, e: React.MouseEvent) => { e.stopPropagation(); setModal({ mode: 'edit', event: ev }) }

  const handleSave = (data: Omit<CalEvent, 'id' | 'colorClass'>) => {
    const colorClass = TAG_COLORS[data.tag]
    if (modal?.mode === 'edit') {
      setEvents(prev => prev.map(ev => ev.id === modal.event.id ? { ...ev, ...data, colorClass } : ev))
    } else {
      setEvents(prev => [...prev, { id: Date.now(), ...data, colorClass }])
    }
  }

  const handleDelete = (id: number) => setEvents(prev => prev.filter(ev => ev.id !== id))

  return (
    <div className="flex min-h-screen bg-surface text-on-surface">
      <SideBar />

      <main className="ml-64 flex-1 flex flex-col h-screen overflow-hidden bg-surface">
        <div className="flex flex-col flex-1 px-10 pb-6 pt-8 gap-6 overflow-hidden">
          <div className="flex flex-col gap-1 shrink-0">
            <span className="text-[0.65rem] font-medium tracking-[0.2em] text-primary uppercase">Editorial Overview</span>
            <h3 className="text-3xl font-bold font-headline text-on-surface">캘린더</h3>
          </div>

          {/* Weather & AI Tip */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 shrink-0">
            <div className="lg:col-span-1 bg-white p-5 rounded-2xl shadow-sm flex items-center gap-6 border border-stone-100">
              <div className="w-14 h-14 bg-primary-container/20 rounded-full flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-primary text-2xl">wb_sunny</span>
              </div>
              <div>
                <p className="text-sm font-semibold text-on-surface">성수동, 18°C 맑음</p>
                <p className="text-xs text-on-surface-variant/70 mt-0.5">강수확률 10% | 습도 45%</p>
              </div>
            </div>
            <div className="lg:col-span-2 bg-[#F2EDE7] p-5 rounded-2xl flex items-start gap-4 border border-stone-200/20">
              <span className="material-symbols-outlined text-tertiary text-xl mt-0.5 shrink-0" style={{ fontVariationSettings: "'FILL' 1" }}>lightbulb</span>
              <div className="space-y-1">
                <p className="text-[10px] font-bold text-tertiary uppercase tracking-widest">AI Curator Tip</p>
                <p className="text-on-secondary-container font-medium text-[0.85rem] leading-relaxed">
                  오후 4시부터 비 예보가 있습니다. 따뜻한 라떼 한 잔의 여유를 추천하는 포스팅은 어떨까요? 매장 내 차분한 분위기를 강조해보세요.
                </p>
              </div>
            </div>
          </div>

          {/* Calendar Card */}
          <div className="flex-1 flex flex-col bg-white rounded-2xl shadow-sm p-6 overflow-hidden border border-stone-100">
            <div className="flex justify-between items-center mb-5 shrink-0">
              <div className="flex items-center gap-6">
                <h4 className="text-xl font-bold font-headline">{year}년 {month + 1}월</h4>
                <div className="flex gap-1.5">
                  <button onClick={prevMonth} className="w-7 h-7 rounded-full bg-surface-container-low flex items-center justify-center hover:bg-surface-container-high transition-colors">
                    <span className="material-symbols-outlined text-sm">chevron_left</span>
                  </button>
                  <button onClick={nextMonth} className="w-7 h-7 rounded-full bg-surface-container-low flex items-center justify-center hover:bg-surface-container-high transition-colors">
                    <span className="material-symbols-outlined text-sm">chevron_right</span>
                  </button>
                </div>
              </div>
              <div className="flex gap-1.5">
                {(['월간', '주간', '리스트'] as ViewMode[]).map(v => (
                  <button
                    key={v}
                    onClick={() => setView(v)}
                    className={`px-3.5 py-1.5 text-[11px] font-semibold rounded-full transition-colors ${view === v ? 'bg-surface-container-high text-on-surface' : 'text-on-surface-variant hover:bg-surface-container-low'}`}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>

            {view === '월간' && <CalendarGrid year={year} month={month} events={events} onDayClick={openAdd} onEventClick={openEdit} />}
            {view === '주간' && <WeekView year={year} month={month} baseDay={today.getDate()} events={events} onDayClick={openAdd} onEventClick={openEdit} />}
            {view === '리스트' && <ListView year={year} month={month} events={events} onEventClick={openEdit} onAddNew={() => openAdd(today.getDate())} />}
          </div>
        </div>
      </main>

      {modal && (
        <EventModal
          state={modal}
          onClose={() => setModal(null)}
          onSave={handleSave}
          onDelete={handleDelete}
        />
      )}
    </div>
  )
}
