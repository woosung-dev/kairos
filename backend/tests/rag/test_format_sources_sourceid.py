# RagService._format_sources 가 chunk PK(id)와 별개로 source 엔티티 PK(sourceId)를 노출하는지 검증 (CAND-E 회귀)
"""CAND-E 회귀: RAG citation -> SourceViewer full-detail fetch 가 올바른 source 엔티티 id 를 받는지.

버그: _format_sources 가 클라이언트 source 의 "id" 로 EmbeddingChunk PK(r["id"])만 노출 →
FE 가 /meetings/{chunkId} 를 호출해 항상 404 → console retry storm. fix 는 r["source_id"]
(meeting/note PK)를 "sourceId" 로 별도 노출한다.

Regression: CAND-E — citation source id was chunk PK, not entity PK
Found by 2026-06-19 multi-agent QA
Report: docs/dev-log/qa/2026-06-19-full-product-team-multi-agent-qa/report.md
"""
import uuid

from src.rag.service import RagService


def _result(chunk_id: uuid.UUID, source_id: uuid.UUID) -> dict:
    """retrieval 결과 dict (embeddings/repository SELECT id, source_id, chunk_text, ... 형태)."""
    return {
        "id": chunk_id,  # EmbeddingChunk PK
        "source_id": source_id,  # meeting/note 엔티티 PK
        "chunk_text": "딥리뷰 스프린트 킥오프 회의 결정 사항 요약 본문",
        "source_type": "meeting",
        "metadata_json": {"title": "딥리뷰 AI 파이프라인 검증 회의"},
        "created_at": "2026-06-01T00:00:00",
        "score": 0.91,
    }


def test_format_sources_exposes_entity_source_id_distinct_from_chunk_id():
    chunk_id = uuid.uuid4()
    source_id = uuid.uuid4()
    assert chunk_id != source_id

    out = RagService._format_sources([_result(chunk_id, source_id)])

    assert len(out) == 1
    s = out[0]
    # 핵심: sourceId 는 엔티티 PK(meeting/note) — FE full-detail fetch 가 이걸 써야 404 가 안 난다.
    assert s["sourceId"] == str(source_id), "sourceId must be the source entity PK, not the chunk PK"
    # id 는 여전히 chunk PK (React key 유니크성 유지)
    assert s["id"] == str(chunk_id)
    # 둘은 달라야 한다 (혼동이 곧 버그였다)
    assert s["sourceId"] != s["id"]
    assert s["sourceType"] == "meeting"
