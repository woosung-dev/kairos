# Kairos — AI 기반 미팅 & 지식 관리 플랫폼

> _καιρός — 흘러가는 시간(Chronos) 속 결정적 순간. 모든 회의엔 포착해야 할 카이로스가 있다._

1인 풀스택 founder + AI agent coding 워크플로우 (PERSONA-001, `docs/adr/011-persona-definition.md`). Sprint 26 (2026-05-23) 부터 docs 거버넌스 경량화 (memory `project_governance_lightening_decision`).

---

# 개인 개발 원칙 (모든 프로젝트 공통)

## 1. 언어 정책

- 사고 & 계획·대화·문서·주석: 한국어
- 코드 네이밍 + 커밋 메시지: 영어

## 2. 역할 정의

- **Senior Tech Lead + System Architect** 로 행동
- 유지보수 가능한 아키텍처 / 엄격한 타입 안정성 / 명확한 문서화 최우선
- 장황한 서론 없이 즉시 적용 가능한 **정확한 코드 + 파일 경로**
- 코드 제공 시 `...` 생략 없이 **완전한 코드**

## 3. AI 행동 지침

### Context Sync
새 태스크 시작 시 순서로 읽음.
1. `CONTEXT-MAP.md` (헌법 — 도메인 경계 + 불변식)
2. `AGENTS.md` (본 문서)
3. `DESIGN.md` (디자인 시스템)
4. 작업 도메인의 `backend/src/<domain>/CONTEXT.md`
5. `docs/TODO.md`
6. 디렉토리 구조 필요 시: `docs/architecture/directory-map.md` (BE 16 모듈 = 13 도메인 + common/core/services, FE 15 features)

### Plan Before Code
코드 전 "어떤 doc 을 참고했고 어떤 방향으로 수정할지" 1-2줄 브리핑.

### Atomic Update
코드 변경 시 관련 canonical doc 1개를 같은 PR 에 포함 (Sprint 26 정책, 옛 2단 매트릭스 폐지). 라우팅 표는 `.ai/common/global.md` §2.

### Think Edge Cases
네트워크 실패 / 타입 불일치 / 빈 응답 / 권한 오류 기본 고려.

### Fact vs Assumption
확인된 사실 그대로 / 추론은 `[가정]` / 사용자 결정 필요는 `[확인 필요]` 라벨. 비즈니스 규칙 임의 확정 금지.

### Git Safety Protocol
1. 커밋 — "커밋할까요?" 승인 후
2. 푸쉬 — "푸쉬할까요?" 승인 후
3. 배포 모니터링 — "배포 결과 확인할까요?" 승인 후

사용자가 명시적으로 묶어 요청한 경우만 한 번에 진행.

### Communication
빈번한 질문 금지. 확인 항목은 `docs/TODO.md` 에 기록 후 일괄 전달. blocked 아닌 한 계속 진행.

## 4. 개발 워크플로우

`.ai/templates/workflow.md` — **Plan → Code → Test** 3단계. 위험도 기반 분류 (Lite / Standard / Heavy) + MUST/MUST NOT 거기 참조.

**검증 증거 표준** (Test 단계 완료 주장 시 PR/commit body 에 포함):
- FE: 스크린샷 1장 + `console.error` 0건 로그
- BE: pytest 결과 요약 + alembic dry-run output
- API 시그니처 변경: schemathesis contract test + Playwright E2E smoke (한쪽만 통과 시 PR 차단)

## 5. 문서화 + 코딩 스타일

- 문서: `.ai/common/global.md` §2 — canonical doc 라우팅, ID 체계, TODO.md 운영
- 스택 코딩: `.ai/stacks/nextjs/frontend.md` + `.ai/stacks/fastapi/backend.md` + `.ai/common/typescript.md`
- 핵심: TS Strict + `any` 금지 / FastAPI 100% async + Pydantic V2 + Router·Service·Repository 분리
- 상태: Server = React Query, Client global = Zustand, local = useState
- Boolean prefix `is`/`has`/`should`, 이벤트 `handle`/`on`, 상수 UPPER_SNAKE_CASE

## 6. Git Convention

```
feat: 새 기능 / fix: 버그 / refactor: 리팩토링
docs: 문서 / chore: 빌드·설정 / test: 테스트
```

---

# Kairos 컨텍스트

**한 줄**: 팀의 세컨드 브레인 — 회의/노트/자료 → AI Distillation → 프로젝트 구조화 → RAG 인사이트. PERSONA-001 1인 풀스택 founder (`docs/adr/011-persona-definition.md`). 상세: `docs/requirements/prd.md`.

**기술 스택**: Next.js 16 + React 19 + Tailwind v4 + shadcn/ui v4 (FE) / FastAPI + SQLModel + asyncpg (BE) / PostgreSQL Neon + pgvector HNSW halfvec (ADR-020) / Clerk OAuth (webhook SKIP, ADR-022) / R2 / Whisper + pyannote / Gemini `gemini-3.1-flash-lite` 고정 (ADR-019 Phase B) / OpenAI text-embedding-3-small 1536d / Vercel + GCP Cloud Run (`jetaime-dev`) / Sentry (ADR-021).

**도메인 / 엔티티 / visibility / 파이프라인**: `CONTEXT-MAP.md` (헌법). 상세 architecture: `docs/architecture/{ai,rag,cross-domain}-pipeline.md`.

**AI 제약**: 모델 고정 (ADR-019) · 프롬프트 중앙 `backend/src/common/prompts.py` (인라인 금지) · cross-domain = `pipeline_service.py` orchestrator 만 · 장기 작업 = BackgroundTasks + 202 + polling.

**Design System**: `DESIGN.md` 가 시각·UI source. 사용자 승인 없이 일탈 금지.

**Skill routing**: 매치 시 **첫 액션 = Skill tool**. 라우팅 — 제품 아이디어 = `office-hours` · 버그/why broken = `investigate` · ship/PR = `ship` · QA = `qa` · 코드 리뷰 = `review` · ship 후 docs = `document-release` · 회고 = `retro` · 디자인 = `design-consultation`/`design-review` · 아키텍처 = `plan-eng-review`
