import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

async function proxy(request: NextRequest, context: { params: { path?: string[] } }) {
  const path = (context.params.path ?? []).join("/");
  const url = new URL(request.url);
  const backendUrl = `${BACKEND_URL}/${path}${url.search}`;

  try {
    const incomingHeaders = new Headers(request.headers);

    // 백엔드로 넘길 헤더 정리
    const headers = new Headers();
    const contentType = incomingHeaders.get("content-type");
    const authorization = incomingHeaders.get("authorization");
    const cookie = incomingHeaders.get("cookie");

    if (contentType) headers.set("content-type", contentType);
    if (authorization) headers.set("authorization", authorization);
    if (cookie) headers.set("cookie", cookie);

    // body가 있는 메서드만 전달
    let body: BodyInit | undefined = undefined;
    if (request.method !== "GET" && request.method !== "HEAD") {
      body = Buffer.from(await request.arrayBuffer());
    }

    const backendResponse = await fetch(backendUrl, {
      method: request.method,
      headers,
      body,
      redirect: "manual",
    });

    const responseText = await backendResponse.text();
    const responseContentType =
      backendResponse.headers.get("content-type") ?? "application/json";

    // 백엔드 응답 헤더 일부만 안전하게 전달
    const responseHeaders = new Headers();
    responseHeaders.set("content-type", responseContentType);

    const setCookie = backendResponse.headers.get("set-cookie");
    if (setCookie) {
      responseHeaders.set("set-cookie", setCookie);
    }

    // JSON이면 JSON 그대로 반환
    if (responseContentType.includes("application/json")) {
      try {
        const data = responseText ? JSON.parse(responseText) : {};
        return NextResponse.json(data, {
          status: backendResponse.status,
          headers: responseHeaders,
        });
      } catch {
        return new NextResponse(responseText || "Invalid JSON from backend", {
          status: backendResponse.status,
          headers: responseHeaders,
        });
      }
    }

    // JSON이 아니면 text로 그대로 반환
    return new NextResponse(responseText, {
      status: backendResponse.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("[API PROXY ERROR]", {
      backendUrl,
      method: request.method,
      error,
    });

    return NextResponse.json(
      {
        detail: "Backend proxy failed",
        backendUrl,
        method: request.method,
        error: error instanceof Error ? error.message : String(error),
      },
      { status: 502 }
    );
  }
}

export async function GET(request: NextRequest, context: { params: { path?: string[] } }) {
  return proxy(request, context);
}

export async function POST(request: NextRequest, context: { params: { path?: string[] } }) {
  return proxy(request, context);
}

export async function PUT(request: NextRequest, context: { params: { path?: string[] } }) {
  return proxy(request, context);
}

export async function PATCH(request: NextRequest, context: { params: { path?: string[] } }) {
  return proxy(request, context);
}

export async function DELETE(request: NextRequest, context: { params: { path?: string[] } }) {
  return proxy(request, context);
}

export async function OPTIONS(request: NextRequest, context: { params: { path?: string[] } }) {
  return proxy(request, context);
}
