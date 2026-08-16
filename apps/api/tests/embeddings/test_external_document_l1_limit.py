# apps/api/tests/embeddings/test_external_document_l1_limit.py
"""BL-EXT-EMBED-1 — 외부 문서 L1 임베딩 입력 상한 + 배치 분할 회귀 테스트.

핵심 불변식: 절단은 **임베딩 입력에만** 적용되고 저장되는 chunk_text 는 전문이다.
L1 벡터는 검색되지 않지만(`repository.py:206`/`:266` 의 `chunk_level = 2` 필터)
L1 의 chunk_text 는 `rag/service.py:323`→`:381` 의 LLM 프롬프트 근거 본문이다.

OpenAI 호출은 generate_embeddings seam 을 stub 으로 대체한다 (실 API 호출 0).
"""
import uuid
from types import SimpleNamespace

import pytest

from src.embeddings import service as service_module
from src.embeddings.service import EmbeddingService


class _RecordingRepository:
    """save_chunk 호출을 순서대로 기록하는 최소 repo 대역."""

    def __init__(self) -> None:
        self.saved_chunks: list[SimpleNamespace] = []
        self.committed = False

    async def delete_by_source(self, source_type: str, source_id: uuid.UUID) -> None:
        return None

    async def save_chunk(self, **kwargs: object) -> SimpleNamespace:
        chunk = SimpleNamespace(id=uuid.uuid4(), **kwargs)
        self.saved_chunks.append(chunk)
        return chunk

    async def commit(self) -> None:
        self.committed = True


def _make_service(repo: _RecordingRepository) -> tuple[EmbeddingService, list[list[str]]]:
    """generate_embeddings 를 stub 으로 교체하고 호출별 입력 배열을 기록한다.

    반환 임베딩은 전역 호출 순서를 값으로 실어 청크↔벡터 대응을 검증 가능하게 한다.
    """
    service = EmbeddingService.__new__(EmbeddingService)
    service.repo = repo
    calls: list[list[str]] = []
    counter = {"next_index": 0}

    async def _stub_generate_embeddings(texts: list[str]) -> list[list[float]]:
        calls.append(list(texts))
        result = []
        for _ in texts:
            result.append([float(counter["next_index"])])
            counter["next_index"] += 1
        return result

    service.generate_embeddings = _stub_generate_embeddings
    return service, calls


async def _embed(service: EmbeddingService, plain_text: str) -> None:
    workspace_id = uuid.uuid4()
    await service.embed_external_document(
        document_id=uuid.uuid4(),
        workspace_id=workspace_id,
        source_workspace_id=workspace_id,
        project_id=None,
        title="외부 문서 제목",
        origin_url="https://docs.google.com/document/d/document-1/edit",
        plain_text=plain_text,
    )


def _level1(repo: _RecordingRepository) -> SimpleNamespace:
    return next(chunk for chunk in repo.saved_chunks if chunk.chunk_level == 1)


class TestLimitConstantsAreBounded:
    """상한 '폭' 자체를 구속한다 — 상수를 키우면 여기서 죽는다.

    fixture 크기가 상수에서 파생되므로 절단 테스트만으로는 상수를 200_000 으로
    바꿔도 전부 초록이다. 상한의 근거를 테스트로 승격해 그 구멍을 막는다.
    """

    def test_l1_char_limit_stays_within_model_token_budget(self) -> None:
        """text-embedding-3-small 입력 상한 8191 토큰을 최악 환산에서도 넘지 않는다.

        BPE 는 UTF-8 바이트 위에서 동작하고 병합은 토큰 수를 줄이기만 하므로
        `토큰 수 <= 바이트 수`, 코드포인트 하나는 최대 4 바이트 → `토큰 수 <= 4 * 문자 수`.
        """
        assert service_module._EXTERNAL_L1_MAX_CHARS * 4 <= 8191

    def test_embed_batch_size_stays_within_input_array_limit(self) -> None:
        """임베딩 요청당 입력 배열 한도(2048) 아래여야 한다.

        L1 1건이 첫 배치에 함께 실리므로 배치 크기 자체가 한도 미만이어야 한다.
        """
        assert service_module._EXTERNAL_EMBED_BATCH_SIZE < 2048


class TestLevel1InputLimit:
    """(a)/(b) — 상한 초과 문서는 임베딩 입력만 절단, 저장 본문은 전문."""

    async def test_oversized_document_truncates_embed_input_but_stores_full_text(
        self,
    ) -> None:
        """상한 초과: 임베딩 입력은 절단, 저장 chunk_text 는 원문 전문, 그리고 서로 다르다."""
        limit = service_module._EXTERNAL_L1_MAX_CHARS
        plain_text = "가나다라마바사아" * ((limit // 8) + 500)  # 상한 초과
        assert len(plain_text) > limit

        repo = _RecordingRepository()
        service, calls = _make_service(repo)
        await _embed(service, plain_text)

        embedded_l1 = calls[0][0]
        stored_l1 = _level1(repo).chunk_text

        # 임베딩 입력은 상한까지 절단된다 (8191 토큰 초과로 호출이 실패하던 원인).
        assert len(embedded_l1) <= limit
        assert embedded_l1 == plain_text[:limit]
        # 저장 본문은 전문이다 — rag/service.py 의 parent_text 가 LLM 근거 본문이다.
        assert stored_l1 == plain_text
        # 비대칭이 실제로 성립하는지 — 이 단언이 없으면 chunk_text 를 절단본으로
        # 되돌려도(= B1 회귀) 스위트가 초록으로 남는다.
        assert stored_l1 != embedded_l1

    async def test_small_document_is_not_truncated(self) -> None:
        """대조군 — 상한 이하 문서는 절단되지 않고 임베딩 입력·저장본 모두 원문이다.

        (이 크기에서는 두 값이 같은 것이 정상이므로 위 '서로 다르다' 단언은 쓰지 않는다.)
        """
        limit = service_module._EXTERNAL_L1_MAX_CHARS
        plain_text = "가나다라마바사아" * 10
        assert len(plain_text) < limit

        repo = _RecordingRepository()
        service, calls = _make_service(repo)
        await _embed(service, plain_text)

        embedded_l1 = calls[0][0]
        stored_l1 = _level1(repo).chunk_text

        assert embedded_l1 == plain_text
        assert stored_l1 == plain_text


class TestBatchSplitting:
    """(c) — 배치 분할이 청크 개수·순서를 바꾸지 않는다."""

    @staticmethod
    def _chunk_signature(repo: _RecordingRepository) -> list[tuple[int, int, str, float]]:
        return [
            (chunk.chunk_level, chunk.chunk_index, chunk.chunk_text, chunk.embedding[0])
            for chunk in repo.saved_chunks
        ]

    async def test_batched_result_matches_unbatched(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """분할 실행과 단일 호출 실행의 청크 개수·순서·벡터 대응이 동일하다."""
        batch_size = service_module._EXTERNAL_EMBED_BATCH_SIZE
        # L2 문단 수가 배치 크기를 넘도록 — _chunk_text 기본값 기준 문단당 진행폭 450 자.
        plain_text = "가나다라마바사아" * (((500 + 450 * (batch_size + 10)) // 8) + 1)

        batched_repo = _RecordingRepository()
        batched_service, batched_calls = _make_service(batched_repo)
        await _embed(batched_service, plain_text)

        # 분할이 실제로 일어났는지 + 각 요청이 상한 이하인지.
        assert len(batched_calls) > 1
        assert all(len(call) <= batch_size for call in batched_calls)

        unbatched_repo = _RecordingRepository()
        unbatched_service, unbatched_calls = _make_service(unbatched_repo)
        monkeypatch.setattr(service_module, "_EXTERNAL_EMBED_BATCH_SIZE", 10_000)
        await _embed(unbatched_service, plain_text)

        assert len(unbatched_calls) == 1
        # 분할된 요청들을 이어붙이면 단일 요청의 입력과 같아야 한다 (순서 포함).
        assert [text for call in batched_calls for text in call] == unbatched_calls[0]
        assert self._chunk_signature(batched_repo) == self._chunk_signature(
            unbatched_repo
        )

    async def test_chunk_order_maps_to_embedding_order(self) -> None:
        """L1 이 인덱스 0, 이후 L2 문단이 입력 순서대로 벡터와 대응한다."""
        batch_size = service_module._EXTERNAL_EMBED_BATCH_SIZE
        plain_text = "가나다라마바사아" * (((500 + 450 * (batch_size + 10)) // 8) + 1)

        repo = _RecordingRepository()
        service, calls = _make_service(repo)
        await _embed(service, plain_text)

        embedded_texts = [text for call in calls for text in call]
        # L2 는 임베딩 입력과 저장 본문이 같다 (절단 대상이 아니다).
        assert [chunk.chunk_text for chunk in repo.saved_chunks[1:]] == embedded_texts[1:]
        # L1 만 비대칭 — 저장은 전문, 입력은 절단본.
        assert repo.saved_chunks[0].chunk_text == plain_text
        assert embedded_texts[0] == plain_text[: service_module._EXTERNAL_L1_MAX_CHARS]
        # stub 은 전역 호출 순서를 벡터 값으로 실어 보낸다 → i 번째 청크 = i 번째 벡터.
        assert [chunk.embedding[0] for chunk in repo.saved_chunks] == [
            float(index) for index in range(len(embedded_texts))
        ]
        assert repo.saved_chunks[0].chunk_level == 1
        assert all(chunk.chunk_level == 2 for chunk in repo.saved_chunks[1:])
        assert repo.committed is True
