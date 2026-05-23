# Deepen-modules audit — rag/ 도메인 (2026-05-12)

## Phase 1: Module Inventory

| 파일 | LOC | Public Surface | 분류 | 비고 |
|------|-----|----------------|------|------|
| service.py | 239 | 1 class, `ask()` 1 public | **DEEP** | 6-layer RAG 핵심 로직 집중 |
| pipeline_service.py | 87 | 1 class, `ask()` 1 public | SHALLOW (의도적) | ADR-014 visibility 검증 전담 |
| router.py | 42 | 2 함수 (ask_rag, event_generator) | SHALLOW | HTTP envelope only |
| dependencies.py | 36 | 2 함수 (get_rag_service, get_rag_pipeline_service) | SHALLOW | DI assembly |
| schemas.py | 12 | 1 class (RagAskRequest) | SCHEMA | — |
| exceptions.py | 8 | 1 class (RagError) | **DEAD CODE** | 정의만 됨, 실제 raise 없음 |

총 424 LOC. 핵심 로직 239 LOC가 service.py에 집중 — 건강한 구조.

## Phase 2: Locality & Coupling 분석

### 주요 발견

**N+1 쿼리 (`service.py:_enrich_context`)**
```python
# 현재: 결과 수(최대 10)만큼 쿼리 발생
for r in results:
    parent = await self.embedding_repo.find_chunk_by_id(parent_id)
```
- EmbeddingRepository에 `find_chunks_by_ids(ids)` 메서드 미존재
- 현재 규모(청크 수 소)에서는 ~10ms 페널티, 청크 수 증가 시 선형 확장

**dual session (`dependencies.py`)**
- `get_rag_service` → `get_async_session` (세션 A)
- `get_rag_pipeline_service` → `get_async_session` (세션 B, 별도)
- ProjectRepository가 세션 B를 받음 — read-only라 허용 결정. architectural looseness는 존재.

**Dead code (`exceptions.py`)**
- `RagError(KairosError)` 정의만 됨
- pipeline_service.py가 직접 SSE `{"type": "error"}` 이벤트를 yield하는 방식으로 대체

### 제외된 후보
- `pipeline_service.py` shallow 구조 — ADR-014 §"Layer 0" 근거 명확 (SSE 시작 전 visibility 검증 강제). deepening 불필요.
- `_format_sources` vs `_format_sources_for_prompt` 중복 — 출력 형태가 다름(클라이언트 vs Gemini). 의도적 분리.

## Phase 3: Grilling Session 결정 로그

- **후보 A (N+1 배치화):** 승인. ROI 높음, risk 낮음.
- **후보 B (exceptions.py 데드 코드):** 사용자 skip. 지금 등재 불필요.

## Phase 4: 등재 결과

- **BL-003** 등재 완료 (`docs/REFACTORING-BACKLOG.md`)
  - 영향 파일: `embeddings/repository.py` + `rag/service.py`
  - 우선순위: ★★★★☆ / Risk: 🟢

## Sprint 권고

BL-003 단독 Sprint 12 처리 권장. 저위험·순수 기능 추가라 다른 BL과 묶을 필요 없음.

## 다음 audit 권고

- `services/` 도메인 (Round 2): `ai_processing.py` LLM 공통 호출 패턴
- `meetings/` 도메인 (Round 3): MeetingService export 로직 분리
