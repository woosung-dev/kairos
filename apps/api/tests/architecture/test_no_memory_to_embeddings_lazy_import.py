# Architecture gate — memory → embeddings 직접 import 회귀 방지 (BL-006 해소, Sprint 24 Wave 2)
"""헌법 §4.2 + ADR-014 옵션 A 회귀 방지.

memory 도메인 service.py 는 embeddings 도메인 직접 import 금지.
embeddings 호출은 `memory/pipeline_service.py` 의 `MemoryPipelineService` 경유.

E-9 (embeddings/CONTEXT.md): `_apply_hnsw_session_params` 외부 사용처는 의도된 예외.
캡슐화 우회의 최소 비용 약속 (Sprint 16). `memory/repository.py` 1 hit 유지.
"""
import re
from pathlib import Path

# apps/api/tests/architecture/* → apps/api/ 까지 3-up
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_memory_service_no_embeddings_import() -> None:
    """memory/service.py 가 `from src.embeddings.*` / `import src.embeddings` 0건.

    BL-006 회귀 방지: lazy import 라도 적재되면 헌법 §4.2 위반.
    """
    service_path = BACKEND_ROOT / "src" / "memory" / "service.py"
    source = service_path.read_text(encoding="utf-8")

    # `from src.embeddings...` 또는 `import src.embeddings` 패턴 검출.
    pattern = re.compile(
        r"^\s*(?:from\s+src\.embeddings|import\s+src\.embeddings)\b",
        re.MULTILINE,
    )
    hits = pattern.findall(source)
    assert hits == [], (
        f"BL-006 회귀: memory/service.py 가 src.embeddings 를 직접 import. "
        f"hits={hits}. orchestrator (memory/pipeline_service.py) 경유 필수."
    )


def test_memory_repository_apply_hnsw_helper_keep() -> None:
    """memory/repository.py 의 `_apply_hnsw_session_params` import 1건 유지 (E-9 예외).

    embeddings/CONTEXT.md E-9 명시: `embedding_chunks` 직접 SQL 외부 도메인은 본 헬퍼
    호출 강제. capsule 우회 최소 비용 약속 (Sprint 16). 본 import 가 사라지면 vector
    검색 트랜잭션이 HNSW 세션 변수 (`ef_search`, `iterative_scan` 등) 없이 실행됨 →
    회귀 위험. BL-006 해소 후에도 본 import 는 의도적으로 유지.
    """
    repo_path = BACKEND_ROOT / "src" / "memory" / "repository.py"
    source = repo_path.read_text(encoding="utf-8")

    pattern = re.compile(
        r"^\s*from\s+src\.embeddings\.repository\s+import\s+.*_apply_hnsw_session_params",
        re.MULTILINE,
    )
    hits = pattern.findall(source)
    assert len(hits) == 1, (
        f"E-9 예외 침해: memory/repository.py 의 `_apply_hnsw_session_params` import "
        f"가 {len(hits)} 건. 정확히 1 건 유지 필요 (embeddings/CONTEXT.md E-9)."
    )
