import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'

async function proxyRequest(req: NextRequest, params: { path: string[] }) {
  const path = params.path.join('/')
  const url = new URL(req.url)
  const backendUrl = `${BACKEND_URL}/${path}${url.search}`

  const headers = new Headers()
  req.headers.forEach((value, key) => {
    if (key !== 'host') {
      headers.set(key, value)
    }
  })

  const body = req.method !== 'GET' && req.method !== 'HEAD'
    ? await req.arrayBuffer()
    : undefined

  try {
    const res = await fetch(backendUrl, {
      method: req.method,
      headers,
      body,
    })

    const responseHeaders = new Headers()
    res.headers.forEach((value, key) => {
      responseHeaders.set(key, value)
    })

    return new NextResponse(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
    })
  } catch {
    return NextResponse.json(
      { error: 'Backend service unavailable' },
      { status: 503 }
    )
  }
}

export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params)
}

export async function POST(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params)
}

export async function PUT(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params)
}

export async function DELETE(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params)
}
