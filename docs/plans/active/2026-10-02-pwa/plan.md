# PWA 도입 (설치형 셸 + 웹 푸시) — plan

> 2026-10-02 시작. 정본 계획은 세션 계획서에서 옮긴 요약이다. 실행 체크리스트는 `checklist.md`, 기능 명세는 `docs/requirements/pwa.md`.

## 목표
- PRD §9 "모바일 네이티브 앱 (PWA로 대체)" (`docs/requirements/prd.md:606`) 실현 1차.
- PR-1: 설치형 셸 (manifest · 아이콘 · viewport · Service Worker 오프라인 화면) — FE 만.
- PR-2: 웹 푸시 — 회의 처리 완료·실패 시 업로드한 본인(`Meeting.created_by_id`)에게만. BE + DB + FE.

## 확정 결정 (2026-10-02 사용자 인터뷰)
| 항목 | 결정 |
|---|---|
| 범위 | 설치형 셸 + 오프라인 안내 + 웹 푸시 |
| 푸시 이벤트 | 회의 처리 완료·실패만. 나머지(메모·액션·초대·Drive)는 BL 등재 |
| PR | 2개 순차 (PR-1 머지 → main 에서 PR-2) |
| 아이콘 | 'K' 모노그램 (Satoshi 700, accent `#3ECFB4`, 배경 `#0A0A0B`) — spec 게이트에서 시안 확인 |
| 검증 도구 | Playwright = 합격 판정 · Claude in Chrome = 실제 Chrome(설치·실푸시) · browser-use CLI = 탐색 QA |

## 워크플로우 (에이전트 3역할)
- **Orchestrator** (메인 세션): 단계 전환 · 서버 lifecycle · 결함 코드 재확인 · 사용자 게이트 · 커밋/PR(승인 후).
- **Generator** (서브에이전트): spec 초안 · 구현 · 자체검증(tsc·eslint·vitest·pytest). 빌드·서버·커밋 금지.
- **Evaluator** (서브에이전트, 매 라운드 새로 생성): spec·코드 적대 검토 · Playwright 판정 · 탐색 QA · 판정 JSON 반환. 파일 수정 금지.
- 역할 경계: 라운드 전후 git 지문(`status`·`diff` 해시·미추적 파일 해시·`log -1`) 비교.
- PR 전 게이트: 새 Evaluator 가 `vercel-react-best-practices` 규칙별 검토 → FAIL 0.

## 핵심 설계 제약 (코드로 확인)
1. SW 는 **Cache Storage 를 쓰지 않는다** — 사용자 데이터 미보관(I-9/I-23/I-24, revocation 즉시성). 내비게이션 실패 시 SW 안의 인라인 오프라인 HTML 반환.
2. SW 는 Next 16.3.6 번들 worker (`new URL('./sw.ts', import.meta.url)`) → `/_next/static/service-worker/sw.js` 고정 URL + `Service-Worker-Allowed: /` (2026-10-02 spike 로 확인).
3. `proxy.ts` matcher 에서 `manifest.webmanifest` 만 제외 (현재 307 → sign-in).
4. SW 등록 진입 페이지는 `/sign-in` (DB 없는 CI 에서 `/` 는 500).
5. SW 작업·수동 설치는 :3005 에서만 (:3003 은 일상 dev origin).
