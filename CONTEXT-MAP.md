<!-- Kairos 도메인 헌법 — 도메인 경계, 핵심 불변식 -->

# Kairos CONTEXT-MAP

> 이 문서는 프로젝트의 **헌법**이다. 모든 코드/문서/명명이 여기에 우선. 충돌 시 즉시 멈추고 헌법 정렬.

---

## 1. 한 문장 정의

**Kairos는 팀의 세컨드 브레인이다.** 회의·노트·자료를 Capture 하면 AI 가 자동 Organize·Distill, RAG 로 Express. 핵심 차별점은 Distill 자동화.

Distill L0~L4 매핑: L0 원본 (upload/meetings/notes) · L1 트랜스크립트+요약 (meetings) · L2 결정+액션 (meetings/actions) · L3 프로젝트 인사이트 (projects 부분) · L4 조직 인사이트 (Phase 4, ADR-007).

## 2. 핵심 엔티티

상세 ERD: `docs/architecture/erd.md`. 본 문서는 코드 사실 우선.

**격리**: Workspace(personal/team) · WorkspaceMember · Project(public/draft/private) · ProjectMember · User(clerk_id, onboarding 0~4). **콘텐츠**: InboxItem · Meeting+TranscriptSegment+MeetingSummary+MeetingProjectLink · ActionItem(nullable parents) · Note(Tiptap) · MemoryItem(text/voice) · FeedbackEntry(dogfooding, user-level·workspace nullable). **audit**: PromoteAudit(memory) · ItemPromotionAudit(4 도메인) · MemoryAiCall · MemoryEvent. **벡터**: EmbeddingChunk(halfvec 1536d L1/L2) · SemanticCache(TTL 7d ≥0.93) · MemoryQueryEmbeddingCache.

### 별칭 금지 (도메인 용어 위반 감지)

| 정식 | 금지 별칭 |
|---|---|
| Workspace | Team, Tenant, Org, Organization |
| Project | Area, Folder, Category, PARA Area |
| Meeting | Recording, Session, Audio |
| ActionItem | Task, Todo, Issue |
| MemoryItem | Memory (단독), Capture (Capture 는 동사), Snippet |

> 그 외 (TranscriptSegment / MeetingSummary / EmbeddingChunk / SemanticCache / Note / User) 의 별칭 금지는 `backend/src/<domain>/CONTEXT.md` 에 도메인별 명시.

## 3. CODE 메서드

```
[Capture] InboxItem → [Organize] AI 분류 → [Distill] L0~L4 → [Express] RAG 6-Layer + SSE
```

현재 구현: L0~L2 완성, L3 부분, L4 미구현 (Phase 4).

## 4. 도메인 경계

### 4.1 백엔드 모듈 (16)

`auth · workspaces · projects · inbox · meetings · notes · actions · feedback · memory · onboarding · upload · embeddings · rag · common · core · services`. 폴더 표준: `router/service/repository/schemas/models/dependencies/exceptions.py`. 상세: `docs/architecture/directory-map.md`.

### 4.2 의존 규칙 (헌법 결정 #1, ADR-014)

| 케이스 | 정책 |
|---|---|
| 도메인 A → 도메인 B `.repository` (read) | ✅ 허용 (workspace 검증 필수) |
| 도메인 service.py 끼리 직접 호출 | ❌ 금지 |
| cross-domain shared service (`embeddings` / `ai_processing` / `transcription`) | orchestrator (`<domain>/pipeline_service.py` 또는 `services/`) 경계 내부만 |
| 3+ 모듈 + commit 트랜잭션 | orchestrator 필수 |

강제: code review + `backend/tests/architecture/test_no_memory_to_embeddings_lazy_import.py` (Sprint 24 Wave 2 BL-006 회귀 방지).

### 4.3 프론트엔드 features (FSD)

`actions · audit · feedback · home · inbox · meetings · members · memory · notes · onboarding · projects · rag · sources · upload · workspaces` (15). shadcn `components/ui/` 수정 금지 (DESIGN.md). TiptapEditor (useEditor/EditorContent) 는 `features/notes/components/note-detail.tsx` (Sprint 29 R3 정정 — 옛 `note-editor.tsx` 는 importer 0 dead-code 로 삭제).

## 5. visibility 도메인 용어 (ADR-014)

`Project.visibility = public / draft / private`. public = workspace 전체. draft = creator(작성자) 전용 (admin/owner 우회). private = ProjectMember 만 (admin/owner 우회) + RAG 검색 자동 제외. 별칭 금지: hidden / secret / closed.

> 2026-05-29 전체정검 정정 (BUG-DRAFT-DOC-CONTRADICTION): 이전엔 draft="ProjectMember 만"으로 기술됐으나 실제 코드(`backend/src/projects/repository.py` `_apply_visibility_filter`)는 draft=creator-only 이며 2계정 라이브로 확정됨(member 가 타인 draft 미접근, 404). 코드 = source of truth, `projects/CONTEXT.md` P-5 와도 정합.

`WorkspaceInvite.default_project_visibility` = 초대 가입 사용자 기본값.

## 6. 핵심 불변식 (위반 즉시 중단)

| # | 불변식 | 강제 위치 |
|---|---|---|
| I-1 | AsyncSession 은 Repository 만 보유 (service 에서 `from sqlalchemy.ext.asyncio import AsyncSession` 금지) | `<domain>/service.py` |
| I-2 | 크로스 도메인 트랜잭션은 orchestrator 경유 (1회 commit). 예외: BackgroundTask polling status 전이별 commit (부분 커밋 모델 인정) | `<domain>/pipeline_service.py` |
| I-3 | AI 모델 고정: Gemini `gemini-3.1-flash-lite` (ADR-019 Phase B, 2026-05-15 swap) | `core/config.py` |
| I-4 | 프롬프트 중앙 관리: `common/prompts.py` 상수 (인라인 금지) | code review |
| I-5 | 장기 작업: BackgroundTasks + 202 Accepted + GET status polling | meetings 패턴 |
| I-6 | 임베딩 모델 고정: OpenAI `text-embedding-3-small` 1536d | `embeddings/service.py` |
| I-7 | 임베딩 검색 대상은 chunk_level=2 만 (L0 미사용, L1 부모 참조) | `embeddings/repository.py` |
| I-8 | SemanticCache TTL 7일, threshold 0.93 | `embeddings/` |
| I-9 | **멀티테넌시 격리** (Sprint 19 PR #1·#2): Repository find/update/delete `workspace_id` WHERE 강제 + service `_verify_secondary_fks` (cross-workspace 거부) + cross-tenant 404 (admin 도 우회 불가) + DB composite FK `(workspace_id, secondary_id)` defense-in-depth. scope = project_id only, BL-046 carry | repository + service + composite FK + integration tests |
| I-10 | Inbox confidence 임계값: 워크스페이스별 `workspaces.inbox_threshold` (기본 0.9), PATCH 가능 | `workspaces/models.py`, `meetings/pipeline_service.py` |
| I-11 | shadcn `components/ui/` 수정 금지 | `frontend/src/components/ui/` |
| I-12 | 언어 정책: 사고/문서/주석 한국어, 코드/네이밍 영어 | AGENTS.md §1 |
| I-13 | API workspace prefix: `/api/v1/workspaces/{workspace_id}/<resource>` (예외: auth `/api/v1/users`, user-level `/api/v1/feedback` — 워크스페이스 비종속 dogfooding 피드백) | `<domain>/router.py` |
| I-14 | Pydantic V2 + 100% async + SQLModel typed query (Sprint 20 BL-054): 상세 allowlist (G1~G3-keep-dialect 5 카테고리) `backend/CONTEXT.md` B-10 | code review |
| I-15 | Secret 은 `SecretStr`, 사용 시 `.get_secret_value()` | `core/config.py` |
| I-16 | DB snake_case ↔ API camelCase: Pydantic alias 변환 | `<domain>/schemas.py` |
| I-17 | cross-workspace ProjectMember 추가 차단 = ProjectService. add_member 시 WorkspaceRepository.find_member 검증, None → `CrossWorkspaceMemberError(403)`. I-9(read)와 분리된 write 검증 | `projects/service.py:add_member` |
| I-18 | Promotion = 복제 + tombstone (ADR-016 + Sprint 23 D4). 5 도메인 (memory/meeting/note/inbox/action) source 보존 + target 복제 + audit row. memory = `PromoteAudit`, 4 도메인 = `ItemPromotionAudit`. 공통 헬퍼 `common/promote_helpers.py` | `memory/service.py:promote` + helpers |
| I-19 | Personal workspace = 1인 격리. `Workspace.type='personal'` → 1 owner, `WorkspaceInvite` 발급 금지, ProjectMember 1명 (R5) | `workspaces/service.py` + `projects/service.py` |
| I-20 | 벡터 컬럼 `halfvec(1536)` 고정 (ADR-020). `EmbeddingChunk.embedding` + `SemanticCache.question_embedding`. `Vector(1536)` 금지. 인덱스 = HNSW (m=16, ef_construction=64), ivfflat 금지. cosine `<=>` 유지 | `embeddings/models.py` + alembic |
| I-21 | 벡터 검색 세션 변수 강제 (ADR-020): `SET LOCAL hnsw.ef_search=40 + iterative_scan='relaxed_order' + max_scan_tuples=20000`. `_apply_hnsw_session_params(session)` 헬퍼. pgvector ≥0.8 서버 + Python ≥0.4.2 | `embeddings/repository.py:_apply_hnsw_session_params` |

> **회귀 가드 (2026-06-18, 2026-07-05 T19~T20 확장)**: I-9/I-13/I-17/I-19 + §5 visibility + RBAC 4-cell + RAG private 누수 0 + revocation 캐시 즉시성 + promote 검색성 + ws 삭제 + 생성 다이얼로그 visibility(W-5 시드)는 멀티계정 e2e 회귀 스위트 `frontend/e2e/tests/team/`(T1~T20, owner+member 2-토큰 실 RBAC 관통, anti-hollow-green mutation-gated) 로 영구 고정. 로컬 게이트 `E2E_RUN_TEAM=true E2E_API_URL=http://localhost:8000 pnpm --dir frontend exec playwright test --project=team --workers=1` (BE :8000 단일 프로세스 + CORS `:3003`). 설계: `docs/plans/active/2026-06-18-team-spine-e2e-regression.md`.

## 7. 현재 부채

활성 D-7 (actions dedupe 부재) · D-8 (회의 R2 hash 중복 미검출) · D-9 (meetings 8회 commit, BL-001) · D-10 (orphan ActionItem 분류 UI) · D-11 (MeetingSummary 타입 어노테이션 오류). 상세: `docs/REFACTORING-BACKLOG.md` BL-NNN.

해소: D-1 (visibility, Sprint 6) · D-2/D-3 (notes/rag pipeline 분리, Sprint 6) · D-5 (inbox threshold, Sprint 6) · D-6 (second-brain §8 5건 — Sprint 27a, ADR-023, 후속 BL-S27-1/2/3).

## 8. 진입점

순서: `CONTEXT-MAP.md` → `AGENTS.md` → `DESIGN.md` → 작업 도메인 `backend/src/<domain>/CONTEXT.md` → `docs/TODO.md`. 상세: `docs/README.md`.

## 9. 문서 갱신 원칙

코드 변경 시 관련 canonical doc 1개를 같은 PR 에 포함. 상세 라우팅 표: [`.ai/common/global.md` §2](.ai/common/global.md). (Sprint 26, 2026-05-23 — 옛 Atomic Update 2단 매트릭스 폐지)
