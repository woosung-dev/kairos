# Kairos 문서 목차

> **본 색인이 active doc 의 유일한 entry point 다.** 여기에 없는 문서는 없는 문서다 —
> stale 해지면 색인에 추가하거나 즉시 `git rm` 한다 (history 는 `git log` 로 복구).

## 구조

| 폴더 | 내용 | 독자 |
|---|---|---|
| `development/` | 로컬 셋업, 테스트, 마이그레이션, 시크릿, 세션 루틴 | 개발자 |
| `operations/` | 배포, 재인덱싱, 정리 작업, 장애 런북 | 운영자 |
| `architecture/` | 현재 시스템이 어떻게 동작하는가 — ERD, 파이프라인, 디렉터리 맵 | 둘 다 |
| `adr/` | 왜 그렇게 결정했는가 — Architecture Decision Records | 둘 다 |
| `product/` | 도메인 용어 색인 + 도메인 인덱스 (정의는 헌법이 소유) | 둘 다 |
| `api/` | API 문서 라우팅 (계약 생성물은 `contracts/`) | 둘 다 |
| `requirements/` | PRD, 기능 명세, 페르소나, 인터뷰, 경쟁사 | 제품 |
| `plans/active/` | 진행 중 sprint plan | 제품 |
| `archive/` | 완료 이력 (TODO / 백로그). **역사 기록 — 소급 수정하지 않는다** | — |
| `TODO.md` | 열린 작업만 (Blocked / Questions / Next Actions) | — |
| `REFACTORING-BACKLOG.md` | 미해소 BL-NNN + "다음 Sprint 진입점" anchor | — |

---

## development/

- [로컬 개발 환경 셋업](development/getting-started.md) — 클론부터 화면이 뜰 때까지
- [**테스트 가이드**](development/testing.md) — 게이트 ↔ CI job 대응표, arch gate, team e2e
- [**마이그레이션**](development/migrations.md) — alembic 규약, 2단계 배포와 그 예외, downgrade 금지
- [Secrets 관리](development/secrets.md) — 환경변수 전체 매트릭스 (로컬/CI/프로덕션)
- [Prompt 환경 변수 문서](development/prompt-env.md)
- [AI 협업 세션 루틴](development/session-routine.md)

## operations/

- [운영 문서 라우팅](operations/README.md) — 서버 런북 정본은 `deploy/oci/README.md`
- [배포 가이드](operations/deployment.md) — **Oracle Cloud A1 + Cloudflare Tunnel** ([ADR-028](adr/028-oci-selfhosting.md))
- [런북: 파이프라인 고착](operations/runbooks/stuck-pipeline.md) — `transcribing`/`analyzing` 정지 복구
- [pgvector 재인덱싱](operations/pgvector-reindex.md)
- [R2 cleanup](operations/r2-cleanup-cron.md)

## architecture/

- [디렉터리 구조 맵](architecture/directory-map.md)
- [**아키텍처 다이어그램 (archify)**](architecture/diagrams/README.md) — 아키텍처 3종(시스템 · 데이터 모델 · 모노레포, 노드마다 레포 근거 `SRC`) + 흐름 4종(AI 데이터 흐름 · RAG 시퀀스 · 회의 상태 전이 · 배포 워크플로우). 인터랙티브 HTML + PNG + 사양 JSON
- [데이터 모델 관계도 (ERD)](architecture/erd.md)
- [AI 파이프라인 명세](architecture/ai-pipeline.md)
- [RAG 파이프라인 설계](architecture/rag-pipeline.md) — 6-Layer
- [크로스 도메인 파이프라인](architecture/cross-domain-pipeline.md) — `pipeline_service.py` 오케스트레이터
- [데이터 흐름 예시](architecture/data-flow-example.md)
- [백엔드 초기 셋업 가이드](architecture/backend-scaffolding.md)

## product/

- [용어집](product/glossary.md) — 색인. 정의의 SSOT 는 `CONTEXT-MAP.md`
- [도메인 인덱스](product/domains/README.md) — BE 도메인 ↔ FE feature 매핑

## api/

- [API 문서 라우팅](api/README.md) — 계약 정본은 `contracts/openapi/v1/openapi.json`

## requirements/

- [PRD (전체 로드맵 Phase 1~4)](requirements/prd.md)
- [MVP Phase 1 기능 명세](requirements/mvp-phase1.md)
- [팀 세컨드 브레인 구현 상세](requirements/second-brain.md) — CODE 프레임워크
- [페르소나 정의](requirements/personas.md) — PERSONA-001 1인 풀스택 founder
- [인터뷰 가이드](requirements/interview-guide.md) + [결과](requirements/interview-results.md)
- [경쟁사 분석](requirements/competitive-analysis.md)
- [UI/UX 인터랙션 명세](requirements/ui-ux-spec.md)

## adr/

`docs/adr/NNN-<slug>.md` (Nygard 포맷). 번호는 재사용하지 않는다 — 갭 사유는
[`000-adr-gap-log.md`](adr/000-adr-gap-log.md). 전체 목록은 `ls docs/adr/`.

최근: [027](adr/027-apps-monorepo-and-contract-governance.md) apps 모노레포 + 계약 거버넌스 ·
[028](adr/028-oci-selfhosting.md) OCI 셀프호스팅 ·
[029](adr/029-ai-rules-relocation.md) `.ai/` 해체 → 디렉터리별 AGENTS.md ·
[030](adr/030-apps-api-rename.md) `apps/backend` → `apps/api`

## plans/active/

진행 중 sprint plan. 정책은 [폴더 README](plans/active/README.md).

---

## 헌법 + 도메인 CONTEXT (docs/ 밖이지만 진입점)

- [`CONTEXT-MAP.md`](../CONTEXT-MAP.md) — **도메인 헌법**. 엔티티 + 별칭 금지 + 불변식 I-1~I-22 + §9 문서 갱신 원칙.
  **도메인 용어(glossary)의 정본이 여기다**
- [`AGENTS.md`](../AGENTS.md) — 개발 원칙 + Atomic Update 라우팅 표
- [`DESIGN.md`](../DESIGN.md) — 디자인 시스템 (시각·UI 정본)
- [`apps/api/CONTEXT.md`](../apps/api/CONTEXT.md) · [`apps/web/CONTEXT.md`](../apps/web/CONTEXT.md) — 스택별 불변식 (B-NN / F-NN)
- `apps/api/src/<domain>/CONTEXT.md` — 도메인별 상세 ([인덱스](product/domains/README.md))
- [`deploy/oci/README.md`](../deploy/oci/README.md) — **서버 운영 런북 정본**
- [`contracts/README.md`](../contracts/README.md) — API 계약 생성물 규약

## 폐지된 것

- `docs/guides/` — 2026-08-16 해체 → `development/` + `operations/`
- `docs/dev-log/` — Sprint 26 (2026-05-23) 폐지 선언, 2026-08-16 잔존물 삭제.
  historical 산출물은 git history + PR body 로 보존한다
- `docs/wireframes/` — 2026-08-16 삭제. 시각 정본은 `DESIGN.md`
- `docs/api/endpoints.md` — 2026-08-13 동결, 2026-08-16 삭제. 정본은 `contracts/`
