# Kairos 2차 정검 (UI/UX 품질 + 엣지케이스) — Executive Report

**날짜** 2026-05-29 · **범위** 1차 전체정검(`../2026-05-29-fullsweep-rbac/`)이 놓친 4개 사각지대 심층 검증 · **plan** `~/.claude/plans/kairos-2-reactive-church.md`

> 1차 정검은 18라우트 렌더 + console.error 0 + owner/member RBAC + AI happy-path 만 봤다. 이번엔 **① 시각·UX 품질(다크/모바일/접근성) ② 미실행 기능 플로우 실제 실행 ③ RBAC 엣지(viewer·admin·동시성) ④ 데이터 상태**를 검증했다.

## 방법
- 메인 에이전트 **MCP Playwright 직접 구동** — 18라우트 × {light·dark·375·768} matrix(~55 스샷) + 기능 플로우 실제 실행 + 3계정(A owner / B member→admin→viewer / C 신규) 라이브 RBAC + 신규 onboarding.
- **2채널(운영 오염 최소화)** — 결정적 검증(RBAC/동시성/만료/실패-pipeline/캐시/페이지네이션/archived)은 **로컬 Docker test DB 통합테스트**(16 PASS), 라이브 관찰은 **운영 Neon**(최소 쓰기).
- **정적 = opus 6-lens Workflow**(시각/접근성/상태/다크/반응형/FE-gating, 42 confirmed/6 refuted + adversarial verify).
- **Evaluator 패널 = 빈컨텍스트 opus×2 + codex** — 4축 + UX 차원 감사 + 헤드라인 adversarial 반증. (plan v2 게이트 opus 6.5 + codex 4.0 반영본)
- 로그 `evidence.md` · 백로그 `bugs.md` · 스샷 `screenshots/`.

## 환경 · 계정
- 운영 BE :8000(→Neon) + FE :3000, Clerk dev. A=d@e.com(owner) · B=a@e.com · C=f@e.com(신규).
- throwaway 팀 WS "QA-EDGE-S28b"(`47f0f895…`) + 신규 개인 WS(C). ⚠️ 삭제 endpoint 부재 → orphan 잔존(§Cleanup).

## 검증되어 정상인 항목 (강점)
- **기능 플로우 전부 실행 OK** — inbox promote/dismiss · note 팀올리기 · meeting export(MD+JSON, 토글 반영) · action-item 토글 · **오디오 실 MP3 E2E**(R2→Whisper→Gemini→embed→완료, 정확 요약) · search(전체/유형필터/빈결과).
- **RBAC 라이브** — admin UI / viewer 제약(생성 전부 차단 + "Member 이상 권한" 게이트) / **private project ProjectMember positive 접근**(1차 미검증분).
- **결정적 통합테스트 16 PASS** — 캐시 무효화(no 60s stale) · max_uses 410 · expiry 410 · I-17 403 · last-owner 403 · 페이지네이션 contract.
- 전 라우트 console.error 0 · 다크모드 CSS-var 아키텍처 견고 · 반응형 breakpoint(375 bottom-nav / 768 icon-rail / desktop full) 동작.

## 판정 — **GO-WITH-CHANGES** (보정 후)
| 평가자 | 판정 | 점수 | 비고 |
|---|---|---|---|
| 빈컨텍스트 opus (eng축) | GO-WITH-CHANGES | 8.1 | 헤드라인 file:line 전부 재현 PASS, qa_edge 16/16 재실행 |
| 빈컨텍스트 opus (ux축) | GO-WITH-CHANGES | 7.6 | a11y 5.5(정적 grep 한계 지적) |
| codex (gpt high) | REVISE | 5.5 | calibration 오류 + 미탐 contract 2건 더 엄격 |

**합의**: 헤드라인 **발견 자체는 전부 실재**(HOLDS UP) 또는 overstated-but-real. 그러나 5건의 심각도/디테일 보정 + codex 가 contract 버그 2건 추가 발굴. **세 평가자가 동일 보정점에 수렴 → 이번 세션에 전부 반영**(아래). 보정 후 산출물은 release-grade.

**반영한 보정**: ① DARK-CONTRAST 비율 1.59→**2.98:1** 정정(AA fail 결론 유지) ② PERSONAL-INVITE "silent fail" 철회(토스트 코드 존재)→**P3** ③ A11Y 클러스터 축소(avatar 1건만 실, 나머지 visible text/sr-only)→**P3** ④ LANDING-TEXT-WHITE reframe→**nit** ⑤ **WS-MEMBER-UNIQUE P2→P1 격상**(Cloud Run 멀티워커 데이터무결성) ⑥ ARCHIVED-LEAK P2↔P3 불일치→**P3 통일** ⑦ codex 발굴 **RQ-KEY-COLLISION(P2) + FE-PAGESIZE-MISMATCH(P3)** 코드확인 후 추가.

## 발견 요약 (보정 최종) — 상세·repro·근본원인은 `bugs.md`
| ID | 우선 | 한 줄 | 상태 |
|---|---|---|---|
| SEC-CLERK-SECRET-COMMITTED | **P0** | 실 Clerk dev secret 가 docs sprint1 spec:30 평문 커밋 | 확정(carry) |
| BUG-WS-MEMBER-UNIQUE | **P1** | workspace_members (ws,user) UNIQUE 부재 → 멀티워커 멤버십 무결성 손상 | 확정·격상 |
| BUG-MEETING-FAILED-UI | P2 | 실패 미팅 "곧 생성됨" 오해 placeholder + retry/error 없음(detail 응답이 error_message 미노출) | 신규·확정 |
| UX-NEW-GRID-375 | P2 | `/new` 3-col 이 375px 미stack(압착·줄바꿈) | 신규·확정 |
| DARK-CONTRAST-MUTED | P2 | 다크 text-muted #5C5C63/#0A0A0B = 2.98:1 (AA 4.5 미달) | 신규·보정 |
| RQ-KEY-COLLISION | P2 | projects queryKey 가 status 미포함 → 사이드바 active/archived 캐시 충돌 | 신규(codex)·확인 |
| BUG-INBOX-PROMOTE-STUB | P2 | inbox "다른 프로젝트" promote stub | 확정(carry) |
| BUG-PERSONAL-INVITE-UX | P3 | 개인 WS 가 초대 UI 노출(BE 403+토스트 정상, affordance 오류) | 확정·강등 |
| BUG-SEARCH-CURRENT-PROJECT-NOOP | P3 | 글로벌 search "현재 프로젝트" 무동작 | 신규·확정 |
| BUG-ARCHIVED-PROJECT-LEAK | P3 | 백엔드 기본 status 미필터(FE /projects 는 active 전송으로 무영향) | 신규·정적 |
| FE-PAGESIZE-PARAM-MISMATCH | P3 | FE page_size vs BE pageSize alias → FE pageSize 무시 | 신규(codex)·확인 |
| A11Y-AVATAR-LABEL | P3 | avatar 트리거 accessible name 부재(나머지 클러스터는 refuted) | 신규·축소 |
| OBS-VIEWER-VISIBILITY-BTN | P3 | viewer 가 private 상세서 visibility 토글 봄 | 신규·관찰 |
| OBS-MEETING-ACTIONS-PROCESSING | P3 | processing/failed 미팅에도 export 활성(빈 산출) | 신규·관찰 |
| A11Y-ICON-RAIL-768 | P3 | 768 사이드바 collapse 시 title(≠aria-label)+focus-visible 부재 | 신규 |
| UX-CMDK-GLYPH | P3 | ⌘K 글리프 렌더 이상(Geist Mono U+2318 미포함) | 신규·cosmetic |
| BL-DATA-HYGIENE-SEED | P3 | displayName "사용자"/email=""(fresh C 포함) | 확정(carry) |
| BUG-MEMORY-WS-FILTER | P3 | memory 5 mutation PK-only WHERE(2-layer 갭) | 정적(carry) |
| LANDING-TEXT-WHITE | nit | 랜딩 CTA 흰텍스트 accent 대비 다소 낮음(white-on-white 아님) | 신규·reframe |
| DESIGN-TOKEN-DRIFT | P3 | 하드코드 컬러/임의 px 타이포/스켈레톤·로딩카피 불일치 cluster | 신규·정적 |

**집계**: P0 ×1 · P1 ×1 · P2 ×5 · P3 ×11 · nit ×1. **버그 아님 종결** 7건(last-admin/선택한소스 stub/bottom-nav·dialog-close·검색·archive aria/ text-secondary 대비/role-enum) — `bugs.md` §종결.

## 이번 스윕 미커버 (evaluator 지적, 후속 권장)
XSS/출력이스케이프(LLM-trust-boundary) · 타 composite-key 동시성(ProjectMember/inbox/action) · 기능적 a11y(키보드·focus-trap·ESC·SR) · 네트워크 에러상태(offline/500/timeout) · memory IDOR 실증 · invite rate-limit · 롱콘텐츠/오버플로 · prefers-reduced-motion. 상세 `bugs.md` §미커버.

## Cleanup / 운영 orphan (삭제 endpoint 부재 → 영구 잔존, 문서화)
**test DB(Channel A)**: TestContainers fixture 자동 폐기 → 무오염. 신규 테스트 `backend/tests/qa_edge/{test_rbac_edges_s28b.py,test_data_state_s28b.py}` 는 regression 가드로 보존 권장(사용자 결정 — pyright 경고 cleanup 필요 시 별도).

**운영 Neon orphan(삭제 불가)** — throwaway 팀 WS **QA-EDGE-S28b** `47f0f895-7e51-4f44-af03-ab7b4d3f647c`:
- 멤버: A(owner) + B(a@e.com, viewer로 강등됨) — B 멤버십 잔존.
- 프로젝트: auto-seed 템플릿 3 + private `cd26d682…`(+ B ProjectMember).
- 미팅: text `61d1b30f` / audio `64a34b74`(완료) / failed `ad17a978`.
- 노트: `3ad269da`(+ "팀올리기" 복사본이 QA Cycle C Team `7f9f446d` 에 1건).
- invite: `rWlqqPzniSRb`(admin, 7일후 만료).
- C(f@e.com) 개인 WS — 첫로그인 lazy seed(정상, 잔존).

→ **delete-workspace endpoint 가 없어 WS·멤버십은 제거 불가**(개별 meeting/note/project 는 delete API 존재하나 부분정리 저효용). 잔존을 사실대로 기록. 운영 정리 sprint 시 SQL/관리 endpoint 로 일괄 제거 권장.

**임시 산출물**: `.playwright-mcp/`(스샷 원본은 `screenshots/` 로 이동 완료, audio copy·export md/json·codex-eval 잔존 — gitignore 대상).

## 다음
fix 는 우선순위 순(P0 시크릿 rotation → P1 UNIQUE 제약 → P2 5건) 별도 PR + 매 단계 사용자 승인. main 무변경 유지.
