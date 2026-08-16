// Next.js 16 proxy (구 middleware.ts) — 로그인 안 된 사용자를 /sign-in 으로 돌린다. ADR-031
//
// ★여기서 하는 일은 **UX 리다이렉트뿐**이고 인가가 아니다.
//   `getSessionCookie` 는 쿠키의 존재만 본다 — 서명도 만료도 검증하지 않는다.
//   진짜 방어선은 FastAPI 의 Bearer JWT 검증(`apps/api/src/auth/dependencies.py`)이다.
//   여기서 `auth.api.getSession()` 을 부르면 **페이지 이동마다 DB 왕복**이 생긴다 —
//   2 OCPU 단일 VM(ADR-028)에서 감당할 이유가 없다.
//
// ★matcher 를 반드시 명시한다. Clerk 시절에는 `clerkMiddleware()` 의 기본 매처에 얹혀
//   이 파일에 `config` 가 아예 없었다. 그대로 두면 `_next/static` 자산 요청까지 proxy 를
//   타면서 조용히 느려진다 — 동작은 하기 때문에 발견이 늦는 종류의 회귀다.
import { getSessionCookie } from "better-auth/cookies";
import { NextResponse, type NextRequest } from "next/server";

/** 로그인 없이 접근 가능한 경로. 여기 없으면 전부 보호 대상이다. */
const PUBLIC_PATHS = [
  "/",
  "/pricing",
  "/sign-in",
  "/sign-up",
  "/invite",
  "/landing",
];

function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`)
  );
}

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (isPublic(pathname)) return NextResponse.next();

  if (!getSessionCookie(request)) {
    const signIn = new URL("/sign-in", request.url);
    // 로그인 후 원래 가려던 곳으로 돌려보낸다. Better Auth 가 trustedOrigins 로
    // callbackURL 을 검증하므로 외부 URL 로의 open redirect 는 성립하지 않는다.
    signIn.searchParams.set("callbackURL", `${pathname}${search}`);
    return NextResponse.redirect(signIn);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // 정적 자산과 Better Auth 핸들러는 통과시킨다.
    //
    // ★`_next` 를 **하위 전체** 로 제외한다. `_next/static`·`_next/image` 만 빼면
    //   `/_next/webpack-hmr`(dev HMR)·`/_next/data/*` 가 proxy 를 타고 /sign-in 으로
    //   리다이렉트된다. Clerk 시절 매처는 `/_next(.*)` 전체를 public 으로 뒀으므로
    //   좁게 쓰면 그게 그대로 회귀다.
    // ★`/api/auth` 를 빼먹으면 로그인 요청 자체가 리다이렉트 루프에 걸린다.
    "/((?!api/auth|_next|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|woff2?)$).*)",
  ],
};
