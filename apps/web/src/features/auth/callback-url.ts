// 로그인·가입 후 돌아갈 경로(callbackURL) — same-origin 상대 경로만 허용한다 (E2-X01)
//
// ★Better Auth 의 trustedOrigins 검증은 **서버 리다이렉트**에만 걸린다. 폼은 성공 뒤
//   `router.push(callbackURL)` 로 직접 이동하므로, 여기서 거르지 않으면 `?callbackURL=https://evil`
//   이 그대로 외부로 보낸다 (open redirect).
// ★문자열 접두어 검사만으로는 부족하다. `//evil.com`, `/\evil.com`, `/<TAB>/evil.com` 은 모두 "/" 로
//   시작하지만 브라우저 URL 파서가 protocol-relative 로 읽는다 → URL 로 파싱해 origin 을 비교한다.
// ★정규화 결과도 다시 검사한다. dot-segment 가 `/.//evil.com` → `//evil.com` 처럼 protocol-relative 를
//   **새로 만든다** (2026-09-27 E-FE E-1).

export const DEFAULT_CALLBACK_URL = "/dashboard";

const PARSE_BASE = "http://callback.invalid";
/** "/" 하나로 시작하고 바로 뒤가 "/" 나 "\" 가 아닌 경로만 (protocol-relative 차단). */
const SAFE_RELATIVE = /^\/(?![/\\])/;

/** 안전한 same-origin 상대 경로면 정규화해 돌려주고, 아니면 기본 목적지. */
export function sanitizeCallbackURL(raw: string | null | undefined): string {
  if (!raw || !raw.startsWith("/")) return DEFAULT_CALLBACK_URL;
  try {
    const url = new URL(raw, PARSE_BASE);
    if (url.origin !== PARSE_BASE) return DEFAULT_CALLBACK_URL;
    const normalized = `${url.pathname}${url.search}${url.hash}`;
    if (!SAFE_RELATIVE.test(normalized)) return DEFAULT_CALLBACK_URL;
    return normalized;
  } catch {
    return DEFAULT_CALLBACK_URL;
  }
}

/** 로그인↔가입 링크에 callbackURL 을 이어 붙인다 — 전환해도 목적지(예: 초대 페이지)를 잃지 않게. */
export function authHrefWithCallback(
  path: "/sign-in" | "/sign-up",
  callbackURL: string | null | undefined,
): string {
  const safe = sanitizeCallbackURL(callbackURL);
  if (safe === DEFAULT_CALLBACK_URL) return path;
  return `${path}?callbackURL=${encodeURIComponent(safe)}`;
}
