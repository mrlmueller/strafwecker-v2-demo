import { NextResponse, type NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  const url = request.nextUrl;
  const ENV_TOKEN = process.env.DEV_TOKEN ?? "";

  // ─── 1) devToken im Query-String ──────────────────────────
  const queryToken = url.searchParams.get("devToken");
  if (queryToken && queryToken === ENV_TOKEN) {
    // Cookie setzen mit sehr langem Ablaufdatum (10 Jahre)
    const res = NextResponse.next();
    const expiryDate = new Date();
    expiryDate.setFullYear(expiryDate.getFullYear() + 10);

    res.cookies.set({
      name: "devToken",
      value: queryToken,
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "strict",
      path: "/",
      expires: expiryDate,
    });
    return res;
  }

  // ─── 2) devToken bereits als Cookie ───────────────────────
  const cookieToken = request.cookies.get("devToken")?.value;
  if (cookieToken && cookieToken === ENV_TOKEN) {
    return NextResponse.next();
  }

  // ─── 3) IP-Whitelist ──────────────────────────────────────
  const allowedIps = ["192.168.178.48", "127.0.0.1", "::1"];
  const xForwardedFor = request.headers.get("x-forwarded-for");
  const forwardedIp = xForwardedFor
    ? xForwardedFor.split(",").map((ip) => ip.trim())[0]
    : null;
  const clientIp =
    forwardedIp ??
    request.headers.get("x-real-ip") ??
    (request as unknown as { ip?: string }).ip ??
    "";

  if (allowedIps.includes(clientIp)) {
    return NextResponse.next();
  }

  // ─── Fallback: Zugriff verweigern ─────────────────────────
  return new NextResponse("Access Denied", { status: 403 });
}

export const config = {
  matcher: "/:path*",
};
