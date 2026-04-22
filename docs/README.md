# Kairos 문서 목차

## 구조

| 폴더             | 내용                                       |
| ---------------- | ------------------------------------------ |
| `requirements/`  | PRD, 기능 명세서, 유저 스토리              |
| `architecture/`  | 시스템 설계, ERD, 디렉토리 맵              |
| `api/`           | API 명세서, 프론트-백엔드 통신 규약        |
| `guides/`        | 로컬 환경 셋업, 배포, 트러블슈팅, 컨벤션  |
| `dev-log/`       | ADR (Architecture Decision Records)        |
| `superpowers/`   | Sprint 실행 계획(plans/) + 설계(specs/)    |
| `TODO.md`        | 작업 현황 (Completed/In Progress/Blocked)  |

## 문서 목록

### requirements/
- [PRD (전체 로드맵 Phase 1~4)](requirements/prd.md)
- [MVP Phase 1 기능 명세](requirements/mvp-phase1.md)
- [팀 세컨드 브레인 구현 상세](requirements/second-brain.md) — CODE 프레임워크 + 프로젝트 중심 구조
- [~~PARA 방법론~~](requirements/para-methodology.md) — *Deprecated: ADR-004에 의해 second-brain.md로 대체*
- [UI/UX 인터랙션 명세](requirements/ui-ux-spec.md) — ADR-006 기준 C|D 2-Panel, Today 피드, Inbox 2그룹, RAG 오버레이

### architecture/
- [디렉토리 구조 맵](architecture/directory-map.md)
- [데이터 모델 관계도 (ERD)](architecture/erd.md)
- [AI 파이프라인 명세](architecture/ai-pipeline.md) — 인제스트 파이프라인 (STT→요약→액션→프로젝트 연결→임베딩)
- [RAG 파이프라인 설계](architecture/rag-pipeline.md) — 검색 파이프라인 (하이브리드 검색, 계층적 청킹, Semantic Cache, Re-ranking)
- [데이터 흐름 예시](architecture/data-flow-example.md)
- [크로스 도메인 파이프라인](architecture/cross-domain-pipeline.md)
- [백엔드 초기 셋업 가이드](architecture/backend-scaffolding.md) — FastAPI + SQLModel + Alembic 프로젝트 구조

### api/
- [REST API 명세](api/endpoints.md) — 32개 엔드포인트 (Sprint 1~2 상세, 3~4 목록)

### guides/
- [로컬 개발 환경 셋업](guides/local-setup.md)
- [개발 방법론 (8 Stage)](guides/development-methodology.md) — AI 기반 1인 풀스택 개발 프로세스
- [AI 협업 세션 루틴](guides/session-routine.md) — 매 세션 시작/실행/마무리 패턴
- [배포 가이드](guides/deployment.md) — Vercel(FE) + GCP Cloud Run(BE)

### dev-log/
- [001: 기술 스택 선정](dev-log/001-tech-stack-decisions.md)
- [002: 실행 전략 — Vertical Slice Sprint 채택](dev-log/002-execution-strategy.md)
- [003: 디자인 도구 선정 — Stitch + Pencil + gstack 조합](dev-log/003-design-tools-decisions.md)
- [004: PARA → 팀 세컨드 브레인 방향 전환](dev-log/004-second-brain-pivot.md)
- [005: 랜딩 페이지 AIDA 리디자인](dev-log/005-landing-redesign-aida.md)
- [006: 서비스 전면 UI/UX 개편](dev-log/006-app-redesign-brainstorm.md) — C|D 2-Panel, Inbox 2그룹, RAG 오버레이 등 11개 결정
- [007: LLM Knowledge Base 패턴](dev-log/007-llm-knowledge-base-insight.md) — Karpathy 워크플로우 인사이트 → L3/L4 + 프로액티브 인사이트 구현 방법론
- [008: DevEx 이니셔티브](dev-log/008-devex-initiative.md) — Playwright E2E 골든패스 + GitHub Actions + WIF + Secret Manager 기반 BE 배포 자동화

### superpowers/ (Sprint 실행 기록)

> superpowers가 자동 생성한 Sprint 별 설계(specs/)와 실행 계획(plans/) 문서.

**specs/ (설계)**
- Phase 0 API 백엔드 설계, FE 리스캐폴딩 설계
- Sprint 1~4 설계 문서

**plans/ (실행)**
- Phase 0 API 백엔드, FE 리스캐폴딩 실행
- Sprint 1~4 실행 계획
