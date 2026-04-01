# backend/src/services/transcription.py
"""Whisper API 트랜스크립션 서비스. 화자 분리 없음 (Sprint 1 MVP)."""
import io

import httpx
from openai import AsyncOpenAI

from src.core.config import get_settings
from src.meetings.models import TranscriptSegment


class TranscriptionService:
    """Whisper API로 오디오 → 트랜스크립트 변환."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        )

    async def transcribe(
        self, audio_bytes: bytes
    ) -> tuple[list[TranscriptSegment], float]:
        """오디오 바이트 → (TranscriptSegment 리스트, 전체 길이 초).

        화자 분리 없음 — 모든 segment의 speaker = "Speaker".
        Sprint 2에서 pyannote 추가 예정.
        """
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"

        response = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

        segments = [
            TranscriptSegment(
                speaker="Speaker",
                start_sec=seg.start,
                end_sec=seg.end,
                text=seg.text.strip(),
            )
            for seg in (response.segments or [])
        ]
        duration = response.duration or 0.0
        return segments, duration

    async def download_audio(self, url: str) -> bytes:
        """presigned URL에서 오디오 파일 다운로드."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=300.0)
            resp.raise_for_status()
            return resp.content
