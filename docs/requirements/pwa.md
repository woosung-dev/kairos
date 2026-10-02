# PWA — 설치형 셸 + 웹 푸시 (기능 명세)

> **상태: PR-1 구현 완료 — 자동 검증 PASS + 실 Chrome 설치 T-PWA-18 PASS (2026-10-02). 수동 T-PWA-17(iOS)·T-PWA-22(배포 후 smoke) 는 별도 · PR-2 확정 · 미구현** — 사용자 spec 게이트 통과 (2026-10-02)
> **근거**: PRD §9 "모바일 네이티브 앱 (PWA로 대체)" (`docs/requirements/prd.md:606`) · 계획 [`docs/plans/active/2026-10-02-pwa/plan.md`](../plans/active/2026-10-02-pwa/plan.md) · 테스트 매트릭스 [`test-matrix.md`](../plans/active/2026-10-02-pwa/test-matrix.md)
> **관련 ADR**: [ADR-034](../adr/034-pwa-installable-shell.md) PWA 셸 (PR-1, Accepted) · ADR-035 웹 푸시 (PR-2, 예정). ADR-033 은 PR #200 이 머지돼(2026-10-02 KST, 커밋 `d35edf6`) main 에 있다 — 034 는 그대로다.
> **불변식**: F-14 (`apps/web/CONTEXT.md` §4, PR-1 반영) · B-16 (`apps/api/CONTEXT.md` §5, PR-2 예정)
> **ID**: REQ-001~011 · SCR-001~002 · API-001~003 · ENT-001 · BL-PWA-1~. 레포에서 처음 부여하는 번호다 (`AGENTS.md` §5 ID 체계 — 이후 변경·재사용 금지).
> **라벨**: `[사실]` 은 file:line 으로 확인함 · `[가정]` 은 확인하지 못한 추론 · `[확인 필요]` 는 사용자 결정 대기 — 2026-10-02 게이트로 전부 확정돼 본문에 남은 것 없음 (§8).

---

## 0. 한 줄 요약

Kairos 를 홈 화면·데스크톱에 **설치할 수 있게** 하고(PR-1, FE 만), 업로드한 회의의 **처리 완료·실패를 업로드한 본인에게 웹 푸시로 알린다**(PR-2, BE+DB+FE). 서비스 워커는 **어떤 데이터도 캐시하지 않는다** — 오프라인이면 SW 안에 든 안내 화면 하나만 보여준다.

## 1. 확정된 사용자 결정 (2026-10-02 인터뷰 — 임의 변경 금지)

| 항목 | 결정 |
|---|---|
| 범위 | 설치형 셸 + 오프라인 안내 + 웹 푸시 |
| 푸시 이벤트 | 회의 처리 **완료·실패만**. 수신자 = 업로드한 본인 (`Meeting.created_by_id`). 그 밖의 이벤트는 비범위 (§6 BL 후보) |
| PR | 2개 순차 — PR-1 셸(FE 만) 머지 → main 에서 PR-2 푸시(BE+DB+FE) |
| 아이콘 | 'K' 모노그램 — Satoshi 700, 글자 `#3ECFB4`, 배경 `#0A0A0B` (시안 승인 + `favicon.ico` 교체: §4.2, 게이트 ③) |
| spec 게이트 ①~⑦ | 2026-10-02 전부 추천안으로 확정 (§8). ⑥ 워크스페이스 딥링크는 PR-2 에 포함 |

## 2. 설계 제약 (코드로 확인한 사실)

| # | 사실 | 근거 | 설계 귀결 |
|---|---|---|---|
| C-1 | `proxy.ts` matcher 가 `/manifest.webmanifest` 를 보호 경로로 취급해 비로그인 요청을 `/sign-in` 으로 307 보낸다 | `apps/web/src/proxy.ts:35-40,55` | matcher 에 `manifest\\.webmanifest$` 제외 **1개만** 추가 (REQ-001) |
| C-2 | Next 는 `VERCEL_ENV==='preview'` 일 때만 manifest `<link>` 에 `crossorigin="use-credentials"` 를 붙인다 — 셀프호스팅에선 manifest 요청에 쿠키가 실리지 않는다고 봐야 한다 | `apps/web/node_modules/next/dist/lib/metadata/metadata.js:290-297` | manifest 는 반드시 비로그인 공개 경로 |
| C-3 | Next 16.3.6 번들 worker: `navigator.serviceWorker.register(new URL('./sw.ts', import.meta.url), { scope: '/', updateViaCache: 'none' })` → `.next/static/service-worker/sw.js` 고정 URL. 서버가 `Cache-Control: public, max-age=0, must-revalidate` + `Service-Worker-Allowed: /` 를 붙인다 | `node_modules/next/dist/server/lib/router-server.js:434-437` (Cache-Control·Service-Worker-Allowed) · `node_modules/next/dist/build/index.js:1657-1670` (빌드 시 `/_next/static/service-worker/:path*` 헤더 라우트 등록) · 2026-10-02 spike (plan `checklist.md` Phase 0) | URL·scope 는 리터럴, 등록 호출부 정확히 1곳, precache 매니페스트 주입 기능 없음. ★부수 asset [사실 — 2026-10-02 오케스트레이터 curl 재확인, GATE-PR1 D1]: Turbopack 이 `'use client'` registrar 를 SSR 용으로도 컴파일하면서 이 `new URL()` 을 일반 asset 으로도 처리해, `sw.ts` **원본**(1770 B)이 `/_next/static/media/sw.<hash>.ts` 로 공개 서빙된다 (200, `content-type: video/mp2t`). 비밀값은 없고(sw.ts 는 env 를 못 읽는다, C-28) 같은 로직이 sw.js 로 이미 공개돼 있어 영향은 최소다 |
| C-4 | 사용자 데이터는 워크스페이스·가시성·작성자 규칙으로 즉시 차단돼야 한다 (revocation 즉시성 회귀 가드 포함) | `CONTEXT-MAP.md:88` (I-9) · `:102` (I-23) · `:103` (I-24) · `:109` | **SW 는 Cache Storage·IndexedDB 를 쓰지 않는다** (F-14 예정) |
| C-5 | API 는 cross-origin (`kairos-api.woosung.dev`), `/api/auth/*` 는 같은 origin 에서 세션·JWT 를 다룬다, RAG 는 SSE | `docs/adr/028-oci-selfhosting.md:99` (D5) · `apps/web/AGENTS.md:57-64` · `apps/web/CONTEXT.md:81` (F-12) | SW 는 **같은 origin 의 `navigate` 요청만** 처리하고 `/api/*` 는 건드리지 않는다 |
| C-6 | CI `frontend-build` 는 DB 없이 `pnpm start` 후 `public-only` 프로젝트만 돈다. DB 가 없으면 `/` 는 500 이지만 `/sign-in` 은 응답한다 (`wait-on` 대상이 `/sign-in`) | `mise.toml:196-219` · `.github/workflows/test.yml:130-139` · `test.yml:323-324` | e2e 의 SW 진입 페이지는 `/sign-in` |
| C-7 | `public-only` 프로젝트는 지금까지 **브라우저 페이지 렌더를 CI 에서 한 적이 없다** — CI chromium 의 `ERR_NAME_NOT_RESOLVED` 를 피하려고 request API 만 썼다 | `apps/web/e2e/tests/security-headers.spec.ts:1-4` · `apps/web/playwright.config.ts:70-88` | 리스크 R-1. 브라우저가 필요한 테스트는 별도 그룹으로 나누고 draft PR spike 로 CI 가능 여부를 판정 |
| C-8 | 헤드리스 Chromium 147 에서 CDP `Page.getInstallabilityErrors` 는 **응답은 하지만 음성 대조군(display=browser, 512 아이콘 없음)에도 `[]` 를 돌려준다** | 2026-10-02 본 라운드 실측 (scratchpad `icon-proof/probe-neg.mjs`) | CI 는 설치 가능성 판정 불가 — manifest 필드 + 아이콘 PNG IHDR 실측으로 대체, 설치는 실제 Chrome 에서만 |
| C-9 | `--bottom-nav-height: 56px` 소비처 4곳 | `apps/web/src/app/globals.css:57` · `components/layout/bottom-nav.tsx:33` · `components/layout/panel-layout.tsx:147` · `app/(app)/memory/page.tsx:142` · `features/feedback/components/feedback-button.tsx:67` | 토큰 1곳만 `calc(56px + env(safe-area-inset-bottom, 0px))` 로 + nav 내부 하단 padding. Chromium inset=0 → `e2e/tests/mobile-responsive.spec.ts:98-118` 의 56px 단언 유지 |
| C-10 | 앱 기본 테마는 dark (`data-theme`, `defaultTheme="dark"`), 랜딩만 `data-theme="landing"` 이고 OS 라이트면 라이트 | `components/layout/theme-provider.tsx:7-12` · `app/(landing)/layout.tsx:4` · `app/globals.css:197,252-253` | `themeColor` 단일값 `#0A0A0B`. OS media 배열은 앱 테마와 어긋나서 쓰지 않는다 |
| C-11 | 로고 파일이 없다. 사이드바 접힘 상태가 'K' 텍스트 (Satoshi, accent). `src/app/favicon.ico` 는 create-next-app 기본값 | `components/layout/sidebar.tsx:394-404` · `apps/web/src/app/favicon.ico` | K 모노그램 아이콘 신규 제작 (REQ-002) |
| C-12 | `/` 는 세션이 있으면 서버에서 `/dashboard` 로 리다이렉트한다 | `app/(landing)/page.tsx:9-14` | `start_url=/dashboard` (왕복 1회 절약). 비로그인이면 proxy 가 `/sign-in?callbackURL=%2Fdashboard` 로 보낸다 (`proxy.ts:36-40`) |
| C-13 | 로그아웃 순서: `queryClient.clear()` → `clearAuthTokenCache()` → `await authClient.signOut()` | `components/layout/header.tsx:164-176` (signOut :174) · `lib/use-api-client.ts:72` | BE 구독 삭제는 **signOut 이전** (이후엔 `/api/auth/token` 이 401) |
| C-14 | FE `NEXT_PUBLIC_*` 는 빌드타임 인라인 → Dockerfile ARG·CI repo Variables(`release.yml`)·맥 비상 `deploy/oci/build.env` 결합 | `apps/web/Dockerfile:27-46` · `.github/workflows/release.yml:136-143` · `mise.toml:287-300` | VAPID 공개키는 BE 엔드포인트로 제공 (API-001) |
| C-15 | 회의 상태 `completed`/`failed` 전이는 `meetings/pipeline_service.py` 에만 있다 — 완료 :185-186 (`_analyze_and_store` 끝), 실패 :259-269 (`process_meeting`), :318-328 (`capture_text`) | `grep update_status( apps/api/src` | 푸시 훅은 오케스트레이터 안 (B-3, `apps/api/CONTEXT.md:73`). 온보딩 훅이 같은 자리에 같은 방식(지연 import + 비치명적 try)으로 있다 (:177-183) |
| C-16 | 사용자 단위 경로 선례 `/api/v1/users/me`, `/api/v1/users/me/onboarding` — I-13 예외 `/api/v1/users` 안 | `apps/api/src/auth/router.py:9-15` · `apps/api/src/onboarding/router.py:10` · `CONTEXT-MAP.md:92` | 푸시 API 는 `/api/v1/users/me/push-*` |
| C-17 | `common/notifications.py` 는 Slack webhook 유틸이다 | `apps/api/src/common/notifications.py:1-29` | 새 도메인 이름은 `push` |
| C-18 | Settings 는 선택 기능을 optional 필드 + warn-only 검증으로 둔다 (부팅 차단형 validator 사고 교훈). CI·`export_openapi.py` 는 fake env 7개만 준다 | `apps/api/src/core/config.py:92-102,131-136` · `test.yml:80-87,152-159` · `apps/api/scripts/export_openapi.py:26-34` | VAPID 설정은 전부 optional, 없으면 기능 비활성 |
| C-19 | upsert 는 `pg_insert(...).on_conflict_do_update(...)` + `session.execute` 가 선례 (B-10 G3-keep-dialect). flush 후 IntegrityError catch 는 금지 (MissingGreenlet) | `apps/api/src/integrations/repository.py:73-96` · `apps/api/CONTEXT.md:80` | REQ-007 upsert |
| C-20 | alembic head 는 단일 `b3d5f8a1c2e4`. rollback 은 migrate 를 건너뛴다 → 마이그레이션은 가산형이어야 한다 | `apps/api/alembic/versions/` (revision−down_revision 차집합) · `mise.toml:402-417` | 새 테이블 추가만 |
| C-21 | CSP 는 Report-Only. `worker-src`·`manifest-src` 미지정 → `script-src 'self'`·`default-src 'self'` 로 폴백 | `apps/web/next.config.ts:26-48,68` | 같은 origin SW·manifest 는 추가 지시문 불필요 |
| C-22 | **Playwright 번들 Chromium 147 에서 `context.setOffline(true)` 는 SW 의 첫 내비게이션 fetch 만 실패시킨다** (Chrome 154 는 오프라인이 유지된다 — EVAL-IMPL-2) — 같은 컨텍스트에서 이어지는 SW fetch 는 서버에 도달한다. reload 3회 결과 = [오프라인 화면, 온라인, 온라인] (Chromium 147 / Playwright 1.59.1, 오케스트레이터 재현 5/5). 반면 `context.route(…, r => r.abort("internetdisconnected"))` 는 SW fetch 까지 실패를 유지한다 (3/3) | scratchpad `eval-spec2/offline-leak2.mjs` · `eval-spec2/retry-route.mjs` (2026-10-02 EVAL-SPEC-2, 오케스트레이터 재현) | `setOffline` 은 **새 컨텍스트의 첫 reload 1회** 판정에만 쓴다. 실패를 유지해야 하는 단계(재시도)는 `context.route` abort 로 (T-PWA-11) |
| C-23 | **navigationPreload 를 켜면 SW 가 `respondWith` 하지 않는 내비게이션도 서버에 2번 도달한다.** 같은 SW·같은 `/api/auth/callback/google?code=ONE_TIME` 내비게이션에서 preload ON = 서버 도달 2회, OFF = 1회 | 2026-10-02 EVAL-SPEC-1 실측, 오케스트레이터 재현 (scratchpad `eval-spec1/navpreload.mjs`, Chromium 147) | **navigationPreload 를 쓰지 않는다** — 일회용 OAuth `code` 가 두 번 소비된다 (REQ-004, T-PWA-13) |
| C-24 | SW 가 503 을 돌려주면 Chromium 이 콘솔에 `console.error` 1건(리소스 로드 실패)을 남긴다. 200 이면 0건 | 2026-10-02 EVAL-SPEC-1 실측 보고 (200 변형 = scratchpad `eval-spec1/offline200.mjs`). Generator 미재현 — T-PWA-11 이 고정 | 오프라인 응답은 **200** + `no-store` (`AGENTS.md` §4 증거 표준 "console.error 0건" 유지) |
| C-25 | sw.js 가 404 가 되면(구 이미지로 롤백) `update()` 가 reject 되고 기존 등록·제어가 그대로 남는다 | 2026-10-02 EVAL-SPEC-1 실측 보고 (scratchpad `eval-spec1/sw404.mjs`). Generator 미재현 | 롤백으로는 SW 가 내려가지 않는다 → 제거는 kill-switch 빌드로만 (R-2) |
| C-26 | Playwright `serviceWorkers: 'block'` 은 init script 로 `navigator.serviceWorker.register` 를 `async () => { console.warn('Service Worker registration blocked by Playwright') }` 로 바꾼다 → `register()` 는 `undefined` 로 resolve, 새 컨텍스트의 `getRegistration()` 은 `undefined`, `ready` 는 pending 으로 남는다 | `node_modules/.pnpm/playwright-core@1.59.1/.../lib/server/browserContext.js:130-133` · scratchpad `eval-spec2/block.mjs` | registrar 는 `register()` 결과를 역참조하지 않는다 (§4.4). 그 warn 1줄은 허용 콘솔 목록에 넣는다. 등록 없음 e2e 케이스에 쓴다 (T-PWA-48·49) |
| C-27 | 페이지 쪽 `registration.unregister()` 뒤 현재 페이지 controller 는 **유지**되고, **다음 내비게이션부터 제어되지 않는다**. (kill sw.js 가 스스로 내려가는 경로 ②는 C-28 로 폐기 — 측정 기록 `eval-spec3/killsw-activate.mjs` 만 남긴다) | scratchpad `eval-spec2/unreg.mjs` | kill-switch 가 열린 창을 강제 이동할 필요가 없다 — 남은 controller 는 Cache Storage 없는 통과형이다 (§4.5, T-PWA-15) |
| C-28 | **Turbopack 의 service worker 청크는 `process.env.NEXT_PUBLIC_*` 를 인라인하지 않는다.** `sw.ts` 에 남은 `process` 참조를 `node:process` 외부 모듈로 처리하려다 빌드가 panic 한다 — `Error [TurbopackInternalError]: Failed to write app endpoint /favicon.ico/route … Execution of service_worker_chunk failed - the chunking context (unknown) does not support external modules (request: node:process)`. Next 번들 PWA 문서에도 worker env 경로가 없다 | 2026-10-02 오케스트레이터 `NEXT_PUBLIC_PWA_SW=off mise run fe-build` 빌드 로그 실측 — 원문 보존 `docs/plans/active/2026-10-02-pwa/evidence/orch/turbopack-worker-panic-node-process.log` | SW 는 빌드 플래그를 읽지 않는다 — sw.js 는 모든 빌드에서 같다. kill-switch 는 페이지 쪽 unregister 만 (§4.5). `lib/pwa/sw.ts` 와 그 상대 import 그래프에 `process` 식별자 0건 (vitest source-scan, T-PWA-14) |

## 3. 요구 목록 (REQ)

| REQ | 요구 | 수용 기준 (요약 — 상세는 §4·§5) | PR | 테스트 |
|---|---|---|---|---|
| REQ-001 | Web App Manifest 제공 + 비로그인 접근 | `GET /manifest.webmanifest` 비로그인 200, `content-type` 에 `application/manifest+json`, 필드값 §4.1 표와 일치. `/dashboard` 비로그인은 여전히 307 | 1 | T-PWA-01·02·04·05·06·18 |
| REQ-002 | K 모노그램 아이콘 세트 | `/icons/icon-192.png` 192×192 · `/icons/icon-512.png` 512×512 · `/icons/icon-maskable-512.png` 512×512 · `/icons/apple-touch-icon.png` 180×180 (IHDR 실측, colortype 2=불투명) · `/favicon.ico` K 로 교체 (게이트 ③ 확정) · 전부 비로그인 200 | 1 | T-PWA-03·06·18 |
| REQ-003 | viewport · theme-color · appleWebApp · safe-area | `<meta name="viewport">` 에 `viewport-fit=cover`, `theme-color=#0A0A0B` 정확히 1개, `mobile-web-app-capable=yes`, `apple-mobile-web-app-title=Kairos`. body 좌우 safe-area padding. 모바일 375×812 Chromium 에서 하단 nav 높이 56px 유지 | 1 | T-PWA-06·16·17 |
| REQ-004 | Service Worker — 등록 조건 + 내비게이션 처리 + 오프라인 화면(SCR-001) | prod 빌드·secure context·`load` 이후에만 등록, scope `/`. 같은 origin `navigate` (단 `/api/*` 제외)만 `respondWith`. navigationPreload 미사용 — `/api/*` 내비게이션은 서버에 **정확히 1회** 도달. 네트워크 실패 시에만 SCR-001 (200 + `no-store`). 서버 5xx 는 그대로 통과. `caches.keys()` 는 항상 `[]` | 1 | T-PWA-07~13·19·21·22·23 |
| REQ-005 | kill-switch + dev 해제 | 빌드 플래그 `NEXT_PUBLIC_PWA_SW=off` 또는 dev 빌드면 등록하지 않고 기존 등록을 전부 unregister (페이지 쪽만). sw.js 는 플래그를 읽지 않는다 — 모든 빌드에서 같다 (C-28) | 1 | T-PWA-14·15·22 |
| REQ-006 | 비범위 명시 | §6 의 항목은 이번 2개 PR 에서 구현하지 않는다 (BL 등재만) | 1·2 | — (리뷰) |
| REQ-007 | 구독 API + 데이터 모델 (API-001~003, ENT-001) | §5.1·§5.2. endpoint 단위 upsert(ON CONFLICT), 재구독 시 현재 사용자로 rebind, 푸시 서비스 호스트 allowlist. 사용자당 개수 상한은 두지 않는다 (BL-PWA-14) | 2 | T-PWA-30~32·34·43·44 |
| REQ-008 | 발송 — 회의 완료·실패 → 업로더 본인 | 최종 commit 이후 · best-effort(실패해도 회의 상태 불변) · 업로더의 구독에만 · 조회 → 트랜잭션 종료 → 발송 → 404/410 정리(새 짧은 트랜잭션) 순서 · `timeout=10` 명시 · 업로더가 워크스페이스 멤버가 아니면 미발송 | 2 | T-PWA-35~42·52·53 |
| REQ-009 | FE 구독·해제·로그아웃·계정 전환 + SW `push`·`notificationclick` | 권한 요청은 토글 클릭 때만. SW 등록은 `getRegistration()` 으로만 조회 (`ready` 대기 금지). 등록이 없으면 알림 UI 는 '사용 불가'. 로그아웃은 BE 삭제 → 로컬 unsubscribe → 기존 순서, 등록이 없어도 대기 없이 진행. 소유자 표식 불일치면 unsubscribe. 클릭 이동은 같은 origin `/meetings/<uuid>` (+ `?workspace=<uuid>` 만) · 상세 진입 시 `?workspace=` 가 활성과 다르고 멤버면 1회 전환 후 파라미터 제거 (§5.5) | 2 | T-PWA-45~54·57·59 |
| REQ-010 | 페이로드 스키마 + 프라이버시 | 페이로드는 `{v, kind, meetingId, workspaceId}` 만 (게이트 ⑥ 확정). 회의 제목·요약·전사 미포함 (게이트 ④). 문구는 SW 가 `kind` 로 결정 | 2 | T-PWA-42·46 |
| REQ-011 | iOS 설치 안내 | iOS·iPadOS 에서 홈 화면 앱이 아닐 때만, 알림 설정(SCR-002) 안에 안내 표시. 그 외 환경에선 렌더하지 않는다 | 2 | T-PWA-56·55 |

> REQ 분할 근거: 오케스트레이터 골격(REQ-001~010)을 유지하고, iOS 설치 안내만 REQ-011 로 분리했다 — 표시 조건(UA·display-mode)이 구독 흐름과 독립적으로 검증 가능해서다.

---

## 4. PR-1 — 설치형 셸 (FE 만)

### 4.1 REQ-001 Manifest

`apps/web/src/app/manifest.ts` (Next 메타데이터 라우트 → `/manifest.webmanifest`).

| 필드 | 값 | 근거 |
|---|---|---|
| `id` | `"/"` | 나중에 `start_url` 을 바꿔도 설치 앱 정체성이 유지되게 명시 |
| `name` | `"Kairos"` | 설치 대화상자·창 제목 |
| `short_name` | `"Kairos"` | 홈 화면 라벨 (12자 이하) |
| `description` | `"회의, 노트, 자료가 쌓일수록 조직이 똑똑해집니다"` | 기존 `metadata.description` (`app/layout.tsx:22`) |
| `start_url` | `"/dashboard"` | C-12 |
| `scope` | `"/"` | SW scope 와 일치 |
| `display` | `"standalone"` | |
| `background_color` | `"#0A0A0B"` | 스플래시. DESIGN.md Dark Background |
| `theme_color` | `"#0A0A0B"` | C-10 |
| `lang` / `dir` | `"ko"` / `"ltr"` | `<html lang="ko">` |
| `icons` | 192 `any` · 512 `any` · 512 `maskable` (전부 `image/png`) | REQ-002 |
| `orientation` · `shortcuts` · `screenshots` | **두지 않는다** | 비범위 (BL-PWA-11) |

- `proxy.ts` matcher 의 부정 전방탐색에 `manifest\\.webmanifest$` 를 **추가만** 한다. 다른 항목은 건드리지 않는다.
  - 전방탐색은 경로 맨 앞(`/` 다음)에서 평가되므로 `/manifest.webmanifest` 만 빠지고 `/x/manifest.webmanifest` 는 계속 보호된다 → T-PWA-05 로 고정.
- 비로그인 `start_url` 동작: `/dashboard` → proxy 307 → `/sign-in?callbackURL=%2Fdashboard` → 로그인 성공 → `sanitizeCallbackURL` 이 `/dashboard` 로 보낸다 (`features/auth/callback-url.ts:18-29`). 이미 있는 동작이며 T-PWA-04 가 Location 을 고정한다.

### 4.2 REQ-002 아이콘

| 파일 (레포 경로) | 크기 | 용도 | 시안 실측 (2026-10-02) |
|---|---|---|---|
| `apps/web/public/icons/icon-192.png` | 192×192 | manifest `any` | 글리프 높이 54.7%, 불투명 (colortype 2) |
| `apps/web/public/icons/icon-512.png` | 512×512 | manifest `any` | 글리프 높이 54.3% |
| `apps/web/public/icons/icon-maskable-512.png` | 512×512 | manifest `maskable` | 글리프 높이 44.1%, **중심에서 글리프 최원 픽셀까지 0.282×S ≤ 안전영역 반지름 0.40×S** |
| `apps/web/public/icons/apple-touch-icon.png` | 180×180 | `<link rel="apple-touch-icon">` | 풀블리드 불투명 (iOS 가 모서리를 깎는다) |
| `apps/web/src/app/favicon.ico` (교체) | 16·32·48 다중 | 탭 아이콘 | 32px 시안 글리프 높이 78% — 16px 에서도 K 로 읽힘 (미리보기 시트) |

- 사양: 'K' 단일 글자, Satoshi 700, 글자 `#3ECFB4`, 배경 `#0A0A0B` 풀블리드, 글리프 bbox 중심 = 캔버스 중심. maskable 의 44% 는 "마스크(지름 80%)로 잘린 뒤 보이는 비율이 `any` 의 54% 와 같아지게" 고른 값이다.
- 시안 파일: scratchpad `icon-proof/` (`icon-192.png`·`icon-512.png`·`icon-maskable-512.png`·`apple-touch-icon.png`·`favicon-32.png`·`preview-sheet.png`). **게이트 ③ 승인 (2026-10-02) — PR-1 구현 라운드에서 레포에 넣는다.**
- **Next 아이콘 파일 컨벤션(`app/icon.png`·`app/apple-icon.png`)을 쓰지 않는다.** 번들 문서상 그 href 가 `/apple-icon?<generated>` 처럼 확장자 없는 경로일 수 있어(`node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/01-metadata/app-icons.md:49-60`) proxy matcher 의 `.png$` 제외에 걸리지 않고 로그인 리다이렉트될 수 있다 [가정 — 실제 출력은 미확인]. `public/icons/*.png` + `metadata.icons.apple` 로 경로를 확정한다. `favicon.ico` 는 경로가 고정(`/favicon.ico`)이고 matcher 가 이미 제외한다 (`proxy.ts:55`).
- `favicon.ico` 생성은 PNG 를 담은 ICO(16/32/48)로 한다 — 외부 도구 의존 없이 스크립트로 만들 수 있다. `favicon.ico` 도 K 로 교체한다 (게이트 ③ 확정).
- ★ICO 안의 PNG 항목은 **RGBA(colortype 6, 8bit)** 여야 한다 — Turbopack 의 ICO 디코더가 RGB(colortype 2) 항목이면 `next build` 를 "Format error decoding Ico: The PNG is not in RGBA format!" 로 실패시킨다 [사실 — 2026-10-02 오케스트레이터 `NEXT_PUBLIC_PWA_SW=off mise run fe-build` 빌드 로그 실측]. 불투명 그대로 alpha=255 를 붙인다. `public/icons/*.png` 는 Next 가 디코드하지 않는 정적 파일이라 colortype 2 그대로 둔다. 빌드 없는 가드: vitest `lib/pwa/__tests__/favicon.test.ts`.
  - 현재 파일 [사실]: 25931 B, sha256 `2b8ad2d3…775932`, ICO 항목 4개 (16·32·48 = BMP, 256 = PNG) — create-next-app 기본값. 교체 판정은 T-PWA-03 (해시 불일치 + 16·32·48 PNG 항목).

### 4.3 REQ-003 viewport · theme-color · appleWebApp · safe-area

root `app/layout.tsx` 에:

```ts
export const viewport: Viewport = { themeColor: "#0A0A0B", viewportFit: "cover" };
// metadata 에 추가
appleWebApp: { capable: true, title: "Kairos", statusBarStyle: "default" },
icons: { apple: "/icons/apple-touch-icon.png" },
```

- 출력 기대값 (`metadata.js:211-212`, `generate-metadata.md:779-820` 로 확인): `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">` · `<meta name="theme-color" content="#0A0A0B">` 1개 · `<meta name="mobile-web-app-capable" content="yes">` · `<meta name="apple-mobile-web-app-title" content="Kairos">` · `<meta name="apple-mobile-web-app-status-bar-style" content="default">` · `<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">`.
- `statusBarStyle` 은 `default` 로 둔다. `black-translucent` 는 웹뷰가 상태바 밑까지 올라가 헤더 상단 safe-area 처리가 추가로 필요하다. `default` 는 웹뷰가 상태바 아래에서 시작해 겹침이 없다고 본다 [가정 — iOS 실기기 T-PWA-17 로 확인]. 상태바 색이 어긋나 보이면 BL-PWA-10 으로 넘긴다.
- safe-area (C-9):
  - `globals.css` `--bottom-nav-height: calc(56px + env(safe-area-inset-bottom, 0px));`
  - `bottom-nav.tsx` `<nav>` style 에 `paddingBottom: "env(safe-area-inset-bottom, 0px)"` — Tailwind preflight 의 `box-sizing: border-box` 로 아이콘 영역 56px 유지.
  - 나머지 소비처 3곳은 토큰을 그대로 쓰므로 수정하지 않는다.
  - `env()` 값은 `viewport-fit=cover` 가 있어야 0 이 아니다. Chromium(데스크톱·모바일 에뮬레이션)은 0 → 기존 56px 단언 유지.
  - **가로 모드 회귀 방지**: `viewport-fit=cover` 를 켜면 iOS Safari 가로 모드에서 콘텐츠가 노치·홈 인디케이터 쪽 좌우 끝까지 그려진다. `globals.css` `@layer base` 의 `body` 에 `padding-left: env(safe-area-inset-left, 0px); padding-right: env(safe-area-inset-right, 0px);` 를 넣는다 [WebKit 동작 기반, 실기기 미확인 — T-PWA-17]. Chromium 은 inset 0 → 레이아웃 영향 없음 (기존 e2e 단언 불변).
  - body padding 은 `position: fixed` 요소(하단 nav 좌우·피드백 버튼·`CaptureSheet`)에는 적용되지 않는다. 그 좌우 inset 과 `CaptureSheet`(`features/memory/components/CaptureSheet.tsx:68`, `p-6` 24px < 홈 인디케이터) 하단 inset 은 이번 범위가 아니다 → BL-PWA-8.

### 4.4 REQ-004 Service Worker + SCR-001 오프라인 화면

**등록 (페이지 쪽)** — `'use client'` 컴포넌트 1개를 root layout `<body>` 에 둔다 (null 렌더). 제안 경로 `apps/web/src/components/layout/service-worker-registrar.tsx`, worker 엔트리 `apps/web/src/lib/pwa/sw.ts`.

| 조건 | 동작 |
|---|---|
| `!('serviceWorker' in navigator)` 또는 `!window.isSecureContext` | 아무것도 안 함 (운영 http 평문 접속 포함 — R-4) |
| 모드 = `unregister` (REQ-005) | `getRegistrations()` 전부 `unregister()` |
| 모드 = `register` | `document.readyState === 'complete'` 면 즉시, 아니면 `window` `load` 1회 리스너 뒤 `register(new URL('../../lib/pwa/sw.ts', import.meta.url), { scope: '/', updateViaCache: 'none' })`. 실패는 `console.warn` 1줄 (error 아님 — 앱 기능과 무관) |

- 호출부는 레포 전체에서 정확히 1곳 (C-3). URL·옵션은 리터럴.
- **`register()` 결과를 역참조하지 않는다** (`reg.update()`·`reg.scope` 등 금지) — Playwright `serviceWorkers: 'block'` 에서는 `undefined` 로 resolve 한다 (C-26). 등록 상태가 필요한 코드는 `getRegistration()` 으로 따로 조회한다 (§5.5).
- `load` 이후 등록 = hydration·LCP 경합 방지 (vercel `bundle-defer-third-party` 와 같은 취지).

**worker (`sw.ts`)**

| 이벤트 | 동작 |
|---|---|
| `install` | `self.skipWaiting()` |
| `activate` | `clients.claim()` 만. **`navigationPreload` 를 켜지 않는다** (C-23) |
| `fetch` | 아래 조건을 **모두** 만족할 때만 `respondWith`: `request.mode === 'navigate'` · `request.method === 'GET'` · URL origin = `self.location.origin` · pathname 이 `/api/` 로 시작하지 않음. 그 외에는 `respondWith` 를 부르지 않는다 (브라우저 기본 처리) |
| `respondWith` 내부 | `fetch(event.request)` 1회. `event.preloadResponse` 는 읽지 않는다. **reject(네트워크 실패)일 때만** SCR-001 응답. 서버가 준 응답은 상태코드와 무관하게 그대로 반환 (5xx·3xx 마스킹 금지) |

- `skipWaiting`+`claim` 근거: 캐시가 없으므로 페이지와 SW 간 버전 불일치로 깨질 자산이 없다 → 수정본이 다음 내비게이션에 즉시 반영되는 쪽이 고착 리스크(R-2)를 줄인다.
- `/api/*` 제외 근거: Better Auth OAuth 콜백(`/api/auth/callback/*`) 같은 내비게이션은 쿠키 설정을 동반한다 — SW 를 거치게 할 이유가 없다.
- **navigationPreload 미사용 근거 (C-23)**: preload 는 SW 의 `respondWith` 여부와 무관하게 모든 내비게이션에 별도 요청을 하나 더 보낸다. 실측 — 오케스트레이터 `navpreload.mjs` 에서 preload ON 이면 `/api/auth/callback/google?code=ONE_TIME` 서버 도달 2회, OFF 면 1회. 일회용 OAuth `code` 가 두 번 소비되면 로그인이 깨진다. 캐시가 없는 SW 라 preload 로 얻을 지연 이득도 없다. 수용 기준 = `/api/*` 내비게이션 서버 도달 정확히 1회 (T-PWA-13, 브라우저 테스트).
- Next 클라이언트 라우터의 RSC 요청은 `navigate` 가 아니라 가로채지 않는다. 오프라인에서 `<Link>` 를 누르면 Next 가 하드 내비게이션으로 폴백해 SCR-001 이 뜬다고 본다 [가정 — 별도 측정 T-PWA-23. 실측 `console.error` 2종 3건 — `Failed to load resource` ×2 (발생 URL `/sign-up?_rsc=`, 테스트가 abort 한 RSC fetch) + `Failed to fetch RSC payload` ×1 — 그 테스트에서만 허용한다 (test-matrix 허용 콘솔 목록)].
- **Cache Storage · IndexedDB 를 열지 않는다.** `caches.open` / `indexedDB.open` 호출 0 (코드 grep + T-PWA-10).
- 핸들러 로직은 vitest 로 단위 검증 가능하게 순수 함수로 분리한다 (예: `shouldHandle(request, origin)` · `handleNavigation(request, fetchFn)`). 정확한 파일 분할은 구현 라운드에 맡긴다.
- `sw.ts` 타입: `ServiceWorkerGlobalScope` 를 쓰려면 `webworker` lib 가 필요한데 현 tsconfig 는 `dom` 만 쓴다 (`apps/web/tsconfig.json:4`). `any` 없이 `tsc --noEmit` 0 errors 가 수용 기준이다 (R-14).

**SCR-001 오프라인 화면** — SW 코드 안의 문자열 상수로 든 HTML 1장. 별도 `/offline` 라우트·precache·캐시 버전 관리 없음.

| 항목 | 값 |
|---|---|
| 응답 | status **`200`**, `Content-Type: text/html; charset=utf-8`, `Cache-Control: no-store` |
| 문서 | `<html lang="ko">`, `<title>오프라인 — Kairos</title>`, viewport meta, `<meta name="theme-color" content="#0A0A0B">`, `<link rel="icon" href="data:image/svg+xml,…">` 정확히 1개 (K 모노그램 축약 SVG — 글자 `#3ECFB4` / 배경 `#0A0A0B`, sans-serif bold, `encodeURIComponent` 인코딩) |
| 본문 | `<main data-testid="offline-screen">` — 'K' 마크(accent) · 제목 "인터넷에 연결되어 있지 않아요" · 설명 "연결되면 자동으로 다시 불러옵니다. 오프라인에서는 회의·노트를 볼 수 없어요." · 버튼 "다시 시도" (`data-testid="offline-retry"`, `location.reload()`) |
| 동작 | `window` `online` 이벤트 시 자동 `location.reload()` (지연·재시도 없음). 한계 [가정 — 미측정]: 네트워크는 연결됐지만 아직 라우팅되지 않는 순간에 `online` 이 오면 그 reload 도 실패해 다시 SCR-001 이 뜬다 → 사용자가 "다시 시도" 를 누른다 |
| 스타일 | 인라인 CSS, DESIGN.md Dark 토큰 hex 고정 — bg `#0A0A0B`, surface `#141416`, border `#2A2A2E`, text `#EDEDEF`/`#8E8E93`, accent `#3ECFB4`, radius 6px, 버튼 높이 36px. 폰트는 오프라인이라 CDN 을 못 쓰므로 시스템 스택(`-apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Pretendard", sans-serif`) |
| 테마 | dark 고정 (앱 기본, C-10) |
| 외부 요청 | 0 (이미지·폰트·스크립트 파일 없음, 인라인만 — 아이콘도 `data:` URL) |

- status 200 근거 (C-24): 503 이면 Chromium 이 페이지 콘솔에 `console.error` 1건을 남겨 `AGENTS.md` §4 증거 표준("console.error 0건")과 충돌한다. `no-store` 라 브라우저·중간 캐시가 이 응답을 실제 페이지로 저장하지 않는다. 오프라인 판별은 상태코드가 아니라 `data-testid="offline-screen"` 으로 한다.
- ★"200 이면 리소스 로드 실패 error 0" 은 **headless 에서만** 맞다 [사실 — EVAL-IMPL-1 MCP Chrome 154·browser-use 관찰, 2026-10-02]: headed(실제) Chrome 은 아이콘 선언이 없는 문서를 그릴 때마다 `/favicon.ico` 를 요청하고, 오프라인이라 `console.error` 1건이 남는다. Playwright 번들 chromium-headless-shell 147 만 favicon 을 요청하지 않아 T-PWA-11 이 못 잡는다 (Chrome 154 headless 는 요청한다 — EVAL-IMPL-2) → SCR-001 은 `data:` 아이콘을 문서 안에 선언한다 (위 '문서' 행, vitest T-PWA-12 가 정확히 1개를 단언).

### 4.5 REQ-005 kill-switch · dev

| 빌드 | 페이지 registrar | sw.js |
|---|---|---|
| `NODE_ENV !== 'production'` (dev) | **unregister 모드** — 등록 안 함 + 기존 등록 해제 | (dev 에선 등록되지 않음) |
| prod + `NEXT_PUBLIC_PWA_SW === 'off'` | unregister 모드 | 기본 빌드와 같다 (§4.4) — worker 번들은 빌드 플래그를 읽지 못한다 (C-28). 등록 호출 참조가 남아 같은 URL 로 산출되므로 404 는 나지 않는다 |
| prod (기본) | register 모드 | §4.4 |

- dev 에서 기존 등록을 해제하는 근거: 같은 origin(:3003 등)에서 한 번이라도 prod 빌드를 띄웠다면 그 SW 가 dev 내비게이션을 계속 가로챈다. 해제 비용은 `getRegistrations()` 1회(대개 빈 배열)다.
- 열린 창 강제 이동을 하지 않는 근거: 해제 뒤에도 열린 창의 controller 는 남지만(C-27) Cache Storage 없는 통과형이라 요청은 네트워크로 그대로 가고, 다음 내비게이션부터 제어되지 않는다 [사실 — C-27, `eval-spec2/unreg.mjs`]. 강제 `navigate()` 는 작성 중인 입력을 날린다.
- kill-switch 가 페이지 쪽만으로 충분한 근거: SW 는 Cache Storage 가 없는 통과형이라 kill 빌드 배포 뒤 다음 내비게이션에서 새 페이지 JS 가 항상 내려오고, registrar 가 `getRegistrations()` → 전부 `unregister()` 한다.
- ★한계 [사실 — C-28]: sw.js 가 스스로 내려가는 보조 안전망은 없다 (worker 번들이 빌드 플래그를 못 읽는다). SW 자체 버그(예: 온라인인데 오프라인 HTML 반환)로 페이지 JS 가 못 뜨면 kill-switch 가 닿지 않는다 → 복구는 **수정한 `sw.ts` 배포**다 (sw.js 바이트 변경 → `updateViaCache: 'none'` + `max-age=0` 로 내비게이션마다 업데이트 확인 → `skipWaiting`+`claim` 으로 즉시 교체).
- 플래그 배선: `apps/web/Dockerfile` ARG/ENV 1줄씩 · `.github/workflows/release.yml` build-args 1줄 (평소 CI 빌드, repo Variables) · `mise.toml` 맥 비상 빌드 `--build-arg` 1줄 · `deploy/oci/build.env.example` 1줄. 비상시 운영자는 repo Variables 에 `NEXT_PUBLIC_PWA_SW=off` 를 넣고 main 에 새 커밋 → 새 sha 태그로 `deploy-ship` 한다 (코드 변경 없음. 같은 sha 는 태그가 이미 있어 빌드를 건너뛴다. 절차 원문 `deploy/oci/build.env.example`).
- PR-2 이후 unregister 는 그 등록에 묶인 푸시 구독도 함께 없앤다 (서버 행은 다음 앱 로드 동기화의 API-003 — 표식 일치 시 — 또는 다음 발송의 404/410 에서 정리, §5.5).
- **등록 없음 상태** — 이 origin 에 SW 등록이 하나도 없는 상태. 다음 경우에 생긴다: dev 빌드 · kill-switch 빌드 · `serviceWorker` 미지원 또는 비보안 컨텍스트(R-4) · prod 첫 방문에서 registrar 가 `load` 뒤 등록을 마치기 전. 이 상태에서 `navigator.serviceWorker.ready` 는 **영원히 resolve 되지 않는다** → 앱 코드는 `ready` 를 기다리지 않고 `navigator.serviceWorker.getRegistration()`(즉시 `undefined` 로 resolve) 으로만 조회한다 (§5.5).

### 4.6 PR-1 변경 파일 (제안)

`app/manifest.ts`(신규) · `app/layout.tsx`(viewport·metadata·registrar) · `proxy.ts`(matcher 1항목) · `app/globals.css`(토큰 1줄 + body 좌우 safe-area padding) · `components/layout/bottom-nav.tsx`(padding 1줄) · `components/layout/service-worker-registrar.tsx`(신규) · `lib/pwa/sw.ts`(+순수 로직·오프라인 HTML 파일, 신규) · `public/icons/*.png` 4장 · `app/favicon.ico`(교체) · `e2e/tests/pwa.spec.ts`(신규) · `playwright.config.ts`(public-only testMatch + chromium testIgnore) · vitest 파일 · `Dockerfile`·`.github/workflows/release.yml`·`mise.toml`·`deploy/oci/build.env.example`(플래그) · 문서 (§9).

---

## 5. PR-2 — 웹 푸시 (BE + DB + FE)

### 5.1 ENT-001 PushSubscription (`push_subscriptions`)

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| `id` | UUID | PK, default uuid4 | |
| `user_id` | UUID | NOT NULL, FK `users.id` ON DELETE CASCADE, index | 내부 `users.id` (auth_user.id 아님) |
| `endpoint` | TEXT | NOT NULL, **UNIQUE** | 푸시 서비스 capability URL. 로그·응답에 절대 내보내지 않는다 |
| `p256dh` | TEXT | NOT NULL | base64url, 디코드 65바이트 (`0x04` 시작) |
| `auth` | TEXT | NOT NULL | base64url, 디코드 16바이트 |
| `created_at` | timestamp | NOT NULL | 기존 모델 컨벤션을 따른다 (`feedback/models.py:26`) |
| `updated_at` | timestamp | NOT NULL | upsert·rebind 마다 갱신 |

- `workspace_id` 없음 — 사용자 단위 리소스다 (FeedbackEntry 와 같은 위치). B-2(`workspace_id` 필터) 의 예외이며, 대신 **Repository 의 모든 조회·삭제에 `user_id` WHERE 강제** (404/410 정리용 내부 삭제도 `id AND user_id`). 이 예외는 B-16 문구에 명시한다 (§9).
- 키를 평문 저장하는 근거: `applicationServerKey`(VAPID 공개키)로 만든 구독은 우리 VAPID 개인키로 서명한 요청만 받는다 (RFC 8292). endpoint+keys 가 새도 제3자는 발송할 수 없다. 대신 응답·로그에 노출하지 않는다.
- 마이그레이션: 새 테이블 1개, 가산형 (C-20). `down_revision` 은 PR-2 착수 시점 head 를 다시 확인한다 (현재 `b3d5f8a1c2e4`). `alembic/env.py` 에 모델 import 추가.

### 5.2 API (모두 Bearer JWT 필수 — `get_current_user`, I-16 camelCase)

| ID | 메서드 · 경로 | 요청 | 응답 | 상태코드 |
|---|---|---|---|---|
| API-001 | `GET /api/v1/users/me/push-config` | — | `{ "isEnabled": bool, "vapidPublicKey": str \| null }` | 200 · 401 |
| API-002 | `PUT /api/v1/users/me/push-subscriptions` | `{ "endpoint": str, "keys": { "p256dh": str, "auth": str } }` (PushSubscription.toJSON() 의 부분집합) | `{ "id": uuid }` | 200 · 401 · 422 |
| API-003 | `DELETE /api/v1/users/me/push-subscriptions/{subscription_id}` | — | 본문 없음 | 204 · 401 · 422(UUID 형식) |

- API-001: VAPID 3개 설정이 다 있을 때만 `isEnabled=true`. 미설정이어도 200 (FE 가 섹션을 숨긴다). 공개키는 base64url 87자.
- API-002 upsert: `INSERT … ON CONFLICT (endpoint) DO UPDATE SET user_id = EXCLUDED.user_id, p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth, updated_at = now() RETURNING id` 를 `session.execute` 로 (C-19). 같은 endpoint 면 id 가 유지된다 → **같은 기기에서 다른 사용자가 구독하면 그 행이 현재 사용자로 rebind** (서버 백스톱).
  - 검증 (Pydantic, 실패 422): `endpoint` 는 `https` · 포트 없음 또는 443 · userinfo 없음 · IP 리터럴 아님 · 길이 ≤ 2048 · **호스트 allowlist** (정확 일치 또는 접미사): `fcm.googleapis.com`, `android.googleapis.com`, `.push.services.mozilla.com`, `.push.apple.com`, `.notify.windows.com` (Edge/WNS — **미검증**: 호스트 형식·실제 발송 모두 이번에 확인하지 않았다). `p256dh`·`auth` 는 base64url 이고 디코드 길이 65·16.
  - allowlist 근거: 서버가 사용자 입력 URL 로 POST 를 보내는 구조라 없으면 SSRF 다 (예: `https://169.254.169.254/`). 목록 밖 브라우저는 "이 브라우저는 지원하지 않음" 으로 처리된다 [가정 — 주요 브라우저 4종 호스트만 확인. 누락 시 422 로 실패하므로 안전 방향].
- 사용자당 구독 개수 상한은 두지 않는다 — 발송은 업로더 본인의 구독에만 가고, 404/410 정리로 죽은 행이 줄어든다. 상한·축출은 BL-PWA-14.
- API-003: `id AND user_id = 현재 사용자` 일 때만 삭제. 없거나 남의 것이어도 **204** (멱등 + 존재 여부 오라클 차단). endpoint 를 URL 에 넣지 않으려고 id 로 지정한다 (capability URL 이 접근 로그에 남지 않게).
- 경로는 기존 I-13 예외 `/api/v1/users` 안이다 (C-16). CONTEXT-MAP I-13 문구에 `push` 를 예외 소유자로 추가한다 (§9).

### 5.3 REQ-008 발송 시퀀스

```
BackgroundTask (meetings/pipeline_service.py, 오케스트레이터) — process_meeting / capture_text 각각
  outcome = None                                   ← 결과 플래그 (kind 또는 None)
  async with self._session_factory() as session:   (:196, :278 — 파이프라인 세션)
    try:
      … _analyze_and_store 끝: update_status("completed") → commit()   (:185-186)
      outcome = "meeting.completed"                 ← try 끝까지 왔을 때만 (조기 return 이면 None 그대로)
    except:
      rollback → update_status("failed") → commit()                    (:259-269, :318-328)
      outcome = "meeting.failed"                    ← 그 commit 이 성공했을 때만
  # async with 를 빠져나온 뒤 = 파이프라인 세션 close 완료
  if outcome: await self._notify_meeting_finished(meeting_id, workspace_id, outcome)

_notify_meeting_finished  — 전체를 try/except Exception 으로 감싼다 (비치명적). 인자는 원시 값만 (rollback 뒤 만료된 ORM 객체를 건드리지 않는다)
  0. 설정 미구성 → return (info 로그 1줄)
  1. 조회 — 새 짧은 세션 `async with self._session_factory() as s:`
       a. MeetingRepository(s).find_by_id(meeting_id, workspace_id) → recipient = created_by_id (없으면 return)
       b. WorkspaceRepository(s) 로 recipient 가 workspace 멤버인지 확인 → 아니면 return
       c. PushRepository(s).list_by_user(recipient) → (id, endpoint, p256dh, auth) 를 원시 값으로 복사
  2. 트랜잭션 종료 — `async with` 를 빠져나와 세션·연결 반납. 구독 0개면 return
     (발송 동안 열린 DB 세션 0개 — 파이프라인 세션은 호출 전에 이미 닫혔고, 조회 세션도 여기서 닫힌다)
  3. 발송 — aiohttp.ClientSession 1개로 구독별 webpush_async 를 asyncio.gather(return_exceptions=True)
       결과 분류: 성공 / 404·410(정리 대상 id 목록) / 그 외 오류 → warning (상태코드만)
  4. 정리 — 404·410 이 1건 이상일 때만 새 짧은 세션:
       PushRepository(s).delete_by_ids(ids, recipient) → commit   (회의 commit 과 별개 트랜잭션)
```

| 규칙 | 기준 |
|---|---|
| 시점 | 회의 상태 commit **이후**. 발송 실패·지연이 회의 상태에 영향 0 |
| best-effort | 재시도 없음 (BL-PWA-6). 예외는 삼키고 `push_dispatch_failed` warning (예외 타입명만) |
| 수신자 | `created_by_id` 1명. 같은 워크스페이스 다른 멤버·admin 에게도 보내지 않는다 |
| 미발송 | 설정 미구성 · `created_by_id` 없음 · 워크스페이스 비멤버 · 구독 0개 · 실패 상태 commit 자체가 실패 · `meeting is None` 조기 return 경로 |
| DB 사용 | 훅은 파이프라인 세션의 `async with` **밖**에서 부른다 (안쪽 else 절에서 부르면 발송 내내 파이프라인 세션이 열려 있다). 조회·정리는 각각 짧은 세션 1개. 발송(네트워크 대기) 중에는 세션 0개 — 느린 푸시 서비스가 커넥션 풀을 붙잡지 않게 |
| 로그 | endpoint·keys·payload 원문 금지. `meeting_id`·`user_id`·`sent/failed/pruned` 개수만 |
| `webpush_async` 인자 | `ttl=86400` · **`timeout=10` 명시 필수** · `headers={"Urgency": "normal"}` · `vapid_claims={"sub": settings.vapid_subject}` **매 호출 새 dict** · `aiohttp_session` 재사용 |

- 라이브러리: **pywebpush 2.5.0** (PyPI 최신, 2026-08-30). 근거:
  - `webpush_async`(aiohttp) 가 2.1.0(2025-09-29)부터 있다 (CHANGELOG) → `asyncio.to_thread` 불필요 (B-10 100% async 유지).
  - 2.5.0 이 `WebPushException.status_code`·`retry_after` 를 추가해 sync/async 응답 분기가 필요 없다.
  - 기본값 함정 (context7 `/web-push-libs/pywebpush` `_autodocs` + 2.5.0 소스):
    - `ttl` 기본 0 = 기기가 오프라인이면 즉시 폐기.
    - **`timeout` 미지정 = 무제한** [사실]: `webpush_async` 의 시그니처가 `timeout: None | float = None` (`pywebpush/__init__.py:546`) 이고 이 값을 `send_async(..., timeout=timeout)` 로 **명시 전달**한다 (`:645-651`). 그래서 `send_async` 의 `kwargs.pop("timeout", 10000)` 기본값(`:395`)은 쓰이지 않고 `None` 이 `session.post(endpoint, timeout=None)` 까지 간다 (`:406`·`:410`). aiohttp 3.13.5 `_request` 는 sentinel 이 아닌 비-`ClientTimeout` 값을 `ClientTimeout(total=timeout)` 으로 바꾼다 (`aiohttp/client.py:589-595`. `None` 을 기본값으로 바꿔 주는 분기 `:333` 은 `ClientSession.__init__` 에만 있다) → `total=None` = 제한 없음. 요청 단위 값이라 `ClientSession(timeout=…)` 기본값도 덮어쓴다. → 반드시 `timeout=10` 을 넘긴다 (T-PWA-42 가 인자 고정).
    - `vapid_claims` dict 를 라이브러리가 변형(`aud`·`exp` 주입) → 매 호출 새 dict.
  - 의존성: `aiohttp`(이미 lock 에 3.13.5) · `requests` · `http-ece` · `py-vapid` · **`cryptography>=47`** — 현재 lock 은 `cryptography 46.0.6` 이라 상향된다 (R-7). 대안은 `pywebpush==2.3.0` (cryptography 하한 2.6.1) 고정 + `ex.response.status` 직접 사용.
- 모듈 배치: 새 도메인 `apps/api/src/push/` — `models.py · schemas.py · repository.py · service.py · router.py · dependencies.py · exceptions.py · sender.py · CONTEXT.md`. `sender.py` 는 pywebpush 호출만 하는 얇은 래퍼(테스트에서 가짜로 교체). `pipeline_service.py` 가 `PushService` 를 부르는 건 오케스트레이터 경계 안이다 (B-3, 온보딩 훅과 같은 지연 import 패턴 :177-183).

### 5.4 REQ-010 페이로드 + 프라이버시

```json
{ "v": 1, "kind": "meeting.completed", "meetingId": "3f2c…-uuid", "workspaceId": "9a1e…-uuid" }
```

- `kind` ∈ `meeting.completed` · `meeting.failed`. `workspaceId` = `meeting.workspace_id` (uuid, 게이트 ⑥ 확정 — 알림 딥링크의 워크스페이스 전환용). **그 외 필드 없음** — 회의 제목·요약·전사·프로젝트명·워크스페이스명·사용자명 미포함 (게이트 ④ 확정). 두 id 는 식별자일 뿐 내용이 아니고 알림에 표시되지 않는다.
- 표시 문구는 SW 가 `kind` 로 정한다 (서버는 사람이 읽는 문자열을 보내지 않는다):

| kind | title | body |
|---|---|---|
| `meeting.completed` | 회의 처리 완료 | 업로드한 회의의 요약·액션이 준비됐어요. |
| `meeting.failed` | 회의 처리 실패 | 업로드한 회의를 처리하지 못했어요. 눌러서 확인하세요. |
| 그 외/파싱 실패 | Kairos | 새 알림이 있어요. |

- 근거: 잠금화면·알림센터는 기기 주인이 아닌 사람도 본다. 로그아웃 없이 계정이 바뀐 기기(R-10 잔여 창)에서도 노출되는 정보가 "어떤 회의가 끝났다" 수준에 머문다.
- 크기: 직렬화 ≤ 512 바이트 (Web Push 페이로드 한도 4KB 대비 여유).
- `tag = "meeting-" + meetingId` — 같은 회의의 실패→재처리 완료 알림이 하나로 교체된다. `icon = /icons/icon-192.png`, `lang = "ko"`. badge 는 단색 아이콘이 없어 두지 않는다 (BL-PWA-12).

### 5.5 REQ-009 FE 구독·해제·계정 전환 + SW

새 feature `apps/web/src/features/push/` (`api.ts`·`hooks.ts`·`components/`) — F-9 (API 호출은 feature `api.ts` 만), wire 타입은 `types/api.gen.ts` 에서 (I-22).

**소유자 표식** — `localStorage["kairos:push:v1"] = { userId: <users.id>, subscriptionId: <uuid> }`, zod v4 스키마로 파싱 (파싱 실패 = 없음). `userId` 는 `useMe()` 의 내부 id (`apps/web/AGENTS.md:66-69`).
- **표식 삭제는 compare-and-delete** — 흐름 시작 때 읽은 `subscriptionId` 와 지금 저장된 값이 같을 때만 지운다 (그 사이 다른 탭·켜기 흐름이 새 표식을 썼으면 남긴다).
- **API-003 DELETE 는 진행 중 promise 를 공유한다** — 같은 `subscriptionId` 에 대해 앱 로드 동기화와 로그아웃 ① 이 겹치면 요청은 1번만 나가고 둘 다 같은 promise 를 기다린다 (모듈 수준 `Map<subscriptionId, Promise>`).

**SW 등록 조회 규칙** — 모든 흐름은 `navigator.serviceWorker.getRegistration()` 1회로 등록을 얻는다. **`navigator.serviceWorker.ready` 를 await 하지 않는다** — 등록 없음 상태(§4.5: dev · kill-switch · 미지원/비보안 · 첫 방문 등록 전)에서는 resolve 되지 않아 로그아웃·설정 화면이 멈춘다. 결과가 `undefined` 면 "등록 없음" 으로 처리한다 (푸시 구독은 등록에 묶이므로 등록이 없으면 이 기기의 구독도 없다).

| 흐름 | 동작 | 수용 기준 |
|---|---|---|
| 켜기 (SCR-002 토글 클릭) | `getRegistration()` → `undefined` 면 '사용 불가' 상태로 전환하고 종료. 있으면 `Notification.requestPermission()` → `granted` 면 `registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey })` → API-002 → 표식 저장. 기존 구독의 `applicationServerKey` 가 현재 공개키와 다르면 먼저 `unsubscribe()` | 권한 요청은 **사용자 클릭 핸들러 안에서만** (페이지 로드 시 0회). `denied` 면 안내 문구 + 토글 비활성 |
| 끄기 | API-003 → (등록 있으면) `unsubscribe()` → 표식 삭제 | 3단계 모두 best-effort, 실패해도 UI 는 꺼짐 |
| 앱 로드 동기화 (`(app)` 셸, 페이지 로드당 1회, `me` 로드 후) | `getRegistration()` → **등록 없음**: 표식 userId == me.id → API-003 (best-effort, 타임아웃 3초) 후 표식 삭제 — kill-switch 등으로 등록만 사라진 경우의 서버 행 정리 · 표식 불일치(또는 없음) → 서버 호출 없이 표식만 삭제. **등록 있음**: 구독 있음 + 표식 userId == me.id → API-002 재전송 (브라우저의 endpoint 교체·서버 행 유실 복구) · 구독 있음 + (표식 없음 또는 불일치) → **`unsubscribe()` 만** (fail-closed, 서버 호출 없음) · 구독 없음 → 표식 삭제 | 불일치 시 PUT 0회. 등록 없음 + 표식 일치 → DELETE 1회 후 표식 삭제 (실패해도 삭제). 등록 없음 + 표식 불일치·없음 → 네트워크 0회 |
| 로그아웃 (`header.tsx:164-176`) | **기존 순서 앞에** ① 표식이 있으면 그 id 로 API-003 (타임아웃 3초 — 등록이 없어도 보낸다: 앱 로드 동기화가 정리하지 못한 잔여, 예컨대 같은 로드 중 kill-switch 로 등록이 사라진 경우) ② `getRegistration()` → 있으면 `pushManager.getSubscription()` → `unsubscribe()`, 없으면 건너뜀 ③ 표식 삭제 → 이후 기존 `queryClient.clear()` → `clearAuthTokenCache()` → `signOut()` | 네트워크 로그상 `DELETE …/push-subscriptions/{id}` 가 `POST /api/auth/sign-out` 보다 앞. 실패·오프라인·**등록 없음**이어도 로그아웃은 대기 없이 진행 (추가 지연 ≤ 3초, `ready` 대기 0) |

- 결과: **로그아웃하면 그 기기의 푸시가 꺼진다.** 같은 사용자가 다시 로그인해도 설정에서 다시 켜야 한다 (게이트 ⑦ 확정). 브라우저 알림 권한은 origin 단위라 사용자를 구분하지 못하므로, 자동 재구독은 다음 사용자를 동의 없이 구독시킨다.
- 로그아웃 없이 다른 계정으로 로그인된 경우(세션 만료 등): 앱 로드 동기화의 표식 불일치 분기가 로컬 구독을 끊는다. 서버의 옛 행은 다음 발송의 404/410 에서 정리된다 [가정 — 푸시 서비스가 unsubscribe 된 endpoint 에 404/410 을 준다].
- kill-switch·수동 해제로 등록만 사라진 경우: 다음 앱 로드 동기화가 표식 일치면 API-003 으로 서버 행을 바로 지운다 (404/410 을 기다리지 않는다). 같은 로드 안에서 등록이 사라져 동기화가 놓친 잔여는 로그아웃 ① 이 지운다.
- `pushsubscriptionchange` 는 처리하지 않는다 — SW 에는 인증 토큰이 없다. 앱 로드 동기화가 대신한다 (BL-PWA-9).

**알림 딥링크 워크스페이스 전환 (게이트 ⑥ 확정)** — 회의 상세(`app/(app)/meetings/[id]/page.tsx` → `MeetingDetail`) 진입 시 `?workspace=<wid>` 를 1회 처리한다. 로직은 전환 규칙의 주인인 `features/workspaces` 에 훅 1개로 둔다. 무효화 predicate 는 `WorkspaceSwitcher.tsx:44-56` 의 `invalidateWorkspaceScopedQueries` 를 같은 feature 의 함수로 추출해 둘이 공유한다 (복제 금지).

| 조건 | 동작 | 수용 기준 |
|---|---|---|
| 파라미터 없음 | 아무것도 안 함 | 전환 0 · `router.replace` 0 |
| 비UUID | 전환 없이 파라미터만 제거 | 전환 0 · `router.replace("/meetings/<mid>")` 1회 |
| 워크스페이스 목록 로딩 중 | 대기 (`useWorkspaceIdGuard(wid)` 의 `isWorkspaceListPending`, `features/workspaces/hooks.ts:28-42`) | 대기 중 전환·제거 0 |
| `me` 로딩 중 · 활성 ws 가 아직 무효 (`null` 또는 목록에 없음 — `panel-layout.tsx:76-93` self-heal 대기) | 대기 — 활성 ws 가 목록 안의 값으로 정착한 뒤에만 판정 | 대기 중 전환·제거 0. 근거: 자식(상세)의 전환 effect 뒤 같은 커밋에서 부모 self-heal 이 낡은 클로저로 `workspaces[0]` 을 덮어쓴다 (scratchpad `eval-spec3/deeplink-selfheal-race.cjs` S2~S4) |
| `wid` == 활성 워크스페이스 | 전환 없이 파라미터만 제거 | 전환 0 · `router.replace` 1회 |
| 멤버 (`isValidWorkspaceId`) 이고 활성과 다름 | 1회 전환 = store 에 소유자가 있으면(`ownerUserId === me.id`) `setActiveWorkspaceId(wid)`, 없거나 다르면 `activateWorkspaceForUser(me.id, wid)` (C-001) → 추출한 predicate 로 `invalidateQueries` → toast 1회 `“<ws명>” 워크스페이스로 전환했습니다` (self-heal 과 같은 `toast()` 방식, `panel-layout.tsx:86-89`) → `router.replace("/meetings/<mid>")` | 전환 정확히 1회 (재렌더·목록 refetch 에도 추가 0 — ref 가드) · toast 정확히 1회 · `["workspaces","list"]` 쿼리는 무효화 대상 밖 · **`queryClient.clear()` 0회** · `router.refresh()` 0회 (Sprint 23 D1) · 히스토리 항목 추가 0 (`replace`) |
| 비멤버 | 전환 없이 파라미터만 제거 → 기존 상세 오류 블록 (일반 문구 "회의 데이터를 불러올 수 없습니다…", `meeting-detail.tsx:148-156`) | 전환 0 · toast 0 · `router.replace` 1회 |

- 파라미터 처리 전에는 상세 쿼리를 옛 활성 워크스페이스로 보내지 않는다 — 옛 wid 로 오류 블록을 한 번 그리는 깜빡임 방지. 쿼리 `enabled` 게이트만 두면 `isLoading=false` 라 `meeting-detail.tsx:145-148` 이 오류 블록을 그리므로, **처리 전에는 `isPending` 기준으로 스켈레톤**(`MeetingDetailSkeleton`)을 그린다. 오류 블록에는 `data-testid="meeting-detail-error"` 를 붙인다 (T-PWA-59 가 미출현을 단언).

**SW 추가 핸들러 (`sw.ts`)**

| 이벤트 | 동작 |
|---|---|
| `push` | `event.data?.json()` 을 타입 가드로 검증 (`v===1`, `kind` 화이트리스트, `meetingId` UUID 정규식). 통과 → §5.4 문구 + `data.url = "/meetings/" + meetingId`, `workspaceId` 도 UUID 정규식을 통과하면 `+ "?workspace=" + workspaceId` (비UUID·누락이면 쿼리 없이) (**URL 은 SW 가 UUID 로 조립 — 서버 문자열을 URL 로 쓰지 않는다**). 실패 → 일반 알림 + `data.url="/dashboard"`. 항상 `showNotification` 1회 (`userVisibleOnly`) |
| `notificationclick` | `close()` → `new URL(data.url, self.location.origin)` 의 origin 이 같고 pathname 이 `/meetings/<uuid>` 또는 `/dashboard` 가 아니면 `/dashboard` 로 대체 (open redirect 방지, defense in depth). 쿼리는 `/meetings/<uuid>` 의 `workspace=<uuid>` 1개만 남기고 나머지 쿼리·hash 는 제거한다. 같은 origin 창이 있으면 `focus()` + `navigate()` (실패 시 `openWindow`), 없으면 `clients.openWindow()` |

### 5.6 SCR-002 알림 설정 + REQ-011 iOS 설치 안내

- 위치: `/settings` 에 새 탭 `notifications` ("알림") — 역할 무관 노출. "이 기기·이 계정에만 적용" 캡션 (게이트 ⑤ 확정). API-001 `isEnabled=false` 면 탭 자체를 숨긴다.
- 상태: 로딩 · **사용 불가**("이 브라우저·환경에서는 알림을 켤 수 없어요" — `PushManager`/`Notification` 미지원 **또는** SW 등록 없음) · iOS 비설치(REQ-011 안내) · 꺼짐 · 켜짐 · 권한 거부("브라우저 설정에서 이 사이트의 알림을 허용해 주세요") · 오류(토스트 + 토글 원복).
- 등록 없음을 탭 숨김이 아니라 '사용 불가' 상태로 둔 근거: 탭 목록은 서버 값(API-001) 하나에만 의존하게 두고, 클라이언트 비동기 조건은 기존 미지원 상태 하나로 합쳐 상태 수를 늘리지 않는다.
- 상태 판정: 마운트 시 `getRegistration()` 1회. 등록 없음이면 '사용 불가' 로 두고 `navigator.serviceWorker` 의 `controllerchange` 1회 리스너로 재판정한다 — prod 첫 방문에서 registrar 가 `load` 뒤 등록하고 `clients.claim()` 하면 이 이벤트가 온다. dev·kill-switch 에선 이벤트가 오지 않아 '사용 불가' 로 남는다.
- 설명 문구: "업로드한 회의의 처리가 끝나거나 실패하면 이 기기로 알려드려요."
- `data-testid`: `push-settings` · `push-toggle` · `push-status` · `ios-install-hint`.
- REQ-011 표시 조건: (`/iPad|iPhone|iPod/` UA 또는 `platform==='MacIntel' && maxTouchPoints>1`) **그리고** (`navigator.standalone !== true` 그리고 `!matchMedia('(display-mode: standalone)').matches`). 문구: "iPhone·iPad 는 홈 화면에 추가한 Kairos 에서만 알림을 받을 수 있어요 (iOS 16.4 이상). Safari 공유 버튼 → '홈 화면에 추가' 후 그 앱에서 알림을 켜 주세요." 근거: Next 번들 문서 `progressive-web-apps.md:88` (iOS 16.4+ 는 홈 화면 앱에서만).
- 커스텀 설치 버튼(`beforeinstallprompt`)은 만들지 않는다 — 번들 문서가 비권장 (`progressive-web-apps.md:597`, Safari iOS 미동작) → BL-PWA-1.

### 5.7 설정 · 배포

| 키 (`core/config.py`) | 타입 | 기본 |
|---|---|---|
| `vapid_public_key` | `str \| None` | None |
| `vapid_private_key` | `SecretStr \| None` (B-11) | None |
| `vapid_subject` | `str \| None` (`mailto:` 또는 `https:`) | None |

- 셋 다 있어야 활성. 형식 오류는 **warn-only** (부팅 차단 금지, C-18). CI fake env 추가 불필요.
- 키 형식(raw base64url vs DER/PEM)은 구현 라운드에서 생성 명령과 함께 확정하고, pytest 로 "설정 키로 서명 → 공개키로 검증" 왕복을 고정한다 [가정 — py_vapid 가 raw base64url 을 받는지 미확인].
- 런타임 env 다 (build.env 아님): `deploy/oci/.env.example` 에 3줄 추가. 운영 서버 `.env` 반영은 사용자 실행 (SSH).

### 5.8 PR-2 변경 파일 (제안)

BE: `src/push/*` (신규) · `src/main.py` (router) · `src/core/config.py` (3필드) · `src/meetings/pipeline_service.py` (훅 2곳) · `alembic/versions/<new>.py` · `alembic/env.py` · `pyproject.toml`/`uv.lock` · `tests/push/*`. 계약: `contracts/openapi/v1/openapi.json` · `apps/web/src/types/api.gen.ts` (`mise run contracts`). FE: `features/push/*` (신규) · `lib/pwa/sw.ts` (push·click) · `features/workspaces/*` (딥링크 전환 훅 + 무효화 predicate 추출, `WorkspaceSwitcher.tsx` 가 추출 함수 사용) · `features/meetings/components/meeting-detail*` (훅 마운트 + 처리 전 쿼리 게이트) · `app/(app)/settings/page.tsx` (탭) · `components/layout/header.tsx` (로그아웃 앞단) · `(app)` 셸 동기화 마운트 · e2e·vitest. 운영: `deploy/oci/.env.example`. 문서 (§9).

---

## 6. 비범위 (REQ-006) + BL 후보

| BL | 내용 | 비범위 근거 | 등재 PR |
|---|---|---|---|
| BL-PWA-1 | 커스텀 설치 버튼 (`beforeinstallprompt`) | Next 번들 문서 비권장 — 크로스 브라우저 아님, Safari iOS 미동작 (`progressive-web-apps.md:597`) | 1 |
| BL-PWA-2 | 오프라인 배너 (`next/offline` `useOffline` — experimental) | SCR-001 이 대신 (게이트 ① 확정). `use-offline.md` 는 experimental 플래그 필요 | 1 |
| BL-PWA-3 | 오프라인 데이터 읽기 (회의·노트 캐시) | I-9/I-23/I-24 + revocation 즉시성 (C-4). 하려면 별도 ADR | 1 |
| BL-PWA-4 | 추가 푸시 이벤트 — 메모 변환 완료 · 액션 담당자 지정 · 초대 · Drive 동기화 완료/실패 | 사용자 결정 (§1) | 2 |
| BL-PWA-5 | 알림 설정 세분화 (이벤트별 on/off · 방해 금지 시간) | 이벤트가 2종뿐 | 2 |
| BL-PWA-6 | 발송 재시도 (429/5xx `Retry-After`) | best-effort 1회로 시작 | 2 |
| BL-PWA-7 | 앱이 포커스된 동안 시스템 알림 억제 | 결정적 동작 우선 (항상 표시) | 2 |
| BL-PWA-8 | `position: fixed` 요소(하단 nav·피드백 버튼·`CaptureSheet`)의 가로 모드 좌우 safe-area · `CaptureSheet` 하단 safe-area | 이번 범위는 하단 nav 하단 inset + body 좌우 padding (§4.3) | 1 |
| BL-PWA-9 | SW `pushsubscriptionchange` 처리 | SW 에 인증 토큰 없음 — 앱 로드 동기화로 대체 | 2 |
| BL-PWA-10 | 라이트 테마·랜딩용 동적 `theme-color` · iOS 상태바 스타일 재검토 | 단일값으로 시작 (C-10) | 1 |
| BL-PWA-11 | manifest `shortcuts`·`screenshots`·iOS 스플래시(`apple-touch-startup-image`) | 설치 최소 요건 밖 | 1 |
| BL-PWA-12 | Android 단색 badge 아이콘 | 시안 없음 | 2 |
| BL-PWA-13 | mise task `fe-security-headers` 명칭 정리 (PWA spec 도 이 task 로 돈다) | 명칭만의 문제, CI 문자 동일 규약상 별도 PR. 낡은 **설명 문구**(mise `description` · `test.yml:122` 주석 · `testing.md` §1 표·§4 · `apps/web/README.md` project 목록)는 PR-1 에서 해소. 남은 것: task **이름** · CI step 이름 · 코드 주석 2곳(`test.yml:121` · `playwright.config.ts:72-73` — 아직 "보안 헤더" 만 적음) | 1 |
| BL-PWA-14 | 사용자당 푸시 구독 개수 상한 + 오래된 순 축출 | 발송 대상이 업로더 본인뿐이고 404/410 정리가 있어 증폭 위험이 작다. 실제 행 수가 늘면 도입 | 2 |

## 7. 리스크

| # | 리스크 | 영향 | 대응 |
|---|---|---|---|
| R-1 | CI `public-only` 가 브라우저 렌더를 한 적이 없다 (C-7) | SW 등록·오프라인 e2e 가 CI 에서 `ERR_NAME_NOT_RESOLVED` 로 실패할 수 있음 | `pwa.spec.ts` 를 **request 그룹(CI 필수)** 과 **browser 그룹** 으로 나눈다. draft PR CI spike 로 browser 그룹 판정. 실패 시 browser 그룹은 로컬 게이트(`mise run fe-security-headers 3005`) 증거로 대체하고 CI 에선 `test.skip` + 사유 주석 |
| R-2 | SW 고착 (잘못된 SW 가 내비게이션을 망가뜨림) | 사용자가 앱을 못 엶 | Cache Storage 미사용 · navigate 만 처리 · 네트워크 실패에만 개입 · `skipWaiting`+`claim` · kill-switch = 페이지 쪽 unregister (§4.5). ★한계 [사실 — C-28]: sw.js 자가 해제가 없어, SW 자체 버그로 페이지 JS 가 못 뜨면 kill-switch 가 닿지 않는다 → 복구는 수정한 `sw.ts` 배포 (바이트 변경 → 업데이트 확인 → `skipWaiting`+`claim`). **`deploy-rollback`(구 이미지)으로는 SW 가 내려가지 않는다** — 구 이미지엔 sw.js 가 없어 404 → `update()` 만 실패하고 기존 등록이 남는다 (C-25). 남은 SW 는 네트워크 통과형이라 무해하다. 제거는 kill-switch 플래그 빌드로만 한다 |
| R-3 | proxy matcher 과다 해제 | 보호 경로가 공개됨 | 정규식 1항목만 추가 · T-PWA-04 (`/dashboard` 307) · T-PWA-05 (`/x/manifest.webmanifest` 307) |
| R-4 | 운영이 평문 http 200 을 준다 (BL-LR-9, `docs/REFACTORING-BACKLOG.md:109-110`) | http 접속 사용자에겐 SW·푸시·설치 불가 | registrar 가 `isSecureContext` 확인 후 무동작. https 리다이렉트는 BL-LR-9 소관 |
| R-5 | iOS standalone 에서 Google 로그인 리다이렉트·Google Picker 팝업(ADR-026) 동작 | 설치 앱에서 Drive 연동·Google 로그인 실패 가능, iOS 홈 화면 앱은 Safari 와 별도 저장소 | iOS 실기기 수동 확인 (T-PWA-17). 실패 시 이메일 로그인 안내 + BL 등재 |
| R-6 | 푸시 endpoint SSRF | 서버가 내부망으로 POST | 호스트 allowlist · https · IP 리터럴 금지 (§5.2) |
| R-7 | pywebpush 2.4+ 가 `cryptography>=47` 요구 (lock 46.0.6) | JWT 검증 등 cryptography 사용처 회귀 | 전체 pytest + `uv lock` diff 검토. 문제 시 `pywebpush==2.3.0` |
| R-8 | `webpush_async` 기본값 — `ttl=0`, `timeout` 미지정 시 `None` 을 명시 전달 → aiohttp `ClientTimeout(total=None)` = 무제한 (§5.3) | 오프라인 기기 미수신 · 응답 없는 푸시 서비스에 발송 task 가 무기한 대기 | `ttl=86400`·`timeout=10` 명시 + T-PWA-42 로 인자 고정. 발송 중 DB 세션 0개라 대기가 길어져도 커넥션 풀은 막지 않는다 (§5.3 2단계) |
| R-9 | 설치 가능성은 CI 에서 판정 불가 (C-8) | 설치 회귀를 CI 가 못 잡음 | 필드·IHDR 검사로 하한 고정 + 실제 Chrome 설치(T-PWA-18) |
| R-10 | 로그아웃 없이 계정이 바뀐 기기의 잔여 창 (다음 사용자가 앱을 열기 전 도착한 알림) | 이전 사용자 알림 1건 노출 가능 | 페이로드 무내용 (§5.4) · 앱 로드 시 표식 불일치 unsubscribe |
| R-11 | 활성 워크스페이스가 다른 회의 알림 클릭 → 상세가 404 | 알림이 쓸모없어짐 | 게이트 ⑥ 확정 — 페이로드 `workspaceId` + 상세 진입 1회 전환 (§5.5) |
| R-12 | CI `e2e` job(chromium, `pnpm start` :3003)이 SW 제어 하에 돈다 | 기존 spec 동작 변화 | 기존 e2e 의 `page.route` 사용 0건 확인 (2026-10-02 grep). 회귀 시 chromium project 에 `serviceWorkers: 'block'` |
| R-13 | Cloudflare 엣지가 sw.js·manifest 를 캐시 | 업데이트·kill-switch 지연 | `max-age=0` 이면 엣지가 캐시하지 않는다고 본다 [가정] → 배포 후 `curl -I` 의 `cf-cache-status` 확인 (T-PWA-22) |
| R-14 | `sw.ts` 타입 — `dom` 과 `webworker` lib 충돌 | tsc 실패 또는 `any` 유혹 | 구현 라운드에서 해결, 수용 기준 = tsc 0 errors + `any` 0 |
| R-15 | standalone 서버(`node server.js`)와 `pnpm start` 의 SW 헤더 동일성 | 운영에서만 헤더 누락 | 같은 router-server 경로라고 본다 [가정] → T-PWA-22 |

## 8. 사용자 spec 게이트 — 확정 (2026-10-02)

> 7개 모두 추천안으로 확정. 이 표가 결정의 정본이고, 본문에 남은 `[확인 필요]` 는 없다.

| # | 질문 | 확정 결정 | 근거 | 반영 위치 |
|---|---|---|---|---|
| ① | 오프라인 배너를 둘까? | **두지 않는다** (BL-PWA-2) | 오프라인 화면(SCR-001)이 내비게이션 실패를 덮고, 배너는 experimental 플래그를 켜야 한다 | §4.4 · §6 |
| ② | iOS 설치 안내 위치 | **iOS 비설치 상태에서 알림 설정(SCR-002) 옆에만** | iOS 사용자가 설치가 필요한 순간은 알림을 켜려 할 때뿐이고, 전역 배너는 소음이다 | §5.6 REQ-011 |
| ③ | K 모노그램 시안 + `favicon.ico` | **시안 승인 + `favicon.ico` 도 K 로 교체** | 설치 앱 창·탭에 create-next-app 기본 favicon 이 남으면 브랜드가 갈린다. 시안: scratchpad `icon-proof/preview-sheet.png` | §4.2 · T-PWA-03 |
| ④ | 푸시에 회의 제목을 넣을까? | **넣지 않는다** — 일반 문구 + 경로 | 잠금화면은 남도 보고, 계정 전환 잔여 창(R-10)에서 노출 범위를 줄인다 | §5.4 |
| ⑤ | 알림 설정 위치 | **`/settings` 새 탭 "알림"** (역할 무관, "이 기기·이 계정에만" 캡션) | 설정 진입점이 이미 한 곳이다. 그 페이지는 워크스페이스 설정이라 캡션으로 구분 | §5.6 |
| ⑥ | 다른 워크스페이스 회의의 알림을 누르면? | **PR-2 에 포함** — 페이로드 `workspaceId` + 상세 진입 시 1회 전환 후 파라미터 제거 | 개인·팀 2개 워크스페이스가 기본인 사용 형태(PERSONA-001)에서 자주 걸린다 | §5.4 · §5.5 딥링크 표 · T-PWA-57·59 |
| ⑦ | 로그아웃 시 그 기기 푸시 | **꺼진다 — 재로그인 후 설정에서 다시 켠다** | 알림 권한은 사용자를 구분하지 못해 자동 재구독은 다음 사용자를 동의 없이 구독시킨다 | §5.5 |

## 9. Atomic Update 대상 (같은 PR 에 포함)

| PR | 문서 |
|---|---|
| PR-1 | 본 문서 상태 갱신 · ADR-034 (셸 — Cache Storage 미사용 · navigate 만 · navigationPreload 미사용 · kill-switch) · `apps/web/CONTEXT.md` §4 **F-14** ("SW 는 Cache Storage·IndexedDB 에 쓰지 않는다 · 같은 origin `navigate` 만 `respondWith` (`/api/*` 제외) · navigationPreload 미사용 · 등록 호출부 1곳") · `apps/web/CONTEXT.md` §3 디렉터리 목록 (`:39` `components/layout/` 에 registrar, `:50` `lib/` 에 `lib/pwa/`) · `docs/architecture/directory-map.md` (`lib/pwa/`, registrar) · `docs/REFACTORING-BACKLOG.md` BL-PWA-1·2·3·8·10·11·13 · `docs/development/secrets.md` FE 변수 표 (`NEXT_PUBLIC_PWA_SW`) |
| PR-2 | 본 문서 · ADR-035 (웹 푸시 — 수신자 규칙 · 페이로드 최소화 · allowlist · 로그아웃 순서) · `docs/architecture/erd.md` (ENT-001) · `docs/architecture/directory-map.md` (BE `push/` · FE `features/push/` — 현재 BE 17·FE 17 표기 `:1`·`:55`·`:84`·`:120`(BE 17 모듈) 를 18 로, `:179` 의 "BE 17 — `audit` 추가 시 18" 문구를 19 기준으로) · `contracts/` 재생성 + `apps/api/src/push/CONTEXT.md` · `CONTEXT-MAP.md` §4.1 (BE 모듈 17→18) · I-13 예외 문구 · §4.3 (FE features 17→18) · `apps/api/CONTEXT.md` §4 표 + **B-16** ("웹 푸시는 최종 commit 이후 best-effort · 수신자는 이벤트 주체 본인 · 엔드포인트 호스트 allowlist · 페이로드에 콘텐츠 미포함 · `push_subscriptions` 는 사용자 단위 리소스라 B-2(`workspace_id` 필터) 예외 — 대신 모든 조회·삭제에 `user_id` WHERE") · `apps/api/CONTEXT.md` §6 API 컨벤션 I-13 예외 목록에 `push → /api/v1/users/me/push-*` 추가 · `apps/web/CONTEXT.md` §3·§5 (`push/`) · `docs/REFACTORING-BACKLOG.md` BL-PWA-4·5·6·7·9·12·14 |

## 10. 외부 근거

- Next 16.3.6 번들 문서: `apps/web/node_modules/next/dist/docs/01-app/02-guides/progressive-web-apps.md` (:88 iOS 16.4+, :597 `beforeinstallprompt` 비권장, :674 Serwist·useOffline), `.../03-file-conventions/01-metadata/{manifest,app-icons}.md`, `.../04-functions/{generate-viewport,generate-metadata,use-offline}.md`
- pywebpush: PyPI `pywebpush` 2.5.0 (2026-08-30, requires_dist) · CHANGELOG (2.1.0 async 추가) · context7 `/web-push-libs/pywebpush` (`webpush_async` 파라미터·`WebPushException`)
- Chrome 설치 기준에서 SW fetch 핸들러 요구 제거 (모바일 108 / 데스크톱 112): https://developer.chrome.com/blog/update-install-criteria
- VAPID: RFC 8292
