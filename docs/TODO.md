# Kairos TODO

> 마지막 업데이트: 2026-05-12
> 이 파일은 리빙 문서입니다. 주요 작업 후 반드시 업데이트하세요.
> 형식 규칙: `.ai/common/global.md` §2 참조

---

## Completed

- [x] Phase 0: 기획 · 아키텍처 · 디자인 (PRD, ERD, API 명세, DESIGN.md)
- [x] ADR-001: 기술 스택 선정
- [x] ADR-002: 실행 전략 — Vertical Slice Sprint 채택
- [x] ADR-003: 디자인 도구 선정
- [x] ADR-004: PARA → 프로젝트 구조 전환
- [x] ADR-005: 랜딩 페이지 AIDA 리디자인
- [x] Phase 1 FE: 3-Panel 레이아웃, Inbox 목록, Dashboard 스캐폴딩
- [x] Phase 1 FE: 랜딩 페이지 리디자인 (13개 컴포넌트)
- [x] Sprint 1 BE: 백엔드 스캐폴딩 + 핵심 도메인 CRUD + Auth [검증됨 2026-04-04]
- [x] Sprint 2: AI 파이프라인 + 프론트엔드 API 연동 [검증됨 2026-04-04]
- [x] Sprint 3: RAG + 노트 [검증됨 2026-04-04]
- [x] Sprint 4: 배포 설정 [검증됨 2026-04-04 — BE/FE 프로덕션 헬스체크 OK]
- [x] Sprint 5: RBAC + 초대 시스템 [검증됨 2026-04-05 — QA 통과, 57 BE 테스트 passed]
  - [x] RoleChecker RBAC 미들웨어 + 전체 라우터 적용
  - [x] WorkspaceInvite 모델 + Alembic 마이그레이션
  - [x] 초대/멤버 관리 API (11개 엔드포인트)
  - [x] FE: /settings 페이지 (멤버/초대/일반 탭)
  - [x] FE: /invite/[code] 초대 수락 페이지
  - [x] FE: 사이드바 설정 링크 + Viewer 쓰기 버튼 숨김
  - [x] ADR-007: LLM Knowledge Base 인사이트 (연구/Phase 4 적용 예정)
- [x] ADR-006 서비스 전면 UI/UX 개편 — 완료 (11/11)
  - [x] 홈 Today 피드 + 온보딩 배너
  - [x] 인라인 출처 [1][2][3] citation-badge
  - [x] C|D 2-Panel 레이아웃 (RAG 오버레이 전환)
  - [x] RAG 소스 범위 선택 (3단계 스코프)
  - [x] 프로젝트 대시보드형 (인사이트 + 2컬럼)
  - [x] Inbox 스마트 일괄 처리 (2그룹)
  - [x] 회의 상세 3뷰 (요약/트랜스크립트/액션)
  - [x] 빠른 메모 + 소스 가져오기 모달
  - [x] 모바일 BottomNav
  - [x] 사이드바 소스 트리 펼침 — 프로젝트 클릭 시 하위 회의/노트/파일 목록 (mock)
  - [x] [1] 클릭 → 소스 뷰어 열림 flow 연결 — CitationBadge → UI Store → SourceViewer
  - [x] Inbox 신뢰도 임계값 설정 UI (프리셋 70/80/90/95%)
  - [x] 내보내기 포맷 MD/JSON (회의/노트)
  - [ ] 내보내기 포맷 PDF (향후 구현)

## Recently Completed — Sprint 10 E2E 검증 + R2 CORS 수정 (2026-05-12)

- [x] **E2E 검증 완료 (2026-05-12)**: 실제 오디오 파일 업로드 → status=completed → 트랜스크립트 세그먼트 + InboxItem 생성 확인. **검증 범위: 오디오 업로드 → STT → 요약 → Inbox 적재까지. RAG/Source Viewer E2E는 ADR-008 후속.**
- [x] **ISSUE-R2-CORS-001 수정**: R2 CORS 정책 미설정으로 브라우저 직접 PUT 차단 → 백엔드 프록시 업로드(`POST /upload/file`, BE→R2 경유)로 수정. TDD 3 테스트 추가 + FE 훅 전환 (commit 9a62d02 + 08cae59).

## Recently Completed — Sprint 9 오디오 파이프라인 수리 (2026-05-12)

- [x] **CRITICAL 버그 수정**: `MeetingPipelineService` BackgroundTask 세션 수명 버그 — request-scoped `AsyncSession`이 HTTP 응답 직후 닫혀 BackgroundTask가 실패하던 문제. `session_factory` 패턴으로 교체 (독립 세션 생성). `database.py` + `dependencies.py` + `pipeline_service.py` + `test_pipeline.py` 수정. 82 테스트 통과.
- [x] **D-11 해소**: `MeetingSummary.key_decisions / topics` 타입 어노테이션 `dict` → `list` 수정 (`models.py`).
- [x] **FE 폴링 수정**: `POLLING_STATUSES`에서 `"embedding"` 제거 (백엔드가 설정하지 않는 상태, `hooks.ts`).

## Recently Completed — Sprint 7 "guarded-doors" 잔여 (2026-05-11)

- [x] **BE-T4/T11/T5**: CORS exception handler — 5xx/4xx/422 응답에 CORS 헤더 보장 (c60ad90)
- [x] **BE-T12**: GET `/workspaces/{wid}/projects/{pid}` workspace mismatch 검증 추가 (2b7c2d4)
- [x] **BE-T6**: TestContainers PostgreSQL 통합 테스트 6개 시나리오 (d1e65e2)
  - add_member 성공 / cross-ws 403 / notfound 404 / ws-mismatch 404 / 중복 / GET mismatch
- [x] **BE-BUG-1**: ProjectRepository.add_member workspace_id 누락 수정 (d1e65e2 포함)
- [x] **T-DOC-1**: `docs/requirements/interview-guide.md` 신설 — ADR-011 §2 7필드 우회 질문 (c2e5198)
- [x] **erd.md + endpoints.md Atomic Update**: cross-workspace 주석(I-17) + BE-T12 GET 404 (c2e5198)
- [x] **AD-33**: cross-workspace ProjectMember 차단 완전 구현 (Sprint 7 BE-T1~T3 + T13 + T12 통합)

## In Progress

- (없음 — 다음 Next Actions 참조)

## Recently Completed — Sprint 6 Dogfooding + Critical 회귀 fix (2026-05-11, PR #14)

- [x] **Sprint 6 dogfooding 자동 검증** — Playwright MCP + BE API 직접 호출. owner 1 user 세션으로 8 케이스 자동 통과 (1G/1H/2A/3A/3B/3G + SETUP). 결과는 `docs/dev-log/sprint-6-dogfooding-matrix.md`.
- [x] **PR #14 fix(workspaces): timezone-naive 통일** — dogfooding에서 발견한 Critical 회귀 patch. `datetime.now(UTC)` → `datetime.utcnow()` (workspaces 모듈 3 파일). 회귀 시점 `da33af54` (2026-04-04, Sprint 4/5, **Sprint 6 무관**). 다른 도메인 모듈 패턴과 통일. 신규 사용자 가입 직후 워크스페이스 생성 정상화.

## Recently Completed — Sprint 6 멤버십 + Private 프로젝트 (2026-05-11, PR #12 머지)

- [x] **Sprint 6 — 멤버십 + Private 프로젝트** (ADR-009 F1 + ADR-014 옵션 A 적용, 11 commits)
  - [x] BE-T1~T3 Project.visibility 컬럼 + 마이그레이션 c4c5709a4ab4 (commit e779541)
  - [x] BE-T5~T8 + T15 ProjectMember 엔티티 + 마이그레이션 754f571d5544 + visibility 권한 분기 (commit cecc888)
  - [x] BE-T9~T14 notes/rag pipeline_service 도입 — D-2/D-3 부채 해소 1차 (commit 8096314)
  - [x] BE-T17~T19 WorkspaceInvite default_project_visibility + 마이그레이션 2d128def6779 (commit 05957c8)
  - [x] V-T1 backend test 회귀 fix (commit d5b325d, 65 passed)
  - [x] T-CONST-1 + T-CONST-2 헌법 §4.2/§7 갱신 + ADR-009 F8 closeout (commit 12f031b)
  - [x] FE-T1/T2a/T2b/T3/T5 visibility 배지 + 변경 모달 + 초대 default visibility (commit 575c613, 시안 1A+1C / 3A)
  - [x] FE-T4 Project 멤버 관리 패널 (commit 9a975e7, 시안 2A inline 단순화)
  - [x] FE-T7 RAG 검색 Private 자동 제외 안내 (commit 6e3f87f)
  - [x] **ADR-014 신설** (`docs/dev-log/014-service-boundary.md`) — service-to-service 경계 정책 (commit 038fe37, PR #11)
  - [x] **F10 closeout patch** — ADR-011 §1을 PERSONA- 접두사 권위 출처로 확정 (commit 589a1aa, PR #10)
  - [x] **docs Atomic Update retrofit** (commit b1b24a4) — Critical 5 + High 3 = 8 문서 동기화 (per-context CONTEXT.md + ERD + endpoints + cross-domain-pipeline + rag-pipeline + directory-map)

**Sprint 6 자의 결정 라벨**: AD-19~35 (`/Users/woosung/.claude/plans/sprint-6-vivid-clarke.md` §5 + ADR-014 §"자의 결정")
**시안 산출물**: `~/.gstack/projects/woosung-dev-kairos/designs/sprint-6-visibility-20260511/` (9 PNG + design-board.html + approved.json)

## Recently Completed — Phase A (Stage 0 헌법 retrofit, 2026-05-11)

- [x] **Phase A — Stage 0 헌법 retrofit** (커밋 `cea0be9`) — 워크플로우 `.ai/templates/workflow.md` Stage 0 retrofit 완료.
  - [x] `CONTEXT-MAP.md` 도메인 헌법 신규 (14 엔티티 + I-1~I-16 불변식 + D-1~D-11 부채 식별)
  - [x] per-context `CONTEXT.md` 7개 (frontend, backend 전역, meetings, inbox, rag, projects, actions)
  - [x] CONTEXT.md ↔ ERD ↔ PRD 정합 lock-in

## Recently Completed — Phase B Stage 1 retrofit (2026-05-11)

- [x] **Phase B Stage 1 — 메타 retrofit** — 워크플로우 `.ai/templates/workflow.md` 정식 Stage 1 (`/office-hours` → `/autoplan`) 누락분 retrofit 완료. 6 forcing question 결과 + product-first demand 시그널 정의 + thesis lock-in. **코드 변경 없음**.
  - [x] **ADR-010** Future-Fit Thesis (`docs/dev-log/010-future-fit-thesis.md`) — 9.2/10 PASS (Round 3). 3-year vision · 3 위협(ChatGPT/Notion AI/Granola) · 4 moat(M1~M4) · L4 timeline risk · AD-5~9 자의 라벨.
  - [x] **ADR-011** Persona Definition (`docs/dev-log/011-persona-definition.md`) — 9.25+/10 PASS (Round 2 + 라벨 동기화). 상태 라벨 4단계(interview-confirmed/self-confirmed/[가설]/deprecated) · 필수 필드 7개 · Wedge W1~W4 · 폐기 기준 a/b/c · AD-10~12 자의 라벨.
  - [x] **ADR-009** Stage 1 Retrofit 총괄 (`docs/dev-log/009-stage1-retrofit.md`) — 9.0/10 PASS + 3건 정정 = 9.5+. 6 Q 결과 매핑 · S1~S6 demand 시그널 + 60% 통일 · D-2/D-3 보류(AD-15) · 후속 F1~F10.
  - [x] **personas.md** (`docs/requirements/personas.md`) — 9.33/10 PASS + 4건 정정 = 9.5+. PERSONA-001 self-confirmed + PERSONA-002~003 `[가설]` + Wedge 매트릭스 분화 점검 + 후속 인터뷰 패치 절차.
  - [x] **competitive-analysis.md** (`docs/requirements/competitive-analysis.md`) — 9.3/10 PASS + 5건 정정 = 9.5+. 5개 경쟁자(Otter/Granola/Reflect/Mem/Tana) 4차원 비교 · ADR-010 moat 정렬 · AD-16~18.
  - [x] **PRD 4개 섹션 batch PATCH** (`docs/requirements/prd.md`) — 9.5/10 PASS + 4건 정정 = 9.7+. §2 Persona 보강 + §2.5 Competitive Analysis + §3.5 Future-Fit Thesis + §7.5 Demand Signal Definition.
  - [x] **TODO.md PATCH** (본 문서) — Stage 1 retrofit 완료 마크 + 후속 등재.

## Recently Completed (온보딩 직전 릴리즈 스프린트)

- [x] 랜딩 페이지 다크 모드 하이드레이션 수정 — `(landing)` · `(app)` · `(auth)` 라우트 그룹 분리 (커밋 `13d5041`, `117f920`)
- [x] Smart Inbox · 회의 상세 3뷰 · 프로젝트 대시보드 실 API 훅 전환 (커밋 `13d5041`)
- [x] Today 피드 mock→실 API 전환 + Dashboard 상단 병합 (커밋 `d8a6d27`)
- [x] 온보딩 템플릿 프로젝트 자동 시딩 — `create_workspace()` 가 🚀 시작하기 · 💡 아이디어 · 📋 회의록 3개 프로젝트 자동 생성 + OnboardingBanner 안내 개편 (커밋 `1e54a5c`)
- [x] 사이드바 소스 트리 + Source Viewer 실 API 연동 — meetings 엔드포인트에 projectId 필터 추가, 펼침 시 하위 회의/노트 실 데이터 렌더, SourceViewer가 `useMeetingDetail`/`useNote`로 풀콘텐츠 보강 (커밋 `7aea79b`)
- [x] **DevEx 이니셔티브 (ADR-008)** — Playwright E2E 환경(골든패스 2개), BE 배포 자동화(deploy.yml + WIF + Secret Manager 가이드), `test.yml` 에 e2e 잡 추가 (이번 커밋)
- [x] 문서 정합성 통합 정리 (ADR-006 기준 전체 문서 정렬)
  - [x] cross-domain-pipeline.md: Claude → Gemini 수정
  - [x] para-methodology.md: deprecated 배너 추가
  - [x] ui-ux-spec.md: ADR-006 기준 전면 재작성 (C|D 2-Panel, Today 피드, Inbox 2그룹, RAG 오버레이)
  - [x] directory-map.md: PARA 라우트 제거, [paraId]→[projectId]
  - [x] 001-tech-stack-decisions.md: PARA 섹션 superseded 표시
  - [x] mvp-phase1.md + second-brain.md: Inbox 정책 ADR-006 통일 (0.8→0.9)
  - [x] DESIGN.md: C|D 2-Panel 레이아웃 + Project Status Colors 전환
  - [x] erd.md: camelCase → snake_case 통일
  - [x] prd.md: Inbox 임계값 + Phase/Sprint/Stage 용어 매핑 추가
  - [x] README.md: ADR-006 문서 목록 추가

## Blocked

(없음)

## 미구현 (요청됨)

- [ ] **브라우저 마이크 직접 녹음** — `/new` 페이지에 파일 업로드 외에 실시간 녹음 탭 추가 필요. 인터뷰이-01 피드백 2026-05-12.

## Questions

- AI 모델 참조 통일 완료: Gemini `gemini-2.5-flash` 확정 (비용 사유)
  → `backend.md`, `global.md`에서 Anthropic → Gemini로 수정 완료

## Next Actions

### Sprint 12 — Architecture Deepening (BL 등재, 2026-05-12) ✅ 완료

- [x] **BL-003 등재** (rag/ 도메인) — `RagService._enrich_context` N+1 → `find_chunks_by_ids` 배치화. `docs/REFACTORING-BACKLOG.md` 등재 완료.
- [x] **BL-004 등재** (services/ 도메인) — co-change 재분석으로 발굴. `ai_processing.py` ↔ `common/prompts.py` 암묵적 JSON 계약 → Pydantic 경계 검증 추가. `docs/REFACTORING-BACKLOG.md` 등재 완료.
- [x] **meetings/ 도메인 audit** — BL-001 미실행 항목 이미 등재됨. export 중복 쿼리 발견, BL-001과 묶어 처리 결정. 추가 BL 불필요.
- 발굴 산출물: BL-003/BL-004 신규 등재. BL-002 완료 마킹. rag/services audit dev-log 신설.

### Sprint 13 — BL-003/004 구현 (2026-05-12) ✅ 완료 (PR #21 머지)

- [x] **BL-003 구현** — `EmbeddingRepository.find_chunks_by_ids()` 추가 + `_enrich_context` N+1 → 배치 1회. 테스트 3개 추가.
- [x] **BL-004 구현** — `MeetingSummaryResult` / `MeetingActionsResult` Pydantic 모델 추가 + `ai_processing.py` 경계 검증. 테스트 4개 추가.
- [x] **pyrightconfig.json** — backend/ + 루트 추가. IDE Pyright venv 경로 설정.
- 테스트: 신규 7개 추가 (BL-003: 3, BL-004: 4) / 전체 87 passed

### 진행 중 (ADR-008 DevEx 후속)

- [ ] **GCP WIF 초기 설정 + Secret Manager 9개 이관** (사용자 작업) — `docs/guides/deployment.md` §2.5.1 참조
- [ ] Clerk testing mode 계정 생성 + GitHub `E2E_*` Secrets 등록 (E2E 활성화)
- [x] **FE ↔ BE 오디오 파이프라인 E2E 검증** (업로드 → STT → Inbox — Sprint 9/10 완료, 2026-05-12)
- [ ] FE ↔ BE 전체 E2E 시나리오 (신규 계정 → 템플릿 프로젝트 3개 → RAG → `[1]` → Source Viewer 풀콘텐츠 렌더) — ADR-008 후속

### Sprint 6 잔여 (sprint 7+ 보류, AD-32~35) — 2026-05-11 dogfooding 결과 반영

- [ ] **AD-32** BE-T16 Project update 권한 강화 — 현재 require_member 유지 결정. creator-only 또는 admin 강화 필요 시 sprint 7+ 검토 (협업 마찰 우려).
- [x] **AD-33** ProjectMember 추가 cross-workspace 차단 — **Sprint 7 완료** (BE-T1~T3 + T12 + T13). FK violation 500 → 의도된 403으로 전환. TestContainers 통합 테스트 검증.
- [ ] **AD-34** FE RBAC 정밀 분기 — visibility 변경 버튼이 모든 멤버에 활성 + BE-T15 403 위임 (1차). useUser+useMembers 매칭으로 정밀화 = sprint 7+ design-review. dogfooding scope 외, sprint 7+ design-review 보류 **확정**.
- [ ] **AD-35** Playwright E2E (V-T2) + schemathesis (V-T4) + RAG 권한 누설 E2E (V-T5) — sprint 7+ devex-review와 묶음. **2026-05-11 dogfooding으로 1A~1F viewer/member 읽기 + 2D Private RAG 누설 + 2E/2F member/viewer visibility 변경 시도 + CORS-1 (BE 5xx CORS 헤더 누락) + SCHEMA-1 (Project `title` vs ERD `name` 정합성) 추가 묶음**.
- [x] **사용자 수동 dogfooding** — Playwright MCP 자동화로 진행 (8 케이스 자동 통과 + Critical TZ-1 회귀 발견 PR #14). 결과 `docs/dev-log/sprint-6-dogfooding-matrix.md`.

### Sprint 6 후속 docs (Medium 보류 4개 중 1개 완료)

- [x] **T-CONST-3** TODO.md Sprint 6 완료 마크 (본 patch)
- [ ] docs/requirements/prd.md — Sprint 6 phase 표 업데이트 (다음 sprint 또는 별도 patch)
- [ ] docs/requirements/second-brain.md §8 — visibility로 "개인↔팀 경계" 부분 해소 표기
- [ ] AGENTS.md — visibility 도메인 용어 추가 (작음)

### Phase B Stage 1 retrofit 후속 (ADR-009 §"후속" F1~F10)

- [ ] **F2** Demand 시그널 S1~S4 측정 (Sprint 6 완료 후 1개월) — usage analytics 도입 + S1(DAU)/S2(회의 빈도)/S3(RAG 만족도)/S4(Inbox 수용률) 실측. 결과물: demand 시그널 1차 보고서.
- [x] **F3** 외부 인터뷰 가이드 작성 — `docs/requirements/interview-guide.md` Sprint 7 T-DOC-1 완료 (c2e5198).
- [ ] **F4** 외부 인터뷰 5-10명 + S5/S6 측정 (진행 중, 2026-05-12 착수) — ADR-010 AD-8 60% + ADR-011 §4-b 60% + ADR-009 S5/S6. 결과물: `docs/requirements/interview-results.md`, ADR: `docs/dev-log/015-f4-demand-signals.md`.
- [ ] **F5** 5분 사용자 세션 관찰 도입 (Sprint 7+, Q5) — 도그푸딩 사용자 1-3명 세션 녹화. 결과물: `docs/requirements/observation-notes.md`.
- [ ] **F6** Wedge 선정 ADR 신규 (Sprint 6 완료 + F2/F4 결과 후) — 페르소나-Wedge 매트릭스 + S5/S6. 결과물: `docs/dev-log/012-wedge-selection.md`.
- [ ] **F7** L4 우선화 검토 ADR 신규 (Sprint 6 완료 + F4 결과 후) — ADR-010 §4 O1/O2/O3 옵션 선택 + ADR-007 Phase 4 진입 결정. 결과물: `docs/dev-log/013-l4-prioritization.md`.
- [ ] **F8** 부채 D-2/D-3 처리 ADR 신규 (Sprint 6 킥오프 시 결정 — 진입 직전 vs 완료 후) — service-to-service 경계 정책. 결과물: `docs/dev-log/014-service-boundary.md`.
- [ ] **F9** ADR-009 본 ADR 갱신 검토 (Sprint 7+ 외부 인터뷰 완료 후) — S1~S6 실측 결과로 임계값 재조정.
- [x] **F10** `.ai/common/global.md` §2 ID 체계 표 갱신 — `PERSONA-` 접두사 추가. Sprint 10 확인 (global.md line 47에 이미 존재, git-ignored 로컬 파일).

### `[가설]` 페르소나 패치 일정

- [ ] PERSONA-002 (김PM) — F4 외부 인터뷰 결과로 `interview-confirmed` 또는 `deprecated` 결정 (ADR-011 §4-b 60% / 3필드 임계값).
- [ ] PERSONA-003 (박PM) — 동상.

### 향후

- [ ] 내보내기 포맷 PDF (향후 구현)
