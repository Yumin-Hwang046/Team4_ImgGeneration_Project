import { NextRequest, NextResponse } from 'next/server'

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

// 인구통계 → 추천 페르소나 ID (1=Warm, 2=Clean, 3=Trendy, 4=Premium)
const PERSONA_REC: Record<string, number[]> = {
  '10대 여성': [3, 2], '20대 여성': [3, 1], '30대 여성': [1, 2],
  '40대 여성': [1, 4], '50대 여성': [4, 1], '60대 이상 여성': [1, 4],
  '10대 남성': [3, 2], '20대 남성': [3, 4], '30대 남성': [4, 2],
  '40대 남성': [4, 1], '50대 남성': [4, 1], '60대 이상 남성': [4, 1],
  '10대 혼성': [3, 2], '20대 혼성': [3, 2], '30대 혼성': [2, 1],
  '40대 혼성': [1, 4], '50대 혼성': [4, 1], '60대 이상 혼성': [1, 4],
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
    if (!res.ok) { console.log('[commercial] 소상공인 HTTP error:', res.status); return null }
    const data: ApiResponse = await res.json()
    console.log('[commercial] 소상공인 totalCount:', data.body?.totalCount)
    return normalizeItems(data.body?.items?.item)
  } catch (e) {
    console.error('[commercial] 소상공인 error:', e)
    return null
  }
}

async function fetchSeoulDemographic(dongName: string, seoulKey: string) {
  if (!dongName) return null
  const url = `http://openapi.seoul.go.kr:8088/${seoulKey}/json/VwsmAdstrdFlpopW/1/100/ADSTRD_CD_NM/${encodeURIComponent(dongName)}`
  try {
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) return null
    const data: SeoulResponse = await res.json()
    const allRows = data.VwsmAdstrdFlpopW?.row ?? []
    if (!allRows.length) return null

    // 가장 최신 분기 데이터 사용
    const rows = allRows
      .filter(r => r.ADSTRD_CD_NM === dongName)
      .sort((a, b) => (b.STDR_YYQU_CD ?? '').localeCompare(a.STDR_YYQU_CD ?? ''))
    const row = rows[0] ?? allRows[0]

    const male = Number(row.ML_FLPOP_CO ?? 0)
    const female = Number(row.FML_FLPOP_CO ?? 0)
    const total = male + female || 1
    const genderLabel = female > male ? '여성' : male > female ? '남성' : '혼성'

    const ages = [
      { label: '10대',    count: Number(row.AGRDE_10_FLPOP_CO ?? 0) },
      { label: '20대',    count: Number(row.AGRDE_20_FLPOP_CO ?? 0) },
      { label: '30대',    count: Number(row.AGRDE_30_FLPOP_CO ?? 0) },
      { label: '40대',    count: Number(row.AGRDE_40_FLPOP_CO ?? 0) },
      { label: '50대',    count: Number(row.AGRDE_50_FLPOP_CO ?? 0) },
      { label: '60대 이상', count: Number(row.AGRDE_60_ABOVE_FLPOP_CO ?? 0) },
    ]
    const totalPop = ages.reduce((s, a) => s + a.count, 0) || 1
    const top3 = [...ages].sort((a, b) => b.count - a.count).slice(0, 3).map((a, i) => ({
      rank: i + 1,
      demographic: `${a.label} ${genderLabel}`,
      pct: Math.round((a.count / totalPop) * 100),
      count: a.count,
    }))

    const top1Demo = top3[0]?.demographic ?? '30대 혼성'
    return {
      top3,
      maleRatio: Math.round((male / total) * 100),
      femaleRatio: Math.round((female / total) * 100),
      recommendedPersonas: getRecommendedPersonas(top1Demo),
    }
  } catch (e) {
    console.error('[commercial] Seoul error:', e)
    return null
  }
}

export async function GET(req: NextRequest) {
  const admCd = req.nextUrl.searchParams.get('admCd') ?? ''
  const dong  = req.nextUrl.searchParams.get('dong')  ?? ''

  const serviceKey = process.env.SANGKWON_API_KEY ?? ''
  const seoulKey   = process.env.SEOUL_API_KEY   ?? ''

  const [stores, seoulDemo] = await Promise.all([
    admCd && serviceKey ? fetchStoreData(admCd, serviceKey) : Promise.resolve(null),
    dong  && seoulKey   ? fetchSeoulDemographic(dong, seoulKey) : Promise.resolve(null),
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

  // 추천 페르소나: 서울 데이터 우선, 없으면 업종 기반
  const top1Demo = seoulDemo?.top3[0]?.demographic
    ?? storeTop3?.[0]?.demographic
    ?? '30대 혼성'

  const rulePersonas = getRecommendedPersonas(top1Demo)

  // LLM 전략 분석
  const strategy = await analyzeStrategy({
    demographics: seoulDemo,
    storeTop3,
    fallbackDemo: top1Demo,
  })

  return NextResponse.json({
    demographics: seoulDemo,
    storeTop3,
    total: stores?.length ?? 0,
    recommendedPersonas: strategy?.recommendedPersonas ?? rulePersonas,
    strategyText: strategy?.strategyText ?? null,
    keyInsight: strategy?.keyInsight ?? null,
  })
}

interface StrategyInput {
  demographics: { top3: { demographic: string; pct: number }[]; maleRatio: number; femaleRatio: number } | null
  storeTop3: { name: string; pct: number }[] | null
  fallbackDemo: string
}

async function analyzeStrategy(input: StrategyInput) {
  const openaiKey = process.env.OPENAI_API_KEY
  if (!openaiKey) return null

  const demoText = input.demographics
    ? `유동인구 연령/성별 분포: ${input.demographics.top3.map(d => `${d.demographic} ${d.pct}%`).join(', ')}. 여성 ${input.demographics.femaleRatio}% / 남성 ${input.demographics.maleRatio}%.`
    : `주요 고객층 추정: ${input.fallbackDemo}`

  const storeText = input.storeTop3?.length
    ? `주변 상권 주요 업종: ${input.storeTop3.map(s => `${s.name}(${s.pct}%)`).join(', ')}.`
    : '상권 데이터 없음.'

  const prompt = `당신은 소상공인 SNS 마케팅 전략 전문가입니다.

아래 지역 데이터를 분석하여 SNS 이미지 콘텐츠 전략을 제시해주세요.

${demoText}
${storeText}

사용 가능한 브랜드 페르소나:
- Warm: 따뜻한 베이지 톤, 포근함, 감성적 안정감
- Clean: 미니멀리즘, 깔끔함, 본질적 가치
- Trendy: 최신 트렌드, 도시적 젊은 감성
- Premium: 럭셔리, 절제된 고급스러움

JSON 형식으로만 응답하세요:
{
  "recommendedPersonas": ["페르소나명1", "페르소나명2"],
  "strategyText": "2-3문장 마케팅 전략",
  "keyInsight": "핵심 인사이트 한 문장"
}`

  try {
    const res = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${openaiKey}`,
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 400,
        response_format: { type: 'json_object' },
      }),
      cache: 'no-store',
    })
    if (!res.ok) return null
    const data = await res.json()
    const content = data.choices?.[0]?.message?.content
    if (!content) return null
    const parsed = JSON.parse(content)
    // 페르소나 ID로 변환
    const PERSONA_NAME_TO_ID: Record<string, number> = { Warm: 1, Clean: 2, Trendy: 3, Premium: 4 }
    const ids = (parsed.recommendedPersonas as string[])
      .map(n => PERSONA_NAME_TO_ID[n])
      .filter(Boolean)
    return {
      recommendedPersonas: ids.length ? ids : null,
      strategyText: parsed.strategyText ?? null,
      keyInsight: parsed.keyInsight ?? null,
    }
  } catch (e) {
    console.error('[commercial] OpenAI error:', e)
    return null
  }
}
