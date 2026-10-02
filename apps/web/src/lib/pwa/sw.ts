// Kairos Service Worker 엔트리 (docs/requirements/pwa.md §4.4·§4.5).
// Next 16 번들 worker — `components/layout/service-worker-registrar.tsx` 의 등록 호출
// (`new URL(..., import.meta.url)` 리터럴)이 이 파일을 `/_next/static/service-worker/sw.js` 로
// 빌드한다 (pwa.md C-3).
//
// ★Cache Storage · IndexedDB 를 쓰지 않는다 — 사용자 데이터는 워크스페이스·가시성·작성자
//   규칙으로 즉시 차단돼야 한다 (pwa.md C-4, F-14 예정). 오프라인이면 안내 화면 1장뿐이다.
// ★캐시가 없으므로 페이지와 SW 의 버전이 어긋나 깨질 자산이 없다 → skipWaiting + claim 으로
//   수정본을 다음 내비게이션에 바로 반영한다 (고착 리스크 R-2 축소).
// ★worker 번들은 env 를 인라인하지 않는다 → SW 는 빌드 플래그를 읽지 않고 모든 빌드에서 같다.
//   kill-switch 는 페이지 쪽 registrar 의 unregister 만이다 (빌드 panic: worker 청크가 `node:` 내장
//   모듈 외부 참조를 지원하지 않음 — pwa.md C-28, 2026-10-02 실측). 이 파일과 그 상대 import 에
//   Node 전역을 쓰지 않는다 (vitest source-scan 이 막는다).
import { respondToNavigation, shouldHandleNavigation } from "./navigation";
import type { SwGlobalScope } from "./sw-types";

const scope = self as unknown as SwGlobalScope;

scope.addEventListener("install", () => {
  void scope.skipWaiting();
});

scope.addEventListener("activate", (event) => {
  event.waitUntil(scope.clients.claim());
});

scope.addEventListener("fetch", (event) => {
  if (!shouldHandleNavigation(event.request, scope.location.origin)) return;
  event.respondWith(respondToNavigation(event.request, (request) => fetch(request)));
});
