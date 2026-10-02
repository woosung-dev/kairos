# PWA PR-1 (설치형 셸) · PR-2 (웹 푸시) — 검증 보고

> 2026-10-02 · 브랜치 `claude/pwa-feature-workflow-1785d8` · spec `docs/requirements/pwa.md` §4 · 결정 `docs/adr/034-pwa-installable-shell.md`
> 진행 방식: 오케스트레이터(메인) / Generator(구현) / Evaluator(매 라운드 새 컨텍스트) 3역할. 라운드 전후 git 지문 비교로 역할 경계를 확인했다 (위반 0).

## 1. 무엇이 동작하나

| 기능 | 확인 방법 | 결과 |
|---|---|---|
| manifest 비로그인 200 (`application/manifest+json`, `start_url=/dashboard`, standalone, `#0A0A0B`, 아이콘 3) | curl · T-PWA-01~04 | PASS |
| proxy matcher 는 `/manifest.webmanifest` 1개만 공개 (`/x/manifest.webmanifest`·`/dashboard` 는 307 유지) | curl 변형 9종 · T-PWA-05 | PASS |
| K 모노그램 아이콘 4장 + favicon.ico (16/32/48 RGBA PNG-in-ICO) | IHDR 파싱 · vitest favicon · T-PWA-03 | PASS |
| SW 등록 (scope `/`, `/_next/static/service-worker/sw.js`, `Service-Worker-Allowed: /`, 페이지 로드당 1회, `load` 이후) | T-PWA-07~09 · Chrome 154 실브라우저 (Claude in Chrome) | PASS |
| SW 는 같은 origin GET `navigate` 만 통과 — `/api/*`·OAuth 콜백·cross-origin·non-GET 미개입, navigationPreload 미사용 (OAuth `code` 1회 소비) | vitest T-PWA-12 · 카운팅 프록시 T-PWA-13 (서버 도달 1) | PASS |
| Cache Storage·IndexedDB 0 | T-PWA-10 · source-scan · 빌드 산출물 grep | PASS |
| 오프라인 화면 SCR-001 (200 + no-store, data: 아이콘, 다시 시도, online 자동 복귀) | T-PWA-11 ①②③ · headed Chrome · Playwright MCP 375px · browser-use | PASS |
| kill-switch `NEXT_PUBLIC_PWA_SW=off` → 다음 로드에서 등록 해제, 열린 탭 강제 이동 0 | T-PWA-14 (vitest) · T-PWA-15 (빌드 교체 실측) | PASS |
| safe-area (`viewport-fit=cover`, nav 높이 토큰, body 좌우 padding) | T-PWA-16 (CDP inset 주입) · Chrome 154 | PASS (chromium nav 케이스는 CI e2e job) |
| 콘솔 | 모든 판정 실행에서 `console.error` 0 (T-PWA-23 측정 테스트의 위치 한정 허용 2종 제외) | PASS |

## 2. 테스트 결과 (오케스트레이터 재실행 기준)

- `pnpm exec tsc --noEmit` → 0 errors
- `pnpm exec vitest run` → 53 files / 332 passed
- `playwright test --project=public-only` (:3005 prod 빌드) → `--repeat-each=3` 54/54, `--repeat-each=2` 36/36
- T-PWA-11 ① `--repeat-each=15 --workers=1` 15/15 · ③ Chromium 147 15/15 · Chrome 154(channel chrome) 15/15 · pwa.spec 전체 Chrome 154 16/16
- 변이 시험 (Evaluator, scratchpad 사본): vitest 13/13 검출, e2e 5/6 검출 (`/api` 처리 변이는 vitest 가 담당)

## 3. 판정 라운드

| 라운드 | 판정 | 요지 |
|---|---|---|
| EVAL-SPEC-1 | REVISE | navigationPreload 가 OAuth 콜백을 2번 보냄(blocker) 외 |
| EVAL-SPEC-2 | REVISE | `setOffline` 은 SW 첫 내비게이션만 막음 (Chromium 147) · 로그아웃 분기 도달 불가 |
| EVAL-SPEC-3 | PASS | 변경분 한정 (사용자 승인) |
| 사용자 spec 게이트 | 승인 | ①~⑦ 추천안, K 아이콘 + favicon 교체, ⑥ PR-2 포함 |
| EVAL-IMPL-1 | REVISE | T-PWA-11 ① flaky · headed 오프라인 favicon 요청 error · 운영 주석 거짓 |
| EVAL-IMPL-2 | PASS | minor 2 |
| GATE-PR1 | PASS | best-practices FAIL 0 (`evidence/pr1-best-practices.md`) |

## 4. 구현 중 바뀐 결정 (빌드가 드러낸 사실)

1. **favicon.ico 항목은 RGBA 여야 한다** — Turbopack ICO 디코더가 RGB PNG 를 거부해 빌드 실패. 빌드 없이 잡는 vitest 추가.
2. **worker 청크는 `NEXT_PUBLIC_*` 를 인라인하지 않는다** — `process` 참조 시 빌드 panic (`evidence/orch/turbopack-worker-panic-node-process.log`). kill-switch 를 페이지 쪽 unregister 만으로 단순화 (pwa.md C-28, ADR-034 D5). 한계: SW 자체 버그는 수정한 sw.ts 배포로 복구.
3. **panic 뒤 남은 `.next` 캐시는 다음 빌드를 깨뜨린다** ("generate_source_map was canceled") — `rm -rf apps/web/.next` 후 재빌드로 해소.

## 5. 증거 파일 (`evidence/`)

- `orch/headed-scr001.png` — headed Chrome 오프라인 화면 (console.error 0)
- `orch/t15-killswitch.json` — kill-switch 실측 결과
- `orch/turbopack-worker-panic-node-process.log` — C-28 원문
- `eval-impl-1/*.png` (7) · `eval-impl-2/mcp-375-offline-scr001.png` — Playwright MCP·browser-use 375px 화면
- `pr1-best-practices.md` — 규칙별 게이트 표

## 6. 남은 수동 확인 · 운영 메모

- **T-PWA-18 실 Chrome 설치 — PASS (2026-10-02, Chrome 154.0.8037.93 macOS)**: 사용자가 주소창 설치 클릭 → `~/Applications/Chrome Apps.localized/Kairos.app` 생성 (`CrAppModeShortcutName`=Kairos, `CrAppModeShortcutURL`=`http://localhost:3005/dashboard` = manifest `start_url`). 앱 아이콘 = 승인한 K 모노그램 (`evidence/orch/t18-installed-app-icon.png`, app.icns 추출). 설치 직전 같은 탭에서 manifest·아이콘 3장 200/실측 크기 일치 · SW activated · controlled 확인. 앱 shim 은 설치 클릭 뒤 수 분 지나 생성됐다. 설치 직후 뜬 창은 주소창·탭 바 없는 독립 창 (standalone, 사용자 육안 확인).
- T-PWA-17 iOS 실기기 (safe-area·statusBarStyle) · T-PWA-22 배포 후 smoke: 배포 뒤 사용자 운영 작업
- 운영 http 평문 접속에서는 SW 가 동작하지 않는다 (비보안 컨텍스트 → registrar `skip`). https 접속만 대상.
- 비상시: repo Variables `NEXT_PUBLIC_PWA_SW=off` → main 에 새 커밋 (release.yml 이 새 sha 빌드) → `mise run deploy-ship sha-<7>`. 맥 비상 경로면 `deploy/oci/build.env`. 구 이미지 롤백으로는 SW 가 내려가지 않는다 (ADR-034 D6). 절차 원문 = `deploy/oci/build.env.example`.
- 2026-10-02 main 병합 (#204 Phase A — 이미지 빌드가 CI `release.yml` 로 이동): CI 빌드 인자에 `NEXT_PUBLIC_PWA_SW` 가 빠져 있어 1줄 추가. 병합 전 PR CI 는 6/6 통과, e2e 62개 중 51 통과 · 11 skip (skip 은 기존 데이터 의존 스펙 — main 기준선 44개 중 10~11 skip, 새 테스트 18개 전부 통과).

---

## 7. PR-2 (웹 푸시) — 검증 보고

> 2026-10-02 · 브랜치 `claude/pwa-push` · spec `docs/requirements/pwa.md` §5 · 결정 `docs/adr/035-web-push.md` · 불변식 B-16

### 7.1 무엇이 동작하나

| 기능 | 확인 방법 | 결과 |
|---|---|---|
| API-001~003 (`/api/v1/users/me/push-*`) — config · endpoint upsert(rebind) · id 삭제(없음·타인도 204) | pytest T-PWA-30·31·34 | PASS |
| endpoint 검증 — ASCII · https · allowlist · IP·userinfo·포트 거부 · 비ASCII/lone surrogate/IDN 은 500 아닌 422 | pytest T-PWA-32 (+ GEN-P2-2 D1 4건) | PASS |
| 회의 완료·실패 → 업로더 본인(현재 멤버)만 · commit 이후 · 발송 중 DB 세션 0 · 404/410 만 정리 · best-effort | pytest T-PWA-35~42 (세션 spy) | PASS |
| 마이그레이션 `563de342c8ae` 가산형 (테이블 1 + 명시 이름 제약 4) | pytest T-PWA-43 · alembic dry-run (오케스트레이터) | PASS |
| 계약 drift 0 | `mise run contracts-check` (T-PWA-44) | PASS |
| SCR-002 알림 탭 · 권한 요청은 토글 클릭 때만 · 등록 없음 = '사용 불가' | vitest · e2e T-PWA-48 | PASS |
| 로그아웃 = ① DELETE ∥ ② unsubscribe (3초 상한) → 표식 삭제 → sign-out | vitest · e2e T-PWA-49 (sign-out stub) | PASS |
| 앱 로드 동기화 — 표식 불일치 unsubscribe · 키 불일치 정리 · 계정 전환 재동기화 | vitest T-PWA-50·51 (+ GEN-P2-2 D2·D3) | PASS |
| SW `push`·`notificationclick` (UUID 로 URL 조립, open redirect 차단) | vitest T-PWA-46·47 | PASS |
| 알림 딥링크 워크스페이스 1회 전환 | vitest T-PWA-57 · e2e T-PWA-59 | PASS |
| 실푸시 수신 (완료·실패·계정 전환 미수신) — 실제 Chrome + FCM | T-PWA-52·53·54 (아래 7.2) | PASS |
| 셸 번들 — push 가 `(app)` 공용 청크에 더한 몫 +2.5 KB gz (zod 0) | GATE-PR2-R2 청크 실측 | PASS |
| arm64 api 이미지 — `pywebpush`·`http_ece`·`py_vapid` import, cryptography 50.0.2 | `docker build --platform linux/arm64` (오케스트레이터) | PASS |

### 7.2 테스트 결과

- pytest 전체: 1082 passed (EVAL-P2-1 오케스트레이터 · 기준선 996) → **1086 passed** (GEN-P2-2, `be-test.sh`) → 1086 passed (GEN-P2-3, 병합 `1063903` 후 `be-test.sh` 재실행 — BE 코드 변경 없음)
- alembic dry-run: 가산형 — `CREATE TABLE push_subscriptions` 1 + 명시 이름 제약 4 (오케스트레이터)
- contracts drift 0
- vitest: 59 files / 415 passed (GEN-P2-2) → **59 files / 423 passed** (GEN-P2-3 — 표식 경계 +7 · 로그아웃 가드 +1) · tsc 0 errors · eslint 0 (변경 파일). 전체 트리 `pnpm lint` 는 이 PR 과 무관한 기존 23 errors
- e2e (오케스트레이터, GEN-P2-3 최종 빌드): public-only **18 passed** · chromium **41 passed / 2 failed / 10 skipped** (`push.spec.ts` 9 전부 통과)
  - 실패 2건 = `home.spec.ts:34`·`mobile-responsive.spec.ts:52` strict mode 위반 — **main(`ef79e3c`) 빌드에서도 같은 2건이 실패**해 이 PR 무관으로 판정, BL-PWA-21 등재. 병합 직후(GEN-P2-3 전) 실행은 42 passed / 11 skipped 였다
- 실푸시 (오케스트레이터, Playwright `channel: "chrome"` 영속 프로필 + `grantPermissions`, 로컬 QA 스택 :3005/:8000, 최종 빌드)
  - 켜기: FCM endpoint · applicationServerKey 65 B · 새로고침 후에도 '켜짐' (EVAL D4 해소)
  - T-PWA-52 완료: capture 202 → **6초** 뒤 "회의 처리 완료" 알림 (tag `meeting-<id>`, URL `/meetings/<id>?workspace=<wid>`)
  - T-PWA-53 실패 (Gemini 키를 일부러 틀린 BE): **2초** 뒤 "회의 처리 실패" 알림. BE 로그 `push_dispatch_done ... sent=1 failed=0 pruned=0`, endpoint 는 로그에 0회
  - T-PWA-54 계정 전환: 로그아웃 353 ms → 구독·표식 삭제, DELETE 204, DB `push_subscriptions` 0행 → member 로 로그인 → owner 회의 완료 뒤 16초 대기 → member 기기 알림 **0건**

### 7.3 판정 라운드

| 라운드 | 판정 | 요지 |
|---|---|---|
| IMPL-P2-BE · IMPL-P2-FE · IMPL-P2-FE-b | — | BE `push/`·마이그레이션·pipeline 훅 / FE 구독·로그아웃·동기화·딥링크 / T-PWA-49 rate limit flake → sign-out stub |
| EVAL-P2-1 | PASS | blocker·major 0. 오케스트레이터가 코드로 확인한 minor 3건 (D1 비ASCII 500 · D2 VAPID 키 교체 후 옛 구독 · D3 계정 전환 시 동기화 생략) |
| GEN-P2-2 | — | D1·D2·D3 수정 + Atomic Update (ADR-035 · erd · CONTEXT-MAP · apps/api·web CONTEXT · directory-map · secrets · BL-PWA-4~19) |
| GATE-PR2 (best-practices 1차) | REVISE | FAIL 1 `bundle-conditional` — `marker.ts` 의 zod 가 `(app)` 셸 청크를 142→236 KB gz 로 키움 (`evidence/pr2-best-practices.md`) |
| GEN-P2-3 | — | 셸 번들 (`marker.ts` zod → 손 타입 가드 · `usePushSettings` 를 `use-push-settings.ts` 로 분리) · 로그아웃 정리가 동기화 가드 초기화 · 배포 안내(rc 3 · VAPID 선반영) · BL-PWA-20 (422 NaN → 500) |
| GATE-PR2-R2 (best-practices 재게이트) | **PASS** | FAIL 0. layout 그룹 144,737 B gz (기준선 +2,493) · `/meetings/[id]` 156,572 · `/settings` 187,433 |

### 7.4 구현 중 바뀐 결정

1. **로그아웃 ①→② 순차 → ①∥② (`Promise.allSettled`, 전체 3초 상한)** — 느린 ①이 예산을 다 쓰면 ②(로컬 unsubscribe)가 돌지 못한다 (pwa.md §5.5, ADR-035 D6).
2. **서비스 2개** — `PushService`(API) · `PushDispatchService`(세션 없는 발송). 발송 구간 세션 0 을 구조로 강제 (ADR-035 D5).
3. **endpoint ASCII 검사 + 422 핸들러 ASCII 폴백** — lone surrogate 는 422 응답 직렬화도 깨뜨려 전역 핸들러에 폴백을 뒀다 (ADR-035 D3).
4. **키 교체 = 다음 앱 로드에서 '꺼짐'** — 자동 재구독 없음, 서버는 403 을 정리하지 않는다 (ADR-035 D7·D8).
5. **동기화 가드 = 마지막 계정 id** — 로그아웃→다른 계정 로그인이 soft navigation 이라 boolean 가드는 새 계정 동기화를 건너뛴다 (ADR-035 D6).

### 7.5 증거 파일

- `evidence/eval-p2-1/explore-granted-first-visit-375.png` · `explore-denied-375.png` — 375px SCR-002 상태별 화면
- `evidence/pr2-best-practices.md` — best-practices 게이트 1차(REVISE) · 수정 · 재게이트(PASS)

### 7.6 남은 확인 · 운영 메모

- 실푸시 로컬 확인은 끝났다 (7.2). **운영 https 에서의 실푸시는 배포 뒤 사용자 로그인으로 확인**한다 (오케스트레이터는 운영 로그인 금지).
- 관찰 (이 PR 무관): T-PWA-54 에서 member 로그인 직후 `GET /api/v1/workspaces/<owner 개인 ws>` 403 이 `console.error` 1건으로 찍혔다. 이전 계정의 `activeWorkspaceId` 가 남은 채 `settings/page.tsx:64` `useWorkspace` 가 먼저 요청하고, `panel-layout.tsx:63` `ensureOwner` 가 effect 에서 뒤늦게 정리하는 기존 경로다 (main 코드 동일, 이 PR diff 에 `useWorkspace(` 추가 0). [가정] main 빌드로 재현하지는 않았다.
- T-PWA-55 iOS 실기기: 사용자 운영 작업.
- 운영 VAPID 키: 생성 명령 `apps/api/src/push/CONTEXT.md` §7 → 서버 `~/kairos/.env` 3줄 (사용자 SSH). **배포 전에** 넣는다 — api 가 `env_file: [.env]` 로 읽어서 (`deploy/oci/docker-compose.prod.yml:73`) 나중에 넣으면 api 컨테이너를 다시 만들어야 한다. 비우면 알림 기능만 꺼진다.
- **배포는 스키마 관문에서 한 번 멈춘다** — 마이그레이션 `563de342c8ae` 때문에 `kairos-deploy.sh` 가 rc 3 으로 아무것도 바꾸지 않고 멈춘다 (`deploy/oci/bin/kairos-deploy.sh:112-123`). 맥 `mise run deploy-ship <tag> --migrate` 또는 Actions `release.yml` `deploy-migrate` job 승인으로 진행 (`docs/operations/deployment.md:65`).
- 후속 BL: BL-PWA-15 (Better Auth rate limit — e2e 예산·`cf-connecting-ip`) · BL-PWA-16 (실제 로그아웃 e2e 0건) · BL-PWA-17~19 · BL-PWA-20 (422 NaN) · BL-PWA-21 (e2e 선택자 strict mode, main 에도 재현) · BL-PWA-22 (best-practices 경미 묶음).
