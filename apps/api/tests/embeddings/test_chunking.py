# apps/api/tests/embeddings/test_chunking.py
"""청킹 로직 단위 테스트."""
from src.embeddings.service import EmbeddingService


def _make_service() -> EmbeddingService:
    """Repository/OpenAI 없이 청킹 로직만 테스트하기 위한 인스턴스."""
    return EmbeddingService.__new__(EmbeddingService)


class TestChunkText:
    """텍스트를 300-500자 청크로 분할하는 로직."""

    def test_short_text_single_chunk(self):
        """300자 미만 텍스트 → 청크 1개."""
        service = _make_service()
        chunks = service._chunk_text("짧은 텍스트입니다.", max_chars=500, overlap_chars=50)
        assert len(chunks) == 1
        assert chunks[0] == "짧은 텍스트입니다."

    def test_long_text_multiple_chunks(self):
        """1000자 텍스트 → 여러 청크, 각 500자 이하."""
        service = _make_service()
        text = "가나다라마바사아" * 125  # 1000자
        chunks = service._chunk_text(text, max_chars=500, overlap_chars=50)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 550  # max + overlap 여유

    def test_overlap_between_chunks(self):
        """인접 청크 사이에 오버랩이 존재해야 한다."""
        service = _make_service()
        text = "A" * 200 + "B" * 200 + "C" * 200  # 600자
        chunks = service._chunk_text(text, max_chars=300, overlap_chars=50)
        assert len(chunks) >= 2
        # 첫 번째 청크의 끝 50자가 두 번째 청크의 시작에 포함
        overlap = chunks[0][-50:]
        assert chunks[1].startswith(overlap)

    def test_empty_text(self):
        """빈 텍스트 → 빈 리스트."""
        service = _make_service()
        chunks = service._chunk_text("", max_chars=500, overlap_chars=50)
        assert len(chunks) == 1
        assert chunks[0] == ""


class TestGroupSegmentsBySpeaker:
    """회의 트랜스크립트를 화자별로 그룹핑."""

    def test_segments_grouped_by_speaker(self):
        """같은 화자의 연속 세그먼트 → Level 1 그룹."""
        service = _make_service()
        segments = [
            {"speaker": "김철수", "text": "안녕하세요. ", "start_sec": 0, "end_sec": 5},
            {"speaker": "김철수", "text": "오늘 안건입니다. ", "start_sec": 5, "end_sec": 10},
            {"speaker": "이영희", "text": "네 알겠습니다. ", "start_sec": 10, "end_sec": 15},
        ]
        groups = service._group_segments_by_speaker(segments)
        assert len(groups) == 2
        assert groups[0]["speaker"] == "김철수"
        assert "안녕하세요" in groups[0]["text"]
        assert "오늘 안건" in groups[0]["text"]
        assert groups[1]["speaker"] == "이영희"

    def test_alternating_speakers(self):
        """화자가 번갈아 가면 각각 별도 그룹."""
        service = _make_service()
        segments = [
            {"speaker": "A", "text": "첫 번째. ", "start_sec": 0, "end_sec": 5},
            {"speaker": "B", "text": "두 번째. ", "start_sec": 5, "end_sec": 10},
            {"speaker": "A", "text": "세 번째. ", "start_sec": 10, "end_sec": 15},
        ]
        groups = service._group_segments_by_speaker(segments)
        assert len(groups) == 3

    def test_empty_segments(self):
        """빈 세그먼트 → 빈 리스트."""
        service = _make_service()
        groups = service._group_segments_by_speaker([])
        assert groups == []
