<!-- Memory 도메인 헌법 — Sprint 15 신설. Recall-first wedge -->

# Memory CONTEXT

> Recall-first wedge (Sprint 15). MemoryItem capture → distill → recall → promote.
> 상위: `CONTEXT-MAP.md` §2 (엔티티) + §4 (도메인 경계) + §6 (불변식 I-18/I-19).
> 관련 ADR: `docs/dev-log/016-personal-team-ia.md` · `docs/dev-log/019-gemini-eol-migration.md`

---

## 1. 책임 범위

Memory 도메인은 **개인 메모리 레이어**를 담당. Notion/Apple Notes 대체가 아니라 "AI가 기억해주는 메모리"의 wedge.

- **Capture**: 텍스트 또는 음성을 받아 MemoryItem 생성 (202 + BackgroundTask)
- **Distill**: Gemini로 `{title, atomic_notes, suggested_visibility}` 추출 (Background)
- **Embed**: 1536d 임베딩 적재 (`source_type='memory'`) — embeddings 모듈 호출
- **Recall**: 사용자 query → query embedding → vector search Top 3 + keyword fallback (O-A lock-in)
- **Promote**: Personal → Team workspace 복제 + tombstone (PromoteAudit row, I-18)
- **Metrics**: capture/recall/promote count + recall p50/p95 (memory_events 기반, R7)
- **Cleanup**: 30일 경과 voice R2 객체 삭제 (admin_router, Cron secret token)

비책임: 회의 (meetings), Tiptap Note (notes), Project insights (projects).

---

## 2. 엔티티 (5종 — CONTEXT-MAP §2 참조)

- MemoryItem (root) — `workspace_id` 격리 강제 (I-9)
- PromoteAudit — I-18 강제 (복제 + tombstone)
- MemoryAiCall — distill / embed / transcribe cost+latency 로그
- MemoryQueryEmbeddingCache — recall query 임베딩 캐시 (C3 fix)
- MemoryEvent — R7 metrics 원천 (Cloud Run stateless 정합)

---

## 3. 외부 의존 (orchestrator 경유 — ADR-014)

| 호출 대상 | 목적 | 현 호출 위치 | BL |
|----------|------|-------------|-----|
| `embeddings.service.create_chunk` | 1536d 임베딩 적재 | `service.py:724` (`_create_memory_embedding_chunk`) | **BL-006** (P0 헌법 갭) — `memory/pipeline_service.py` 분리 대기 |
| `services/ai_processing.distill_meeting` 패턴 (Gemini) | `{title, atomic_notes, suggested_visibility}` 추출 | `service.py:644` (`_call_distill`) | **BL-007** (P1) — `services/memory_ai_calls.py` 통합 검토 |
| `services/transcription.transcribe_audio` 패턴 (Whisper) | voice → text | `service.py:696` (`_call_transcribe`) | **BL-007** |
| `R2Service` (boto3 wrapper) | voice audio 객체 저장 / 삭제 | `service.py:602, 620` (boto3 client 재생성) | **BL-008** (P1) — R2Service public API로 상향 |
| `workspaces.repository` | Personal/Team 검증 | `service.py:420, 431` (session 직접 접근) | **BL-005** (P0 헌법 갭) — WorkspaceRepository 메서드화 |

---

## 4. 핵심 불변식

| # | 불변식 | 위치 |
|---|--------|------|
| **I-9 (memory 적용)** | MemoryItem 모든 query는 `workspace_id` 필터 + embeddings.create_chunk 시 `workspace_id`가 source memory의 workspace와 매칭 (4-C atomic patch) | `repository.py` 전역 + `service.py:721` assertion |
| **I-18** | Promotion = 복제 + tombstone. PromoteAudit 4-key 강제 | `service.py:407~434` (promote) |
| **I-19** | Personal workspace 1인 격리 — Personal에 capture는 1 user만 가능 (auth/dependencies 시드) | `auth/dependencies.py` lazy seed |
| I-3 (Gemini 모델) | `gemini-3.1-flash-lite` (ADR-019 Phase B 적용 완료, 2026-05-15. 이전: `gemini-2.5-flash` EOL 2026-06-17) | `service.py:64` `GEMINI_MODEL` |
| I-4 (프롬프트 중앙 관리) | distill prompt = `common/prompts.py` 상수 (인라인 금지) | Sprint 15 R1 lock-in |

---

## 5. Status state machine (MemoryItem.status)

```
text capture     → processing → embedding_pending → active
                                                  → embedding_failed
voice capture    → processing → transcription_pending → embedding_pending → active
                                                      → embedding_failed
promote 복제      → processing → embedding_pending → active
archived         (cleanup 30일 또는 사용자 요청)
```

> **BL-009** (P2): 위 transition이 3개 BG task (`_bg_distill_and_embed` / `_bg_transcribe_distill_embed` / `_bg_promote_embed`)에 유사 중복. status state machine 분리 대기.

---

## 6. 외부 호출자

| Caller | Endpoint | 메서드 |
|--------|----------|-------|
| FE `/memory` page | `POST/GET /api/v1/workspaces/{ws_id}/memory*` | router.py |
| Founder admin page | `GET /api/v1/workspaces/{ws_id}/memory/metrics` | router.py (admin gate FE-side) |
| GCP Cloud Scheduler | `POST /api/v1/admin/memory/r2-cleanup` | admin_router.py (Cron secret token) |

---

## 7. 테스트 표면

```
backend/tests/memory/
├── test_api.py            # router 표면 (status code + 시그니처)
├── test_service.py        # capture text/voice + status 전이 (BG task 분리)
├── test_recall.py         # vector + keyword fallback
├── test_promote.py        # 복제 + tombstone + PromoteAudit row
├── test_metrics.py        # memory_events 기반 R7
└── test_admin_cleanup.py  # 30일 TTL R2 삭제
```

> **검증 갭**: BG task 내부 (distill/embed/transcribe 실 호출)은 monkeypatch 진입점 (`service.py:637~709`)만 활용. 실제 Gemini/Whisper/OpenAI 호출은 별도 spike (`scripts/sprint15_day0_spike.py`)에서.

---

## 8. 후속 (BL refactor backlog — `docs/REFACTORING-BACKLOG.md` + `docs/TODO.md` 참조)

- **BL-005** [P0]: promote() 메서드의 Service Session 직접 접근 제거 → WorkspaceRepository 메서드화
- **BL-006** [P0]: embeddings.service.create_chunk 직접 호출 → `memory/pipeline_service.py` 분리 (ADR-014 정합)
- **BL-007** [P1]: AI 호출 helper (`_call_distill` 외 2종) → `services/memory_ai_calls.py` 통합 + BG task session 정합
- **BL-008** [P1]: R2 boto3 client 재생성 → R2Service 메서드로 상향
- **BL-009** [P2]: MemoryItem status state machine 분리 — 3 BG task 유사 코드 제거
- **BL-010** [P2]: query embedding cache race condition 결정 (workspace 간 cache 공유 정책)
