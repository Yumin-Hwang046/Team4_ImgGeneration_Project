import http from 'http'
import { NextRequest, NextResponse } from 'next/server'

const BACKEND_HOST = 'localhost'
const BACKEND_PORT = 8000

async function proxy(request: NextRequest, path: string): Promise<NextResponse> {
  const search = request.nextUrl.search
  const pathname = `/api/${path}${search}`
  const bodyBuffer =
    request.method !== 'GET' ? Buffer.from(await request.arrayBuffer()) : undefined

  const forwardHeaders: Record<string, string> = {}
  request.headers.forEach((value, key) => {
    if (!['host', 'connection', 'transfer-encoding'].includes(key.toLowerCase())) {
      forwardHeaders[key] = value
    }
  })

  return new Promise((resolve) => {
    const req = http.request(
      {
        hostname: BACKEND_HOST,
        port: BACKEND_PORT,
        path: pathname,
        method: request.method,
        headers: forwardHeaders,
        timeout: 0,
      },
      (res) => {
        const chunks: Buffer[] = []
        res.on('data', (chunk: Buffer) => chunks.push(chunk))
        res.on('end', () => {
          const responseBody = Buffer.concat(chunks)
          const headers = new Headers()
          Object.entries(res.headers).forEach(([k, v]) => {
            if (v != null) headers.set(k, Array.isArray(v) ? v.join(', ') : v)
          })
          resolve(
            new NextResponse(responseBody, { status: res.statusCode ?? 502, headers })
          )
        })
        res.on('error', (err: Error) => {
          resolve(
            NextResponse.json({ detail: `응답 오류: ${err.message}` }, { status: 502 })
          )
        })
      }
    )

    req.on('error', (err: Error) => {
      resolve(
        NextResponse.json({ detail: `백엔드 연결 실패: ${err.message}` }, { status: 502 })
      )
    })

    if (bodyBuffer) req.write(bodyBuffer)
    req.end()
  })
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  return proxy(request, path.join('/'))
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  return proxy(request, path.join('/'))
}
