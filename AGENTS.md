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
새 태스크 시작 시 `CLAUDE.md` (또는 `AGENTS.md`) + `docs/README.md`를 먼저 읽어
전체 아키텍처와 현재 작업 컨텍스트를 파악한다.

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

새로운 기능이나 주요 변경 사항은 아래 루프를 따른다:

1. **계획 (Plan)** — 작업 범위와 영향 분석, 관련 규칙·설계 문서 참조
2. **문서화 (Docs)** — 구현 계획을 `docs/` 적절한 위치에 작성
3. **리뷰 (Human Review)** — 사용자 피드백, 만족할 때까지 반복
4. **구현 (Implement)** — 확정된 문서 기반 코드 작성, 중단 없이 끝까지

---

## 5. 문서화 원칙

```
docs/
├── README.md          # 문서 목차 (진입점)
├── requirements/      # PRD, 기능 명세, PARA 방법론, UI/UX 스펙
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
- **한 줄 설명:** 회의 녹음 → AI 요약/액션/PARA 분류 → 벡터 임베딩 → RAG Q&A
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
| AI | Claude `claude-sonnet-4-20250514` (고정) | `docs/architecture/ai-pipeline.md` |
| Embedding | OpenAI text-embedding-3-small (1536d) | `docs/architecture/rag-pipeline.md` |
| Deploy | Vercel (FE) + GCP Cloud Run (BE) | |

### 핵심 파이프라인

```
회의 녹음 → STT (Whisper + pyannote 화자 분리)
         → AI 구조화 (Claude: 요약 / 액션 아이템 / PARA 분류 추천)
         → Inbox 적재 → PARA 분류 확정
         → 벡터 임베딩 → RAG 검색 & Q&A
```

### 핵심 도메인

1. **PARA 방법론** — Projects/Areas/Resources/Archives, 실행도 기반 분류, N:M 관계
   → `docs/requirements/para-methodology.md`
2. **Inbox 워크플로우** — AI 추천(`is_processed=false`) → 사용자 확정 → N:M PARA 연결
3. **회의 처리 5-Stage** — Upload → STT → AI처리 → Inbox → 임베딩
   → `docs/architecture/ai-pipeline.md`, `docs/architecture/cross-domain-pipeline.md`
4. **RAG 6-Layer** — Cache → Query Processing → Hybrid Search → Re-ranking → Generation → Cache Store
   → `docs/architecture/rag-pipeline.md`
5. **오케스트레이터 패턴** — 크로스 도메인 서비스 조합, 직접 import 금지
   → `docs/architecture/cross-domain-pipeline.md`

### 핵심 엔티티

Workspace, User, ParaItem, InboxItem, Meeting, MeetingSummary,
TranscriptSegment, ActionItem, Note, EmbeddingChunk(계층적), SemanticCache
→ `docs/architecture/erd.md`

### AI 제약사항

- Claude 모델 고정: `claude-sonnet-4-20250514` (임의 변경 금지)
- 프롬프트 중앙 관리: `backend/src/common/prompts.py` 상수 (인라인 금지)
- 크로스 도메인: `pipeline_service.py` 오케스트레이터만 — 도메인 간 직접 import 금지
- 장기 작업: BackgroundTasks + 202 Accepted + polling

### 현재 진행 상태

| Phase | 상태 | 범위 |
|-------|------|------|
| Phase 1 (프론트엔드 스캐폴딩) | **진행 중** ~40% | 3-Panel, Inbox, PARA CRUD 완료. Clerk/업로드/칸반 미완 |
| Phase 2 (백엔드 + AI 파이프라인) | 미착수 | `backend/` 디렉토리 미존재 |
| Phase 3 (RAG + 고급 UI) | 설계 완료 | `docs/architecture/rag-pipeline.md` |
| Phase 4 (권한 + 보고서) | 계획 | |

→ `docs/requirements/prd.md` Phase 로드맵 참조

### 실제 코드 현황

```
kairos/
├── frontend/          # Next.js 16 (56 TS/TSX, pnpm)
│   └── src/
│       ├── app/       # 라우트 (dashboard, inbox, workspace/[id]/...)
│       ├── components/# ui/ (shadcn), layout/ (sidebar, header, rag-panel)
│       ├── features/  # inbox/, para/, meetings/(types만), actions/(types만)
│       ├── mocks/     # mock data (Phase 1)
│       └── store/     # Zustand (ui.ts)
├── backend/           # 미존재 (Phase 2에서 생성)
├── docs/              # 13개 문서
└── .ai/               # 규칙 파일
```

---

## 스택 규칙 참조

> `.ai/rules/`는 심링크 허브. 원본은 `.ai/common/`, `.ai/stacks/`, `.ai/project/`에 위치.

| 파일 | 내용 |
|------|------|
| `.ai/rules/global.md` | 문서화, Git Convention, 환경변수, 자기개선 루프 |
| `.ai/rules/typescript.md` | TypeScript 공통 (Strict, 네이밍) |
| `.ai/rules/frontend.md` | Next.js 16 + shadcn v4 + FSD + Zod v4 |
| `.ai/rules/backend.md` | FastAPI + SQLModel + Claude API + R2 |

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
