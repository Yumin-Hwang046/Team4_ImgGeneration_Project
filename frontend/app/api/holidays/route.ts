import { NextRequest, NextResponse } from 'next/server'

// Nager.Date 응답 타입
interface NagerHoliday {
  date: string        // "2026-02-17"
  localName: string   // "설날"
  name: string        // "Lunar New Year"
  countryCode: string
  fixed: boolean
  global: boolean
  types: string[]
}

// 캐시 (서버 메모리, 재시작 전까지 유지)
const cache: Record<number, { data: NagerHoliday[]; fetchedAt: number }> = {}
const CACHE_TTL_MS = 24 * 60 * 60 * 1000 // 24시간

export async function GET(req: NextRequest) {
  const year = Number(req.nextUrl.searchParams.get('year') ?? new Date().getFullYear())

  if (!year || year < 2020 || year > 2100) {
    return NextResponse.json({ error: 'invalid year' }, { status: 400 })
  }

  const cached = cache[year]
  if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
    return NextResponse.json(cached.data)
  }

  try {
    const res = await fetch(
      `https://date.nager.at/api/v3/PublicHolidays/${year}/KR`,
      { next: { revalidate: 86400 } },
    )

    if (!res.ok) {
      return NextResponse.json(cached?.data ?? [], { status: 200 })
    }

    const data: NagerHoliday[] = await res.json()
    cache[year] = { data, fetchedAt: Date.now() }

    return NextResponse.json(data)
  } catch {
    return NextResponse.json(cached?.data ?? [], { status: 200 })
  }
}
