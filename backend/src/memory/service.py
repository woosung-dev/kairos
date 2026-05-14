# Memory 도메인 서비스 — BackgroundTask 분리 architecture (R1)
"""Memory Service — capture (text|voice) + distill + embed.

patch §4 P-R1 architecture:
- POST /memory → 202 + {status: processing} enqueue (≤500ms p95)
- BackgroundTask: text → distill → embed | voice → transcribe → distill → embed
- 별도 AsyncSession (session_factory 패턴, Sprint 9 lesson — request session은 응답 후 닫힘)
- MemoryAICall로 cost/latency 추적 (C2)
- ffmpeg normalize_audio (A2) — webm/mp4/aac → wav 16kHz mono
- capture 후 embedding 경로 항상 (A6)

backend rules §3 — AsyncSession import 금지. session_factory만 보유.
"""
import asyncio
import io
import logging
import os
import subprocess
import tempfile
import time
import uuid

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.common.prompts import (
    MEMORY_DISTILL_PROMPT,
    MemoryDistilledResult,
    parse_json_response,
)
from src.common.r2 import R2Service
from src.core.config import get_settings
from src.memory.exceptions import (
    AudioTooLargeError,
    EmptyMemoryError,
    MemoryNotFoundError,
)
from src.memory.models import MemoryAICall, MemoryEvent, MemoryItem
from src.memory.repository import MemoryRepository
from src.memory.schemas import MemoryCreateOut, MemoryDetailOut

logger = logging.getLogger(__name__)

# 상수
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # Whisper API 25MB 한도
WHISPER_MODEL = "gpt-4o-mini-transcribe"  # patch §13 — $0.003/min 기본
GEMINI_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "text-embedding-3-small"


class MemoryService:
    """Memory 도메인 서비스.

    - capture_text / capture_voice: 즉시 enqueue + 202 반환
    - BackgroundTask는 `_bg_*` 메소드가 session_factory로 새 session 생성하여 수행
    - AsyncSession은 Repository만 보유 — 본 서비스는 session_factory만 가짐
    """

    def __init__(
        self,
        repo: MemoryRepository,
        session_factory: async_sessionmaker[AsyncSession],
        r2_service: R2Service,
    ) -> None:
        self.repo = repo
        self._session_factory = session_factory
        self.r2_service = r2_service

    # ── 요청 핸들러 ──

    async def capture_text(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        text: str,
        background_tasks: BackgroundTasks,
    ) -> MemoryCreateOut:
        """텍스트 메모 capture — 즉시 202 enqueue."""
        if not text.strip():
            raise EmptyMemoryError()
        item = MemoryItem(
            user_id=user_id,
            workspace_id=workspace_id,
            type="text",
            raw_content=text,
            status="processing",
        )
        await self.repo.save_item(item)
        await self.repo.save_event(
            MemoryEvent(
                workspace_id=workspace_id,
                user_id=user_id,
                event_type="capture",
                event_metadata={"type": "text", "length": len(text)},
            )
        )
        await self.repo.commit()

        background_tasks.add_task(
            self._bg_distill_and_embed,
            memory_id=item.id,
            workspace_id=workspace_id,
            raw_text=text,
        )
        return MemoryCreateOut(
            memory_id=item.id,
            status="processing",
            distilled_json=None,
            created_at=item.created_at,
        )

    async def capture_voice(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        audio_bytes: bytes,
        filename: str,
        background_tasks: BackgroundTasks,
    ) -> MemoryCreateOut:
        """음성 메모 capture — R2 upload 후 즉시 202 enqueue."""
        if not audio_bytes:
            raise EmptyMemoryError()
        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise AudioTooLargeError()

        # ffmpeg normalize (A2) — webm/mp4/aac → wav 16kHz mono
        wav_bytes = await _normalize_audio(audio_bytes, filename)

        # R2 업로드 — memory 전용 경로
        r2_key = await self._upload_audio_to_r2(workspace_id, filename, wav_bytes)

        item = MemoryItem(
            user_id=user_id,
            workspace_id=workspace_id,
            type="voice",
            raw_content="",
            r2_audio_key=r2_key,
            status="transcription_pending",
        )
        await self.repo.save_item(item)
        await self.repo.save_event(
            MemoryEvent(
                workspace_id=workspace_id,
                user_id=user_id,
                event_type="capture",
                event_metadata={"type": "voice", "bytes": len(audio_bytes)},
            )
        )
        await self.repo.commit()

        background_tasks.add_task(
            self._bg_transcribe_distill_embed,
            memory_id=item.id,
            workspace_id=workspace_id,
            r2_key=r2_key,
        )
        return MemoryCreateOut(
            memory_id=item.id,
            status="transcription_pending",
            distilled_json=None,
            created_at=item.created_at,
        )

    async def get_memory(
        self, memory_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> MemoryDetailOut:
        """단일 메모 조회 — polling endpoint."""
        item = await self.repo.get_by_id(memory_id, workspace_id)
        if not item:
            raise MemoryNotFoundError()
        return MemoryDetailOut(
            memory_id=item.id,
            workspace_id=item.workspace_id,
            type=item.type,
            raw_content=item.raw_content,
            distilled_json=item.distilled_json,
            status=item.status,
            embedding_chunk_id=item.embedding_chunk_id,
            r2_audio_key=item.r2_audio_key,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    # ── BackgroundTask 헬퍼 (별도 session) ──

    async def _bg_distill_and_embed(
        self,
        memory_id: uuid.UUID,
        workspace_id: uuid.UUID,
        raw_text: str,
    ) -> None:
        """Text capture 후 distill → embed 백그라운드 처리."""
        async with self._session_factory() as session:
            repo = MemoryRepository(session)
            # 1. distill
            distilled, in_tok, out_tok, elapsed_ms, error = await _call_distill(raw_text)
            await repo.save_ai_call(
                MemoryAICall(
                    memory_id=memory_id,
                    workspace_id=workspace_id,
                    call_type="distill",
                    model_name=GEMINI_MODEL,
                    elapsed_ms=elapsed_ms,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    status="success" if not error else "failed",
                    error_message=error,
                )
            )
            await repo.update_distilled(memory_id, distilled, "embedding_pending")
            await repo.commit()

            # 2. embed (A6 — capture 후 항상 embedding)
            embed_text = _build_embed_text(distilled, raw_text)
            embedding, embed_tok, embed_elapsed, embed_error = await _call_embedding(
                embed_text
            )
            await repo.save_ai_call(
                MemoryAICall(
                    memory_id=memory_id,
                    workspace_id=workspace_id,
                    call_type="embedding",
                    model_name=EMBEDDING_MODEL,
                    elapsed_ms=embed_elapsed,
                    input_tokens=embed_tok,
                    output_tokens=0,
                    status="success" if not embed_error else "failed",
                    error_message=embed_error,
                )
            )
            if embed_error or not embedding:
                await repo.update_status(memory_id, "embedding_failed")
                await repo.commit()
                return

            chunk_id = await _create_memory_embedding_chunk(
                session, memory_id, workspace_id, embed_text, embedding
            )
            await repo.update_embedding(memory_id, chunk_id, "active")
            await repo.commit()

    async def _bg_transcribe_distill_embed(
        self,
        memory_id: uuid.UUID,
        workspace_id: uuid.UUID,
        r2_key: str,
    ) -> None:
        """Voice capture 후 transcribe → distill → embed 백그라운드 처리."""
        async with self._session_factory() as session:
            repo = MemoryRepository(session)
            try:
                wav_bytes = await self._download_audio_from_r2(r2_key)
            except Exception as exc:  # R2 다운로드 실패
                logger.warning("R2 다운로드 실패 (memory=%s): %s", memory_id, exc)
                await repo.update_status(memory_id, "embedding_failed")
                await repo.commit()
                return

            transcript, transcribe_elapsed, error = await _call_transcribe(wav_bytes)
            await repo.save_ai_call(
                MemoryAICall(
                    memory_id=memory_id,
                    workspace_id=workspace_id,
                    call_type="transcription",
                    model_name=WHISPER_MODEL,
                    elapsed_ms=transcribe_elapsed,
                    input_tokens=0,
                    output_tokens=0,
                    status="success" if not error else "failed",
                    error_message=error,
                )
            )
            if error or not transcript:
                await repo.update_status(memory_id, "embedding_failed")
                await repo.commit()
                return
            await repo.update_transcript(memory_id, transcript)
            await repo.update_status(memory_id, "processing")
            await repo.commit()

        # text branch와 동일한 흐름 재사용
        await self._bg_distill_and_embed(memory_id, workspace_id, transcript)

    # ── R2 헬퍼 (R2Service 위임) ──

    async def _upload_audio_to_r2(
        self, workspace_id: uuid.UUID, filename: str, content: bytes
    ) -> str:
        """memory 전용 R2 키로 업로드. R2Service.upload_file_bytes는 uploads/{uuid}/ prefix이므로
        memory/{workspace_id}/ prefix 패턴은 직접 boto3 호출로 처리."""
        settings = get_settings()
        key = f"memory/{workspace_id}/{uuid.uuid4()}-{filename}.wav"
        async with self.r2_service._session.client(
            "s3",
            endpoint_url=self.r2_service._get_endpoint_url(),
            aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
            aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
            region_name="auto",
        ) as client:
            await client.put_object(
                Bucket=settings.r2_bucket_name,
                Key=key,
                Body=content,
                ContentType="audio/wav",
            )
        return key

    async def _download_audio_from_r2(self, key: str) -> bytes:
        """memory/* 키의 wav 다운로드."""
        settings = get_settings()
        async with self.r2_service._session.client(
            "s3",
            endpoint_url=self.r2_service._get_endpoint_url(),
            aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
            aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
            region_name="auto",
        ) as client:
            resp = await client.get_object(
                Bucket=settings.r2_bucket_name, Key=key
            )
            async with resp["Body"] as stream:
                return await stream.read()


# ── 모듈-level AI 호출 헬퍼 (테스트 monkeypatch 진입점) ──


async def _call_distill(
    text: str,
) -> tuple[dict, int, int, int, str | None]:
    """Gemini distill 호출. 반환: (distilled, in_tok, out_tok, elapsed_ms, error)."""
    from google import genai

    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
    start = time.time()
    try:
        prompt = MEMORY_DISTILL_PROMPT.format(content=text)
        resp = await client.aio.models.generate_content(
            model=GEMINI_MODEL, contents=prompt
        )
        elapsed = int((time.time() - start) * 1000)
        raw = parse_json_response(resp.text or "")
        validated = MemoryDistilledResult.model_validate(raw)
        usage = getattr(resp, "usage_metadata", None)
        in_tok = getattr(usage, "prompt_token_count", 0) or 0
        out_tok = getattr(usage, "candidates_token_count", 0) or 0
        return validated.model_dump(), in_tok, out_tok, elapsed, None
    except Exception as exc:
        elapsed = int((time.time() - start) * 1000)
        # fallback — 사용자가 검색 가능하도록 최소 정보 유지
        fallback = {
            "title": (text[:20] if text else "메모") or "메모",
            "atomic_notes": [text[:200]] if text else [],
            "suggested_visibility": "personal",
        }
        return fallback, 0, 0, elapsed, str(exc)


async def _call_embedding(
    text: str,
) -> tuple[list[float], int, int, str | None]:
    """OpenAI 임베딩 호출. 반환: (embedding, total_tokens, elapsed_ms, error)."""
    from openai import AsyncOpenAI

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    start = time.time()
    try:
        resp = await client.embeddings.create(
            model=EMBEDDING_MODEL, input=text
        )
        elapsed = int((time.time() - start) * 1000)
        return resp.data[0].embedding, resp.usage.total_tokens, elapsed, None
    except Exception as exc:
        elapsed = int((time.time() - start) * 1000)
        return [], 0, elapsed, str(exc)


async def _call_transcribe(
    audio_bytes: bytes,
) -> tuple[str, int, str | None]:
    """Whisper transcribe 호출. 반환: (transcript, elapsed_ms, error)."""
    from openai import AsyncOpenAI

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    start = time.time()
    try:
        f = io.BytesIO(audio_bytes)
        f.name = "audio.wav"
        resp = await client.audio.transcriptions.create(
            model=WHISPER_MODEL, file=f, language="ko"
        )
        elapsed = int((time.time() - start) * 1000)
        return (getattr(resp, "text", "") or ""), elapsed, None
    except Exception as exc:
        elapsed = int((time.time() - start) * 1000)
        return "", elapsed, str(exc)


async def _create_memory_embedding_chunk(
    session: AsyncSession,
    memory_id: uuid.UUID,
    workspace_id: uuid.UUID,
    content: str,
    embedding: list[float],
) -> uuid.UUID:
    """memory_id를 source_id로 EmbeddingChunk(level=2) insert.

    source_type='memory' — recall(R3)에서 source_type 필터로 사용.
    """
    from src.embeddings.models import EmbeddingChunk

    chunk = EmbeddingChunk(
        workspace_id=workspace_id,
        source_id=memory_id,
        source_type="memory",
        chunk_text=content,
        chunk_index=0,
        chunk_level=2,
        embedding=embedding,
        metadata_json={},
    )
    session.add(chunk)
    await session.flush()
    return chunk.id


def _build_embed_text(distilled: dict, fallback_text: str) -> str:
    """임베딩 입력 문자열 구성. title + atomic_notes 우선, 없으면 원문 fallback."""
    title = distilled.get("title", "") or ""
    notes = " ".join(distilled.get("atomic_notes", []) or [])
    combined = f"{title} {notes}".strip()
    return combined or fallback_text


# ── ffmpeg normalize_audio (A2 fix) ──


async def _normalize_audio(audio_bytes: bytes, filename: str) -> bytes:
    """ffmpeg로 webm/mp4/aac → wav 16kHz mono 변환.

    ffmpeg 실패 시 raw bytes fallback — Whisper가 webm/mp4 직접 처리 가능.
    """
    suffix = os.path.splitext(filename)[1] or ".webm"
    fd_in, in_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd_in)
    out_path = in_path + ".wav"
    try:
        with open(in_path, "wb") as f_in:
            f_in.write(audio_bytes)
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            in_path,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "wav",
            out_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0 or not os.path.exists(out_path):
            logger.warning(
                "ffmpeg 변환 실패 (filename=%s) — raw bytes로 fallback", filename
            )
            return audio_bytes
        with open(out_path, "rb") as f_out:
            return f_out.read()
    except FileNotFoundError:
        # ffmpeg 미설치 환경 (테스트 등) — raw bytes fallback
        logger.warning("ffmpeg 미설치 — raw bytes로 fallback")
        return audio_bytes
    finally:
        if os.path.exists(in_path):
            os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)
