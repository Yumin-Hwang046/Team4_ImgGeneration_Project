import { NextRequest, NextResponse } from 'next/server'
import { traceFrontendApiCall } from '@/lib/langfuse'

interface StoreRecord {
  indsMclsNm?: string
}

interface ApiResponse {
  body?: {
    items?: { item?: StoreRecord | StoreRecord[] }
    totalCount?: number
  }
}

interface SeoulRow {
  STDR_YYQU_CD?: string
  ADSTRD_CD_NM?: string
  TOT_FLPOP_CO?: number
  ML_FLPOP_CO?: number
  FML_FLPOP_CO?: number
  AGRDE_10_FLPOP_CO?: number
  AGRDE_20_FLPOP_CO?: number
  AGRDE_30_FLPOP_CO?: number
  AGRDE_40_FLPOP_CO?: number
  AGRDE_50_FLPOP_CO?: number
  AGRDE_60_ABOVE_FLPOP_CO?: number
}

interface SeoulResponse {
  VwsmAdstrdFlpopW?: {
    list_total_count?: number
    row?: SeoulRow[]
  }
  RESULT?: { CODE: string; MESSAGE: string }
}

interface KakaoPlace {
  place_name?: string
  category_name?: string
  category_group_code?: string
}

interface NearbyCategory {
  name: string
  count: number
}

interface NearbyBusinesses {
  total: number
  categories: NearbyCategory[]
  density: 'high' | 'medium' | 'low'
}

// 페르소나 ID: 1=Warm, 2=Clean, 3=Trendy, 4=Premium
const PERSONA_REC: Record<string, number[]> = {
  '10대 여성': [3, 2], '20대 여성': [3, 1], '30대 여성': [1, 2],
  '40대 여성': [1, 4], '50대 여성': [4, 1], '60대 이상 여성': [1, 4],
  '10대 남성': [3, 2], '20대 남성': [3, 4], '30대 남성': [4, 2],
  '40대 남성': [4, 1], '50대 남성': [4, 1], '60대 이상 남성': [4, 1],
  '10대 혼성': [3, 2], '20대 혼성': [3, 2], '30대 혼성': [2, 1],
  '40대 혼성': [1, 4], '50대 혼성': [4, 1], '60대 이상 혼성': [1, 4],
}

const PERSONA_NAME_TO_ID: Record<string, number> = {
  Warm: 1, Clean: 2, Trendy: 3, Premium: 4,
}

const DEMO_MAP: Record<string, string> = {
  커피: '20대 여성', 카페: '20대 여성', 베이커리: '20대 여성',
  디저트: '20대 여성', 한식: '30대 여성', 분식: '10대 혼성',
  패스트푸드: '10대 남성', 치킨: '20대 남성', 주점: '30대 남성',
  호프: '30대 남성', 의류: '20대 여성', 미용: '30대 여성',
  스포츠: '30대 남성', 편의점: '20대 혼성', 마트: '40대 여성',
  일식: '30대 남성', 중식: '30대 남성', 양식: '20대 여성',
}

function inferDemographic(name: string): string {
  const match = Object.keys(DEMO_MAP).find(k => name.includes(k))
  return match ? DEMO_MAP[match] : '30대 혼성'
}

function normalizeItems(raw: StoreRecord | StoreRecord[] | undefined): StoreRecord[] {
  if (!raw) return []
  return Array.isArray(raw) ? raw : [raw]
}

function getRecommendedPersonas(top1Demo: string): number[] {
  return PERSONA_REC[top1Demo] ?? [1, 3]
}

async function fetchStoreData(admCd: string, serviceKey: string) {
  const params = new URLSearchParams({
    serviceKey, divId: 'adongCd', key: admCd,
    pageIndex: '1', pageSize: '100', type: 'json',
  })
  const apiUrl = `https://apis.data.go.kr/B553077/api/open/sdctrdartrdarinfopd/storeListInDong?${params}`
  try {
    const res = await fetch(apiUrl, { cache: 'no-store' })
    if (!res.ok) return null
    const data: ApiResponse = await res.json()
    return normalizeItems(data.body?.items?.item)
  } catch (e) {
    console.error('[commercial] 소상공인 error:', e)
    return null
  }
}

async function fetchSeoulDemographic(dongName: string, seoulKey: string) {
  if (!dongName) return null
  // 서울시 행정동 수 ~430개, 분기당 430행 → 2분기 커버하려면 1000행
  const url = `http://openapi.seoul.go.kr:8088/${seoulKey}/json/VwsmAdstrdFlpopW/1/1000/`
  try {
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) return null
    const data: SeoulResponse = await res.json()
    const allRows = data.VwsmAdstrdFlpopW?.row ?? []
    if (!allRows.length) return null

    // 최신 분기 우선, 없으면 이전 분기에서도 탐색
    const latestQuarter = allRows
      .map(r => r.STDR_YYQU_CD ?? '')
      .sort((a, b) => b.localeCompare(a))[0]

    const matchedRows = allRows.filter(r => {
      const apiName = r.ADSTRD_CD_NM ?? ''
      return apiName === dongName || apiName.includes(dongName) || dongName.includes(apiName)
    })
    const latestMatch = matchedRows.filter(r => r.STDR_YYQU_CD === latestQuarter)

    const row = latestMatch[0] ?? matchedRows.sort(
      (a, b) => (b.STDR_YYQU_CD ?? '').localeCompare(a.STDR_YYQU_CD ?? '')
    )[0]

    if (!row) {
      console.log('[commercial] 서울 API 동명 미매칭:', dongName)
      return null
    }

    const male = Number(row.ML_FLPOP_CO ?? 0)
    const female = Number(row.FML_FLPOP_CO ?? 0)
    const total = male + female || 1
    const genderLabel = female > male ? '여성' : male > female ? '남성' : '혼성'

    const ages = [
      { label: '10대',     count: Number(row.AGRDE_10_FLPOP_CO ?? 0) },
      { label: '20대',     count: Number(row.AGRDE_20_FLPOP_CO ?? 0) },
      { label: '30대',     count: Number(row.AGRDE_30_FLPOP_CO ?? 0) },
      { label: '40대',     count: Number(row.AGRDE_40_FLPOP_CO ?? 0) },
      { label: '50대',     count: Number(row.AGRDE_50_FLPOP_CO ?? 0) },
      { label: '60대 이상', count: Number(row.AGRDE_60_ABOVE_FLPOP_CO ?? 0) },
    ]
    const totalPop = ages.reduce((s, a) => s + a.count, 0) || 1
    const top3 = [...ages]
      .sort((a, b) => b.count - a.count)
      .slice(0, 3)
      .map((a, i) => ({
        rank: i + 1,
        demographic: `${a.label} ${genderLabel}`,
        pct: Math.round((a.count / totalPop) * 100),
        count: a.count,
      }))

    return {
      top3,
      maleRatio: Math.round((male / total) * 100),
      femaleRatio: Math.round((female / total) * 100),
      recommendedPersonas: getRecommendedPersonas(top3[0]?.demographic ?? '30대 혼성'),
    }
  } catch (e) {
    console.error('[commercial] Seoul error:', e)
    return null
  }
}

// 카카오 로컬 API로 반경 500m 주변 업소 분석
async function fetchNearbyBusinesses(lat: string, lng: string, kakaoKey: string): Promise<NearbyBusinesses | null> {
  if (!lat || !lng || !kakaoKey) return null

  const headers = { Authorization: `KakaoAK ${kakaoKey}` }
  const radius = 500

  // 음식점(FD6), 카페(CE7) 카테고리 병렬 조회
  const categoryGroups = ['FD6', 'CE7']
  try {
    const results = await Promise.all(
      categoryGroups.map(async (code) => {
        const url = `https://dapi.kakao.com/v2/local/search/category.json?category_group_code=${code}&x=${lng}&y=${lat}&radius=${radius}&size=15`
        const res = await fetch(url, { headers, cache: 'no-store' })
        if (!res.ok) return []
        const data = await res.json()
        return (data.documents ?? []) as KakaoPlace[]
      })
    )

    const allPlaces = results.flat()
    if (!allPlaces.length) return null

    // 세부 카테고리별 집계 (예: "음식점 > 한식 > 국밥" → "한식")
    const catCounts: Record<string, number> = {}
    for (const place of allPlaces) {
      const parts = place.category_name?.split(' > ') ?? []
      const subCat = parts[1] ?? parts[0] ?? '기타'
      catCounts[subCat] = (catCounts[subCat] ?? 0) + 1
    }

    const categories = Object.entries(catCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, count]) => ({ name, count }))

    const density: NearbyBusinesses['density'] =
      allPlaces.length >= 20 ? 'high' : allPlaces.length >= 8 ? 'medium' : 'low'

    return { total: allPlaces.length, categories, density }
  } catch (e) {
    console.error('[commercial] Kakao nearby error:', e)
    return null
  }
}

export async function GET(req: NextRequest) {
  const admCd    = req.nextUrl.searchParams.get('admCd')    ?? ''
  const dong     = req.nextUrl.searchParams.get('dong')     ?? ''
  const lat      = req.nextUrl.searchParams.get('lat')      ?? ''
  const lng      = req.nextUrl.searchParams.get('lng')      ?? ''
  const category = req.nextUrl.searchParams.get('category') ?? ''

  const serviceKey = process.env.SANGKWON_API_KEY  ?? ''
  const seoulKey   = process.env.SEOUL_API_KEY      ?? ''
  const kakaoKey   = process.env.KAKAO_REST_API_KEY ?? ''

  const [stores, seoulDemo, nearby] = await Promise.all([
    admCd && serviceKey ? fetchStoreData(admCd, serviceKey) : Promise.resolve(null),
    dong  && seoulKey   ? fetchSeoulDemographic(dong, seoulKey) : Promise.resolve(null),
    lat   && lng        ? fetchNearbyBusinesses(lat, lng, kakaoKey) : Promise.resolve(null),
  ])

  let storeTop3 = null
  if (stores?.length) {
    const counts: Record<string, number> = {}
    for (const s of stores) {
      const cat = s.indsMclsNm ?? '기타'
      counts[cat] = (counts[cat] ?? 0) + 1
    }
    storeTop3 = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([name, count], i) => ({
        rank: i + 1, name, count,
        demographic: inferDemographic(name),
        pct: Math.round((count / stores.length) * 100),
      }))
  }

  const top1Demo = seoulDemo?.top3[0]?.demographic
    ?? storeTop3?.[0]?.demographic
    ?? '30대 혼성'

  const rulePersonas = getRecommendedPersonas(top1Demo)

  const strategy = await analyzeStrategy({
    demographics: seoulDemo,
    storeTop3,
    nearby,
    category,
    fallbackDemo: top1Demo,
  })

  return NextResponse.json({
    demographics: seoulDemo,
    storeTop3,
    nearby,
    total: stores?.length ?? 0,
    recommendedPersonas: strategy?.recommendedPersonas ?? rulePersonas,
    personaReasons: strategy?.personaReasons ?? null,
    strategyText: strategy?.strategyText ?? null,
    keyInsight: strategy?.keyInsight ?? null,
  })
}

interface StrategyInput {
  demographics: {
    top3: { demographic: string; pct: number }[]
    maleRatio: number
    femaleRatio: number
  } | null
  storeTop3: { name: string; pct: number }[] | null
  nearby: NearbyBusinesses | null
  category: string
  fallbackDemo: string
}

async function analyzeStrategy(input: StrategyInput) {
  const openaiKey = process.env.OPENAI_API_KEY
  if (!openaiKey) return null

  const demoText = input.demographics
    ? `유동인구 연령/성별 분포: ${input.demographics.top3.map(d => `${d.demographic} ${d.pct}%`).join(', ')}. 여성 ${input.demographics.femaleRatio}% / 남성 ${input.demographics.maleRatio}%.`
    : `주요 고객층 추정: ${input.fallbackDemo}`

  const nearbyText = input.nearby
    ? `반경 500m 주변 업소 ${input.nearby.total}개 (밀도: ${input.nearby.density === 'high' ? '높음' : input.nearby.density === 'medium' ? '보통' : '낮음'}). 주요 업종: ${input.nearby.categories.map(c => `${c.name}(${c.count}개)`).join(', ')}.`
    : '주변 상권 데이터 없음.'

  const storeText = input.storeTop3?.length
    ? `행정동 내 업종 분포: ${input.storeTop3.map(s => `${s.name}(${s.pct}%)`).join(', ')}.`
    : ''

  const categoryText = input.category ? `운영 업종: ${input.category}.` : ''

  const prompt = `당신은 소상공인 SNS 마케팅 전략 전문가입니다.

아래 데이터를 종합 분석하여 최적의 브랜드 페르소나를 추천해주세요.

[매장 정보]
${categoryText}

[지역 유동인구 분석]
${demoText}

[반경 500m 상권 분석]
${nearbyText}
${storeText}

[선택 가능한 브랜드 페르소나 4종]
- Warm: 따뜻한 베이지 톤, 포근함, 감성적 안정감 — 감성적 유대를 원하는 고객층에 적합
- Clean: 미니멀리즘, 깔끔함, 본질적 가치 — 심플하고 신뢰감 있는 이미지를 원할 때
- Trendy: 최신 트렌드, 도시적 젊은 감성 — 젊고 트렌디한 고객층 집중 공략 시
- Premium: 럭셔리, 절제된 고급스러움 — 차별화된 프리미엄 포지셔닝 목표 시

위 데이터를 근거로 4개 페르소나 중 이 지역/업종에 가장 적합한 1순위와 2순위를 선정하세요.
주변 경쟁 업종 밀도, 주 유동인구 연령·성별, 업종 특성을 모두 고려하세요.

JSON 형식으로만 응답하세요:
{
  "rank1": "페르소나명",
  "rank2": "페르소나명",
  "reason1": "1순위 선택 근거 (데이터 기반, 한 문장)",
  "reason2": "2순위 선택 근거 (데이터 기반, 한 문장)",
  "keyInsight": "이 지역 상권의 핵심 인사이트 (한 문장)",
  "strategyText": "SNS 이미지 마케팅 전략 2-3문장"
}`

  try {
    const url = 'https://api.openai.com/v1/chat/completions'
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${openaiKey}`,
      },
      body: JSON.stringify({
        model: 'gpt-5-mini',
        messages: [{ role: 'user', content: prompt }],
        max_completion_tokens: 2000,
      }),
      cache: 'no-store',
    })
    await traceFrontendApiCall({
      name: 'frontend.commercial.openai_strategy',
      method: 'POST',
      url,
      request: {
        model: 'gpt-5-mini',
        category: input.category,
        fallbackDemo: input.fallbackDemo,
        hasDemographics: Boolean(input.demographics),
        hasNearby: Boolean(input.nearby),
        hasStoreTop3: Boolean(input.storeTop3?.length),
      },
      response: { status: res.status, ok: res.ok, url: res.url, text: await res.clone().text() },
      tags: ['frontend', 'commercial', 'openai'],
    })
    if (!res.ok) return null
    const data = await res.json()
    const raw = data.choices?.[0]?.message?.content
    if (!raw) return null

    // 마크다운 코드블록 제거 후 파싱
    const jsonStr = raw.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim()
    const parsed = JSON.parse(jsonStr)
    const rank1Id = PERSONA_NAME_TO_ID[parsed.rank1]
    const rank2Id = PERSONA_NAME_TO_ID[parsed.rank2]
    const ids = [rank1Id, rank2Id].filter(Boolean)

    return {
      recommendedPersonas: ids.length ? ids : null,
      personaReasons: {
        rank1: parsed.reason1 ?? null,
        rank2: parsed.reason2 ?? null,
      },
      strategyText: parsed.strategyText ?? null,
      keyInsight: parsed.keyInsight ?? null,
    }
  } catch (e) {
    await traceFrontendApiCall({
      name: 'frontend.commercial.openai_strategy',
      method: 'POST',
      url: 'https://api.openai.com/v1/chat/completions',
      request: {
        category: input.category,
        fallbackDemo: input.fallbackDemo,
        hasDemographics: Boolean(input.demographics),
        hasNearby: Boolean(input.nearby),
        hasStoreTop3: Boolean(input.storeTop3?.length),
      },
      error: e instanceof Error ? e.message : String(e),
      tags: ['frontend', 'commercial', 'openai'],
    })
    console.error('[commercial] OpenAI error:', e)
    return null
  }
}
