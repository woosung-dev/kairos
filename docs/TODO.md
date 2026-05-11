# Kairos TODO

> 마지막 업데이트: 2026-05-11
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

## In Progress

- (없음 — 다음 Next Actions 참조)

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

- (없음)

## Questions

- AI 모델 참조 통일 완료: Gemini `gemini-2.5-flash` 확정 (비용 사유)
  → `backend.md`, `global.md`에서 Anthropic → Gemini로 수정 완료

## Next Actions

### 진행 중 (ADR-008 DevEx 후속)

- [ ] **GCP WIF 초기 설정 + Secret Manager 9개 이관** (사용자 작업) — `docs/guides/deployment.md` §2.5.1 참조
- [ ] Clerk testing mode 계정 생성 + GitHub `E2E_*` Secrets 등록 (E2E 활성화)
- [ ] FE ↔ BE 실제 프로덕션 E2E 시나리오 검증 (신규 계정 → 템플릿 프로젝트 3개 확인 → 업로드 → STT → Inbox → 프로젝트 → RAG → `[1]` 클릭 → Source Viewer 풀콘텐츠 렌더)

### Sprint 6 진입 (Phase B Stage 1 retrofit 완료 후 정식 워크플로우 사이클 복귀)

- [ ] **Sprint 6 — 멤버십 + Private 프로젝트** (ADR-009 F1) — D-1 visibility 구현, WorkspaceMember 권한 분기, Private 프로젝트.
- [ ] 각 도메인 페이지 CRUD 버튼 세밀 역할 분기 (Member vs Admin)

### Phase B Stage 1 retrofit 후속 (ADR-009 §"후속" F1~F10)

- [ ] **F2** Demand 시그널 S1~S4 측정 (Sprint 6 완료 후 1개월) — usage analytics 도입 + S1(DAU)/S2(회의 빈도)/S3(RAG 만족도)/S4(Inbox 수용률) 실측. 결과물: demand 시그널 1차 보고서.
- [ ] **F3** 외부 인터뷰 가이드 작성 (Sprint 6 완료 직후) — ADR-011 §2 필수 필드 7개 + 승진/실패 우회 질문. 결과물: `docs/requirements/interview-guide.md`.
- [ ] **F4** 외부 인터뷰 5-10명 + S5/S6 측정 (Sprint 7+) — ADR-010 AD-8 60% + ADR-011 §4-b 60% + ADR-009 S5/S6. 결과물: `docs/requirements/interview-results.md`.
- [ ] **F5** 5분 사용자 세션 관찰 도입 (Sprint 7+, Q5) — 도그푸딩 사용자 1-3명 세션 녹화. 결과물: `docs/requirements/observation-notes.md`.
- [ ] **F6** Wedge 선정 ADR 신규 (Sprint 6 완료 + F2/F4 결과 후) — 페르소나-Wedge 매트릭스 + S5/S6. 결과물: `docs/dev-log/012-wedge-selection.md`.
- [ ] **F7** L4 우선화 검토 ADR 신규 (Sprint 6 완료 + F4 결과 후) — ADR-010 §4 O1/O2/O3 옵션 선택 + ADR-007 Phase 4 진입 결정. 결과물: `docs/dev-log/013-l4-prioritization.md`.
- [ ] **F8** 부채 D-2/D-3 처리 ADR 신규 (Sprint 6 킥오프 시 결정 — 진입 직전 vs 완료 후) — service-to-service 경계 정책. 결과물: `docs/dev-log/014-service-boundary.md`.
- [ ] **F9** ADR-009 본 ADR 갱신 검토 (Sprint 7+ 외부 인터뷰 완료 후) — S1~S6 실측 결과로 임계값 재조정.
- [ ] **F10** `.ai/common/global.md` §2 ID 체계 표 갱신 PR (본 retrofit 머지 직후) — `PERSONA-` 접두사 추가.

### `[가설]` 페르소나 패치 일정

- [ ] PERSONA-002 (김PM) — F4 외부 인터뷰 결과로 `interview-confirmed` 또는 `deprecated` 결정 (ADR-011 §4-b 60% / 3필드 임계값).
- [ ] PERSONA-003 (박PM) — 동상.

### 향후

- [ ] 내보내기 포맷 PDF (향후 구현)
