'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_LINKS = [
  { href: '#', label: 'Dashboard' },
  { href: '#', label: 'Assets' },
  { href: '/generator', label: 'Campaigns' },
  { href: '#', label: 'History' },
] as const;

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="bg-[#FBF9F6] flex justify-between items-center px-10 h-20 w-full sticky top-0 z-50 border-b border-surface-container">
      <div className="flex items-center gap-12">
        <Link href="/generator">
          <span className="text-2xl font-bold text-[#1B1C1A] font-headline tracking-tight cursor-pointer">
            Nordic Muse
          </span>
        </Link>
        <div className="hidden md:flex gap-8 items-center">
          {NAV_LINKS.map((link) => {
            const isActive = link.href === '/generator' && pathname === '/generator';
            return (
              <Link
                key={link.label}
                href={link.href}
                className={
                  isActive
                    ? 'font-headline font-semibold text-[#296678] border-b-2 border-[#296678] pb-1'
                    : 'font-headline font-semibold text-[#1B1C1A]/60 hover:text-[#296678] transition-colors duration-200'
                }
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      </div>
      <div className="flex items-center gap-6">
        <div className="w-10 h-10 rounded-full bg-surface-container-highest overflow-hidden ml-2 ring-2 ring-surface-container flex items-center justify-center">
          <span className="text-on-surface-variant text-sm font-bold font-headline">NM</span>
        </div>
      </div>
    </nav>
  );
}
