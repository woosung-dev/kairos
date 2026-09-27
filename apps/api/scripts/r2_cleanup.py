#!/usr/bin/env python3
# R2 미참조 객체 정리 — DB 가 참조하지 않는 Kairos 객체만 고른다 (체크리스트 0-12 · BL-OCI-5)
"""R2 cleanup — Kairos prefix(uploads/ · memory/) 중 **DB 가 참조하지 않고** N 일 지난 객체만 정리.

★2026-09-27 재작성. 이전 버전은 uploads/ 아래 N 일 지난 객체를 DB 참조 여부와 무관하게 전부
  골랐다. delete 모드로 돌렸다면 살아 있는 회의 원본까지 삭제됐다 (D-001 · D-002).

안전 규칙 — 전부 코드로 강제한다:
  1. 참조 키는 실행 시점에 DB 에서 직접 읽는다 (meetings.file_key ∪ memory_items.r2_audio_key,
     읽기 전용 트랜잭션). 참조 0건이면 중단한다 — 잘못된 DB 나 조회 실패를 "전부 고아" 로 읽지 않는다.
  2. 참조 키는 나이와 무관하게 절대 후보가 되지 않는다. 삭제 직전에 한 번 더 교차 검사한다.
  3. 대상 prefix 는 uploads/ · memory/ 뿐이다. 같은 버킷(kairos-prod, ADR-033)의 backups/kairos/ 등
     다른 prefix 는 목록 조회조차 하지 않는다.
  4. --days 최소 7 — 업로드 직후 ~ 회의 생성 사이의 객체를 보호한다.
  5. --delete 는 APP_ENV=production 에서만 — 개발 DB 를 기준으로 운영 버킷을 돌리면 운영 원본이
     전부 "미참조" 로 보인다 (버킷이 나뉜 뒤에도 잘못된 .env 조합을 막는 벽).
  6. --inventory 는 DB 없이 prefix 별 개수·용량만 출력한다. 키를 출력하지 않는다
     (공개 레포의 GitHub Actions 로그는 누구나 읽는다 — 회의 파일명이 키에 들어 있다).

실행 — 운영 서버의 api 컨테이너 안에서 돈다 (R2_* · DATABASE_URL · aioboto3 · asyncpg 가 전부 있다).
레포 체크아웃이 있는 맥에서 스크립트를 stdin 으로 흘려보낸다 (서버에 파일을 두지 않는다):

  ssh truewords-oracle 'bash -lc "docker exec -i kairos-api python - --days 30"' < apps/api/scripts/r2_cleanup.py
  ssh truewords-oracle 'bash -lc "docker exec -i kairos-api python - --days 30 --delete"' < apps/api/scripts/r2_cleanup.py

인벤토리 (DB 불필요, 키 미출력): python -m scripts.r2_cleanup --inventory
런북: docs/operations/r2-cleanup-cron.md

환경변수: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME,
          DATABASE_URL (inventory 제외), APP_ENV (--delete 시 production 필수)
종료 코드: 0 = 정상, 1 = 안전 규칙에 의한 거부 또는 삭제 실패, 2 = 인자 오류
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Awaitable, Callable, Iterable, Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, cast
from urllib.parse import urlsplit

ALLOWED_PREFIXES: tuple[str, ...] = ("uploads/", "memory/")
MIN_DAYS = 7
DELETE_BATCH = 1000  # S3 DeleteObjects 1회 한도

# R2 키를 담는 컬럼 전수 (2026-09-27 models.py grep 기준). 새 컬럼이 생기면 여기에 추가해야 한다 —
# 빠뜨리면 그 컬럼이 참조하는 객체가 "미참조" 로 보인다.
#   meetings.file_key          uploads/{uuid}/{filename}  (common/r2.py) — promote 복제본도 같은 키 공유
#   memory_items.r2_audio_key  memory/{workspace_id}/...  (memory/service.py) — TTL 후 NULL
REFERENCED_KEYS_SQL = """
SELECT file_key FROM meetings WHERE file_key IS NOT NULL AND file_key <> ''
UNION
SELECT r2_audio_key FROM memory_items WHERE r2_audio_key IS NOT NULL AND r2_audio_key <> ''
"""

S3Object = Mapping[str, Any]  # list_objects_v2 Contents 원소: Key / LastModified(aware) / Size
ClientFactory = Callable[[Mapping[str, str]], AbstractAsyncContextManager[Any]]
FetchReferenced = Callable[[str], Awaitable[set[str]]]


@dataclass(frozen=True)
class Selection:
    candidates: list[S3Object]
    protected: int  # DB 가 참조 중이라 제외된 객체 수
    too_young: int  # 미참조지만 cutoff 이후라 제외된 객체 수


def select_orphans(
    objects: Iterable[S3Object], referenced: set[str], cutoff: datetime
) -> Selection:
    """미참조 + cutoff 이전 + 허용 prefix 인 객체만 후보로 고른다 (순수 함수)."""
    candidates: list[S3Object] = []
    protected = 0
    too_young = 0
    for obj in objects:
        key = str(obj["Key"])
        if not key.startswith(ALLOWED_PREFIXES):
            continue  # 목록 조회가 prefix 를 지켜도 한 번 더 거른다
        if key in referenced:
            protected += 1
            continue
        if obj["LastModified"] >= cutoff:
            too_young += 1
            continue
        candidates.append(obj)
    return Selection(candidates, protected, too_young)


async def list_objects(client: Any, bucket: str, prefix: str) -> list[S3Object]:
    if not prefix.startswith(ALLOWED_PREFIXES):
        raise ValueError(f"허용되지 않은 prefix: {prefix!r}")
    objects: list[S3Object] = []
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 1000}
        if token:
            kwargs["ContinuationToken"] = token
        response = await client.list_objects_v2(**kwargs)
        objects.extend(response.get("Contents", []))
        if not response.get("IsTruncated"):
            return objects
        token = response.get("NextContinuationToken")


async def delete_keys(client: Any, bucket: str, keys: list[str]) -> list[str]:
    """삭제하고 실패한 키 목록을 돌려준다."""
    failed: list[str] = []
    for i in range(0, len(keys), DELETE_BATCH):
        batch = keys[i : i + DELETE_BATCH]
        response = await client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
        )
        failed.extend(str(e.get("Key", "?")) for e in response.get("Errors", []))
    return failed


async def fetch_referenced_keys(database_url: str) -> set[str]:
    import asyncpg  # 지연 import — 인벤토리·테스트는 DB 드라이버 없이 돈다

    dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn)
    try:
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(REFERENCED_KEYS_SQL)
    finally:
        await conn.close()
    return {str(r[0]) for r in rows}


def r2_client(env: Mapping[str, str]) -> AbstractAsyncContextManager[Any]:
    import aioboto3  # 지연 import

    # aioboto3 의 client() 반환 타입 힌트가 async context manager 프로토콜을 드러내지 않아 cast 한다.
    return cast(
        AbstractAsyncContextManager[Any],
        aioboto3.Session().client(
            "s3",
            endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=env["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        ),
    )


def _describe_db(database_url: str) -> str:
    """비밀번호 없이 host:port/db 만 보여준다."""
    parts = urlsplit(database_url)
    return f"{parts.hostname}:{parts.port or 5432}{parts.path}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="R2 미참조 객체 정리 (Kairos prefix 한정, DB 참조 대조)"
    )
    parser.add_argument(
        "--days", type=int, default=30, help=f"이 N 일보다 오래된 객체만 (default 30, 최소 {MIN_DAYS})"
    )
    parser.add_argument(
        "--prefix",
        action="append",
        choices=ALLOWED_PREFIXES,
        help="대상 prefix (반복 가능, default 전부)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--delete", action="store_true", help="실제 삭제 (생략 시 DRY RUN)")
    mode.add_argument(
        "--inventory", action="store_true", help="DB 없이 prefix 별 개수·용량만 (키 미출력)"
    )
    parser.add_argument(
        "--max-keys", type=int, default=10000, help="1회 실행의 최대 삭제 후보 수 (default 10000)"
    )
    args = parser.parse_args(argv)
    if args.days < MIN_DAYS:
        parser.error(f"--days 는 {MIN_DAYS} 이상이어야 한다 (받은 값 {args.days})")
    if args.max_keys < 1:
        parser.error("--max-keys 는 1 이상이어야 한다")
    args.prefixes = tuple(dict.fromkeys(args.prefix or ALLOWED_PREFIXES))
    return args


async def run(
    args: argparse.Namespace,
    env: Mapping[str, str],
    client_factory: ClientFactory = r2_client,
    fetch_referenced: FetchReferenced = fetch_referenced_keys,
    now: datetime | None = None,
) -> int:
    missing = [
        k
        for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")
        if not env.get(k)
    ]
    if missing:
        print(f"❌ env 누락: {', '.join(missing)}")
        return 1
    bucket = env["R2_BUCKET_NAME"]
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.days)

    if args.inventory:
        async with client_factory(env) as client:
            print(f"=== R2 inventory — bucket={bucket} older_than={args.days}d (키는 출력하지 않는다)")
            for prefix in args.prefixes:
                objects = await list_objects(client, bucket, prefix)
                old = sum(1 for o in objects if o["LastModified"] < cutoff)
                size = sum(int(o.get("Size", 0)) for o in objects)
                print(f"  {prefix:<10} objects={len(objects)} bytes={size} older_than_{args.days}d={old}")
        return 0

    database_url = env.get("DATABASE_URL", "")
    if not database_url:
        print("❌ DATABASE_URL 없음 — 참조 대조 없이는 후보를 고르지 않는다 (인벤토리는 --inventory)")
        return 1
    if args.delete and env.get("APP_ENV") != "production":
        print(
            "❌ --delete 는 APP_ENV=production 에서만 허용된다. 로컬 개발도 같은 버킷을 쓰므로"
            " 개발 DB 기준으로 지우면 운영 원본이 삭제된다."
        )
        return 1

    # 참조 → 목록 순서로 읽는다. 그 사이에 올라온 객체는 cutoff 이후라 후보가 될 수 없다.
    referenced = await fetch_referenced(database_url)
    print(
        f"=== R2 cleanup — bucket={bucket} prefixes={list(args.prefixes)} "
        f"older_than={args.days}d (before {cutoff.isoformat()})"
    )
    print(f"  referenced keys from DB {_describe_db(database_url)}: {len(referenced)}")
    if not referenced:
        print("❌ DB 참조 키 0건 — 잘못된 DB 이거나 조회 실패로 본다. 중단.")
        return 1

    async with client_factory(env) as client:
        objects: list[S3Object] = []
        for prefix in args.prefixes:
            objects.extend(await list_objects(client, bucket, prefix))

        selection = select_orphans(objects, referenced, cutoff)
        targets = selection.candidates[: args.max_keys]
        mode = "DELETE" if args.delete else "DRY RUN"
        print(
            f"  scanned={len(objects)} protected(referenced)={selection.protected} "
            f"too_young={selection.too_young} candidates={len(selection.candidates)} [{mode}]"
        )
        for obj in targets:
            age_days = (now - obj["LastModified"]).days
            print(f"  → {obj['Key']}  ({age_days}d old, {obj.get('Size', '?')}B)")
        if len(selection.candidates) > len(targets):
            print(f"⚠ --max-keys {args.max_keys} 도달 — 나머지는 다음 실행으로")

        if not args.delete:
            print(f"\n✅ would_delete={len(targets)} (dry run — 삭제 0건)")
            return 0

        keys = [str(o["Key"]) for o in targets]
        overlap = set(keys) & referenced
        if overlap:  # select_orphans 가 보장하지만 삭제 직전에 한 번 더 막는다
            print(f"❌ 내부 오류: 참조 키 {len(overlap)}건이 삭제 목록에 있다. 중단.")
            return 1
        failed = await delete_keys(client, bucket, keys)

    if failed:
        print(f"\n❌ deleted={len(keys) - len(failed)} failed={len(failed)}")
        for key in failed:
            print(f"  ✗ {key}")
        return 1
    print(f"\n✅ deleted={len(keys)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return asyncio.run(run(args, os.environ))


if __name__ == "__main__":
    sys.exit(main())
