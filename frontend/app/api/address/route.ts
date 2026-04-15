import { NextRequest, NextResponse } from 'next/server'

interface RegionDoc {
  region_type: string
  code: string
  region_3depth_name: string
  address_name: string
}

async function getRegionFromCoords(x: string, y: string, headers: Record<string, string>) {
  const res = await fetch(
    `https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x=${x}&y=${y}`,
    { headers, cache: 'no-store' }
  )
  if (!res.ok) return null
  const data = await res.json()
  // H타입 = 행정동 (서울 API와 동일한 명칭 체계)
  const region: RegionDoc | undefined = data.documents?.find(
    (d: RegionDoc) => d.region_type === 'H'
  )
  return region ?? null
}

export async function GET(req: NextRequest) {
  const query = req.nextUrl.searchParams.get('query')
  if (!query || query.trim().length < 2) {
    return NextResponse.json({ documents: [], coords: null, dongNm: null })
  }

  const apiKey = process.env.KAKAO_REST_API_KEY
  if (!apiKey) {
    return NextResponse.json({ error: 'API key missing' }, { status: 500 })
  }

  const headers = { Authorization: `KakaoAK ${apiKey}` }

  // 1차: 주소 검색 (h_code 포함)
  const addressRes = await fetch(
    `https://dapi.kakao.com/v2/local/search/address.json?query=${encodeURIComponent(query)}&size=5`,
    { headers, cache: 'no-store' }
  )
  const addressData = await addressRes.json()
  const firstDoc = addressData.documents?.[0]
  const hCode = firstDoc?.address?.h_code

  if (hCode && firstDoc?.x && firstDoc?.y) {
    // 좌표로 정확한 행정동명 조회 (서울 API 매칭용)
    const region = await getRegionFromCoords(firstDoc.x, firstDoc.y, headers)
    console.log('[address] h_code:', hCode, '| 행정동:', region?.region_3depth_name ?? 'NONE')
    return NextResponse.json({
      ...addressData,
      coords: { lat: firstDoc.y, lng: firstDoc.x },
      dongNm: region?.region_3depth_name ?? null,
    })
  }

  // 2차: 키워드 검색 → 좌표 → 행정동코드/명 역조회
  const keywordRes = await fetch(
    `https://dapi.kakao.com/v2/local/search/keyword.json?query=${encodeURIComponent(query)}&size=1`,
    { headers, cache: 'no-store' }
  )
  const keywordData = await keywordRes.json()
  const place = keywordData.documents?.[0]

  if (!place?.x || !place?.y) {
    console.log('[address] keyword fallback empty')
    return NextResponse.json({ documents: [], coords: null, dongNm: null })
  }

  const region = await getRegionFromCoords(place.x, place.y, headers)
  console.log('[address] coord2region h_code:', region?.code ?? 'NONE', '| 행정동:', region?.region_3depth_name ?? 'NONE')

  if (!region) return NextResponse.json({ documents: [], coords: null, dongNm: null })

  return NextResponse.json({
    documents: [{
      address_name: region.address_name,
      address_type: 'REGION_ADDR',
      address: { h_code: region.code, address_name: region.address_name },
      road_address: null,
    }],
    coords: { lat: place.y, lng: place.x },
    dongNm: region.region_3depth_name,
  })
}
