# Memory 도메인 서비스 — BackgroundTask 분리 architecture (R1)
"""Memory Service — capture (text|voice) + distill + embed.

patch §4 P-R1 architecture:
- POST /memory → 202 + {status: processing} enqueue (≤500ms p95)
- BackgroundTask: text → distill → embed | voice → transcribe → distill → embed
- 별도 AsyncSession (session_factory 패턴, Sprint 9 lesson — request session은 응답 후 닫힘)
- MemoryAICall로 cost/latency 추적 (C2)
- ffmpeg normalize_audio (A2) — webm/mp4/aac → wav 16kHz mono
- capture 후 embedding 경로 항상 (A6)

backend rules §3 — Service는 AsyncSession 인스턴스를 직접 보유하지 않고
session_factory(async_sessionmaker) 만 보유. BackgroundTask 내부에서 별도 session 생성.
(BL-053 Sprint 20 — AsyncSession 자체는 SQLModel 타입으로 import 가능, 단 인스턴스 보유 금지.)
"""
import asyncio
import io
import logging
import os
import re
import subprocess
import tempfile
import time
import uuid
from datetime import datetime

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.prompts import (
    MEMORY_DISTILL_PROMPT,
    MemoryDistilledResult,
    parse_json_response,
)
from src.common.r2 import R2Service
from src.core.config import get_settings
from src.memory.exceptions import (
    AudioTooLargeError,
    CannotPromoteToPersonalError,
    CannotPromoteToSameWorkspaceError,
    EmptyMemoryError,
    MemoryNotFoundError,
    TargetWorkspaceInvalidError,
)
from src.memory.models import (
    MemoryAICall,
    MemoryEvent,
    MemoryItem,
    PromotionAudit,
)
from src.memory.pipeline_service import MemoryPipelineService
from src.memory.repository import MemoryRepository
from src.workspaces.repository import WorkspaceRepository
from src.memory.schemas import (
    MemoryCreateOut,
    MemoryDetailOut,
    MemoryMetricsOut,
    MemoryPromoteOut,
    MemoryRecallOut,
    MemoryRecallSource,
)

logger = logging.getLogger(__name__)

# 상수
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # Whisper API 25MB 한도
WHISPER_MODEL = "gpt-4o-mini-transcribe"  # patch §13 — $0.003/min 기본
GEMINI_MODEL = "gemini-3.1-flash-lite"
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
        workspace_repo: WorkspaceRepository | None = None,
        pipeline: MemoryPipelineService | None = None,
    ) -> None:
        self.repo = repo
        self._session_factory = session_factory
        self.r2_service = r2_service
        # Sprint 19 PR #1 C10 (Codex F-4): promote 의 cross-workspace 검증을 repo API 로 이동
        # (backend rule §3 회복 — service 가 session 직접 사용 금지)
        self.workspace_repo = workspace_repo
        # Sprint 24 Wave 2 BL-006: embeddings 호출은 MemoryPipelineService 경유 (헌법 §4.2 / ADR-014).
        # `_bg_*` 흐름 진입 전 fail-closed 검사 — pipeline 미주입 = orchestrator 우회 = 헌법 위반.
        self._pipeline = pipeline

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

    async def get_metrics(self, workspace_id: uuid.UUID) -> MemoryMetricsOut:
        """Sprint 15 R7 — DB-backed metrics (patch §10 P-R7).

        memory_events 테이블 직접 집계 (Cloud Run stateless 정합).
        모듈-level deque/counter 사용 X.
        """
        counts = await self.repo.get_metrics_counts(workspace_id)
        p50, p95 = await self.repo.get_recall_latency_percentiles(workspace_id)
        return MemoryMetricsOut(
            capture_count=counts.get("capture", 0),
            recall_count=counts.get("recall", 0),
            promote_count=counts.get("promote", 0),
            recall_p50_ms=p50,
            recall_p95_ms=p95,
        )

    async def cleanup_expired_r2_audio(self, days: int = 30) -> int:
        """Sprint 15 R-CRON — 30일 TTL R2 audio cleanup. O-E lock-in.

        매일 GCP Cloud Scheduler에서 호출. 삭제 카운트 반환.
        """
        from datetime import timedelta
        from src.common.r2 import R2Service

        cutoff = datetime.utcnow() - timedelta(days=days)
        expired = await self.repo.list_expired_audio(cutoff)
        r2 = R2Service()
        deleted = 0
        for item in expired:
            if not item.r2_audio_key:
                continue
            try:
                await r2.delete_object(item.r2_audio_key)
            except Exception:
                continue
            await self.repo.clear_r2_audio_key(item.id)
            deleted += 1
        if deleted:
            await self.repo.commit()
        return deleted

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

    # ── R3 recall ──

    async def recall(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        top_k: int = 3,
    ) -> MemoryRecallOut:
        """Vector search + keyword fallback. I-9 workspace_id 강제 + C7 event log.

        O-A: top_k=3 lock-in.
        O-B: keyword fallback은 token overlap count (BM25는 Sprint 17+ defer).
        """
        start = time.time()

        # 1. Vector search — query embedding (C3 cache) + pgvector cosine
        query_embedding = await self._get_query_embedding(workspace_id, query)
        vector_rows: list[tuple] = []
        if query_embedding:
            vector_rows = await self.repo.vector_search(
                workspace_id, query_embedding, top_k
            )

        vector_sources: list[MemoryRecallSource] = []
        for row in vector_rows:
            distilled = row[1] if isinstance(row[1], dict) else {}
            title = distilled.get("title") if distilled else None
            if not title:
                raw = row[2] or ""
                title = raw[:60] if raw else "(제목 없음)"
            atomic_notes = (
                distilled.get("atomic_notes", []) if distilled else []
            )
            vector_sources.append(
                MemoryRecallSource(
                    memory_id=uuid.UUID(str(row[0])),
                    title=title,
                    atomic_notes_excerpt=" / ".join(atomic_notes[:2]),
                    score=float(row[4]),
                    match_type="vector",
                    created_at=row[3],
                )
            )

        if vector_sources:
            elapsed_ms = int((time.time() - start) * 1000)
            await self._log_recall_event(
                workspace_id=workspace_id,
                user_id=user_id,
                latency_ms=elapsed_ms,
                match_type="vector",
                query_len=len(query),
                source_count=len(vector_sources),
            )
            return MemoryRecallOut(
                query=query, sources=vector_sources, fallback_used=False
            )

        # 2. Keyword fallback (O-B)
        tokens = self._tokenize_query(query)
        rows = await self.repo.search_keyword(workspace_id, tokens, limit=top_k)
        keyword_sources: list[MemoryRecallSource] = []
        for item, cnt in rows:
            distilled = item.distilled_json or {}
            title = distilled.get("title") or (
                item.raw_content[:60] if item.raw_content else "(제목 없음)"
            )
            atomic_notes = distilled.get("atomic_notes", []) or []
            keyword_sources.append(
                MemoryRecallSource(
                    memory_id=item.id,
                    title=title,
                    atomic_notes_excerpt=" / ".join(atomic_notes[:2]),
                    score=min(1.0, cnt / max(len(tokens), 1)),
                    match_type="keyword",
                    created_at=item.created_at,
                )
            )

        elapsed_ms = int((time.time() - start) * 1000)
        await self._log_recall_event(
            workspace_id=workspace_id,
            user_id=user_id,
            latency_ms=elapsed_ms,
            match_type="keyword",
            query_len=len(query),
            source_count=len(keyword_sources),
        )
        return MemoryRecallOut(
            query=query, sources=keyword_sources, fallback_used=True
        )

    async def _get_query_embedding(
        self, workspace_id: uuid.UUID, query: str
    ) -> list[float] | None:
        """C3 cache lookup → 미스 시 OpenAI 호출 + cache 저장.

        OpenAI 호출 실패 시 None 반환 (recall은 keyword fallback로 진행).
        """
        normalized = " ".join(query.lower().split())
        cached = await self.repo.get_query_embedding_cache(
            workspace_id, normalized
        )
        if cached is not None:
            return cached
        embedding, _tokens, _elapsed, error = await _call_embedding(query)
        if error or not embedding:
            return None
        await self.repo.save_query_embedding_cache(
            workspace_id, normalized, embedding
        )
        await self.repo.commit()
        return embedding

    @staticmethod
    def _tokenize_query(query: str) -> list[str]:
        """한국어 어절 + 영문 단어 단위 split (2자 이상). 대소문자 normalize."""
        tokens = re.findall(
            r"[가-힣]+|[A-Za-z][A-Za-z0-9_]*", query.lower()
        )
        return [t for t in tokens if len(t) >= 2]

    async def _log_recall_event(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        latency_ms: int,
        match_type: str,
        query_len: int,
        source_count: int,
    ) -> None:
        """C7: memory_events 'recall' row 기록."""
        await self.repo.save_event(
            MemoryEvent(
                workspace_id=workspace_id,
                user_id=user_id,
                event_type="recall",
                latency_ms=latency_ms,
                event_metadata={
                    "match_type": match_type,
                    "query_len": query_len,
                    "source_count": source_count,
                },
            )
        )
        await self.repo.commit()

    # ── R6 promote 1-button ──

    async def promote(
        self,
        *,
        memory_id: uuid.UUID,
        source_workspace_id: uuid.UUID,
        target_workspace_id: uuid.UUID,
        promoted_by_user_id: uuid.UUID,
        background_tasks: BackgroundTasks,
    ) -> MemoryPromoteOut:
        """1-button promote: 원본 보존 + target ws 복제 + audit row + bg embedding 재생성.

        ADR-016 AD-41 (복제 + tombstone) — source MemoryItem.status 변경 없음.
        검증: source != target / target type='team' / user가 target ws 멤버.
        Sprint 19 PR #1 C10 (Codex F-4): WorkspaceRepository 통한 검증 (backend rule §3 회복).
        """
        if source_workspace_id == target_workspace_id:
            raise CannotPromoteToSameWorkspaceError()

        # Sprint 19 PR #1 C10 (Codex F-4): fail-closed — workspace_repo 미주입 시 RuntimeError
        if self.workspace_repo is None:
            raise RuntimeError("workspace_repo 필수 (F-4 promote target 검증)")
        # Sprint 24 Wave 2 BL-006: pipeline 주입 강제 (BG embed 단계에서 embeddings 위임).
        if self._pipeline is None:
            raise RuntimeError(
                "MemoryPipelineService 미주입 — BL-006 헌법 §4.2 위반 (embeddings 직접 호출 금지)"
            )

        # 1. 원본 fetch (workspace_id 강제 필터로 I-9 격리)
        source = await self.repo.get_by_id(memory_id, source_workspace_id)
        if source is None:
            raise MemoryNotFoundError()

        # 2. target workspace 검증 — WorkspaceRepository API 사용 (Codex F-4)
        target = await self.workspace_repo.find_by_id(target_workspace_id)
        if target is None:
            raise TargetWorkspaceInvalidError()
        if getattr(target, "type", "team") == "personal":
            raise CannotPromoteToPersonalError()
        member = await self.workspace_repo.find_member(
            target_workspace_id, promoted_by_user_id
        )
        if member is None:
            raise TargetWorkspaceInvalidError()

        # 3. 복제본 MemoryItem 신규 (원본은 그대로 보존)
        duplicate = MemoryItem(
            user_id=promoted_by_user_id,
            workspace_id=target_workspace_id,
            type=source.type,
            raw_content=source.raw_content,
            distilled_json=source.distilled_json,
            r2_audio_key=source.r2_audio_key,
            status="embedding_pending",
        )
        await self.repo.save_item(duplicate)

        # 4. promotion_audit row
        audit = PromotionAudit(
            memory_id=source.id,
            source_workspace_id=source_workspace_id,
            target_workspace_id=target_workspace_id,
            target_project_id=None,
            promoted_by_user_id=promoted_by_user_id,
            embedding_status="pending",
        )
        await self.repo.save_promotion_audit(audit)

        # 5. promote 이벤트 (C7 DB-backed metrics)
        await self.repo.save_event(
            MemoryEvent(
                workspace_id=source_workspace_id,
                user_id=promoted_by_user_id,
                event_type="promote",
                event_metadata={
                    "source_memory_id": str(source.id),
                    "target_workspace_id": str(target_workspace_id),
                    "new_memory_id": str(duplicate.id),
                },
            )
        )
        await self.repo.commit()

        # 6. background: target ws에 embedding 재생성 + audit status 갱신
        embed_text = _build_embed_text(
            source.distilled_json or {}, source.raw_content
        )
        background_tasks.add_task(
            _bg_promote_embed,
            new_memory_id=duplicate.id,
            target_workspace_id=target_workspace_id,
            audit_id=audit.id,
            embed_text=embed_text,
            session_factory=self._session_factory,
            pipeline=self._pipeline,
        )

        return MemoryPromoteOut(
            new_memory_id=duplicate.id,
            audit_id=audit.id,
            status="embedding_pending",
        )

    # ── BackgroundTask 헬퍼 (별도 session) ──

    async def _bg_distill_and_embed(
        self,
        memory_id: uuid.UUID,
        workspace_id: uuid.UUID,
        raw_text: str,
    ) -> None:
        """Text capture 후 distill → embed 백그라운드 처리."""
        # Sprint 24 Wave 2 BL-006: pipeline 주입 강제 (fail-closed).
        if self._pipeline is None:
            raise RuntimeError(
                "MemoryPipelineService 미주입 — BL-006 헌법 §4.2 위반 (embeddings 직접 호출 금지)"
            )
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

            # Sprint 24 Wave 2 BL-006: embeddings 호출은 MemoryPipelineService 위임 (헌법 §4.2).
            # source_type='memory' 는 pipeline 이 고정. I-9 4-C workspace_id 매칭 assertion 은
            # EmbeddingRepository.save_chunk 가 강제.
            chunk = await self._pipeline.save_memory_chunk(
                session,
                workspace_id=workspace_id,
                source_workspace_id=workspace_id,
                source_id=memory_id,
                chunk_text=embed_text,
                embedding=embedding,
                chunk_index=0,
                chunk_level=2,
            )
            await repo.update_embedding(memory_id, chunk.id, "active")
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
        # 보안: filename에 path traversal / control char 차단 + 길이 제한 (R2 key 폭주 방지)
        import re
        # 확장자 제거 (서버는 정규화 후 .wav로 저장)
        base = filename.rsplit(".", 1)[0]
        safe_base = re.sub(r"[^A-Za-z0-9._-]", "_", base)[:64]
        settings = get_settings()
        key = f"memory/{workspace_id}/{uuid.uuid4()}-{safe_base}.wav"
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
        # 보안: LLM 우회 시 raw user input이 distilled_json에 그대로 들어가지 않도록
        # Pydantic re-validation 강제 (atomic_notes 길이 / visibility enum 검증).
        title = (text[:20] if text else "메모") or "메모"
        atomic_notes = [text[:200]] if text else []
        try:
            validated_fallback = MemoryDistilledResult.model_validate(
                {
                    "title": title,
                    "atomic_notes": atomic_notes,
                    "suggested_visibility": "personal",
                }
            )
            fallback = validated_fallback.model_dump()
        except Exception:
            # validation도 실패하면 가장 안전한 minimal shape (XSS/injection 차단)
            fallback = {
                "title": "메모",
                "atomic_notes": [],
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


async def _bg_promote_embed(
    new_memory_id: uuid.UUID,
    target_workspace_id: uuid.UUID,
    audit_id: uuid.UUID,
    embed_text: str,
    session_factory: "async_sessionmaker[AsyncSession]",
    pipeline: MemoryPipelineService,
) -> None:
    """R6 promote 백그라운드: 복제 MemoryItem에 embedding 생성 + audit status 갱신.

    pending → processing → completed/failed 흐름. session_factory로 별도 session.
    Sprint 24 Wave 2 BL-006: embeddings 호출은 MemoryPipelineService 위임 (헌법 §4.2).
    """
    from sqlmodel import update as _update

    async with session_factory() as session:
        repo = MemoryRepository(session)
        # processing 마크
        await session.exec(
            _update(PromotionAudit)
            .where(PromotionAudit.id == audit_id)
            .values(embedding_status="processing")
        )
        await session.commit()

        embedding, _tokens, _elapsed, error = await _call_embedding(embed_text)
        if error or not embedding:
            await session.exec(
                _update(PromotionAudit)
                .where(PromotionAudit.id == audit_id)
                .values(embedding_status="failed")
            )
            await repo.update_status(new_memory_id, "embedding_failed")
            await session.commit()
            return

        # Sprint 24 Wave 2 BL-006: pipeline 위임 (헌법 §4.2). I-9 4-C target workspace
        # 매칭 assertion 은 EmbeddingRepository.save_chunk 가 강제.
        chunk = await pipeline.save_memory_chunk(
            session,
            workspace_id=target_workspace_id,
            source_workspace_id=target_workspace_id,
            source_id=new_memory_id,
            chunk_text=embed_text,
            embedding=embedding,
            chunk_index=0,
            chunk_level=2,
        )
        await repo.update_embedding(new_memory_id, chunk.id, "active")
        await session.exec(
            _update(PromotionAudit)
            .where(PromotionAudit.id == audit_id)
            .values(embedding_status="completed")
        )
        await session.commit()


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
