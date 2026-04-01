# Kairos 문서 목차

## 구조

| 폴더             | 내용                                       |
| ---------------- | ------------------------------------------ |
| `requirements/`  | PRD, 기능 명세서, 유저 스토리              |
| `architecture/`  | 시스템 설계, ERD, 디렉토리 맵              |
| `api/`           | API 명세서, 프론트-백엔드 통신 규약        |
| `guides/`        | 로컬 환경 셋업, 배포, 트러블슈팅, 컨벤션  |
| `dev-log/`       | ADR (Architecture Decision Records)        |

## 문서 목록

### requirements/
- [PRD (전체 로드맵 Phase 1~4)](requirements/prd.md)
- [MVP Phase 1 기능 명세](requirements/mvp-phase1.md)
- [PARA 방법론 구현 상세](requirements/para-methodology.md)
- [UI/UX 인터랙션 명세](requirements/ui-ux-spec.md)

### architecture/
- [디렉토리 구조 맵](architecture/directory-map.md)
- [데이터 모델 관계도 (ERD)](architecture/erd.md)
- [AI 파이프라인 명세](architecture/ai-pipeline.md) — 인제스트 파이프라인 (STT→요약→액션→PARA→임베딩)
- [RAG 파이프라인 설계](architecture/rag-pipeline.md) — 검색 파이프라인 (하이브리드 검색, 계층적 청킹, Semantic Cache, Re-ranking)
- [데이터 흐름 예시](architecture/data-flow-example.md)
- [크로스 도메인 파이프라인](architecture/cross-domain-pipeline.md)
- [백엔드 초기 셋업 가이드](architecture/backend-scaffolding.md) — FastAPI + SQLModel + Alembic 프로젝트 구조

### api/
- [REST API 명세](api/endpoints.md) — 32개 엔드포인트 (Sprint 1~2 상세, 3~4 목록)

### guides/
- [로컬 개발 환경 셋업](guides/local-setup.md)
- [개발 방법론 (8 Stage)](guides/development-methodology.md) — AI 기반 1인 풀스택 개발 프로세스

### dev-log/
- [001: 기술 스택 선정](dev-log/001-tech-stack-decisions.md)
- [002: 실행 전략 — Vertical Slice Sprint 채택](dev-log/002-execution-strategy.md)
- [003: 디자인 도구 선정 — Stitch + Pencil + gstack 조합](dev-log/003-design-tools-decisions.md)
