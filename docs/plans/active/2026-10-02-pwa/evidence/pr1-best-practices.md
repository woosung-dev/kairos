# PR-1 best-practices 게이트 (GATE-PR1)

> 2026-10-02 · 기준 = `vercel-react-best-practices` 스킬 (규칙 파일 23개 Read) · 대상 = PR-1 diff (커밋 전 `git diff HEAD` + 미추적) · 판정자 = 새 Evaluator (cold context)
> **결과: PASS — FAIL 0** (24개 규칙 판정: PASS 15 · N/A 9)

## 규칙별 판정

| 규칙 | 판정 | 근거 (file:line) | 메모 |
|---|---|---|---|
| `bundle-analyzable-paths` | PASS | `apps/web/src/components/layout/service-worker-registrar.tsx:18` | `new URL("../../lib/pwa/sw.ts", import.meta.url)` 리터럴 → 클라이언트 청크가 `/_next/static/service-worker/sw.js` 로 고정. 부수 산출물은 아래 "경미 사항 1" |
| `bundle-barrel-imports` | PASS | `service-worker-registrar.tsx:11-15` · `app/layout.tsx:4` | 파일 직접 import. `lib/pwa/index.ts` barrel 없음, 새 패키지 import 0 |
| `bundle-conditional` | PASS | `apps/web/src/lib/pwa/sw.ts:14` | navigation·OFFLINE_HTML 은 `static/service-worker/sw.js` 에만 있다 (`offline-screen` grep 결과 다른 위치 0). 페이지 청크의 registrar 모듈 = 1052 B |
| `bundle-defer-third-party` | N/A | `app/layout.tsx:85` | 서드파티 추가 없음. registrar 는 1st-party 이고 `load` 이후로 미룬다 |
| `bundle-dynamic-imports` | N/A | `service-worker-registrar.tsx:36-59` | 무거운 컴포넌트 없음 (null 렌더, minified 1052 B) |
| `js-request-idle-callback` | PASS | `apps/web/src/lib/pwa/registration.ts:72-82` | `load` 이후로 지연. `register()` 는 async, SW fetch·parse 는 메인 스레드 밖. Safari/iOS 에 rIC 가 없어 `load` 가 맞는 시점 |
| `advanced-init-once` | PASS | `service-worker-registrar.tsx:34-39` | 모듈 가드. e2e T-PWA-09 = register ×1 (readyState=complete), vitest = 재마운트·2번째 인스턴스에서 추가 호출 0 |
| `advanced-event-handler-refs` | N/A | `service-worker-registrar.tsx:56` | 전달받는 handler prop 없음, 재구독 없음 (deps `[]`) |
| `client-event-listeners` | PASS | `registration.ts:81` · `app/layout.tsx:85` | `load` 리스너 1개 `{once:true}`. root layout 단일 인스턴스 + init-once 가드 |
| `rendering-hydration-no-flicker` | PASS | `service-worker-registrar.tsx:58` | 서버·클라이언트 모두 null → client-only 데이터 렌더 0. 새 Playwright 컨텍스트에서 `/sign-in`(미제어·제어)·`/` 콘솔 메시지 0 |
| `rendering-hydration-suppress-warning` | PASS | `app/layout.tsx:46` | 새 `suppressHydrationWarning` 없음 (html 의 기존 next-themes 것 그대로). hydration 경고 실측 0 |
| `rendering-conditional-render` | N/A | `components/layout/bottom-nav.tsx:31,37` | diff 에 `&&` JSX 없음. bottom-nav 는 속성·style 추가만, registrar 는 null |
| `rendering-hoist-jsx` | N/A | `service-worker-registrar.tsx:58` | 새 클라이언트 컴포넌트에 정적 JSX 없음. layout 은 RSC |
| `rerender-derived-state-no-effect` | PASS | `service-worker-registrar.tsx:37-56` | useState·setState 없음. effect 는 외부 시스템(navigator/window) 동기화만 |
| `rerender-move-effect-to-event` | N/A | `service-worker-registrar.tsx:37` | 사용자 동작이 아닌 마운트 시 초기화. 오프라인 '다시 시도' 는 click 핸들러 (`lib/pwa/offline-page.ts:91`) |
| `rerender-dependencies` | PASS | `service-worker-registrar.tsx:56` | deps `[]` |
| `server-hoist-static-io` | N/A | `apps/web/src/app/manifest.ts:7-35` | I/O 없음. 빌드 로그상 `/manifest.webmanifest` 는 정적 prerender (○). 상수는 `:7` 에 hoist |
| `server-serialization` | PASS | `app/layout.tsx:85` | `<ServiceWorkerRegistrar />` prop 0 → RSC→client 직렬화 0 |
| `server-no-shared-module-state` | PASS | `service-worker-registrar.tsx:34,38-39` | SSR 청크(`src_0nk-2t7._.js`)에서 `let g=!1` 는 useEffect 콜백 안에서만 변경. Fizz 는 effect 를 실행하지 않아 서버에선 false 고정, 요청 데이터 보관 0. navigator 접근은 함수 안에서만 |
| `js-hoist-regexp` | PASS | `proxy.ts:57` · `lib/pwa/navigation.ts:18` | 프로덕션 diff 에 RegExp 생성 없음. matcher 는 빌드타임 정적 config, prefix 판정은 상수 + `startsWith`. 테스트 정규식은 모듈 레벨 hoist (`source-scan.test.ts:32-35`) |
| `js-early-exit` | PASS | `navigation.ts:24` · `registration.ts:24-27,49` · registrar `:38,47` | 싼 mode·method 판정을 URL 파싱보다 먼저 |
| `async-parallel` | PASS | `registration.ts:53` | unregister 를 `Promise.all` 로 병렬 |
| `rendering-script-defer-async` | N/A | `lib/pwa/offline-page.ts:90-93` | body 끝 인라인 스크립트, 외부 src 없음 |
| `client-passive-event-listeners` | N/A | — | scroll·touch·wheel 리스너 없음 |

## 같은 라운드에서 확인한 것 (요지)

- `.next` 산출물: 클라이언트 청크의 register URL = `/_next/static/service-worker/sw.js`, sw.js sha256 앞 16자 `58956eebfbe297af` (오케스트레이터 빌드와 일치). SSR 청크에서 `hasStarted` 는 effect 안에서만 쓰기.
- `eslint --max-warnings 0` (변경 src·테스트) exit 0. curl: sw.js `Service-Worker-Allowed: /` · `Cache-Control: public, max-age=0, must-revalidate`, manifest·아이콘 4장·favicon 200, `/x/manifest.webmanifest` 307.
- ADR-034 인용 재현: `navpreload.mjs` preload ON 2회 / OFF 1회 (C-23), 503 응답 시 console.error (C-24), T-PWA-23 3회 모두 2종 3건 (pwa.md:168).
- ID 충돌 없음 (origin/main `bb9033e` 기준 최고 ADR-033 · F-13 · B-15, BL-PWA·SCR·REQ·API·ENT 미사용).

## 경미 사항 (게이트 통과와 공존, 후속 처리)

1. Turbopack 이 `'use client'` registrar 를 SSR 용으로도 컴파일하면서 `new URL()` 을 일반 asset 으로 처리 → `sw.ts` **원본**(1770 B)이 `/_next/static/media/sw.<hash>.ts` 로 공개 서빙된다 (200, `video/mp2t`, 오케스트레이터 curl 재확인). 비밀값 없음(sw.ts 는 env 를 읽지 못함) + 같은 로직이 sw.js 로 이미 공개 → 영향 최소. ADR-034 D4 에 기록.
2. `apps/web/README.md:109,114` · `docs/development/testing.md:88` 의 public-only 설명이 "보안 헤더 전용" 으로 남음.
3. origin/main 이 4 커밋 앞섬 (`layout.tsx` ← #203 `next/font/local`, `REFACTORING-BACKLOG.md` ← #200 BL-LR-17~19 충돌) → 병합 후 재빌드·public-only 재실행 필요.
4. C-28 worker panic 로그 원문 → `evidence/orch/turbopack-worker-panic-node-process.log` 로 보존 (오케스트레이터).
