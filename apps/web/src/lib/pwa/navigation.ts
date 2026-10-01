// SW 내비게이션 처리 순수 로직 (docs/requirements/pwa.md §4.4) — sw.ts 와 vitest 가 같이 쓴다.
//
// ★같은 origin 의 GET `navigate` 만 처리하고 `/api/*` 는 건드리지 않는다.
//   Better Auth OAuth 콜백(`/api/auth/callback/*`)처럼 쿠키를 설정하는 내비게이션을 SW 가
//   거칠 이유가 없다.
// ★내비게이션 프리로드를 켜지 않는다 — 켜면 respondWith 하지 않는 내비게이션도 서버에
//   2번 도달해 일회용 OAuth code 가 두 번 소비된다 (pwa.md C-23). 이 디렉터리에 그 API
//   이름이 등장하면 소스 스캔 테스트(T-PWA-12)가 실패한다 — 주석에도 쓰지 않는다.
// ★네트워크 실패(reject)일 때만 오프라인 화면이다. 서버가 준 응답은 5xx·3xx 라도 그대로 돌려준다.
import { OFFLINE_HTML } from "./offline-page";

export interface NavigationRequestLike {
  readonly mode: string;
  readonly method: string;
  readonly url: string;
}

const API_PATH_PREFIX = "/api/";

export function shouldHandleNavigation(
  request: NavigationRequestLike,
  origin: string
): boolean {
  if (request.mode !== "navigate" || request.method !== "GET") return false;
  const url = new URL(request.url);
  return url.origin === origin && !url.pathname.startsWith(API_PATH_PREFIX);
}

/**
 * 오프라인 응답은 200 이다. 503 이면 Chromium 이 페이지 콘솔에 error 1건을 남긴다 (pwa.md C-24).
 * `no-store` 라 이 응답이 실제 페이지로 저장되지 않는다.
 */
export function createOfflineResponse(): Response {
  return new Response(OFFLINE_HTML, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

export async function respondToNavigation(
  request: Request,
  fetchFn: (request: Request) => Promise<Response>
): Promise<Response> {
  try {
    return await fetchFn(request);
  } catch {
    return createOfflineResponse();
  }
}
