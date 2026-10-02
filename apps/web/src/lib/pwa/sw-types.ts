// Service Worker 전역 스코프의 최소 타입 — sw.ts 가 실제로 쓰는 표면만 선언한다.
//
// ★tsconfig 는 `dom` lib 만 쓴다. `webworker` lib 를 더하면 `self`·`addEventListener` 같은
//   전역 선언이 dom 과 겹쳐 프로젝트 전체 타입이 흔들린다 (docs/requirements/pwa.md R-14).
//   그래서 표준 lib 를 끌어오지 않고 필요한 부분만 여기 둔다. PR-2 의 push·notificationclick 도
//   이 파일에 같은 방식으로 더한다.

export interface SwExtendableEvent extends Event {
  waitUntil(promise: Promise<unknown>): void;
}

export interface SwFetchEvent extends SwExtendableEvent {
  readonly request: Request;
  respondWith(response: Response | Promise<Response>): void;
}

interface SwEventMap {
  install: SwExtendableEvent;
  activate: SwExtendableEvent;
  fetch: SwFetchEvent;
}

export interface SwGlobalScope {
  readonly location: { readonly origin: string };
  readonly clients: { claim(): Promise<void> };
  skipWaiting(): Promise<void>;
  addEventListener<K extends keyof SwEventMap>(
    type: K,
    listener: (event: SwEventMap[K]) => void
  ): void;
}
