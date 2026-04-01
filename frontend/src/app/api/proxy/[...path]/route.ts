import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const API_KEY = process.env.API_KEY || "";

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(request, await params);
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(request, await params);
}

async function proxy(request: NextRequest, params: { path: string[] }) {
  const path = params.path.join("/");
  const url = new URL(`/${path}`, BACKEND_URL);

  // Forward query params
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  const headers = new Headers();
  headers.set("X-API-Key", API_KEY);

  // Forward content-type for POST requests
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }

  // Forward X-Request-ID if present
  const requestId = request.headers.get("x-request-id");
  if (requestId) {
    headers.set("X-Request-ID", requestId);
  }

  const fetchOptions: RequestInit = {
    method: request.method,
    headers,
  };

  // Forward body for POST requests
  if (request.method === "POST") {
    fetchOptions.body = await request.arrayBuffer();
    // Don't set duplex for regular requests
  }

  try {
    const backendResponse = await fetch(url.toString(), fetchOptions);

    // For SSE, stream the response
    if (backendResponse.headers.get("content-type")?.includes("text/event-stream")) {
      return new NextResponse(backendResponse.body, {
        status: backendResponse.status,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    }

    // For PDF, stream binary
    if (backendResponse.headers.get("content-type")?.includes("application/pdf")) {
      const disposition = backendResponse.headers.get("content-disposition");
      return new NextResponse(backendResponse.body, {
        status: backendResponse.status,
        headers: {
          "Content-Type": "application/pdf",
          ...(disposition ? { "Content-Disposition": disposition } : {}),
        },
      });
    }

    // For JSON and other responses
    const body = await backendResponse.text();
    return new NextResponse(body, {
      status: backendResponse.status,
      headers: {
        "Content-Type": backendResponse.headers.get("content-type") || "application/json",
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 502 }
    );
  }
}
