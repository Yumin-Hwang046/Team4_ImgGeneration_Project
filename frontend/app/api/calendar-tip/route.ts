import { NextRequest, NextResponse } from 'next/server'

interface WeatherInfo {
  condition: string
  temp: number
  hasRain: boolean
  rainSummary: string | null
}

interface Festival {
  title: string
  startDate: string
  endDate: string
  distance: string | null
}

interface HolidayInfo {
  name: string
  kind: 'public' | 'commemorative'
}

export async function POST(req: NextRequest) {
  const openaiKey = process.env.OPENAI_API_KEY
  if (!openaiKey) return NextResponse.json({ tip: null })

  const body = await req.json()
  const weather: WeatherInfo = body.weather
  const festivals: Festival[] = body.festivals ?? []
  const category: string = body.category ?? ''
  const currentHour: number = body.currentHour ?? new Date().getHours()
  const holidays: HolidayInfo[] = body.holidays ?? []

  const weatherText = weather
    ? `오늘 날씨: ${weather.condition}, 현재기온 ${weather.temp}°C.${weather.rainSummary ? ` ${weather.rainSummary}.` : ''}`
    : '날씨 정보 없음.'

  const festivalText = festivals.length > 0
    ? `인근 행사/축제: ${festivals.slice(0, 3).map(f => `${f.title}(${f.distance ?? '근처'})`).join(', ')}.`
    : '인근 행사 없음.'

  const holidayText = holidays.length > 0
    ? `오늘 기념일/공휴일: ${holidays.map(h => h.name).join(', ')}.`
    : ''

  const categoryText = category ? `운영 업종: ${category}.` : ''

  const period = currentHour < 12 ? '오전' : '오후'
  const displayHour = currentHour % 12 || 12
  const nowText = `현재 시각: ${period} ${displayHour}시`

  const systemPrompt = `당신은 소상공인 SNS 마케팅 전문가입니다.
절대 지켜야 할 규칙:
1. 메뉴 이름(냉우동, 사시미, 라떼, 아메리카노 등 특정 음식·음료명)을 절대 언급하지 마세요.
2. 대신 "시원한 국물요리", "뜨거운 음료", "달콤한 디저트" 처럼 카테고리·속성으로 표현하세요.
3. 포스팅 추천 시간은 반드시 현재 시각 이후 시간만 제시하세요. 이미 지난 시간은 절대 언급하지 마세요.
4. 끝난 행사나 오늘 진행되지 않는 행사는 언급하지 마세요.
5. 오늘 기념일이나 공휴일이 있으면 그와 연계한 마케팅 팁을 우선 제시하세요.
6. 한 문장, 자연스러운 한국어, 70자 이내로만 답하세요.`

  const userPrompt = `오늘 상황을 바탕으로 SNS 포스팅 팁을 한 문장으로 알려주세요.

${nowText}
${categoryText}
${weatherText}
${festivalText}
${holidayText}

- 오늘 기념일/공휴일이 있으면 해당 내용을 마케팅에 연계할 것
- 날씨 데이터(기온, 강수 시간대)를 구체적으로 반영할 것
- 인근 행사가 있으면 연계 언급할 것
- 지금(${nowText}) 이후 시간대 중 최적 포스팅 시간을 추천할 것

팁:`

  try {
    const res = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${openaiKey}`,
      },
      body: JSON.stringify({
        model: 'gpt-5-mini',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
        max_completion_tokens: 2000,
      }),
      cache: 'no-store',
    })

    if (!res.ok) return NextResponse.json({ tip: null })
    const data = await res.json()
    const raw = data.choices?.[0]?.message?.content ?? ''
    const tip = raw.trim().replace(/^팁:\s*/i, '')

    return NextResponse.json({ tip: tip || null })
  } catch (e) {
    console.error('[calendar-tip] error:', e)
    return NextResponse.json({ tip: null })
  }
}
