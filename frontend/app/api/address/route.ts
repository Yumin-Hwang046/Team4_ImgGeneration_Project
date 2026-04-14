import { NextRequest, NextResponse } from 'next/server'

export async function GET(req: NextRequest) {
  const query = req.nextUrl.searchParams.get('query')
  if (!query || query.trim().length < 2) {
    return NextResponse.json({ documents: [] })
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

  console.log('[address] query:', query, '| docs:', addressData.documents?.length ?? 0, '| h_code:', hCode ?? 'NONE', '| raw:', JSON.stringify(addressData).slice(0, 200))

  // h_code가 있으면 바로 반환
  if (hCode) return NextResponse.json(addressData)

  // 2차: 키워드 검색으로 좌표 획득 후 행정동코드 역조회
  const keywordRes = await fetch(
    `https://dapi.kakao.com/v2/local/search/keyword.json?query=${encodeURIComponent(query)}&size=1`,
    { headers, cache: 'no-store' }
  )
  const keywordData = await keywordRes.json()
  const place = keywordData.documents?.[0]

  if (!place?.x || !place?.y) {
    console.log('[address] keyword fallback also empty')
    return NextResponse.json({ documents: [] })
  }

  // 좌표 → 행정동코드 변환
  const regionRes = await fetch(
    `https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x=${place.x}&y=${place.y}`,
    { headers, cache: 'no-store' }
  )
  const regionData = await regionRes.json()
  // H 타입 = 행정동
  const region = regionData.documents?.find((d: { region_type: string }) => d.region_type === 'H')

  console.log('[address] coord2region h_code:', region?.code ?? 'NONE')

  if (!region) return NextResponse.json({ documents: [] })

  // address 검색과 같은 형태로 맞춰서 반환
  return NextResponse.json({
    documents: [{
      address_name: region.address_name,
      address_type: 'REGION_ADDR',
      address: { h_code: region.code, address_name: region.address_name },
      road_address: null,
    }],
  })
}
