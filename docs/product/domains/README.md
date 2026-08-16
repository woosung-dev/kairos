# 도메인 인덱스 (링크만 — 정의를 소유하지 않는다)

> ★ 각 도메인의 정본은 `apps/api/src/<domain>/CONTEXT.md` 다. 여기는 **링크 인덱스**다.
> 책임 설명을 이 파일에 늘려 쓰지 않는다 — 늘리는 순간 두 번째 정본이 되고 드리프트가 시작된다.
> **모듈 개수도 여기에 적지 않는다.** 개수의 정본은 [`CONTEXT-MAP.md`](../../../CONTEXT-MAP.md) §4.1 / §4.3 이다.

## BE 도메인 ↔ FE feature

| 도메인 | 한 줄 | BE 정본 | 대응 FE feature |
|---|---|---|---|
| auth | Clerk JWT 검증 + User 매핑 + RBAC | [`src/auth/CONTEXT.md`](../../../apps/api/src/auth/CONTEXT.md) | — (`proxy.ts` + Clerk) |
| workspaces | Workspace + Member + Invite | [`src/workspaces/CONTEXT.md`](../../../apps/api/src/workspaces/CONTEXT.md) | `workspaces/` · `members/` |
| projects | Project CRUD + ProjectMember + visibility | [`src/projects/CONTEXT.md`](../../../apps/api/src/projects/CONTEXT.md) | `projects/` |
| inbox | Capture 적재 + AI 분류 | [`src/inbox/CONTEXT.md`](../../../apps/api/src/inbox/CONTEXT.md) | `inbox/` |
| meetings | 인제스트 · STT · AI 파이프라인 | [`src/meetings/CONTEXT.md`](../../../apps/api/src/meetings/CONTEXT.md) | `meetings/` |
| notes | Tiptap 노트 | [`src/notes/CONTEXT.md`](../../../apps/api/src/notes/CONTEXT.md) | `notes/` |
| actions | ActionItem | [`src/actions/CONTEXT.md`](../../../apps/api/src/actions/CONTEXT.md) | `actions/` |
| memory | Recall-first wedge (capture/distill/recall/promote) | [`src/memory/CONTEXT.md`](../../../apps/api/src/memory/CONTEXT.md) | `memory/` |
| rag | RAG 6-Layer + Gemini 답변 (SSE) | [`src/rag/CONTEXT.md`](../../../apps/api/src/rag/CONTEXT.md) | `rag/` · `sources/` |
| embeddings | EmbeddingChunk + SemanticCache (cross-domain shared) | [`src/embeddings/CONTEXT.md`](../../../apps/api/src/embeddings/CONTEXT.md) | — (내부 전용) |
| upload | R2 presigned + proxy + MIME 검증 | [`src/upload/CONTEXT.md`](../../../apps/api/src/upload/CONTEXT.md) | `upload/` |
| integrations | Google Drive 연결 + ExternalDocument | [`src/integrations/CONTEXT.md`](../../../apps/api/src/integrations/CONTEXT.md) | `integrations/` |
| onboarding | `User.onboarding_step` lifecycle | [`src/onboarding/CONTEXT.md`](../../../apps/api/src/onboarding/CONTEXT.md) | `onboarding/` |
| feedback | dogfooding 피드백 (user-level) | [`src/feedback/CONTEXT.md`](../../../apps/api/src/feedback/CONTEXT.md) | `feedback/` |

BE 전용 공용 레이어 — `common/` (visibility · pagination · prompts · r2 · audit/promote),
`core/` (config · lifespan · database), `services/` (외부 API wrapper: transcription · ai_processing · ai_resilience).
이들은 도메인이 아니므로 `CONTEXT.md` 를 갖지 않는다.

BE 도메인에 1:1 로 매핑되지 않는 FE feature — `home/`(대시보드 다도메인 조합),
`audit/`(감사 조회 UI, BE 는 `common/audit_router.py`), `sources/`(RAG 출처 뷰).

## 구조 규칙

- BE 도메인 폴더 표준: `router / service / repository / schemas / models / dependencies / exceptions.py`
- cross-domain 호출이 필요한 도메인만 `pipeline_service.py` 를 추가로 갖는다 (ADR-014)
- 의존 규칙(도메인 A → B `.repository` read 허용, `service` 끼리 직접 호출 금지)의 정본은
  [`CONTEXT-MAP.md` §4.2](../../../CONTEXT-MAP.md) 이고, arch gate 가 CI 에서 강제한다
- 디렉터리 트리 전체: [`../../architecture/directory-map.md`](../../architecture/directory-map.md)
