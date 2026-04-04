# Kairos TODO

> 마지막 업데이트: 2026-04-04
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
- [x] Sprint 1 BE: 백엔드 스캐폴딩 + 핵심 도메인 CRUD + Auth [가정]
- [x] Sprint 2: AI 파이프라인 + 프론트엔드 API 연동 [가정]
- [x] Sprint 3: RAG + 노트 [가정]
- [x] Sprint 4: 배포 설정 [가정]

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
  - [ ] **⚠️ 사이드바 소스 트리 펼침** — 프로젝트 클릭 시 하위 회의/노트/파일 목록
  - [ ] **⚠️ [1] 클릭 → 소스 뷰어 열림 flow 연결** — 컴포넌트 있으나 호출 미연결
  - [ ] Inbox 신뢰도 임계값 설정 UI (하드코딩 상태)
  - [ ] 온보딩 템플릿 프로젝트 자동 생성 (백엔드 필요)
  - [ ] 내보내기 포맷 (MD/PDF/JSON)
- [/] 랜딩 페이지 QA — 다크 모드 하이드레이션 미스매치 수정 필요
- [/] 워크플로우 · 문서 체계 고도화

## Blocked

- (없음)

## Questions

- AI 모델 참조 통일 완료: Gemini `gemini-2.5-flash` 확정 (비용 사유)
  → `backend.md`, `global.md`에서 Anthropic → Gemini로 수정 완료

## Next Actions

- [ ] 프론트엔드 `.env.example` 생성
- [ ] E2E 테스트 환경 구축
- [ ] Phase 2 잔여: 프론트엔드 ↔ 백엔드 실제 연동 검증
- [ ] 다음 Sprint 계획 (Stage 4)
