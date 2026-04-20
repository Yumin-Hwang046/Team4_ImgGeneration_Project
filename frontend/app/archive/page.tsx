'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import Link from 'next/link'
import SideBar from '@/components/SideBar'
import { api, GenerationListItem } from '@/lib/api'

type Tab = '전체' | '날짜별' | '행사별'
type DateView = 'grid' | 'list'

const MONTH_COLORS = [
  'bg-sky-100', 'bg-rose-100', 'bg-green-100', 'bg-amber-100',
  'bg-lime-100', 'bg-teal-100', 'bg-slate-100', 'bg-blue-100',
  'bg-orange-100', 'bg-violet-100', 'bg-stone-100', 'bg-cyan-100',
]

const MONTH_LABELS = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월']

const INITIAL_FOLDERS = [
  { name: '기념일', count: 0 },
  { name: '데일리', count: 0 },
  { name: '축제 및 행사', count: 0 },
]

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
}

const BACKEND_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

function validImgSrc(url: string | null): string | null {
  if (!url) return null
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  if (url.startsWith('/media/')) return `${BACKEND_ORIGIN}${url}`
  return null
}

function GenerationCard({
  item, onDelete, selectMode = false, isSelected = false, onToggleSelect,
}: {
  item: GenerationListItem
  onDelete: (id: number) => void
  selectMode?: boolean
  isSelected?: boolean
  onToggleSelect?: (id: number) => void
}) {
  const src = validImgSrc(item.generated_image_url)
  const title = item.menu_name ?? item.business_category ?? '콘텐츠'
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('이 콘텐츠를 삭제하시겠습니까?')) return
    setDeleting(true)
    try {
      await api.generations.delete(item.id)
      onDelete(item.id)
    } catch {
      setDeleting(false)
    }
  }

  const handleClick = () => {
    if (selectMode && onToggleSelect) onToggleSelect(item.id)
  }

  return (
    <div className="group flex flex-col gap-4 cursor-pointer" onClick={handleClick}>
      <div className={`relative aspect-[4/5] rounded-xl overflow-hidden bg-surface-container-low shadow-sm transition-transform duration-300 ${selectMode ? '' : 'group-hover:-translate-y-1'} ${isSelected ? 'ring-2 ring-primary ring-offset-2' : ''}`}>
        {src ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={src} alt={title} className={`w-full h-full object-cover transition-all duration-500 ${isSelected ? '' : 'grayscale-[0.2] group-hover:grayscale-0 group-hover:scale-105'}`} />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="material-symbols-outlined text-outline/30 text-5xl">image</span>
          </div>
        )}
        {selectMode ? (
          <div className={`absolute top-2 left-2 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${isSelected ? 'bg-primary border-primary' : 'bg-white/80 border-stone-300'}`}>
            {isSelected && <span className="material-symbols-outlined text-white text-sm">check</span>}
          </div>
        ) : (
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="absolute top-2 right-2 w-8 h-8 bg-black/40 hover:bg-error/80 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-200 backdrop-blur-sm"
            title="삭제"
          >
            <span className="material-symbols-outlined text-sm">
              {deleting ? 'hourglass_empty' : 'delete'}
            </span>
          </button>
        )}
      </div>
      <div className="px-1">
        <div className="flex items-center gap-2 mb-1">
          <h4 className="text-base font-medium font-headline truncate">{title}</h4>
          {item.generation_status === 'PENDING' && (
            <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-600 rounded font-bold shrink-0">처리중</span>
          )}
          {item.generation_status === 'FAILED' && (
            <span className="text-[10px] px-1.5 py-0.5 bg-error/10 text-error rounded font-bold shrink-0">실패</span>
          )}
        </div>
        <p className="text-xs text-on-surface-variant">{formatDate(item.created_at)}</p>
      </div>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-32 gap-4 text-on-surface-variant/40">
      <span className="material-symbols-outlined text-5xl">image_search</span>
      <p className="text-sm font-medium">{message}</p>
    </div>
  )
}

function AllTab({ query, items, loading, error, onDelete, selectMode, selectedIds, onToggleSelect }: {
  query: string; items: GenerationListItem[]; loading: boolean; error: string | null
  onDelete: (id: number) => void
  selectMode: boolean; selectedIds: Set<number>; onToggleSelect: (id: number) => void
}) {
  const filtered = query.trim()
    ? items.filter(item =>
        (item.menu_name ?? '').toLowerCase().includes(query.toLowerCase()) ||
        (item.business_category ?? '').toLowerCase().includes(query.toLowerCase())
      )
    : items

  return (
    <section className="p-8 pb-16">
      <div className="mb-12">
        <span className="text-[10px] tracking-[0.2em] font-medium text-primary uppercase">Recent Acquisitions</span>
        <h3 className="text-3xl font-headline font-bold mt-2 text-on-surface">
          {query ? `"${query}" 검색 결과 (${filtered.length})` : '가장 최근 생성된 이미지'}
        </h3>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-32">
          <span className="material-symbols-outlined text-primary text-3xl animate-spin">progress_activity</span>
        </div>
      )}

      {error && <EmptyState message={`불러오기 실패: ${error}`} />}

      {!loading && !error && filtered.length === 0 && (
        <EmptyState message={query ? '검색 결과가 없습니다' : '아직 생성된 콘텐츠가 없습니다'} />
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {filtered.map(item => (
            <GenerationCard
              key={item.id} item={item} onDelete={onDelete}
              selectMode={selectMode} isSelected={selectedIds.has(item.id)} onToggleSelect={onToggleSelect}
            />
          ))}
        </div>
      )}

      {!selectMode && (
        <Link
          href="/studio"
          className="fixed bottom-8 right-8 w-14 h-14 rounded-full cta-gradient text-white shadow-lg flex items-center justify-center hover:scale-105 transition-transform duration-200"
        >
          <span className="material-symbols-outlined">add</span>
        </Link>
      )}
    </section>
  )
}

function MonthFolder({ name, items, onBack, onDelete, selectMode, selectedIds, onToggleSelect }: {
  name: string; items: GenerationListItem[]; onBack: () => void; onDelete: (id: number) => void
  selectMode: boolean; selectedIds: Set<number>; onToggleSelect: (id: number) => void
}) {
  return (
    <div className="p-10 flex flex-col flex-1">
      <div className="flex items-center gap-4 mb-10">
        <button onClick={onBack} className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container-high transition-colors">
          <span className="material-symbols-outlined">arrow_back</span>
        </button>
        <div>
          <p className="text-[10px] font-bold tracking-[0.2em] text-primary uppercase mb-0.5">폴더</p>
          <h3 className="text-2xl font-bold font-headline text-on-surface">{name}</h3>
        </div>
      </div>
      {items.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 text-on-surface-variant/40">
          <span className="material-symbols-outlined text-7xl" style={{ fontVariationSettings: "'FILL' 1" }}>folder_open</span>
          <p className="text-base font-semibold">파일이 없습니다</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {items.map(item => (
            <GenerationCard
              key={item.id} item={item} onDelete={onDelete}
              selectMode={selectMode} isSelected={selectedIds.has(item.id)} onToggleSelect={onToggleSelect}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function DateTab({ items, onDelete, selectMode, selectedIds, onToggleSelect }: {
  items: GenerationListItem[]; onDelete: (id: number) => void
  selectMode: boolean; selectedIds: Set<number>; onToggleSelect: (id: number) => void
}) {
  const [year, setYear] = useState(new Date().getFullYear())
  const [dateView, setDateView] = useState<DateView>('grid')
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null)

  const countByMonth = useCallback((m: number) =>
    items.filter(item => {
      const d = new Date(item.created_at)
      return d.getFullYear() === year && d.getMonth() + 1 === m
    }).length
  , [items, year])

  const itemsForMonth = useCallback((m: number) =>
    items.filter(item => {
      const d = new Date(item.created_at)
      return d.getFullYear() === year && d.getMonth() + 1 === m
    })
  , [items, year])

  if (selectedMonth !== null) {
    return (
      <MonthFolder
        name={`${year} ${MONTH_LABELS[selectedMonth - 1]}`}
        items={itemsForMonth(selectedMonth)}
        onBack={() => setSelectedMonth(null)}
        onDelete={onDelete}
        selectMode={selectMode} selectedIds={selectedIds} onToggleSelect={onToggleSelect}
      />
    )
  }

  return (
    <div className="p-12 flex-1">
      <div className="flex items-center justify-between mb-12">
        <div className="flex items-center gap-6">
          <button onClick={() => setYear(y => y - 1)} className="w-12 h-12 flex items-center justify-center rounded-xl bg-surface-container-lowest shadow-sm hover:bg-surface-container-low transition-colors group">
            <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors">chevron_left</span>
          </button>
          <h2 className="text-4xl font-headline font-bold tracking-tighter text-on-surface">{year}</h2>
          <button onClick={() => setYear(y => y + 1)} className="w-12 h-12 flex items-center justify-center rounded-xl bg-surface-container-lowest shadow-sm hover:bg-surface-container-low transition-colors group">
            <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors">chevron_right</span>
          </button>
        </div>
        <div className="h-px flex-1 mx-12 bg-outline-variant/20" />
        <div className="flex gap-3">
          {(['grid', 'list'] as DateView[]).map(v => (
            <button
              key={v}
              onClick={() => setDateView(v)}
              className={`px-5 py-2.5 rounded-full text-xs font-label tracking-widest font-bold transition-colors ${dateView === v ? 'bg-secondary-container text-on-secondary-container' : 'hover:bg-surface-container-high text-on-surface-variant'}`}
            >
              {v === 'grid' ? 'GRID VIEW' : 'LIST VIEW'}
            </button>
          ))}
        </div>
      </div>

      {dateView === 'grid' ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-8">
          {MONTH_LABELS.map((month, i) => {
            const count = countByMonth(i + 1)
            return (
              <div key={month} className="group cursor-pointer" onClick={() => setSelectedMonth(i + 1)}>
                <div className="relative aspect-square w-full bg-surface-container-lowest rounded-3xl p-3 shadow-sm border border-outline-variant/10 group-hover:shadow-md group-hover:border-primary-container/30 transition-all duration-300">
                  <div className={`h-full w-full rounded-2xl overflow-hidden flex items-center justify-center ${MONTH_COLORS[i]}`}>
                    {count > 0 ? (
                      <span className="text-2xl font-headline font-bold text-on-surface/50">{count}</span>
                    ) : (
                      <span className="material-symbols-outlined text-on-surface/20 text-3xl">image</span>
                    )}
                  </div>
                </div>
                <div className="mt-4 flex flex-col items-center">
                  <span className="text-lg font-headline font-semibold text-on-surface group-hover:text-primary transition-colors">{month}</span>
                  {count > 0 && <span className="text-xs text-on-surface-variant/50">{count}개</span>}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="space-y-2">
          {MONTH_LABELS.map((month, i) => {
            const count = countByMonth(i + 1)
            return (
              <div key={month} className="group flex items-center gap-6 p-4 rounded-2xl hover:bg-surface-container-low transition-colors cursor-pointer" onClick={() => setSelectedMonth(i + 1)}>
                <div className={`w-12 h-12 rounded-2xl overflow-hidden ${MONTH_COLORS[i]} shrink-0 flex items-center justify-center`}>
                  {count > 0 && <span className="text-sm font-bold text-on-surface/50">{count}</span>}
                </div>
                <span className="text-lg font-headline font-semibold text-on-surface group-hover:text-primary transition-colors w-16">{month}</span>
                <div className="h-px flex-1 bg-outline-variant/15" />
                <div className="flex items-center gap-2 text-on-surface-variant/50">
                  <span className="material-symbols-outlined text-base">image</span>
                  <span className="text-xs font-medium">{count}개</span>
                </div>
                <span className="material-symbols-outlined text-on-surface-variant/30 group-hover:text-primary transition-colors">chevron_right</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function EventTab({ onNewFolder }: { onNewFolder: () => void }) {
  const [folders, setFolders] = useState(INITIAL_FOLDERS)
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null)

  if (selectedFolder) {
    return (
      <MonthFolder
        name={selectedFolder}
        items={[]}
        onBack={() => setSelectedFolder(null)}
        onDelete={() => {}}
        selectMode={false}
        selectedIds={new Set<number>()}
        onToggleSelect={() => {}}
      />
    )
  }

  return (
    <section className="p-10 flex-1">
      <div className="max-w-6xl">
        <div className="mb-12">
          <span className="text-[10px] font-bold tracking-[0.2em] text-primary uppercase mb-2 block">Directory</span>
          <h3 className="font-headline text-4xl font-extrabold text-on-surface tracking-tight">행사별 보관</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {folders.map(folder => (
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
  const [items, setItems] = useState<GenerationListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const searchRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.generations.list()
      .then(setItems)
      .catch(err => setFetchError((err as Error).message))
      .finally(() => setLoading(false))
  }, [])

  const toggleSearch = () => {
    const next = !showSearch
    setShowSearch(next)
    if (!next) setSearchQuery('')
    else setTimeout(() => searchRef.current?.focus(), 100)
  }

  const handleDelete = (id: number) => setItems(prev => prev.filter(i => i.id !== id))

  const handleToggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleSelectAll = () => setSelectedIds(new Set(items.map(i => i.id)))
  const handleDeselectAll = () => setSelectedIds(new Set())

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`선택한 ${selectedIds.size}개를 삭제하시겠습니까?`)) return
    await Promise.all(Array.from(selectedIds).map(id => api.generations.delete(id).catch(() => {})))
    setItems(prev => prev.filter(i => !selectedIds.has(i.id)))
    setSelectedIds(new Set())
    setSelectMode(false)
  }

  const exitSelectMode = () => {
    setSelectMode(false)
    setSelectedIds(new Set())
  }

  return (
    <div className="flex min-h-screen bg-surface text-on-surface">
      <SideBar />

      {showModal && (
        <NewFolderModal
          onClose={() => setShowModal(false)}
          onConfirm={() => setShowModal(false)}
        />
      )}

      <main className="ml-64 flex-1 min-h-screen flex flex-col bg-surface">
        <header className="sticky top-0 w-full z-30 bg-surface border-b border-outline-variant/10">
          <div className="flex justify-between items-center px-8 h-20">
            <div className="flex items-center gap-8">
              <h2 className="font-headline font-bold text-2xl text-on-surface">보관함</h2>
              <nav className="flex gap-6">
                {(['전체', '날짜별', '행사별'] as Tab[]).map(tab => (
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

            <div className="flex items-center gap-3">
              {selectMode ? (
                <>
                  <button
                    onClick={selectedIds.size === items.length ? handleDeselectAll : handleSelectAll}
                    className="px-4 py-2 rounded-xl text-sm font-semibold text-on-surface-variant hover:bg-surface-container-high transition-colors"
                  >
                    {selectedIds.size === items.length ? '전체 해제' : '전체 선택'}
                  </button>
                  <button
                    onClick={handleBulkDelete}
                    disabled={selectedIds.size === 0}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-error text-white text-sm font-semibold hover:opacity-90 transition-all disabled:opacity-40"
                  >
                    <span className="material-symbols-outlined text-sm">delete</span>
                    삭제 {selectedIds.size > 0 && `(${selectedIds.size}개)`}
                  </button>
                  <button
                    onClick={exitSelectMode}
                    className="px-4 py-2 rounded-xl text-sm font-semibold text-on-surface-variant hover:bg-surface-container-high transition-colors"
                  >
                    취소
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={toggleSearch}
                    className={`w-10 h-10 flex items-center justify-center rounded-full transition-colors ${showSearch ? 'bg-primary text-white' : 'hover:bg-surface-container-high text-on-surface-variant'}`}
                  >
                    <span className="material-symbols-outlined">{showSearch ? 'close' : 'search'}</span>
                  </button>
                  {activeTab !== '행사별' && (
                    <button
                      onClick={() => setSelectMode(true)}
                      className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container-high text-on-surface-variant transition-colors"
                      title="선택"
                    >
                      <span className="material-symbols-outlined">checklist</span>
                    </button>
                  )}
                  {activeTab === '행사별' && (
                    <button
                      onClick={() => setShowModal(true)}
                      className="flex items-center gap-2 cta-gradient text-white px-5 py-2.5 rounded-xl font-semibold shadow-sm hover:opacity-90 transition-all"
                    >
                      <span className="material-symbols-outlined text-[20px]">add</span>
                      <span>새 폴더</span>
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          {showSearch && (
            <div className="px-8 pb-4 flex items-center gap-3 animate-in slide-in-from-top-2 duration-200">
              <div className="flex-1 flex items-center gap-3 bg-surface-container-low rounded-xl px-4 py-2.5">
                <span className="material-symbols-outlined text-on-surface-variant text-lg">search</span>
                <input
                  ref={searchRef}
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="메뉴명 또는 업종으로 검색..."
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

        {activeTab === '전체' && (
          <AllTab
            query={searchQuery} items={items} loading={loading} error={fetchError} onDelete={handleDelete}
            selectMode={selectMode} selectedIds={selectedIds} onToggleSelect={handleToggleSelect}
          />
        )}
        {activeTab === '날짜별' && (
          <DateTab
            items={items} onDelete={handleDelete}
            selectMode={selectMode} selectedIds={selectedIds} onToggleSelect={handleToggleSelect}
          />
        )}
        {activeTab === '행사별' && <EventTab onNewFolder={() => setShowModal(true)} />}
      </main>
    </div>
  )
}
