# Kairos TODO

> 마지막 업데이트: 2026-04-05 (Sprint 6 완료)
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
- [x] Sprint 6: 온보딩 준비 — 실사용 품질 달성 [검증됨 2026-04-05 — 빌드 통과]
  - [x] 전 도메인 mutation toast (notes/actions/projects/meetings)
  - [x] Quick Memo mock→Real API 전환 (useNotes + useCreateNote)
  - [x] Viewer 역할 차단 — 액션 칸반 드래그, 회의 액션 체크박스
  - [x] Viewer 역할 차단 — 프로젝트 생성/추가/온보딩 버튼 숨김
  - [x] Viewer 역할 차단 — Inbox 확정/수정/무시 버튼 숨김

## In Progress

- [/] **ADR-006 서비스 전면 UI/UX 개편 — 부분 구현 (7/11 완료, 4/11 부분)**
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
  - [x] Inbox 신뢰도 임계값 설정 UI (Settings 페이지 완료)
  - [ ] 온보딩 템플릿 프로젝트 자동 생성 (백엔드 필요)
  - [x] 내보내기 포맷 (MD/JSON — 회의/노트 완료, PDF는 P2)
- [x] 랜딩 페이지 QA — suppressHydrationWarning 이미 적용 확인, 빌드 통과
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

- [x] ~~ADR-006 핵심 UX 마무리 (P0)~~
  - [x] ~~사이드바 소스 트리 펼침~~
  - [x] ~~[1] 클릭 → 소스 뷰어 열림 flow 연결~~
- [x] ~~프론트엔드 `.env.example` 생성~~ (이미 존재 확인)
- [ ] E2E 테스트 환경 구축
- [ ] Phase 2 잔여: 프론트엔드 ↔ 백엔드 실제 연동 검증 (Quick Memo 완료, 나머지 도메인)
- [ ] Sprint 7 계획 (프로젝트 멤버십 + Private 프로젝트)
- [x] ~~각 도메인 페이지 CRUD 버튼 세밀 역할 분기 (Member vs Admin)~~ Sprint 6 완료
- [ ] Header 멤버 수 뱃지
- [x] ~~mutation 에러 toast 피드백~~ Sprint 6 완료
- [ ] 온보딩 템플릿 프로젝트 자동 생성 (백엔드 필요)
- [ ] PDF 내보내기
