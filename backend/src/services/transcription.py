# backend/src/services/transcription.py
"""Whisper API 트랜스크립션 서비스. 화자 분리 없음 (Sprint 1 MVP)."""
import asyncio
import io
import json
import logging
import os
import tempfile

import httpx
from openai import AsyncOpenAI

from src.core.config import get_settings
from src.meetings.models import TranscriptSegment

logger = logging.getLogger(__name__)


async def convert_to_wav(input_path: str) -> str:
    """ffmpeg로 입력 파일을 wav 16kHz mono로 변환. 이미 wav면 스킵.

    카카오톡 m4a(3GP 컨테이너) 등 비표준 오디오를 Whisper API 호환 형식으로 변환한다.
    보안을 위해 create_subprocess_exec 사용 (shell injection 방지).
    """
    # 1. ffprobe로 포맷 감지
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", input_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *probe_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()

    try:
        format_info = json.loads(stdout)
        format_name = format_info.get("format", {}).get("format_name", "")
    except (json.JSONDecodeError, KeyError):
        format_name = ""

    # 2. 이미 wav면 스킵
    if "wav" in format_name:
        logger.debug("이미 WAV 형식, 변환 스킵: %s", input_path)
        return input_path

    # 3. wav로 변환 (16kHz mono, PCM 16-bit)
    output_path = tempfile.mktemp(suffix=".wav")
    convert_cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        output_path,
    ]
    logger.info("ffmpeg 변환 시작: %s → %s", input_path, output_path)

    proc = await asyncio.create_subprocess_exec(
        *convert_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 변환 실패: {stderr.decode()}")

    logger.info("ffmpeg 변환 완료: %s", output_path)
    return output_path


class TranscriptionService:
    """Whisper API로 오디오 → 트랜스크립트 변환."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        )

    async def transcribe(
        self, audio_bytes: bytes, filename: str = "audio.mp3"
    ) -> tuple[list[TranscriptSegment], float]:
        """오디오 바이트 → (TranscriptSegment 리스트, 전체 길이 초).

        비표준 오디오(카카오톡 m4a 등)는 ffmpeg로 WAV 변환 후 Whisper에 전달.
        화자 분리 없음 — 모든 segment의 speaker = "Speaker".
        Sprint 2에서 pyannote 추가 예정.
        """
        # ffmpeg 변환: bytes → 임시 파일 → convert_to_wav → 변환된 bytes
        input_tmp = None
        wav_path = None
        try:
            # 원본 bytes를 임시 파일에 저장 (확장자 유지)
            ext = os.path.splitext(filename)[1] or ".mp3"
            input_fd, input_tmp = tempfile.mkstemp(suffix=ext)
            os.write(input_fd, audio_bytes)
            os.close(input_fd)

            # ffmpeg 변환 (이미 wav면 input_tmp 그대로 반환)
            wav_path = await convert_to_wav(input_tmp)

            # 변환된 파일을 읽어서 Whisper에 전달
            with open(wav_path, "rb") as f:
                converted_bytes = f.read()

            # 변환된 경우 filename을 .wav로
            whisper_filename = "audio.wav" if wav_path != input_tmp else filename
            audio_file = io.BytesIO(converted_bytes)
            audio_file.name = whisper_filename

        finally:
            # 임시 파일 정리
            if input_tmp and os.path.exists(input_tmp):
                os.unlink(input_tmp)
            if wav_path and wav_path != input_tmp and os.path.exists(wav_path):
                os.unlink(wav_path)

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
