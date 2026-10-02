# PWA 도입 — 체크리스트

> plan.md 의 실행 체크리스트. 완료 시 체크 + 날짜 + 증거 경로.

## PR-1 — 설치형 셸

### Phase 0 — 준비
- [x] 2026-10-02 `pnpm install` (apps/web, frozen-lockfile)
- [x] 2026-10-02 SW spike — TS 번들 worker 빌드 → `.next/static/service-worker/sw.js` · `Service-Worker-Allowed: /` · `Cache-Control: public, max-age=0, must-revalidate` · headless Chromium 에서 scope `/` 등록 + 리로드 후 controlled. spike 코드 제거
- [x] 2026-10-02 browser-use CLI 0.1.13 설치 (`uv tool install`). 텔레메트리는 실행마다 env 로 끔. 사용자 메인 Chrome 이 아닌 별도 프로필 Chrome(CDP 포트)에만 붙인다
- [x] 2026-10-02 Claude in Chrome 확장 연결 (Browser 1, macOS)
- [x] 2026-10-02 베이스라인 `mise run fe-security-headers 3005` → public-only 2 passed (security-headers.spec.ts 2건)

### Phase 1 — Spec
- [x] 2026-10-02 Generator spec 초안 → GEN-SPEC-2 (EVAL-SPEC-1 D1~D15·인용 4건) → GEN-SPEC-3 (EVAL-SPEC-2 D1~D9·C-22 + 게이트 결정)
- [x] 2026-10-02 Evaluator spec 검토 PASS — EVAL-SPEC-1 REVISE · EVAL-SPEC-2 REVISE · EVAL-SPEC-3 PASS (변경분 한정, 사용자 승인한 축소 범위). 경미 9건·인용 4건은 구현 라운드 첫 단계에서 반영
- [x] 2026-10-02 사용자 spec 게이트 — ①~⑦ 전부 추천안 확정, ③ K 아이콘 승인 + favicon 교체, ⑥ PR-2 포함

### Phase 2~3 — 구현·평가
- [x] 2026-10-02 Generator 구현 + 자체검증 — IMPL-1 → 1b(favicon ICO RGBA, Turbopack 디코더 요구) → 1c(worker 청크 env 미인라인 panic → kill-switch 페이지 쪽만, C-28) → 2(EVAL-IMPL-1 D1~D5) → 3(Phase 4 문서). tsc 0 · vitest 53 files/332
- [x] 2026-10-02 Evaluator 라운드 PASS — EVAL-IMPL-1 REVISE(major 3) · EVAL-IMPL-2 PASS. public-only 54/54(×3) · T-PWA-11 ③ Chromium 147·Chrome 154 각 15/15 · T-PWA-15 kill-switch 실측 PASS (`evidence/orch/t15-killswitch.json`)
- [ ] draft PR CI spike (public-only 페이지 렌더)
- [x] 2026-10-02 Claude in Chrome 실제 설치 (사용자 클릭) — `Kairos.app` 생성, start URL `/dashboard`, K 아이콘 (`evidence/orch/t18-installed-app-icon.png`)

### Phase 4 — 게이트·PR
- [x] 2026-10-02 best-practices 게이트 FAIL 0 — GATE-PR1 PASS, 24 규칙 (PASS 15 · N/A 9) (`evidence/pr1-best-practices.md`)
- [x] 2026-10-02 Atomic Update (ADR-034 · pwa.md · F-14 · `apps/web/CONTEXT.md` §3 목록(:39 layout 에 registrar · :50 lib 에 `lib/pwa/`) · directory-map · BL-PWA-1·2·3·8·10·11·13 — pwa.md §9 와 동일). PR-1 은 새 FE feature 를 만들지 않으므로(registrar=`components/layout/`, worker=`lib/pwa/`) CONTEXT-MAP §4.3 갱신 없음 — §4.3 FE features 17→18 은 PR-2(`features/push/`)
- [x] 2026-10-02 report.md 증거 (스크린샷 · console.error 0 · vitest/e2e)
- [ ] 커밋 → 푸쉬 → PR (각 승인) → CI green → 사용자 머지

## PR-2 — 웹 푸시
- [x] 2026-10-02 Phase 5 전체 스택 환경 (kairos-qa-db · BE :8000 — EVAL-P2-1 chromium e2e 실행 기준. dev VAPID 실발송은 T-PWA-52 에서 확인)
- [x] 2026-10-02 Phase 6 구현 — IMPL-P2-BE (BE `push/` · 마이그레이션 `563de342c8ae` · pipeline 훅) → IMPL-P2-FE (FE 구독·로그아웃 ①∥②·동기화·딥링크·SW) → IMPL-P2-FE-b (T-PWA-49 rate limit flake → sign-out stub)
- [x] 2026-10-02 Phase 7 자동 평가 — EVAL-P2-1 PASS (blocker·major 0). pytest 1082 (기준선 996) · alembic dry-run 가산형 · contracts drift 0 · public-only 18 · chromium 42 pass/11 skip · push.spec 9 ✓
- [x] 2026-10-02 GEN-P2-2 minor 3건 수정 (D1 비ASCII 422 · D2 VAPID 키 불일치 정리 · D3 계정 전환 재동기화) — pytest 1086 · vitest 59 files/415 · tsc 0 · eslint 0 · contracts drift 0
- [ ] e2e 재실행 (GEN-P2-2 D2·D3 이후 — chromium `push.spec.ts`)
- [ ] 실푸시 수신 T-PWA-52·53·54 — 오케스트레이터 실브라우저 확인 대기
- [x] 2026-10-02 Atomic Update — ADR-035 · erd(ENT-001) · CONTEXT-MAP(§4.1 BE 18 · I-13 · §4.3 FE 18) · `apps/api/CONTEXT.md`(§4 · B-16 · §6) · `apps/web/CONTEXT.md`(§3 · §5) · directory-map · secrets(VAPID) · BL-PWA-4·5·6·7·9·12·14 + 15~19 · pwa.md · `apps/api/src/push/CONTEXT.md`
- [ ] Phase 8 게이트 · 커밋 → 푸쉬 → PR (각 승인) → CI green → 사용자 머지

## 로컬 정리 절차 (작업 종료 시)
- `chrome://serviceworker-internals` 에서 localhost:3005 등록 제거 · 설치한 앱 제거
- 별도 프로필 Chrome 종료 + scratchpad 프로필 폴더 삭제
- `uv tool uninstall browser-use` (계속 쓸 거면 유지)
