"""apps/api/scripts/r2_cleanup.py 안전 규칙 테스트 (체크리스트 0-12 · T-32).

가짜 S3 클라이언트와 가짜 DB 참조 조회만 쓴다 — R2·DB 에 연결하지 않는다.
외부 의존성 없이 돈다 (스크립트가 aioboto3/asyncpg 를 지연 import 하므로).

  python3 scripts/tests/test_r2_cleanup.py                      # 표준 라이브러리만
  cd apps/api && uv run pytest ../../scripts/tests/test_r2_cleanup.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import io
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_SCRIPT = Path(__file__).resolve().parents[2] / "apps" / "api" / "scripts" / "r2_cleanup.py"
_spec = importlib.util.spec_from_file_location("r2_cleanup_under_test", _SCRIPT)
assert _spec and _spec.loader
r2 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = r2  # dataclass 가 모듈을 찾을 수 있게 등록
_spec.loader.exec_module(r2)

NOW = datetime(2026, 9, 27, 0, 0, tzinfo=timezone.utc)
OLD = NOW - timedelta(days=90)
YOUNG = NOW - timedelta(days=1)

# 운영 형태를 흉내 낸 목록 — 살아 있는 회의 원본(uploads/)·음성 메모(memory/)·고아·다른 프로젝트 키
LIVE_MEETING = "uploads/11111111-1111-1111-1111-111111111111/weekly-sync.m4a"
LIVE_MEETING_PROMOTED = "uploads/22222222-2222-2222-2222-222222222222/beta-meeting.m4a"
LIVE_MEMO = "memory/33333333-3333-3333-3333-333333333333/aaaa-voice.wav"
ORPHAN_MEETING = "uploads/44444444-4444-4444-4444-444444444444/deleted-meeting.m4a"
ORPHAN_MEMO = "memory/33333333-3333-3333-3333-333333333333/bbbb-deleted.wav"
YOUNG_UNREFERENCED = "uploads/55555555-5555-5555-5555-555555555555/just-uploaded.m4a"
OTHER_PROJECT_ROOT = "0f1e2d3c4b5a69788796a5b4c3d2e1f0.png"  # nexus-core: 루트 키
OTHER_PROJECT_BACKUP = "db-backups/nexus-20260901-0417.dump.gz"  # nexus-core 백업

FAKE_BUCKET = [
    {"Key": LIVE_MEETING, "LastModified": OLD, "Size": 5_000_000},
    {"Key": LIVE_MEETING_PROMOTED, "LastModified": OLD, "Size": 2_000_000},
    {"Key": LIVE_MEMO, "LastModified": OLD, "Size": 300_000},
    {"Key": ORPHAN_MEETING, "LastModified": OLD, "Size": 1_000_000},
    {"Key": ORPHAN_MEMO, "LastModified": OLD, "Size": 200_000},
    {"Key": YOUNG_UNREFERENCED, "LastModified": YOUNG, "Size": 900_000},
    {"Key": OTHER_PROJECT_ROOT, "LastModified": OLD, "Size": 10_000},
    {"Key": OTHER_PROJECT_BACKUP, "LastModified": OLD, "Size": 50_000_000},
]
DB_REFERENCED = {LIVE_MEETING, LIVE_MEETING_PROMOTED, LIVE_MEMO}
ENV_PROD = {
    "R2_ACCOUNT_ID": "acct",
    "R2_ACCESS_KEY_ID": "id",
    "R2_SECRET_ACCESS_KEY": "secret",
    "R2_BUCKET_NAME": "nexus-core-storage",
    "DATABASE_URL": "postgresql+asyncpg://kairos:pw@db:5432/kairos",
    "APP_ENV": "production",
}


class FakeS3:
    """list_objects_v2 (prefix 필터 + 페이지네이션) / delete_objects 기록만 하는 가짜."""

    def __init__(self, objects: list[dict[str, Any]], page_size: int = 2, fail_keys: set[str] | None = None):
        self.objects = objects
        self.page_size = page_size
        self.fail_keys = fail_keys or set()
        self.listed_prefixes: list[str] = []
        self.deleted: list[str] = []

    async def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]:
        prefix = kwargs["Prefix"]
        self.listed_prefixes.append(prefix)
        matching = sorted((o for o in self.objects if o["Key"].startswith(prefix)), key=lambda o: o["Key"])
        start = int(kwargs.get("ContinuationToken") or 0)
        page = matching[start : start + self.page_size]
        truncated = start + self.page_size < len(matching)
        response: dict[str, Any] = {"Contents": page, "IsTruncated": truncated}
        if truncated:
            response["NextContinuationToken"] = str(start + self.page_size)
        return response

    async def delete_objects(self, **kwargs: Any) -> dict[str, Any]:
        errors = []
        for item in kwargs["Delete"]["Objects"]:
            if item["Key"] in self.fail_keys:
                errors.append({"Key": item["Key"], "Code": "AccessDenied"})
            else:
                self.deleted.append(item["Key"])
        return {"Errors": errors} if errors else {}


def _factory(fake: FakeS3):
    @contextlib.asynccontextmanager
    async def factory(_env: Any):
        yield fake

    return factory


def _refs(keys: set[str], calls: list[str] | None = None):
    async def fetch(database_url: str) -> set[str]:
        if calls is not None:
            calls.append(database_url)
        return set(keys)

    return fetch


def _run(argv: list[str], env: dict[str, str], fake: FakeS3, refs: set[str], calls: list[str] | None = None) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = asyncio.run(r2.run(r2.parse_args(argv), env, _factory(fake), _refs(refs, calls), now=NOW))
    return code, out.getvalue()


# ── T-32 핵심: 참조 중인 키는 절대 후보가 되지 않는다 ─────────────────────────


def test_dry_run_never_lists_referenced_keys() -> None:
    fake = FakeS3(FAKE_BUCKET)
    code, out = _run(["--days", "30"], ENV_PROD, fake, DB_REFERENCED)
    assert code == 0
    for key in DB_REFERENCED:
        assert key not in out, f"참조 키가 dry-run 목록에 나왔다: {key}"
    assert ORPHAN_MEETING in out and ORPHAN_MEMO in out
    assert YOUNG_UNREFERENCED not in out  # cutoff 이후
    assert "protected(referenced)=3" in out and "too_young=1" in out and "candidates=2" in out
    assert fake.deleted == []  # dry-run 은 삭제 0건


def test_delete_removes_only_unreferenced_old_keys() -> None:
    fake = FakeS3(FAKE_BUCKET)
    code, _ = _run(["--days", "30", "--delete"], ENV_PROD, fake, DB_REFERENCED)
    assert code == 0
    assert sorted(fake.deleted) == sorted([ORPHAN_MEETING, ORPHAN_MEMO])
    assert not set(fake.deleted) & DB_REFERENCED


def test_other_project_prefixes_are_never_listed() -> None:
    fake = FakeS3(FAKE_BUCKET)
    code, out = _run(["--days", "30", "--delete"], ENV_PROD, fake, DB_REFERENCED)
    assert code == 0
    assert set(fake.listed_prefixes) <= set(r2.ALLOWED_PREFIXES)
    assert OTHER_PROJECT_ROOT not in fake.deleted and OTHER_PROJECT_BACKUP not in fake.deleted
    assert OTHER_PROJECT_ROOT not in out and OTHER_PROJECT_BACKUP not in out


def test_randomized_referenced_keys_are_never_selected() -> None:
    rng = random.Random(20260927)
    objects = []
    for i in range(3000):
        prefix = rng.choice(["uploads/", "memory/", "db-backups/", ""])
        age = timedelta(days=rng.randint(0, 400), hours=rng.randint(0, 23))
        objects.append({"Key": f"{prefix}{i:05d}/f.bin", "LastModified": NOW - age, "Size": 1})
    referenced = {o["Key"] for o in objects if rng.random() < 0.5}
    cutoff = NOW - timedelta(days=30)
    selection = r2.select_orphans(objects, referenced, cutoff)
    selected = {o["Key"] for o in selection.candidates}
    expected = {
        o["Key"]
        for o in objects
        if o["Key"].startswith(r2.ALLOWED_PREFIXES) and o["Key"] not in referenced and o["LastModified"] < cutoff
    }
    assert not selected & referenced
    assert selected == expected
    # 전 경로(페이지네이션 포함)로도 같은 결과
    fake = FakeS3(objects, page_size=97)
    code, _ = _run(["--days", "30", "--delete"], ENV_PROD, fake, referenced)
    assert code == 0
    assert set(fake.deleted) == expected and not set(fake.deleted) & referenced


# ── 거부 규칙 ─────────────────────────────────────────────────────────────


def test_empty_reference_set_aborts_before_listing() -> None:
    fake = FakeS3(FAKE_BUCKET)
    code, out = _run(["--days", "30", "--delete"], ENV_PROD, fake, set())
    assert code == 1 and "참조 키 0건" in out
    assert fake.listed_prefixes == [] and fake.deleted == []


def test_missing_database_url_refuses_cleanup() -> None:
    env = {k: v for k, v in ENV_PROD.items() if k != "DATABASE_URL"}
    fake = FakeS3(FAKE_BUCKET)
    code, out = _run(["--days", "30"], env, fake, DB_REFERENCED)
    assert code == 1 and "DATABASE_URL" in out
    assert fake.listed_prefixes == [] and fake.deleted == []


def test_delete_requires_production_env() -> None:
    fake = FakeS3(FAKE_BUCKET)
    calls: list[str] = []
    code, out = _run(["--days", "30", "--delete"], {**ENV_PROD, "APP_ENV": "development"}, fake, DB_REFERENCED, calls)
    assert code == 1 and "APP_ENV=production" in out
    assert calls == [] and fake.listed_prefixes == [] and fake.deleted == []


def test_days_below_minimum_is_rejected() -> None:
    for bad in (["--days", "0"], ["--days", "6"]):
        try:
            r2.parse_args(bad)
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError(f"{bad} 가 거부되지 않았다")


def test_prefix_outside_allowlist_is_rejected() -> None:
    for bad in (["--prefix", "db-backups/"], ["--prefix", ""], ["--prefix", "uploads"]):
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                r2.parse_args(bad)
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError(f"{bad} 가 거부되지 않았다")


def test_delete_errors_exit_nonzero() -> None:
    fake = FakeS3(FAKE_BUCKET, fail_keys={ORPHAN_MEMO})
    code, out = _run(["--days", "30", "--delete"], ENV_PROD, fake, DB_REFERENCED)
    assert code == 1 and "failed=1" in out
    assert fake.deleted == [ORPHAN_MEETING]


def test_inventory_needs_no_db_and_prints_no_keys() -> None:
    env = {k: v for k, v in ENV_PROD.items() if k not in ("DATABASE_URL", "APP_ENV")}
    fake = FakeS3(FAKE_BUCKET)
    calls: list[str] = []
    code, out = _run(["--inventory", "--days", "30"], env, fake, DB_REFERENCED, calls)
    assert code == 0 and calls == [] and fake.deleted == []
    for obj in FAKE_BUCKET:
        assert obj["Key"] not in out, f"인벤토리가 키를 출력했다: {obj['Key']}"
    assert "uploads/   objects=4" in out and "memory/    objects=2" in out


def test_inventory_and_delete_are_mutually_exclusive() -> None:
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            r2.parse_args(["--inventory", "--delete"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("--inventory --delete 가 거부되지 않았다")


def _demo() -> None:
    """T-32 증거용 — 가짜 목록에 대한 dry-run 출력을 그대로 보여준다."""
    print("── dry-run against fake listing (DB referenced = 2 meeting originals + 1 voice memo) ──")
    _, out = _run(["--days", "30"], ENV_PROD, FakeS3(FAKE_BUCKET), DB_REFERENCED)
    print(out.rstrip())
    print("──────────────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    _demo()
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001 — 러너가 실패를 모아 보고한다
            failed += 1
            print(f"FAIL {name}: {exc!r}")
    print(f"\n{len(tests) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
