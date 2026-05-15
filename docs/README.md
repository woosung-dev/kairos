# Kairos 문서 목차

## 구조

| 폴더             | 내용                                       |
| ---------------- | ------------------------------------------ |
| `requirements/`  | PRD, 기능 명세서, 페르소나, 인터뷰         |
| `architecture/`  | 시스템 설계, ERD, 디렉토리 맵, 파이프라인  |
| `api/`           | API 명세서, 프론트-백엔드 통신 규약        |
| `guides/`        | 로컬 셋업, 배포, secrets, prompt, 세션 루틴 |
| `dev-log/`       | ADR (Architecture Decision Records) + Sprint plan/verification |
| `superpowers/`   | `superpowers:writing-plans` 스킬 자동 산출 — plans/ + specs/ (Sprint 단위 plan/design) |
| `_archive/`      | superseded/stale 문서 (검색 제외) — `_archive/README.md` 참조 |
| `TODO.md`        | 작업 현황 (Completed / In Progress / Blocked) |
| `REFACTORING-BACKLOG.md` | BL-NNN 리팩토링 백로그 (P0~P3 분류) |

> **본 색인이 active doc 의 유일한 entry point.** `_archive/` 는 history 보존용 — 검색 대상 아님.

## 문서 목록

### requirements/
- [PRD (전체 로드맵 Phase 1~4 + v3.0 §3.6 AI memory layer)](requirements/prd.md)
- [MVP Phase 1 기능 명세](requirements/mvp-phase1.md)
- [팀 세컨드 브레인 구현 상세](requirements/second-brain.md) — CODE 프레임워크 + 프로젝트 중심 구조
- [페르소나 정의](requirements/personas.md) — PERSONA-001 1인 풀스택 founder
- [인터뷰 가이드](requirements/interview-guide.md) + [인터뷰 결과](requirements/interview-results.md)
- [경쟁사 분석](requirements/competitive-analysis.md)
- [UI/UX 인터랙션 명세](requirements/ui-ux-spec.md) — ADR-006 기준 C|D 2-Panel, Today 피드, Inbox 2그룹, RAG 오버레이

### architecture/
- [디렉토리 구조 맵](architecture/directory-map.md)
- [데이터 모델 관계도 (ERD)](architecture/erd.md) — Sprint 15 memory_items / promote_audit 포함
- [AI 파이프라인 명세](architecture/ai-pipeline.md) — 인제스트 파이프라인 (STT→요약→액션→프로젝트 연결→임베딩)
- [RAG 파이프라인 설계](architecture/rag-pipeline.md) — 6-Layer (Cache → Query → Hybrid Search → Re-ranking → Generation → Cache Store)
- [크로스 도메인 파이프라인](architecture/cross-domain-pipeline.md) — pipeline_service.py 오케스트레이터 패턴
- [데이터 흐름 예시](architecture/data-flow-example.md)
- [백엔드 초기 셋업 가이드](architecture/backend-scaffolding.md) — FastAPI + SQLModel + Alembic

### api/
- [REST API 명세](api/endpoints.md) — Sprint 1~15 전체 endpoint 목록 (memory capture/recall/promote/metrics + R2 cleanup 포함)

### guides/
- [로컬 개발 환경 셋업](guides/local-setup.md)
- [배포 가이드](guides/deployment.md) — Vercel(FE) + GCP Cloud Run(BE)
- [Secrets 관리](guides/secrets.md) — env vars + GitHub secrets + GCP WIF
- [Prompt 환경 변수 문서](guides/prompt-env-docs.md)
- [R2 cleanup cron 가이드](guides/r2-cleanup-cron.md) — Cloud Scheduler 30일 voice cleanup
- [개발 방법론 (8 Stage)](guides/development-methodology.md) — AI 기반 1인 풀스택 개발 프로세스
- [AI 협업 세션 루틴](guides/session-routine.md) — 매 세션 시작/실행/마무리 패턴

### dev-log/

**ADR (Architecture Decision Records)**
- [001: 기술 스택 선정](dev-log/001-tech-stack-decisions.md)
- [002: 실행 전략 — Vertical Slice Sprint 채택](dev-log/002-execution-strategy.md)
- [003: 디자인 도구 선정 — Stitch + Pencil + gstack 조합](dev-log/003-design-tools-decisions.md)
- [004: PARA → 팀 세컨드 브레인 방향 전환](dev-log/004-second-brain-pivot.md)
- [005: 랜딩 페이지 AIDA 리디자인](dev-log/005-landing-redesign-aida.md)
- [006: 서비스 전면 UI/UX 개편](dev-log/006-app-redesign-brainstorm.md) — C|D 2-Panel, Inbox 2그룹, RAG 오버레이 11개 결정
- [007: LLM Knowledge Base 패턴](dev-log/007-llm-knowledge-base-insight.md) — Karpathy 워크플로우 → L3/L4 + 프로액티브 인사이트
- [008: DevEx 이니셔티브](dev-log/008-devex-initiative.md) — Playwright E2E + GitHub Actions + WIF + Secret Manager
- [009: Stage 1 retrofit](dev-log/009-stage1-retrofit.md)
- [010: Future-fit thesis](dev-log/010-future-fit-thesis.md)
- [011: 페르소나 정의](dev-log/011-persona-definition.md)
- [014: 서비스 경계 (Service boundary)](dev-log/014-service-boundary.md)
- [015: F4 수요 신호 (Demand signals)](dev-log/015-f4-demand-signals.md)
- [016: Personal ↔ Team IA + Promotion flow](dev-log/016-personal-team-ia.md) — Sprint 15
- [019: Gemini EOL 마이그레이션 (2.5-flash → 3.1-flash-lite)](dev-log/019-gemini-eol-migration.md) — Sprint 15 Phase A spike validated

**Sprint plan / verification**
- [Sprint 6 dogfooding matrix](dev-log/sprint-6-dogfooding-matrix.md)
- [Sprint 14 plan](dev-log/sprint-14-plan.md)
- [Sprint 15 plan](dev-log/sprint-15-plan.md) — Personal workspace + Memory module + Recall-first wedge
- [Sprint 15 verification](dev-log/sprint-15-verification.md)
- [Sprint 15 R8 outreach 로그](dev-log/sprint-15-r8-outreach.md) — 14일 stagger 진행 doc
- [Sprint 15 R8 Day 14 retro template](dev-log/sprint-15-r8-day14-retro-template.md)
- [Sprint 16 plan draft](dev-log/2026-05-14-sprint16-plan-draft.md) — R8 결과 분기 매트릭스

**Architecture deepening (Sprint 12)**
- [Meetings deepen audit](dev-log/2026-05-12-meetings-deepen.md) + [Sprint 12 분](dev-log/2026-05-12-meetings-deepen-sprint12.md)
- [RAG deepen audit](dev-log/2026-05-12-rag-deepen.md)
- [Services deepen audit](dev-log/2026-05-12-services-deepen.md)

**Multi-agent QA (Sprint 13)**
- [Multi-agent QA reports](dev-log/2026-05-13-multi-agent-qa/) — Sentinel / Curious / Casual 3축 통합 검증

### superpowers/ (Sprint 자동 산출)

> `superpowers:writing-plans` + `superpowers:executing-plans` / `subagent-driven-development` 스킬이 Sprint 진행 시 자동 생성.
> `plans/YYYY-MM-DD-<topic>.md` (실행 계획 + Task 의존도) + `specs/YYYY-MM-DD-<topic>-design.md` (설계 결정).
> 산출물은 그대로 유지 — 스킬이 다시 호출되면 동일 위치에 누적.

### _archive/ (보관)

> 2026-05-15 Sprint 18 PR-B 에서 stale 문서 분리. 진입 색인에서 제외, history 보존.
> 자세한 이동 이력은 [`_archive/README.md`](_archive/README.md) 참조.

### Meta docs

- [TODO.md](TODO.md) — 작업 현황 (Completed / Blocked / Questions / Next Actions)
- [REFACTORING-BACKLOG.md](REFACTORING-BACKLOG.md) — BL-001~021 리팩토링 백로그 (P0~P3 분류)

## 헌법 + 도메인 CONTEXT

본 docs/ 외부에 위치하지만 진입점:
- [`CONTEXT-MAP.md`](../CONTEXT-MAP.md) — 도메인 경계 + 핵심 불변식 (I-1 ~ I-21) + §9 Atomic Update 강제
- [`DESIGN.md`](../DESIGN.md) — 디자인 시스템 (Industrial/Utilitarian)
- 도메인별 `backend/src/<domain>/CONTEXT.md` (workspaces, projects, meetings, notes, inbox, rag, embeddings, memory)
