import { NextRequest, NextResponse } from 'next/server'

interface OpenMeteoResponse {
  current: {
    temperature_2m: number
    weathercode: number
  }
  hourly: {
    time: string[]
    temperature_2m: number[]
    precipitation_probability: number[]
    weathercode: number[]
  }
  daily: {
    time: string[]
    weathercode: number[]
  }
}

type PrecipType = 'rain' | 'snow' | 'thunder'

interface PrecipHour {
  hour: number
  label: string
  probability: number
  type: PrecipType
}

interface PrecipPeriod {
  start: string
  end: string
  maxProb: number
  type: PrecipType
}

const SNOW_CODES    = new Set([71, 73, 75, 77, 85, 86])
const RAIN_CODES    = new Set([51, 53, 55, 57, 61, 63, 65, 67, 80, 81, 82])
const THUNDER_CODES = new Set([95, 96, 99])

function wmoToCondition(code: number): { label: string; icon: string } {
  if (code === 0) return { label: '맑음', icon: 'wb_sunny' }
  if (code <= 3)  return { label: '구름 조금', icon: 'partly_cloudy_day' }
  if (code <= 48) return { label: '안개', icon: 'foggy' }
  if (code <= 67) return { label: '비', icon: 'rainy' }
  if (code <= 77) return { label: '눈', icon: 'ac_unit' }
  if (code <= 82) return { label: '소나기', icon: 'rainy' }
  if (code <= 86) return { label: '눈', icon: 'ac_unit' }
  return { label: '천둥번개', icon: 'thunderstorm' }
}

function formatHour(isoTime: string): string {
  const hour = new Date(isoTime).getHours()
  if (hour === 0)  return '자정'
  if (hour < 12)  return `오전 ${hour}시`
  if (hour === 12) return '정오'
  return `오후 ${hour - 12}시`
}

function groupPeriods(hours: PrecipHour[], targetType: PrecipType): PrecipPeriod[] {
  const filtered = hours.filter(h => h.type === targetType)
  const periods: PrecipPeriod[] = []
  let pStart: PrecipHour | null = null
  let pEnd:   PrecipHour | null = null
  let maxP = 0

  for (const h of filtered) {
    if (!pStart) {
      pStart = h; pEnd = h; maxP = h.probability
    } else if (h.hour - pEnd!.hour <= 1) {
      pEnd = h; maxP = Math.max(maxP, h.probability)
    } else {
      periods.push({ start: pStart.label, end: pEnd!.label, maxProb: maxP, type: targetType })
      pStart = h; pEnd = h; maxP = h.probability
    }
  }
  if (pStart && pEnd) {
    periods.push({ start: pStart.label, end: pEnd.label, maxProb: maxP, type: targetType })
  }
  return periods
}

function periodsToText(periods: PrecipPeriod[], label: string): string {
  return periods.map(p =>
    p.start === p.end
      ? `${label}: ${p.start} (${p.maxProb}%)`
      : `${label}: ${p.start}~${p.end} (최대 ${p.maxProb}%)`
  ).join(', ')
}

export async function GET(req: NextRequest) {
  const lat = req.nextUrl.searchParams.get('lat')
  const lng = req.nextUrl.searchParams.get('lng')

  if (!lat || !lng) {
    return NextResponse.json({ error: 'lat/lng required' }, { status: 400 })
  }

  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&hourly=temperature_2m,precipitation_probability,weathercode&current=temperature_2m,weathercode&daily=weathercode&timezone=Asia%2FSeoul&forecast_days=14`
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) return NextResponse.json({ error: 'weather fetch failed' }, { status: 500 })

    const data: OpenMeteoResponse = await res.json()
    const todayStr = new Date().toISOString().split('T')[0]

    const todayIndices = data.hourly.time
      .map((t, i) => ({ t, i }))
      .filter(({ t }) => t.startsWith(todayStr))
      .map(({ i }) => i)

    const temps   = todayIndices.map(i => data.hourly.temperature_2m[i])
    const maxTemp = Math.round(Math.max(...temps))
    const minTemp = Math.round(Math.min(...temps))

    const threshold = 40
    const precipHours: PrecipHour[] = todayIndices
      .filter(i => (data.hourly.precipitation_probability[i] ?? 0) >= threshold)
      .map(i => {
        const code = data.hourly.weathercode[i]
        const type: PrecipType =
          THUNDER_CODES.has(code) ? 'thunder'
          : SNOW_CODES.has(code)  ? 'snow'
          : RAIN_CODES.has(code)  ? 'rain'
          : 'rain' // 확률 높으면 기본 비로 처리
        return {
          hour: new Date(data.hourly.time[i]).getHours(),
          label: formatHour(data.hourly.time[i]),
          probability: data.hourly.precipitation_probability[i],
          type,
        }
      })

    const rainPeriods    = groupPeriods(precipHours, 'rain')
    const snowPeriods    = groupPeriods(precipHours, 'snow')
    const thunderPeriods = groupPeriods(precipHours, 'thunder')

    const summaryParts: string[] = []
    if (rainPeriods.length)    summaryParts.push(periodsToText(rainPeriods, '비'))
    if (snowPeriods.length)    summaryParts.push(periodsToText(snowPeriods, '눈'))
    if (thunderPeriods.length) summaryParts.push(periodsToText(thunderPeriods, '천둥'))

    const currentCode = data.current.weathercode
    const { label: condition, icon } = wmoToCondition(currentCode)
    const currentTemp = Math.round(data.current.temperature_2m)

    const precipSummary = summaryParts.length > 0 ? summaryParts.join(' · ') : null
    const summary = precipSummary
      ? `${condition} ${currentTemp}°C · ${precipSummary}`
      : `${condition} ${currentTemp}°C · 최고 ${maxTemp}° / 최저 ${minTemp}°`

    const dailyForecast = (data.daily?.time ?? []).map((date, i) => ({
      date,
      icon: wmoToCondition(data.daily.weathercode[i]).icon,
    }))

    return NextResponse.json({
      condition,
      icon,
      temp: currentTemp,
      maxTemp,
      minTemp,
      rainPeriods,
      snowPeriods,
      thunderPeriods,
      rainSummary: precipSummary,
      summary,
      hasRain: rainPeriods.length > 0 || thunderPeriods.length > 0,
      hasSnow: snowPeriods.length > 0,
      dailyForecast,
    })
  } catch (e) {
    console.error('[weather] error:', e)
    return NextResponse.json({ error: 'internal error' }, { status: 500 })
  }
}
