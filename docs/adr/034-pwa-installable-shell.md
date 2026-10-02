# ADR-034 — PWA 설치형 셸 (캐시 없는 Service Worker + 오프라인 화면 1장)

**Status**: Accepted — PR-1 구현 완료, 자동 검증 PASS + 실 Chrome 설치 T-PWA-18 PASS (2026-10-02). 수동 T-PWA-17(iOS)·T-PWA-22(배포 후 smoke) 는 별도
**Date**: 2026-10-02
**Spec**: [`docs/requirements/pwa.md`](../requirements/pwa.md) §3·§4 (PR-1) · 테스트 [`test-matrix.md`](../plans/active/2026-10-02-pwa/test-matrix.md)
**Invariant**: `apps/web/CONTEXT.md` §4 **F-14**
**Related**: ADR-035 웹 푸시 (PR-2, 예정 — 같은 SW 에 `push`·`notificationclick` 을 더한다)

---

## 배경

PRD §9 는 모바일 네이티브 앱을 PWA 로 대신한다고 적었다 (`docs/requirements/prd.md:606`). 1차(PR-1)는
**홈 화면·데스크톱 설치**와 **오프라인일 때 깨진 화면 대신 안내 1장**까지다. 웹 푸시는 PR-2 에서 다룬다.

PWA 의 흔한 형태는 "Service Worker 가 앱 셸과 데이터를 캐시해 오프라인에서도 읽게 한다"이다.
Kairos 에서는 이 형태를 그대로 쓸 수 없다:

- 사용자 데이터는 워크스페이스·가시성·작성자 규칙으로 **즉시** 막혀야 한다 — 멀티테넌시 격리(I-9),
  파생 데이터 가시성 = 원본 가시성(I-23), 메모 작성자 전용(I-24). 권한을 잃은 순간 이후에도 기기에 남은
  사본이 보이면 그 규칙이 깨진다 (pwa.md C-4).
- Better Auth OAuth 콜백(`/api/auth/callback/*`)은 일회용 `code` 를 쓰는 내비게이션이다.

---

## 결정

### D1. SW 는 Cache Storage·IndexedDB 를 쓰지 않는다 (F-14)

캐시가 없으므로 오프라인 데이터 읽기는 제공하지 않는다 (BL-PWA-3 — 하려면 별도 ADR).
같은 이유로 **페이지와 SW 사이 버전 불일치로 깨질 자산이 없다** → `install` 에서 `skipWaiting()`,
`activate` 에서 `clients.claim()` 으로 수정본을 다음 내비게이션에 바로 반영한다.

### D2. 같은 origin `navigate` GET 만 `respondWith` 한다 · `/api/*` 제외 · navigationPreload 미사용

- 나머지 요청(자산·RSC·API·cross-origin·POST)은 `respondWith` 를 부르지 않는다 — 브라우저 기본 처리.
- `/api/*` 내비게이션(OAuth 콜백 등)은 SW 를 거치지 않는다.
- **navigationPreload 를 켜지 않는다** (pwa.md C-23): preload 는 SW 가 `respondWith` 하지 않는 내비게이션에도
  요청을 하나 더 보낸다. 실측 — preload ON 이면 `/api/auth/callback/google?code=ONE_TIME` 서버 도달 2회,
  OFF 면 1회. 일회용 `code` 가 두 번 소비되면 로그인이 깨진다. 캐시 없는 SW 라 preload 로 얻을 지연 이득도 없다.
- 서버가 준 응답은 상태코드와 무관하게 그대로 돌려준다 (5xx·3xx 마스킹 금지). SW 가 개입하는 건
  `fetch` 가 reject(네트워크 실패)될 때뿐이다.

### D3. 오프라인 응답 = SW 안 인라인 HTML 1장 (SCR-001), **200 + `Cache-Control: no-store`**

- 503 이면 Chromium 이 `console.error` 1건을 남겨 FE 증거 표준("console.error 0건")과 충돌한다 (pwa.md C-24).
  `no-store` 라 브라우저·중간 캐시가 이 응답을 실제 페이지로 저장하지 않는다. 오프라인 판별은 상태코드가
  아니라 `data-testid="offline-screen"` 이다.
- 외부 요청 0 — CSS·스크립트 인라인, 아이콘은 `data:` SVG. headed Chrome 은 아이콘 선언이 없으면
  `/favicon.ico` 를 요청해 오프라인 error 를 남긴다 (pwa.md §4.4).
- 별도 `/offline` 라우트·precache 가 없다.

### D4. 등록은 Next 16 번들 worker 로, 호출부는 레포 전체에서 1곳

`components/layout/service-worker-registrar.tsx` 의 `navigator.serviceWorker.register(new URL("../../lib/pwa/sw.ts", import.meta.url), { scope: "/", updateViaCache: "none" })`
리터럴이 `lib/pwa/sw.ts` 를 `/_next/static/service-worker/sw.js` 고정 URL 로 빌드한다. 서버가
`Service-Worker-Allowed: /` · `Cache-Control: public, max-age=0, must-revalidate` 를 붙인다 (pwa.md C-3).
prod 빌드 · secure context · `load` 이후에만 등록한다. dev 빌드는 기존 등록을 해제한다.

★부수 asset [사실 — 2026-10-02 오케스트레이터 curl 재확인, GATE-PR1 D1]: Turbopack 이 `'use client'` registrar 를 SSR 용으로도 컴파일하면서 같은 `new URL()` 을 일반 asset 으로도 처리해, `sw.ts` **원본**(1770 B)이 `/_next/static/media/sw.<hash>.ts` 로 공개 서빙된다 (200, `content-type: video/mp2t`). 비밀값은 없고(sw.ts 는 env 를 못 읽는다, C-28) 같은 로직이 sw.js 로 이미 공개돼 있어 영향은 최소다 (pwa.md C-3).

### D5. kill-switch 는 페이지 쪽 unregister 만이다

빌드 플래그 `NEXT_PUBLIC_PWA_SW=off` 로 다시 배포하면 페이지 registrar 가 등록 대신
`getRegistrations()` → 전부 `unregister()` 한다. 열린 창을 강제 이동하지 않는다 — controller 는 남지만
통과형이라 무해하고, 다음 내비게이션부터 제어되지 않는다 (pwa.md C-27, T-PWA-15 로컬 실측 PASS).

**sw.js 는 플래그를 읽지 않는다.** Turbopack 의 service worker 청크는 `process.env.NEXT_PUBLIC_*` 를
인라인하지 않고, 남은 참조를 `node:process` 외부 모듈로 처리하려다 빌드가 panic 한다 (pwa.md C-28,
2026-10-02 실측). 그래서 sw.js 는 모든 빌드에서 같고, `lib/pwa/sw.ts` 와 그 import 그래프에 Node 전역을
쓰지 않는다 (vitest source-scan 이 막는다).

**한계**: SW 자체 버그로 페이지 JS 가 아예 안 뜨면 kill-switch 가 닿지 않는다. 그때 복구는
**수정한 `sw.ts` 배포**다 (sw.js 바이트 변경 → `updateViaCache: 'none'` + `max-age=0` 로 내비게이션마다
업데이트 확인 → `skipWaiting`+`claim`). D1·D2 로 SW 가 하는 일을 "네트워크 실패 시 안내 1장" 으로 줄인 것이
이 위험을 작게 만드는 1차 방어선이다.

### D6. 롤백(`deploy-rollback`)으로는 SW 가 내려가지 않는다

구 이미지에는 sw.js 가 없어 404 → 브라우저의 `update()` 만 실패하고 기존 등록·제어가 남는다
(pwa.md C-25, R-2). 남은 SW 는 D2 의 통과형이라 구 이미지 앱도 그대로 동작한다. 등록을 걷어내는 수단은
D5 의 플래그 빌드뿐이다 — 운영 절차는 `deploy/oci/build.env.example` 주석에 둔다.

### D7. 설치 메타 — manifest·아이콘은 비로그인 공개 경로

- `app/manifest.ts` → `/manifest.webmanifest`. 셀프호스팅에선 manifest 요청에 쿠키가 실리지 않으므로
  (pwa.md C-2) `proxy.ts` matcher 에서 `manifest.webmanifest` **1항목만** 제외한다.
- 아이콘은 `public/icons/*.png` + `metadata.icons.apple` 로 경로를 고정한다. `favicon.ico` 는 PNG-in-ICO
  16·32·48 이고 항목은 RGBA 여야 한다 (Turbopack ICO 디코더 요구, pwa.md §4.2).
- `start_url=/dashboard`, `theme_color`=`background_color`=`#0A0A0B` 단일값 (앱 기본 dark, pwa.md C-10·C-12).
- `viewport-fit=cover` + safe-area 토큰(하단 nav · body 좌우 padding).

---

## 위험 — iOS

- **standalone 에서 Google 로그인 리다이렉트·Google Picker 팝업(ADR-026)** 이 실패할 수 있고, 홈 화면 앱은
  Safari 와 저장소가 분리된다 (pwa.md R-5). iOS 실기기 수동 확인(T-PWA-17) 전이다 — 실패 시 이메일 로그인
  안내 + BL 등재.
- body 좌우 safe-area padding 은 WebKit 동작을 근거로 한 설계다 — 가로 모드 노치·홈 인디케이터 확인 지점도
  T-PWA-17 이다. Chromium 에서는 CDP inset 주입(T-PWA-16)으로 회귀만 고정한다.
- iOS 웹 푸시(16.4+, 홈 화면 설치 필요)는 PR-2 / ADR-035 소관이다.

---

## 기각한 대안

**① 앱 셸·데이터 precache (Serwist 등 Workbox 계열, Cache Storage)** — 오프라인 읽기를 주지만 D1 의 근거
(I-9·I-23·I-24, revocation 즉시성)와 정면으로 충돌한다. 권한을 잃은 뒤에도 기기에 남은 사본이 보인다.
캐시 버전 관리·고착(R-2) 비용도 생긴다.

**② navigationPreload 로 SW 경유 지연 상쇄** — 일회용 OAuth `code` 이중 소비 (C-23). 캐시가 없어 이득도 없다.

**③ 오프라인 응답 503** — 의미상 더 정확하지만 `console.error` 1건이 남아 증거 표준과 충돌한다 (C-24).

**④ sw.js 쪽 자가 해제 kill-switch (플래그 빌드의 sw.js 가 스스로 `unregister`)** — "페이지 JS 가 안 뜨는
SW 버그" 까지 덮는 2층 안전망이었으나, worker 번들이 env 를 인라인하지 않아 빌드가 panic 한다 (C-28).
빌드타임 대체 수단을 따로 만들면 SW 소스가 빌드마다 갈라진다 — D5 의 한계로 받아들인다.

**⑤ 오프라인 배너 (`next/offline` `useOffline`)** — experimental 플래그가 필요하고, 내비게이션 실패는 SCR-001 이
이미 덮는다 (spec 게이트 ①, BL-PWA-2).

**⑥ Next 아이콘 파일 컨벤션 (`app/icon.png`·`app/apple-icon.png`)** — href 가 확장자 없는 경로일 수 있어
proxy matcher 의 이미지 확장자 제외에 걸리지 않고 로그인 리다이렉트될 수 있다 [가정, pwa.md §4.2].
`public/icons/` 고정 경로로 피한다.

**⑦ 커스텀 설치 버튼 (`beforeinstallprompt`)** — Next 번들 문서 비권장, Safari iOS 미동작 (BL-PWA-1).

---

## 검증

- 단위: vitest — 가로채기 조건·응답 마스킹 금지·오프라인 HTML(T-PWA-12), 등록 모드(T-PWA-14), 소스 스캔
  (navigationPreload·Cache Storage·IndexedDB 0건, 등록 호출부 1곳, sw 그래프 Node 전역·비상대 import 0건),
  favicon 형식.
- e2e (`public-only`, prod 빌드): manifest·아이콘·메타·SW 헤더(request 그룹) + 등록·오프라인·`/api/*` 1회
  도달·inset(browser 그룹, CI 판정은 draft PR spike — pwa.md R-1).
- 수동: kill-switch 실동작 T-PWA-15 (2026-10-02 로컬 실측 PASS, `evidence/orch/t15-killswitch.json`).
  실제 Chrome 설치 T-PWA-18 은 2026-10-02 PASS (Chrome 154 macOS, `Kairos.app` · start URL `/dashboard` · K 아이콘 — `docs/plans/active/2026-10-02-pwa/report.md` §6). **iOS 실기기 T-PWA-17 · 배포 후 헤더 스모크 T-PWA-22 는 채택 시점에 미실행 — 별도로 한다.**
- 행별 상태·기대값의 정본은 test-matrix 다.
