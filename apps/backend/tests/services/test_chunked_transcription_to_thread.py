# Sprint 29 R1 (svc-blocking) 회귀 가드 — chunk 파일 읽기 asyncio.to_thread 오프로드.
"""_whisper_transcribe_single 이 동기 Path.read_bytes() 대신 asyncio.to_thread 로
파일을 읽어도 bytes 가 정상 전달되고 segment dict 를 반환하는지 검증.
"""
from types import SimpleNamespace

import pytest

import src.services.chunked_transcription as ct


@pytest.mark.asyncio
async def test_whisper_transcribe_single_reads_via_to_thread(tmp_path, monkeypatch):
    audio = tmp_path / "chunk0.wav"
    audio.write_bytes(b"RIFF-fake-audio-bytes")

    captured: dict = {}

    class _FakeTranscription:
        async def transcribe(self, audio_bytes, filename):
            captured["bytes"] = audio_bytes
            captured["filename"] = filename
            seg = SimpleNamespace(start_sec=0.0, end_sec=1.5, text="안녕하세요")
            return [seg], None

    # _whisper_transcribe_single 내부 import 대상 monkeypatch
    monkeypatch.setattr(
        "src.services.transcription.TranscriptionService", _FakeTranscription
    )

    result = await ct._whisper_transcribe_single(str(audio))

    assert captured["bytes"] == b"RIFF-fake-audio-bytes"  # to_thread read 정확
    assert captured["filename"] == "chunk0.wav"
    assert result == [{"start": 0.0, "end": 1.5, "text": "안녕하세요"}]
