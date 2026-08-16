# Kairos 문서 목차

## 구조

| 폴더             | 내용                                       |
| ---------------- | ------------------------------------------ |
| `requirements/`  | PRD, 기능 명세서, 페르소나, 인터뷰         |
| `architecture/`  | 시스템 설계, ERD, 디렉토리 맵, 파이프라인  |
| `api/`           | API 명세서, 프론트-백엔드 통신 규약        |
| `guides/`        | 로컬 셋업, 배포, secrets, prompt, 세션 루틴 |
| `adr/`           | Architecture Decision Records (Nygard 포맷) |
| `plans/active/`  | 현재 활성 계획과 작업 추적 문서 |
| `TODO.md`        | 작업 현황 (Completed / Blocked / Questions / Next Actions) |
| `REFACTORING-BACKLOG.md` | BL-NNN 리팩토링 백로그 + "다음 Sprint 진입점" anchor |

> **본 색인이 active doc 의 유일한 entry point.** stale 문서는 즉시 `git rm` (history 는 git log 로 복구).
> Sprint 26 (2026-05-23) 부터 dev-log/ 폐지 — sprint-별 handoff/closeout/verification 작성 안 함.
> 2026-06-23 cleanup 부터 historical audit/sprint/superpowers 산출물은 git history와 PR body로 보존한다.

## 문서 목록

### requirements/
- [PRD (전체 로드맵 Phase 1~4)](requirements/prd.md)
- [MVP Phase 1 기능 명세](requirements/mvp-phase1.md)
- [팀 세컨드 브레인 구현 상세](requirements/second-brain.md) — CODE 프레임워크
- [페르소나 정의](requirements/personas.md) — PERSONA-001 1인 풀스택 founder
- [인터뷰 가이드](requirements/interview-guide.md) + [결과](requirements/interview-results.md)
- [경쟁사 분석](requirements/competitive-analysis.md)
- [UI/UX 인터랙션 명세](requirements/ui-ux-spec.md)

### architecture/
- [디렉토리 구조 맵](architecture/directory-map.md)
- [데이터 모델 관계도 (ERD)](architecture/erd.md)
- [AI 파이프라인 명세](architecture/ai-pipeline.md)
- [RAG 파이프라인 설계](architecture/rag-pipeline.md) — 6-Layer
- [크로스 도메인 파이프라인](architecture/cross-domain-pipeline.md) — pipeline_service.py 오케스트레이터
- [데이터 흐름 예시](architecture/data-flow-example.md)
- [백엔드 초기 셋업 가이드](architecture/backend-scaffolding.md)

### api/
- [REST API 명세](api/endpoints.md)

### guides/
- [로컬 개발 환경 셋업](guides/local-setup.md)
- [배포 가이드](guides/deployment.md) — Vercel(FE) + GCP Cloud Run(BE)
- [Secrets 관리](guides/secrets.md)
- [Prompt 환경 변수 문서](guides/prompt-env-docs.md)
- [R2 cleanup cron 가이드](guides/r2-cleanup-cron.md)
- ~~개발 방법론 (`development-methodology.md`)~~ — 옛 8-Stage 프레임워크. Sprint 26 (2026-05-23) 폐지,
  2026-08-15 삭제 ([ADR-029](adr/029-ai-rules-relocation.md)). 현행 워크플로우는 `AGENTS.md` §4. 원문 = git history @ `e419acd`
- [AI 협업 세션 루틴](guides/session-routine.md)

### adr/
`docs/adr/NNN-<slug>.md` (Nygard 포맷). 예: 011 페르소나 정의, 020 pgvector HNSW halfvec, 027 apps 모노레포 + 계약 거버넌스, 028 OCI 셀프호스팅, 029 `.ai/` 해체 → 디렉터리별 AGENTS.md. 전체 목록은 `ls docs/adr/`.

### plans/active/
현재 진행 sprint plan. 폴더 README 참조.

## 헌법 + 도메인 CONTEXT

본 docs/ 외부에 위치하지만 진입점:
- [`CONTEXT-MAP.md`](../CONTEXT-MAP.md) — 도메인 경계 + 핵심 불변식 (I-1 ~ I-21) + §9 문서 갱신 원칙
- [`DESIGN.md`](../DESIGN.md) — 디자인 시스템
- 도메인별 `apps/api/src/<domain>/CONTEXT.md` (workspaces, projects, meetings, notes, inbox, rag, embeddings, memory)
