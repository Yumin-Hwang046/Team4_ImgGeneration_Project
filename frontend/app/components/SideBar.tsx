'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const SIDE_NAV_ITEMS = [
  { href: '/generator', label: 'Generator' },
  { href: '#', label: 'Templates' },
  { href: '#', label: 'Library' },
  { href: '#', label: 'Analytics' },
  { href: '#', label: 'Archive' },
] as const;

export default function SideBar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex flex-col h-full p-6 gap-3 bg-[#F5F3F0] w-72 border-r border-surface-container font-body font-medium text-sm">
      <div className="mb-10 px-2">
        <h2 className="text-xl font-bold text-[#296678] font-headline">Marketing Studio</h2>
        <p className="text-xs text-on-surface-variant/70 mt-1">Premium Tier Plan</p>
      </div>
      <nav className="flex flex-col gap-2">
        {SIDE_NAV_ITEMS.map((item) => {
          const isActive = item.href === pathname;
          return (
            <Link
              key={item.label}
              href={item.href}
              className={
                isActive
                  ? 'flex items-center gap-4 px-5 py-4 bg-[#FFFFFF] text-[#296678] rounded-xl shadow-sm'
                  : 'flex items-center gap-4 px-5 py-4 text-[#1B1C1A]/70 hover:bg-[#EAE8E5] transition-all duration-200 rounded-xl'
              }
            >
              <span className={isActive ? 'font-semibold' : ''}>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto pt-6 flex flex-col gap-3">
        <button className="w-full mb-6 py-4 px-5 bg-gradient-to-br from-primary to-primary-container text-on-primary rounded-xl font-semibold shadow-lg active:scale-95 transition-all font-body">
          New Project
        </button>
        <Link
          href="#"
          className="flex items-center gap-4 px-5 py-4 text-[#1B1C1A]/70 hover:bg-[#EAE8E5] transition-all duration-200 rounded-xl"
        >
          <span>Help Center</span>
        </Link>
      </div>
    </aside>
  );
}
