# Whisper chunked transcription — Sprint 24 Wave 2 T-N+4 BL-T2-003
# 4시간+ production audio 처리 차단 해소. ffmpeg duration probe + 1hr chunk + 5초 overlap + 병렬 Whisper.
"""4시간+ 오디오 chunk 분할 트랜스크립션.

설계:
- 1hr (CHUNK_SECONDS) 이하: 단일 Whisper 호출
- 1hr 초과: ffmpeg 로 1hr 단위 chunk + 5초 overlap 으로 잘라서 병렬 Whisper 호출
- merge 시 chunk index 기반 offset (i * CHUNK_SECONDS) 적용 → 전체 timeline 보존
- chunk N 끝 overlap 영역과 chunk N+1 시작 overlap 영역의 동일 text segment dedupe

주: Whisper API 25MB 제한 회피 + asyncio.gather 병렬 처리로 4hr 처리 시간 단축.
"""
import asyncio
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

CHUNK_SECONDS = 3600  # 1시간 (Whisper 25MB 제한 회피 안전 마진 포함)
OVERLAP_SECONDS = 5   # chunk 경계 문장 잘림 방지용 overlap


async def _ffmpeg_probe_duration(audio_url: str) -> float:
    """ffprobe 로 audio 전체 길이 (초) 측정.

    Returns:
        duration in seconds (float). probe 실패 시 ValueError raise.
    """
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise ValueError(
            f"ffprobe duration 측정 실패 (returncode={proc.returncode}): {stderr.decode(errors='ignore')}"
        )
    text = stdout.decode(errors="ignore").strip()
    if not text:
        raise ValueError("ffprobe 응답이 비어있음")
    return float(text)


async def _ffmpeg_split(
    audio_url: str,
    chunk_seconds: int = CHUNK_SECONDS,
    overlap_seconds: int = OVERLAP_SECONDS,
) -> list[str]:
    """ffmpeg 로 1hr 단위 chunk 분할 + overlap 적용.

    각 chunk i 는 [max(0, i*chunk_seconds - overlap), min(duration, (i+1)*chunk_seconds + overlap)] 범위.
    chunk 0 은 앞쪽 overlap 없음, 마지막 chunk 는 뒤쪽 overlap 없음 (boundary 자동 clamp).

    Returns:
        chunk 파일 경로 리스트 (임시파일, 호출자가 cleanup 책임).
    """
    duration = await _ffmpeg_probe_duration(audio_url)
    n_chunks = int(duration // chunk_seconds) + (1 if duration % chunk_seconds > 0 else 0)
    if n_chunks <= 0:
        return []

    chunks: list[str] = []
    for i in range(n_chunks):
        start = max(0.0, i * chunk_seconds - overlap_seconds)
        end = min(duration, (i + 1) * chunk_seconds + overlap_seconds)
        chunk_path = tempfile.mktemp(suffix=".mp3")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", audio_url,
            "-ss", str(start), "-to", str(end), "-c", "copy", chunk_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            # cleanup partial chunks
            for p in chunks:
                Path(p).unlink(missing_ok=True)
            Path(chunk_path).unlink(missing_ok=True)
            raise RuntimeError(
                f"ffmpeg chunk 분할 실패 (chunk={i}): {stderr.decode(errors='ignore')}"
            )
        chunks.append(chunk_path)
    return chunks


async def _whisper_transcribe_single(audio_path: str) -> list[dict]:
    """단일 chunk 를 Whisper 로 transcribe → dict segment 리스트 반환.

    기존 TranscriptionService.transcribe(bytes, filename) 를 재사용. 각 segment 는
    {"start": float, "end": float, "text": str} 포맷 (chunked merge 계약).
    """
    from src.services.transcription import TranscriptionService

    audio_bytes = Path(audio_path).read_bytes()
    filename = Path(audio_path).name
    service = TranscriptionService()
    segments, _ = await service.transcribe(audio_bytes, filename)
    return [
        {"start": seg.start_sec, "end": seg.end_sec, "text": seg.text}
        for seg in segments
    ]


def _merge_with_offset(
    chunked_segments: list[list[dict]],
    chunk_seconds: int = CHUNK_SECONDS,
    overlap_seconds: int = OVERLAP_SECONDS,
) -> list[dict]:
    """chunk별 segment 리스트 → 전체 timeline 단일 리스트.

    - chunk i 모든 segment start/end 에 offset = i * chunk_seconds 적용 (전체 timeline 복원)
    - chunk i 의 뒤쪽 overlap_seconds 영역과 chunk i+1 의 앞쪽 overlap_seconds 영역에서
      동일 text 의 segment 가 두 번 등장하면 (Whisper 가 양쪽에서 같은 발화 인식) 중복 제거.
    - dedup 기준: 직전 chunk 마지막 segment 와 text 가 일치하고 시간 차가 overlap 영역 내.
    """
    merged: list[dict] = []
    for i, segments in enumerate(chunked_segments):
        offset = i * chunk_seconds
        for seg in segments:
            seg_copy = {
                **seg,
                "start": seg["start"] + offset,
                "end": seg["end"] + offset,
            }
            # overlap dedupe — 직전 chunk 끝 영역과 현재 chunk 시작 영역 중복 segment 차단
            if merged:
                last = merged[-1]
                # 동일 text + 시간 차가 overlap window 안 → 중복으로 판단
                is_overlap_window = seg_copy["start"] < last["end"] + overlap_seconds
                if is_overlap_window and seg_copy["text"] == last["text"]:
                    continue
            merged.append(seg_copy)
    return merged


async def transcribe_chunked(audio_url: str) -> list[dict]:
    """4시간+ chunk 분할 transcription entry point.

    Args:
        audio_url: ffmpeg 가 접근 가능한 audio 경로 또는 URL (http/https/s3/file path).

    Returns:
        전체 timeline segment 리스트. 각 segment: {"start", "end", "text"}.

    Behavior:
        - duration ≤ CHUNK_SECONDS (1hr): 단일 Whisper 호출 (split 없음).
        - duration > CHUNK_SECONDS: ffmpeg 로 1hr chunk + 5초 overlap 분할 →
          asyncio.gather 로 병렬 Whisper → offset merge + overlap dedup.
        - chunk 임시파일은 finally 에서 cleanup (실패해도 누수 X).
    """
    duration = await _ffmpeg_probe_duration(audio_url)
    if duration <= CHUNK_SECONDS:
        logger.debug("audio duration=%.1fs ≤ %ds, 단일 호출", duration, CHUNK_SECONDS)
        return await _whisper_transcribe_single(audio_url)

    logger.info(
        "audio duration=%.1fs > %ds, chunk 분할 시작",
        duration, CHUNK_SECONDS,
    )
    chunk_paths = await _ffmpeg_split(audio_url, CHUNK_SECONDS, OVERLAP_SECONDS)
    try:
        # 병렬 Whisper — chunk N개 동시에 호출 (4hr → ~4 chunk → 4 병렬)
        chunked_segments = await asyncio.gather(
            *[_whisper_transcribe_single(p) for p in chunk_paths]
        )
        return _merge_with_offset(chunked_segments, CHUNK_SECONDS, OVERLAP_SECONDS)
    finally:
        for p in chunk_paths:
            Path(p).unlink(missing_ok=True)
