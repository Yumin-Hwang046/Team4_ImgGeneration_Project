'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { api, MeResponse } from '@/lib/api'
import { removeToken } from '@/lib/auth'

const navItems = [
  { href: '/dashboard', icon: 'grid_view',           label: '워크스페이스' },
  { href: '/studio',    icon: 'auto_awesome',         label: '생성하기'     },
  { href: '/archive',   icon: 'auto_awesome_motion',  label: '보관함'       },
  { href: '/calendar',  icon: 'calendar_today',       label: '캘린더'       },
]

export default function SideBar() {
  const pathname = usePathname()
  const router = useRouter()
  const [user, setUser] = useState<MeResponse | null>(null)

  useEffect(() => {
    api.auth.me()
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  const handleLogout = () => {
    removeToken()
    router.push('/auth/login')
  }

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-stone-100/50 flex flex-col p-8 space-y-4 z-10 border-r border-outline-variant/10">
      <Link href="/dashboard" className="mb-12 block hover:opacity-80 transition-opacity">
        <h1 className="font-serif italic text-2xl text-stone-900 tracking-tight">
          The Digital Curator
        </h1>
        <p className="text-[10px] uppercase tracking-[0.2em] text-on-surface-variant/70 mt-1.5">
          Editorial Studio
        </p>
      </Link>

      <nav className="flex-1 space-y-1">
        {navItems.map(item => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
                isActive
                  ? 'bg-white/80 text-stone-900 shadow-sm'
                  : 'text-stone-500 hover:bg-stone-200/40'
              }`}
            >
              <span className="material-symbols-outlined text-xl">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="pt-6 border-t border-stone-200/60 space-y-1">
        <Link
          href="/settings"
          className="flex items-center gap-3 px-4 py-3 text-stone-500 hover:bg-stone-200/40 rounded-xl transition-all duration-300"
        >
          <span className="material-symbols-outlined text-xl">tune</span>
          <span className="text-sm">설정</span>
        </Link>

        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-3 text-stone-500 hover:bg-stone-200/40 rounded-xl transition-all duration-300"
        >
          <span className="material-symbols-outlined text-xl">logout</span>
          <span className="text-sm">로그아웃</span>
        </button>

        <div className="mt-4 flex items-center gap-3 px-4">
          <div className="w-9 h-9 rounded-full bg-stone-200 flex items-center justify-center overflow-hidden shrink-0">
            <span className="material-symbols-outlined text-stone-400 text-lg">person</span>
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-xs font-semibold text-on-surface truncate">
              {user?.name ?? '—'}
            </span>
            <span className="text-[10px] text-on-surface-variant/60 truncate">
              {user?.email ?? '로딩 중...'}
            </span>
          </div>
        </div>
      </div>
    </aside>
  )
}
