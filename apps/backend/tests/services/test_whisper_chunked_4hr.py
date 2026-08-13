# Sprint 24 Wave 2 T-N+4 (BL-T2-003) — Whisper 4hr+ chunked transcription 회귀 테스트.
"""4시간+ audio chunk 분할 transcription 테스트.

mock 으로 ffmpeg/ffprobe/Whisper 실제 호출 회피. 검증 포인트:
- 1hr 이하: 단일 Whisper 호출 (chunking X)
- 4hr: 4 chunk + offset 보존 (i * 3600)
- chunk N 끝 overlap 영역과 chunk N+1 시작 영역 중복 segment dedupe
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_short_audio_uses_single_call():
    """CHUNK_SECONDS 이하 audio = 단일 Whisper 호출 (split 미발생, ffmpeg_split 미호출).

    Codex F-5 fix 후 default = 600s (10min). 본 test 는 mock duration < CHUNK_SECONDS 확인.
    """
    from src.services import chunked_transcription

    with patch.object(
        chunked_transcription,
        "_ffmpeg_probe_duration",
        AsyncMock(return_value=300.0),  # 5min (Codex F-5: CHUNK_SECONDS=600 정합)
    ):
        with patch.object(
            chunked_transcription,
            "_whisper_transcribe_single",
            AsyncMock(return_value=[{"start": 0.0, "end": 10.0, "text": "안녕하세요"}]),
        ) as mock_whisper:
            with patch.object(
                chunked_transcription, "_ffmpeg_split", AsyncMock()
            ) as mock_split:
                segments = await chunked_transcription.transcribe_chunked("file:///fake.mp3")

    # 단일 호출 — split 진입 X
    mock_whisper.assert_called_once()
    mock_split.assert_not_called()
    assert len(segments) == 1
    assert segments[0]["text"] == "안녕하세요"
    assert segments[0]["start"] == 0.0


@pytest.mark.asyncio
async def test_4hr_audio_uses_4_chunks_with_overlap(monkeypatch):
    """4hr audio = 4 chunk + offset 보존 (chunk i 의 모든 segment start += i * CHUNK_SECONDS).

    monkeypatch: 본 test 는 CHUNK_SECONDS=3600 가정 하 작성됨. Codex F-5 (Whisper 25MB) 후
    default 가 600 (10분) 으로 변경됨 → test 격리 위해 monkeypatch 로 3600 강제.
    실 production 에서는 4hr = 24 chunks 처리 (mock 무관, default 600s 적용).
    """
    from src.services import chunked_transcription

    monkeypatch.setattr(chunked_transcription, "CHUNK_SECONDS", 3600)

    fake_chunk_paths = ["/tmp/c0.mp3", "/tmp/c1.mp3", "/tmp/c2.mp3", "/tmp/c3.mp3"]

    # 각 chunk 마다 다른 text 반환 → overlap dedup 영향 없이 offset 만 검증
    chunk_outputs = [
        [{"start": 0.0, "end": 10.0, "text": f"chunk-{i}"}] for i in range(4)
    ]

    async def fake_whisper_single(path: str) -> list[dict]:
        idx = fake_chunk_paths.index(path)
        return chunk_outputs[idx]

    # Codex F-12 fix 후 transcribe_chunked 가 _ffmpeg_split_single 을 batch loop 로 호출.
    # mock 도 single 변환. chunk_index 별로 fake path 반환.
    async def fake_split_single(audio_url, chunk_index, *args, **kwargs):
        return fake_chunk_paths[chunk_index]

    with patch.object(
        chunked_transcription,
        "_ffmpeg_probe_duration",
        AsyncMock(return_value=14400.0),  # 4hr
    ):
        with patch.object(
            chunked_transcription,
            "_ffmpeg_split_single",
            AsyncMock(side_effect=fake_split_single),
        ):
            with patch.object(
                chunked_transcription,
                "_whisper_transcribe_single",
                AsyncMock(side_effect=fake_whisper_single),
            ) as mock_whisper:
                with patch("pathlib.Path.unlink"):  # cleanup mock — 가짜 경로라 실제 unlink 회피
                    segments = await chunked_transcription.transcribe_chunked("file:///fake-4hr.mp3")

    # 4 chunk 모두 Whisper 호출
    assert mock_whisper.call_count == 4
    # 4 segment 모두 보존 (서로 다른 text → dedup 없음)
    assert len(segments) == 4
    # offset 보존: chunk i 의 segment.start = i * CHUNK_SECONDS (3600)
    assert segments[0]["start"] == 0.0
    assert segments[1]["start"] == 3595.0  # 1*3600 - 5 (Codex F-4)
    assert segments[2]["start"] == 7195.0  # 2*3600 - 5 (Codex F-4)
    assert segments[3]["start"] == 10795.0  # 3*3600 - 5 (Codex F-4)
    assert segments[0]["text"] == "chunk-0"
    assert segments[3]["text"] == "chunk-3"


@pytest.mark.asyncio
async def test_chunk_overlap_dedupe(monkeypatch):
    """chunk N 마지막 overlap 영역 + chunk N+1 처음 overlap 영역 동일 text segment dedup.

    시나리오: 2 chunk (2hr) 가정. Codex F-4 fix 후 chunk 1 offset = 3600 - 5 = 3595.
    monkeypatch: CHUNK_SECONDS=3600 강제 (Codex F-5 default 600 무관 test 격리).
    - chunk 0 마지막 segment: start=3595, end=3599, text="overlap-word"
    - chunk 1 첫 segment (post-offset 3595): start=3596 (=1+3595), end=3599, text="overlap-word"
    - merge 시 chunk 1 의 동일 text segment 는 직전 segment 와 같은 영역 → dedup.
    """
    from src.services import chunked_transcription

    monkeypatch.setattr(chunked_transcription, "CHUNK_SECONDS", 3600)

    fake_chunk_paths = ["/tmp/c0.mp3", "/tmp/c1.mp3"]

    # chunk 0: 정상 segment + overlap 영역 (마지막) 의 "overlap-word"
    # chunk 1: 시작 영역 의 동일 "overlap-word" (Whisper 가 양쪽 chunk 에서 같이 인식) + 신규 segment
    chunk0_segments = [
        {"start": 0.0, "end": 10.0, "text": "첫번째"},
        {"start": 3595.0, "end": 3599.0, "text": "overlap-word"},
    ]
    chunk1_segments = [
        {"start": 1.0, "end": 4.0, "text": "overlap-word"},  # post-offset 3595: 3596~3599, dedup 대상
        {"start": 100.0, "end": 105.0, "text": "두번째-chunk-신규"},  # post-offset 3595: 3695~3700
    ]

    async def fake_whisper_single(path: str) -> list[dict]:
        if path == "/tmp/c0.mp3":
            return chunk0_segments
        return chunk1_segments

    async def fake_split_single_2hr(audio_url, chunk_index, *args, **kwargs):
        return fake_chunk_paths[chunk_index]

    with patch.object(
        chunked_transcription,
        "_ffmpeg_probe_duration",
        AsyncMock(return_value=7200.0),  # 2hr
    ):
        with patch.object(
            chunked_transcription,
            "_ffmpeg_split_single",
            AsyncMock(side_effect=fake_split_single_2hr),
        ):
            with patch.object(
                chunked_transcription,
                "_whisper_transcribe_single",
                AsyncMock(side_effect=fake_whisper_single),
            ):
                with patch("pathlib.Path.unlink"):
                    segments = await chunked_transcription.transcribe_chunked("file:///fake-2hr.mp3")

    # 4 → 3 segment (overlap-word 중복 1건 dedup)
    assert len(segments) == 3
    texts = [s["text"] for s in segments]
    # overlap-word 는 1번만 등장 (chunk 0 의 것 유지, chunk 1 의 것 dedup)
    assert texts.count("overlap-word") == 1
    assert texts == ["첫번째", "overlap-word", "두번째-chunk-신규"]
    # offset 검증 (Codex F-4 fix: chunk 1 의 offset = 1*3600 - 5 = 3595)
    assert segments[0]["start"] == 0.0           # chunk 0 의 첫번째
    assert segments[1]["start"] == 3595.0        # chunk 0 의 overlap-word (offset=0)
    assert segments[2]["start"] == 3695.0        # chunk 1 의 신규 (offset 3595 + 100)
