'use client'

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import SideBar from '@/components/SideBar'

type Tab = '전체' | '날짜별' | '행사별'
type DateView = 'grid' | 'list'

const allItems = [
  { id: 1, title: '여름 시즌 라떼', date: '2024.05.20', img: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=400&h=500&fit=crop&auto=format&q=80' },
  { id: 2, title: '주말 브런치 홍보', date: '2024.05.18', img: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=500&fit=crop&auto=format&q=80' },
  { id: 3, title: '매장 인테리어 컨셉', date: '2024.05.15', img: 'https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=400&h=500&fit=crop&auto=format&q=80' },
  { id: 4, title: '원두 로스팅 디테일', date: '2024.05.14', img: 'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&h=500&fit=crop&auto=format&q=80' },
  { id: 5, title: '데스크테리어 홍보', date: '2024.05.12', img: 'https://images.unsplash.com/photo-1499951615-1a9b61d55f1b?w=400&h=500&fit=crop&auto=format&q=80' },
  { id: 6, title: '핸드드립 시연', date: '2024.05.10', img: 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=400&h=500&fit=crop&auto=format&q=80' },
  { id: 7, title: '디저트 신메뉴', date: '2024.05.08', img: 'https://images.unsplash.com/photo-1578985545062-64d7f8fd45cd?w=400&h=500&fit=crop&auto=format&q=80' },
  { id: 8, title: '시그니처 머그', date: '2024.05.05', img: 'https://images.unsplash.com/photo-1497515114629-f71d768fd07c?w=400&h=500&fit=crop&auto=format&q=80' },
]

const monthColors = [
  'bg-sky-100', 'bg-rose-100', 'bg-green-100', 'bg-amber-100',
  'bg-lime-100', 'bg-teal-100', 'bg-slate-100', 'bg-blue-100',
  'bg-orange-100', 'bg-violet-100', 'bg-stone-100', 'bg-cyan-100',
]

const monthImages = [
  'https://images.unsplash.com/photo-1507914372368-b2b085b925a1?w=200&h=200&fit=crop&q=80',
  'https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=200&h=200&fit=crop&q=80',
  'https://images.unsplash.com/photo-1490750967868-88df5691cc07?w=200&h=200&fit=crop&q=80',
  'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=200&h=200&fit=crop&q=80',
  'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=200&h=200&fit=crop&q=80',
  'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=200&h=200&fit=crop&q=80',
  'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=200&h=200&fit=crop&q=80',
  'https://images.unsplash.com/photo-1578985545062-64d7f8fd45cd?w=200&h=200&fit=crop&q=80',
  'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=200&h=200&fit=crop&q=80',
  'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=200&h=200&fit=crop&q=80',
  'https://images.unsplash.com/photo-1499951615-1a9b61d55f1b?w=200&h=200&fit=crop&q=80',
  'https://images.unsplash.com/photo-1497515114629-f71d768fd07c?w=200&h=200&fit=crop&q=80',
]

const initialFolders = [
  { name: '기념일', count: 124 },
  { name: '데일리', count: 85 },
  { name: '축제 및 행사', count: 242 },
]

function imgFallback(e: React.SyntheticEvent<HTMLImageElement>, seed: string) {
  const t = e.target as HTMLImageElement
  t.onerror = null
  t.src = `https://picsum.photos/seed/${seed}/400/500`
}

function AllTab({ query }: { query: string }) {
  const filtered = query.trim()
    ? allItems.filter(item => item.title.toLowerCase().includes(query.toLowerCase()))
    : allItems

  return (
    <section className="p-8 pb-16">
      <div className="mb-12">
        <span className="text-[10px] tracking-[0.2em] font-medium text-primary uppercase">Recent Acquisitions</span>
        <h3 className="text-3xl font-headline font-bold mt-2 text-on-surface">
          {query ? `"${query}" 검색 결과 (${filtered.length})` : '가장 최근 생성된 이미지'}
        </h3>
      </div>

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 gap-4 text-on-surface-variant/40">
          <span className="material-symbols-outlined text-5xl">image_search</span>
          <p className="text-sm font-medium">검색 결과가 없습니다</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {filtered.map((item) => (
            <div key={item.id} className="group flex flex-col gap-4 cursor-pointer">
              <div className="aspect-[4/5] rounded-xl overflow-hidden bg-surface-container-low shadow-sm transition-transform duration-300 group-hover:-translate-y-1">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={item.img}
                  alt={item.title}
                  className="w-full h-full object-cover grayscale-[0.2] group-hover:grayscale-0 group-hover:scale-105 transition-all duration-500"
                  onError={(e) => imgFallback(e, `item-${item.id}`)}
                />
              </div>
              <div className="px-1">
                <h4 className="text-base font-medium font-headline">{item.title}</h4>
                <p className="text-xs text-on-surface-variant mt-1">{item.date}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <Link
        href="/studio"
        className="fixed bottom-8 right-8 w-14 h-14 rounded-full cta-gradient text-white shadow-lg flex items-center justify-center hover:scale-105 transition-transform duration-200"
      >
        <span className="material-symbols-outlined">add</span>
      </Link>
    </section>
  )
}

function FolderEmpty({ name, onBack }: { name: string; onBack: () => void }) {
  return (
    <div className="p-10 flex flex-col flex-1">
      <div className="flex items-center gap-4 mb-10">
        <button
          onClick={onBack}
          className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container-high transition-colors"
        >
          <span className="material-symbols-outlined">arrow_back</span>
        </button>
        <div>
          <p className="text-[10px] font-bold tracking-[0.2em] text-primary uppercase mb-0.5">폴더</p>
          <h3 className="text-2xl font-bold font-headline text-on-surface">{name}</h3>
        </div>
      </div>
      <div className="flex-1 flex flex-col items-center justify-center gap-4 text-on-surface-variant/40">
        <span className="material-symbols-outlined text-7xl" style={{ fontVariationSettings: "'FILL' 1" }}>folder_open</span>
        <p className="text-base font-semibold">파일이 없습니다</p>
        <p className="text-sm">아직 이 폴더에 저장된 이미지가 없어요</p>
      </div>
    </div>
  )
}

function DateTab() {
  const [year, setYear] = useState(new Date().getFullYear())
  const [dateView, setDateView] = useState<DateView>('grid')
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null)
  const months = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월']

  if (selectedMonth) return <FolderEmpty name={`${year} ${selectedMonth}`} onBack={() => setSelectedMonth(null)} />

  return (
    <div className="p-12 flex-1">
      <div className="flex items-center justify-between mb-12">
        <div className="flex items-center gap-6">
          <button
            onClick={() => setYear(y => y - 1)}
            className="w-12 h-12 flex items-center justify-center rounded-xl bg-surface-container-lowest shadow-sm hover:bg-surface-container-low transition-colors group"
          >
            <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors">chevron_left</span>
          </button>
          <h2 className="text-4xl font-headline font-bold tracking-tighter text-on-surface">{year}</h2>
          <button
            onClick={() => setYear(y => y + 1)}
            className="w-12 h-12 flex items-center justify-center rounded-xl bg-surface-container-lowest shadow-sm hover:bg-surface-container-low transition-colors group"
          >
            <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors">chevron_right</span>
          </button>
        </div>
        <div className="h-px flex-1 mx-12 bg-outline-variant/20" />
        <div className="flex gap-3">
          <button
            onClick={() => setDateView('grid')}
            className={`px-5 py-2.5 rounded-full text-xs font-label tracking-widest font-bold transition-colors ${dateView === 'grid' ? 'bg-secondary-container text-on-secondary-container' : 'hover:bg-surface-container-high text-on-surface-variant'}`}
          >
            GRID VIEW
          </button>
          <button
            onClick={() => setDateView('list')}
            className={`px-5 py-2.5 rounded-full text-xs font-label tracking-widest font-bold transition-colors ${dateView === 'list' ? 'bg-secondary-container text-on-secondary-container' : 'hover:bg-surface-container-high text-on-surface-variant'}`}
          >
            LIST VIEW
          </button>
        </div>
      </div>

      {dateView === 'grid' ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-8">
          {months.map((month, i) => (
            <div key={month} className="group cursor-pointer" onClick={() => setSelectedMonth(month)}>
              <div className="relative aspect-square w-full bg-surface-container-lowest rounded-3xl p-3 shadow-sm border border-outline-variant/10 group-hover:shadow-md group-hover:border-primary-container/30 transition-all duration-300">
                <div className={`h-full w-full rounded-2xl overflow-hidden ${monthColors[i]}`}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={monthImages[i]}
                    alt={month}
                    className="w-full h-full object-cover opacity-70 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                  />
                </div>
              </div>
              <div className="mt-4 flex flex-col items-center">
                <span className="text-lg font-headline font-semibold text-on-surface group-hover:text-primary transition-colors">{month}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {months.map((month, i) => (
            <div key={month} className="group flex items-center gap-6 p-4 rounded-2xl hover:bg-surface-container-low transition-colors cursor-pointer" onClick={() => setSelectedMonth(month)}>
              <div className={`w-12 h-12 rounded-2xl overflow-hidden ${monthColors[i]} shrink-0`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={monthImages[i]} alt={month} className="w-full h-full object-cover opacity-70 group-hover:opacity-100 transition-opacity" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
              </div>
              <span className="text-lg font-headline font-semibold text-on-surface group-hover:text-primary transition-colors w-16">{month}</span>
              <div className="h-px flex-1 bg-outline-variant/15" />
              <div className="flex items-center gap-2 text-on-surface-variant/50">
                <span className="material-symbols-outlined text-base">image</span>
                <span className="text-xs font-medium">{Math.floor(Math.random() * 30 + 5)} 개</span>
              </div>
              <span className="material-symbols-outlined text-on-surface-variant/30 group-hover:text-primary transition-colors">chevron_right</span>
            </div>
          ))}
        </div>
      )}

      <footer className="mt-16 pt-8 flex justify-between items-center text-on-surface-variant/40 border-t border-outline-variant/10">
        <div className="text-[10px] font-label tracking-widest font-bold">THE HUMAN ARCHIVE v2.0</div>
        <div className="text-[10px] font-label tracking-widest uppercase">System status: All repositories operational</div>
      </footer>
    </div>
  )
}

function EventTab({ onNewFolder }: { onNewFolder: () => void }) {
  const [folders, setFolders] = useState(initialFolders)
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null)

  if (selectedFolder) return <FolderEmpty name={selectedFolder} onBack={() => setSelectedFolder(null)} />

  return (
    <section className="p-10 flex-1">
      <div className="max-w-6xl">
        <div className="mb-12">
          <span className="text-[10px] font-bold tracking-[0.2em] text-primary uppercase mb-2 block">Directory</span>
          <h3 className="font-headline text-4xl font-extrabold text-on-surface tracking-tight">행사별 보관</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {folders.map((folder) => (
            <div key={folder.name} className="group cursor-pointer" onClick={() => setSelectedFolder(folder.name)}>
              <div className="aspect-square bg-surface-container-lowest rounded-[2rem] p-8 shadow-sm group-hover:shadow-md transition-all duration-300 flex flex-col items-center justify-center relative overflow-hidden">
                <div className="absolute inset-0 bg-primary opacity-0 group-hover:opacity-[0.03] transition-opacity" />
                <div className="w-20 h-20 rounded-2xl bg-surface-container-low flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                  <span className="material-symbols-outlined text-primary text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>folder</span>
                </div>
                <p className="font-headline text-lg font-bold text-on-surface">{folder.name}</p>
                <p className="text-sm text-on-surface-variant/50 mt-1 font-medium">{folder.count} items</p>
              </div>
            </div>
          ))}

          <div className="group cursor-pointer" onClick={onNewFolder}>
            <div className="aspect-square border-2 border-dashed border-outline-variant/30 rounded-[2rem] p-8 flex flex-col items-center justify-center hover:border-primary/40 transition-all duration-300">
              <div className="w-16 h-16 rounded-full bg-surface-container-high flex items-center justify-center mb-4 group-hover:bg-primary-container transition-colors">
                <span className="material-symbols-outlined text-on-surface-variant group-hover:text-white">add</span>
              </div>
              <p className="font-headline text-sm font-semibold text-on-surface-variant/60">추가하기</p>
            </div>
          </div>
        </div>

        {/* Stats bento */}
        <div className="mt-20 grid grid-cols-12 gap-8">
          <div className="col-span-12 lg:col-span-8 bg-surface-container-low rounded-[2rem] p-10 flex flex-col justify-between">
            <div>
              <span className="text-[10px] font-bold tracking-[0.2em] text-tertiary uppercase mb-4 block">System Insights</span>
              <h4 className="font-headline text-2xl font-bold mb-6">최근 업데이트된 아카이브</h4>
            </div>
            <div className="flex gap-4 overflow-x-auto pb-4">
              {[
                { label: 'EVENTS', img: 'https://images.unsplash.com/photo-1507914372368-b2b085b925a1?w=200&h=150&fit=crop&q=80' },
                { label: 'ANNUAL', img: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=200&h=150&fit=crop&q=80' },
                { label: 'DAILY', img: 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=200&h=150&fit=crop&q=80' },
              ].map((item, i) => (
                <div key={i} className="min-w-[120px] h-32 rounded-2xl overflow-hidden shadow-sm relative group flex-shrink-0">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={item.img} alt={item.label} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onError={(e) => { (e.target as HTMLImageElement).style.display='none' }} />
                  <div className="absolute inset-0 bg-black/30 z-10" />
                  <span className="absolute bottom-3 left-3 z-20 text-[10px] font-bold text-white tracking-wider">{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="col-span-12 lg:col-span-4 bg-primary text-white rounded-[2rem] p-10 flex flex-col justify-between shadow-xl shadow-primary/20">
            <div className="flex justify-between items-start">
              <span className="material-symbols-outlined text-4xl opacity-50">data_usage</span>
              <span className="text-[10px] font-bold tracking-[0.2em] opacity-60 uppercase">Storage Capacity</span>
            </div>
            <div>
              <div className="text-5xl font-headline font-extrabold mb-2">72%</div>
              <div className="w-full bg-white/20 h-1 rounded-full mb-4">
                <div className="bg-white h-1 rounded-full" style={{ width: '72%' }} />
              </div>
              <p className="text-sm opacity-80 leading-relaxed font-medium">
                사용 가능한 용량이 2.4TB 남았습니다. 효율적인 보관을 위해 정기적인 백업을 권장합니다.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function NewFolderModal({ onClose, onConfirm }: { onClose: () => void; onConfirm: (name: string) => void }) {
  const [name, setName] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  const handleSubmit = () => {
    if (!name.trim()) return
    onConfirm(name.trim())
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-surface-container-lowest rounded-3xl p-8 w-full max-w-sm shadow-2xl" onClick={e => e.stopPropagation()}>
        <h3 className="font-headline text-xl font-bold text-on-surface mb-1">새 폴더 만들기</h3>
        <p className="text-xs text-on-surface-variant mb-6">폴더 이름을 입력하세요</p>
        <input
          ref={inputRef}
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          placeholder="예: 시즌 프로모션"
          className="w-full bg-surface-container-low rounded-xl px-4 py-3 text-sm text-on-surface placeholder:text-stone-400 outline-none focus:ring-2 focus:ring-primary/30 transition-all"
        />
        <div className="flex gap-3 mt-6">
          <button onClick={onClose} className="flex-1 py-3 rounded-xl border border-outline-variant text-on-surface-variant text-sm font-medium hover:bg-surface-container-low transition-colors">
            취소
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim()}
            className="flex-1 py-3 rounded-xl cta-gradient text-white text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-40"
          >
            만들기
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ArchivePage() {
  const [activeTab, setActiveTab] = useState<Tab>('전체')
  const [showSearch, setShowSearch] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showModal, setShowModal] = useState(false)
  const searchRef = useRef<HTMLInputElement>(null)

  const toggleSearch = () => {
    const next = !showSearch
    setShowSearch(next)
    if (!next) setSearchQuery('')
    else setTimeout(() => searchRef.current?.focus(), 100)
  }

  return (
    <div className="flex min-h-screen bg-surface text-on-surface">
      <SideBar />

      {showModal && (
        <NewFolderModal
          onClose={() => setShowModal(false)}
          onConfirm={(name) => console.info('New folder:', name)}
        />
      )}

      <main className="ml-64 flex-1 min-h-screen flex flex-col bg-surface">
        {/* TopAppBar */}
        <header className="sticky top-0 w-full z-30 bg-surface border-b border-outline-variant/10">
          <div className="flex justify-between items-center px-8 h-20">
            <div className="flex items-center gap-8">
              <h2 className="font-headline font-bold text-2xl text-on-surface">보관함</h2>
              <nav className="flex gap-6">
                {(['전체', '날짜별', '행사별'] as Tab[]).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`font-headline font-bold text-base pb-1 transition-all ${activeTab === tab ? 'text-primary border-b-2 border-primary' : 'text-on-surface/40 hover:text-primary'}`}
                  >
                    {tab}
                  </button>
                ))}
              </nav>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={toggleSearch}
                className={`w-10 h-10 flex items-center justify-center rounded-full transition-colors ${showSearch ? 'bg-primary text-white' : 'hover:bg-surface-container-high text-on-surface-variant'}`}
              >
                <span className="material-symbols-outlined">{showSearch ? 'close' : 'search'}</span>
              </button>
              {activeTab === '행사별' && (
                <button
                  onClick={() => setShowModal(true)}
                  className="flex items-center gap-2 cta-gradient text-white px-5 py-2.5 rounded-xl font-semibold shadow-sm hover:opacity-90 transition-all"
                >
                  <span className="material-symbols-outlined text-[20px]">add</span>
                  <span>새 폴더</span>
                </button>
              )}
            </div>
          </div>

          {/* Search bar slide-down */}
          {showSearch && (
            <div className="px-8 pb-4 flex items-center gap-3 animate-in slide-in-from-top-2 duration-200">
              <div className="flex-1 flex items-center gap-3 bg-surface-container-low rounded-xl px-4 py-2.5">
                <span className="material-symbols-outlined text-on-surface-variant text-lg">search</span>
                <input
                  ref={searchRef}
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="이미지 검색..."
                  className="flex-1 bg-transparent text-sm text-on-surface placeholder:text-stone-400 outline-none"
                />
                {searchQuery && (
                  <button onClick={() => setSearchQuery('')} className="text-on-surface-variant/60 hover:text-on-surface transition-colors">
                    <span className="material-symbols-outlined text-lg">close</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </header>

        {activeTab === '전체' && <AllTab query={searchQuery} />}
        {activeTab === '날짜별' && <DateTab />}
        {activeTab === '행사별' && <EventTab onNewFolder={() => setShowModal(true)} />}
      </main>
    </div>
  )
}
