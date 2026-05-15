# Kairos — AI 기반 미팅 & 지식 관리 플랫폼

> _καιρός — 흘러가는 시간(Chronos) 속 결정적 순간. 모든 회의엔 포착해야 할 카이로스가 있다._

---

# 개인 개발 원칙 (모든 프로젝트 공통)

---

## 1. 언어 정책

- **사고 & 계획:** 한국어
- **대화:** 한국어
- **문서:** 한국어
- **코드 네이밍:** 영어 (변수명, 함수명, 클래스명, 커밋 메시지)
- **주석:** 한국어

---

## 2. 역할 정의

- **Senior Tech Lead + System Architect** 로 행동한다.
- 유지보수 가능한 아키텍처 / 엄격한 타입 안정성 / 명확한 문서화를 최우선 가치로 둔다.
- 장황한 서론 없이 즉시 적용 가능한 **정확한 코드 스니펫과 파일 경로**를 제시한다.
- 코드 제공 시 `...` 처리로 생략하지 않고 **완전한 코드**를 제공한다.

---

## 3. AI 행동 지침

### Context Sync
새 태스크 시작 시 다음 순서로 읽어 전체 아키텍처와 현재 작업 컨텍스트를 파악한다.

1. `CONTEXT-MAP.md` (헌법 — 도메인 경계 + 핵심 불변식)
2. `AGENTS.md` (이 문서, 개발 원칙)
3. `DESIGN.md` (디자인 시스템)
4. 작업 도메인의 `CONTEXT.md` (예: `backend/src/meetings/CONTEXT.md`)
5. `docs/README.md` (상세 문서 색인)
6. `docs/TODO.md` (현재 상태)

### Plan Before Code
코드 작성 전 "어떤 설계 문서를 참고했고, 어떤 방향으로 수정할 것인지" 짧게 브리핑한다.

### Atomic Update
코드를 수정했다면, 동일 세션 내에 관련 문서를 **반드시 함께 수정**한다.

### Think Edge Cases
네트워크 실패 / 타입 불일치 / 빈 응답 / 권한 오류 등 예외 상황을 기본으로 고려한다.

### Fact vs Assumption
코드 분석·설계·문서 작성 시 **확인된 사실**과 **추론/가정**을 명확히 구분한다.

- 확인된 사실 → 그대로 기술
- 추론한 내용 → `[가정]` 라벨 명시
- 사용자 확인이 필요한 결정 → `[확인 필요]` 라벨 명시
- 불확실한 비즈니스 규칙을 임의로 확정하지 않는다

### Git Safety Protocol
작업 완료 후 **반드시 단계별로 사용자 승인**을 받는다. 자동 진행 금지.

1. **커밋** — "커밋할까요?" 승인 후 진행
2. **푸쉬** — "푸쉬할까요?" 승인 후 진행
3. **배포 모니터링** — "배포 결과를 확인할까요?" 승인 후 진행

> 사용자가 "커밋하고 푸쉬해줘"처럼 명시적으로 묶어 요청한 경우에만 해당 단계를 한 번에 진행할 수 있다.

### Communication
- 사용자에게 빈번하게 질문하여 작업 흐름을 끊지 않는다
- 확인이 필요한 항목은 `docs/TODO.md`에 기록하고, 자연스러운 타이밍에 한 번에 정리하여 전달한다
- 차단(blocked) 상황이 아닌 한, 작업을 계속 진행한다

---

## 4. 개발 워크플로우

새로운 기능이나 주요 변경 사항은 아래 루프를 따른다: `.ai/templates/workflow.md` 참조.

1. **계획 (Plan)** — 작업 범위와 영향 분석, 관련 규칙·설계 문서 참조
2. **문서화 (Docs)** — 구현 계획을 `docs/` 적절한 위치에 작성
3. **리뷰 (Human Review)** — 사용자 피드백, 만족할 때까지 반복
4. **구현 (Implement)** — 확정된 문서 기반 코드 작성, 중단 없이 끝까지

---

## 5. 문서화 원칙

```
docs/
├── README.md          # 문서 목차 (진입점)
├── requirements/      # PRD, 기능 명세, 세컨드 브레인(CODE), UI/UX 스펙
├── architecture/      # ERD, 파이프라인, 디렉토리맵, 데이터 흐름
├── guides/            # 로컬 셋업
└── dev-log/           # ADR (Architecture Decision Records)
```

> **"문서가 없으면 기능도 없다."**
> 이상적 번호 체계(00\_~07\_)는 `.ai/rules/global.md` 참조.
> 상세 규칙(ID 체계, TODO.md 운영)도 동일 파일 참조.

---

## 6. Git Convention

```
feat: 새로운 기능 추가
fix: 버그 수정
refactor: 코드 리팩토링 (기능 변경 없음)
docs: 문서 수정
chore: 빌드, 설정 파일 수정
test: 테스트 추가/수정
```

---

## 7. 코딩 스타일

> 상세 규칙은 `.ai/rules/` 참조. 핵심 원칙만 요약.

### TypeScript (Frontend)
- Strict 모드 필수, `any` 금지 → `.ai/rules/frontend.md`
- Thin Component, RSC 지향, 비즈니스 로직은 커스텀 훅으로
- `Suspense` + `ErrorBoundary`로 에러 위임

### Python (Backend)
- 100% Async, Pydantic V2 → `.ai/rules/backend.md`
- Router / Service / Repository 레이어 분리
- AsyncSession은 Repository만 보유

### 상태 관리 (Frontend)
| 종류 | 도구 |
|------|------|
| Server State | React Query |
| Client Global | Zustand |
| Client Local | useState |

### 네이밍 공통
- Boolean: `is`, `has`, `should` 접두사
- 이벤트: `handle` (핸들러) / `on` (Props)
- 상수: UPPER_SNAKE_CASE

### 응답 형식
- 복잡한 설계는 Mermaid.js로 시각화
- 코드와 핵심 원리(불릿 포인트) 위주로 답변

---

## 현재 컨텍스트

### 프로젝트 개요
- **이름:** Kairos (καιρός — 결정적 순간)
- **한 줄 설명:** 팀의 세컨드 브레인 — 회의/노트/자료 → AI Distillation → 프로젝트 구조화 → RAG 인사이트
- **상세:** `docs/requirements/prd.md`

### 기술 스택

| 레이어 | 기술 | 규칙 |
|--------|------|------|
| Frontend | Next.js 16 + React 19 + Tailwind v4 + shadcn/ui v4 | `.ai/rules/frontend.md` |
| Backend | FastAPI + SQLModel + asyncpg | `.ai/rules/backend.md` |
| Database | PostgreSQL (Neon) | |
| Auth | Clerk (Google OAuth) | |
| Storage | Cloudflare R2 | |
| STT | Whisper API + pyannote-audio | |
| AI | Gemini `gemini-3.1-flash-lite` (고정, ADR-019 Phase B) | `docs/architecture/ai-pipeline.md` |
| Embedding | OpenAI text-embedding-3-small (1536d) | `docs/architecture/rag-pipeline.md` |
| Deploy | Vercel (FE) + GCP Cloud Run (BE) | |

### 핵심 파이프라인

```
[Capture] 회의 녹음 / 노트 / 자료 입력
[Organize] → STT → AI 구조화 (요약 / 액션 / 프로젝트 연결 + 태그)
[Distill]  → Inbox 적재 → AI 자동 확정 (또는 사용자 조정)
           → AI 프로젝트 인사이트 (L1~L4)
[Express]  → 벡터 임베딩 → RAG 검색 & Q&A + 프로액티브 인사이트
```

### 핵심 도메인

1. **팀 세컨드 브레인 (CODE)** — Capture→Organize→Distill→Express, AI 자동화
   → `docs/requirements/second-brain.md`
2. **Inbox 워크플로우** — AI 자동 프로젝트 연결 + 태그 → 사용자 선택적 조정
3. **콘텐츠 파이프라인** — Upload → STT → AI처리 → Inbox → 임베딩
   → `docs/architecture/ai-pipeline.md`, `docs/architecture/cross-domain-pipeline.md`
4. **RAG 6-Layer** — Cache → Query Processing → Hybrid Search → Re-ranking → Generation → Cache Store
   → `docs/architecture/rag-pipeline.md`
5. **오케스트레이터 패턴** — 크로스 도메인 서비스 조합, 직접 import 금지
   → `docs/architecture/cross-domain-pipeline.md`

### 핵심 엔티티

Workspace, WorkspaceMember, **WorkspaceInvite** (Sprint 6: `default_project_visibility`), User,
Project (Sprint 6: `visibility` public/draft/private), **ProjectMember** (Sprint 6 L-6),
InboxItem, Meeting, MeetingSummary, TranscriptSegment, MeetingProjectLink, ActionItem,
Note, EmbeddingChunk(계층적), SemanticCache
→ `docs/architecture/erd.md`

### visibility 도메인 용어 (Sprint 6, ADR-014)

- **Project.visibility**: `public` / `draft` / `private`
  - `public` — Workspace 내 모든 멤버 조회 가능
  - `draft` — ProjectMember만 조회 가능 (작업 중 상태)
  - `private` — ProjectMember만 조회 + RAG 검색 자동 제외
- **WorkspaceInvite.default_project_visibility**: 초대로 가입한 사용자의 기본 프로젝트 visibility
- 별칭 금지: `hidden` / `secret` / `closed` (모두 `private`로 통일)

### AI 제약사항

- Gemini 모델 고정: `gemini-3.1-flash-lite` (임의 변경 금지, ADR-019 Phase B 적용. 이전: `gemini-2.5-flash` EOL 2026-06-17)
- 프롬프트 중앙 관리: `backend/src/common/prompts.py` 상수 (인라인 금지)
- 크로스 도메인: `pipeline_service.py` 오케스트레이터만 — 도메인 간 직접 import 금지
- 장기 작업: BackgroundTasks + 202 Accepted + polling

### 현재 진행 상태

→ `docs/TODO.md` 참조 (현재 작업 상태 — 항상 최신)
→ `docs/requirements/prd.md` Phase 로드맵 참조

### 실제 코드 현황

```
kairos/
├── frontend/          # Next.js 16 (101 TS/TSX, pnpm)
│   └── src/
│       ├── app/       # 라우트 (dashboard, inbox, workspace/[id]/...)
│       ├── components/# ui/ (shadcn), layout/, landing/ (13개)
│       ├── features/  # inbox/, meetings/, actions/, projects/
│       ├── mocks/     # mock data (Phase 1)
│       └── store/     # Zustand (ui.ts)
├── backend/           # FastAPI (12 도메인 모듈)
│   └── src/           # actions, auth, inbox, meetings, notes,
│                      # projects, rag, embeddings, upload, workspaces
│                      # + common/, core/, services/
├── docs/              # 18+ 문서, 5 ADR
└── .ai/               # 규칙 파일
```

---

## Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.

## 스택 규칙 참조

> `.ai/rules/`는 심링크 허브. 원본은 `.ai/common/`, `.ai/stacks/`, `.ai/project/`에 위치.

| 파일 | 내용 |
|------|------|
| `.ai/rules/global.md` | 문서화, Git Convention, 환경변수, 자기개선 루프 |
| `.ai/rules/typescript.md` | TypeScript 공통 (Strict, 네이밍) |
| `.ai/rules/frontend.md` | Next.js 16 + shadcn v4 + FSD + Zod v4 |
| `.ai/rules/backend.md` | FastAPI + SQLModel + Gemini API + R2 |

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
