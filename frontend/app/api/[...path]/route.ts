import { NextRequest, NextResponse } from "next/server";

const PI_BASE = process.env.PI_API_URL ?? "http://raspberrypi:8000";
const API_KEY = process.env.API_KEY ?? "";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, "GET");
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, "POST");
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, "PUT");
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, "DELETE");
}

async function proxyRequest(
  request: NextRequest,
  pathSegments: string[],
  method: string
): Promise<NextResponse> {
  const path = pathSegments.join("/");
  const search = request.nextUrl.search;
  const targetUrl = `${PI_BASE}/api/v1/${path}${search}`;

  const body =
    method !== "GET" && method !== "DELETE"
      ? await request.text()
      : undefined;

  const res = await fetch(targetUrl, {
    method,
    headers: {
      "Content-Type": "application/json",
      "x-api-key": API_KEY,
    },
    body,
    cache: "no-store",
  });

  const data = await res.text();
  return new NextResponse(data, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
