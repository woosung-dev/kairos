# PWA PR-1 (설치형 셸) — 검증 보고

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
