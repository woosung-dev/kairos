# 용어집 (색인 — 규칙을 소유하지 않는다)

> ★ **정의의 SSOT 는 [`CONTEXT-MAP.md`](../../CONTEXT-MAP.md) 다.**
> 본 문서는 "이 단어가 무슨 뜻이고 정본이 어디인지" 를 찾는 **색인**이며, 규칙을 여기에 쓰지 않는다.
> 충돌하면 헌법이 맞다. 용어·별칭·불변식을 **추가할 때는 헌법에만** 쓴다 —
> 두 곳에 쓰는 순간 드리프트가 시작된다 ([ADR-029](../adr/029-ai-rules-relocation.md) 원칙).

## 제품 한 줄

**Kairos 는 팀의 세컨드 브레인이다.** 회의·노트·자료를 Capture 하면 AI 가 자동으로
Organize·Distill 하고, RAG 로 Express 한다. 핵심 차별점은 **Distill 자동화**.

```
[Capture] InboxItem → [Organize] AI 분류 → [Distill] L0~L4 → [Express] RAG 6-Layer + SSE
```

## Distill 레벨

| 레벨 | 뜻 | 담당 도메인 |
|---|---|---|
| L0 | 원본 | upload / meetings / notes |
| L1 | 트랜스크립트 + 요약 | meetings |
| L2 | 결정 + 액션 | meetings / actions |
| L3 | 프로젝트 인사이트 | projects (부분) |
| L4 | 조직 인사이트 | 미구현 (Phase 4, ADR-007) |

임베딩 검색 대상은 **L2 청크만**이다 (I-7). L1 은 부모 컨텍스트로 참조된다.

## 엔티티 용어

| 정식 용어 | 한 줄 | 정본 |
|---|---|---|
| Workspace | 격리의 최상위 단위. `personal`(1인) / `team` | 헌법 §2 · `apps/api/src/workspaces/CONTEXT.md` |
| WorkspaceMember | 워크스페이스 구성원 + 역할(owner/admin/member/viewer) | `src/workspaces/CONTEXT.md` · [ADR-025](../adr/025-rbac-and-pricing-decisions.md) |
| Project | 워크스페이스 안의 주제 단위. `visibility` 를 소유 | 헌법 §5 · `src/projects/CONTEXT.md` |
| ProjectMember | `private` 프로젝트 접근 주체 | 헌법 §5 |
| User | Clerk 신원 매핑 + `onboarding_step`(0~4) | `src/auth/CONTEXT.md` |
| InboxItem | Capture 진입점. AI 분류 대기열 | `src/inbox/CONTEXT.md` |
| Meeting | 오디오 인제스트 → STT → AI 파이프라인 | `src/meetings/CONTEXT.md` |
| TranscriptSegment / MeetingSummary | 회의의 L1 산출물 | `src/meetings/CONTEXT.md` |
| ActionItem | 회의·노트에서 추출된 실행 항목 (부모 nullable) | `src/actions/CONTEXT.md` |
| Note | Tiptap 노트 | `src/notes/CONTEXT.md` |
| MemoryItem | Recall-first wedge 의 캡처 단위 (text/voice) | `src/memory/CONTEXT.md` |
| ExternalDocument | 외부 소스(Google Drive) 문서 | `src/integrations/CONTEXT.md` · [ADR-026](../adr/026-external-source-ingest-rail.md) |
| FeedbackEntry | dogfooding 피드백 (user-level, workspace nullable) | `src/feedback/CONTEXT.md` |
| EmbeddingChunk | 벡터 청크 (`halfvec(1536)`, HNSW) | `src/embeddings/CONTEXT.md` · [ADR-020](../adr/020-pgvector-hnsw-halfvec.md) |
| SemanticCache | RAG 질의 캐시 (TTL 7일, threshold 0.93) | `src/embeddings/CONTEXT.md` |
| ItemPromotionAudit / PromoteAudit | 승격(promote) 감사 기록 | 헌법 I-18 |

**별칭 금지표는 여기에 복사하지 않는다** → [`CONTEXT-MAP.md` §2](../../CONTEXT-MAP.md).
(Workspace 를 Team/Tenant/Org 로, ActionItem 을 Task/Todo 로 부르는 것 등이 금지돼 있다.)

## visibility — 사용자 관점

| 값 | 누가 보나 |
|---|---|
| `public` | 워크스페이스 전체 |
| `draft` | **작성자 본인만** (admin/owner 는 우회) |
| `private` | ProjectMember 만 (admin/owner 우회) + **RAG 검색에서 자동 제외** |

규칙 구현의 SSOT 는 `apps/api/src/common/visibility.py` 단일 파일이고,
사본 재발은 arch gate 가 CI 에서 차단한다. 상세 → [`CONTEXT-MAP.md` §5](../../CONTEXT-MAP.md).

## 승격 (Promotion)

**복제 + tombstone** 이다 — 원본을 보존하고 대상 도메인에 복제한 뒤 audit row 를 남긴다.
5 도메인(memory / meeting / note / inbox / action)이 지원한다. 상세 → 헌법 I-18.

## 더 읽을 것

- 도메인 인덱스: [`domains/README.md`](domains/README.md)
- 제품 요구사항: [`../requirements/prd.md`](../requirements/prd.md)
- 페르소나 PERSONA-001: [`../adr/011-persona-definition.md`](../adr/011-persona-definition.md)
