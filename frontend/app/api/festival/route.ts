import { NextRequest, NextResponse } from 'next/server'

interface TourApiItem {
  title: string
  addr1?: string
  eventstartdate?: string
  eventenddate?: string
  firstimage?: string
  contentid?: string
  mapx?: string
  mapy?: string
  dist?: string
}

interface TourApiResponse {
  response?: {
    body?: {
      items?: { item?: TourApiItem | TourApiItem[] }
      totalCount?: number
    }
    header?: { resultCode: string; resultMsg: string }
  }
}

/**
 * 날짜 차이 계산 (YYYYMMDD)
 */
function getDurationDays(start: string, end: string): number {
  if (!start || !end || start.length !== 8 || end.length !== 8) return 999;
  const startDate = new Date(`${start.slice(0, 4)}-${start.slice(4, 6)}-${start.slice(6, 8)}`);
  const endDate = new Date(`${end.slice(0, 4)}-${end.slice(4, 6)}-${end.slice(6, 8)}`);
  const diffTime = Math.abs(endDate.getTime() - startDate.getTime());
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
}

function normalizeItems(raw: TourApiItem | TourApiItem[] | undefined): TourApiItem[] {
  if (!raw) return []
  return Array.isArray(raw) ? raw : [raw]
}

function formatDate(yyyymmdd: string): string {
  if (!yyyymmdd || yyyymmdd.length < 8) return yyyymmdd
  return `${yyyymmdd.slice(0, 4)}-${yyyymmdd.slice(4, 6)}-${yyyymmdd.slice(6, 8)}`
}

function haversineMeters(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371000
  const toRad = (v: number) => v * Math.PI / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

export async function GET(req: NextRequest) {
  const lat = req.nextUrl.searchParams.get('lat')
  const lng = req.nextUrl.searchParams.get('lng')
  const serviceKey = process.env.FESTIVAL_API_KEY

  if (!serviceKey) return NextResponse.json([], { status: 200 })

  try {
    const todayStr = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    
    // 전국 최신 데이터 호출
    const url = `https://apis.data.go.kr/B551011/KorService2/searchFestival2?serviceKey=${encodeURIComponent(serviceKey)}&pageNo=1&numOfRows=1000&eventStartDate=${todayStr}&arrange=D&MobileOS=ETC&MobileApp=TDC&_type=json`

    const res = await fetch(url, { cache: 'no-store' })
    const data: TourApiResponse = await res.json()
    const items = normalizeItems(data.response?.body?.items?.item)

    const userLat = lat ? Number(lat) : null
    const userLng = lng ? Number(lng) : null

    // 위치 정보가 아예 없으면 빈 결과를 반환하거나 에러 처리를 할 수 있습니다.
    // 여기서는 위치 정보가 없을 경우 필터링 없이 20개만 보여주도록 설정했습니다.
    if (!userLat || !userLng) {
      console.warn('[festival] 위치 정보가 없어 거리 필터링을 수행할 수 없습니다.')
      return NextResponse.json([]) // 혹은 안내 메시지와 함께 빈 배열 반환
    }

    const festivals = items
      .filter(item => {
        // 1. 날짜 및 기간 필터 (30일 이내 단기 행사만)
        if (!item.eventstartdate || !item.eventenddate) return false
        if (item.eventenddate < todayStr) return false
        if (getDurationDays(item.eventstartdate, item.eventenddate) > 30) return false

        // 2. 키워드 필터 (문화제, 전시 등 제외)
        const exclude = ['전시', '기획', '특별', '상설', '교육', '체험관', '프로그램', '문화제', '기념식', '대회']
        if (exclude.some(k => item.title.includes(k))) return false

        const include = ['축제', '페스티벌', '페스타', '제', '야시장', '행사']
        if (!include.some(k => item.title.includes(k))) return false

        // 3. 거리 필터 (20km 이내로 제한)
        const itemLat = item.mapy ? Number(item.mapy) : null
        const itemLng = item.mapx ? Number(item.mapx) : null
        if (!itemLat || !itemLng) return false // 위치 정보 없는 데이터 제외

        const distM = haversineMeters(userLat, userLng, itemLat, itemLng)
        return distM <= 10000 //  20km 이내만 허용
      })
      .map(item => {
        const itemLat = item.mapy ? Number(item.mapy) : null
        const itemLng = item.mapx ? Number(item.mapx) : null
        const distM = (userLat && userLng && itemLat && itemLng)
          ? haversineMeters(userLat, userLng, itemLat, itemLng)
          : 0;

        return {
          contentId: item.contentid ?? '',
          title:     item.title,
          address:   item.addr1 ?? '',
          startDate: formatDate(item.eventstartdate ?? ''),
          endDate:   formatDate(item.eventenddate ?? ''),
          image:     item.firstimage ?? null,
          distance:  `${Math.round(distM / 1000)}km`,
          rawDist:   distM
        }
      })
      .sort((a, b) => a.rawDist - b.rawDist) // 가까운 순 정렬

    console.log(`[festival] 10km 반경 내 최종 결과: ${festivals.length}건`)
    return NextResponse.json(festivals.map(({ rawDist, ...rest }) => rest))
    
  } catch (e) {
    console.error('[festival] error:', e)
    return NextResponse.json([])
  }
}
