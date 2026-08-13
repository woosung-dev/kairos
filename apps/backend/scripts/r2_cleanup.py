#!/usr/bin/env python3
# R2 uploads/ 누적 객체 정리 — nightly e2e 의 Whisper/STT 업로드 잔존물 청소 (BL-043)
"""R2 cleanup script — uploads/ prefix 의 N 일 이상 오래된 객체 정리.

기본 DRY RUN. 실제 삭제는 --delete 명시 필요. workflow_dispatch 수동 트리거 전용
(.github/workflows/r2-cleanup.yml). cron 자동 실행은 사용자 검증 후 추가.

사용:
  python -m scripts.r2_cleanup                  # dry run, default 30 일 기준
  python -m scripts.r2_cleanup --days 7         # 7 일 기준 dry run
  python -m scripts.r2_cleanup --days 7 --delete  # 실제 삭제

환경변수: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import aioboto3


def _env_required(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        sys.exit(f"❌ env 누락: {key}")
    return value


async def cleanup_r2(
    days: int, prefix: str, delete: bool, max_keys: int
) -> tuple[int, int]:
    """오래된 객체 식별 + (옵션) 삭제. (scanned, target) 반환."""
    account_id = _env_required("R2_ACCOUNT_ID")
    access_key = _env_required("R2_ACCESS_KEY_ID")
    secret_key = _env_required("R2_SECRET_ACCESS_KEY")
    bucket = _env_required("R2_BUCKET_NAME")
    endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    print(
        f"=== R2 cleanup — bucket={bucket} prefix={prefix!r} "
        f"older_than={days}d (before {cutoff.isoformat()})"
    )
    if not delete:
        print("ℹ DRY RUN — --delete 옵션 없음. 삭제 안 함.")

    session = aioboto3.Session()
    scanned = 0
    target = 0

    async with session.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    ) as client:
        continuation_token: str | None = None

        while True:
            list_kwargs = {
                "Bucket": bucket,
                "Prefix": prefix,
                "MaxKeys": 1000,
            }
            if continuation_token:
                list_kwargs["ContinuationToken"] = continuation_token

            response = await client.list_objects_v2(**list_kwargs)
            contents = response.get("Contents", [])
            scanned += len(contents)

            to_delete: list[dict] = []
            for obj in contents:
                last_modified = obj["LastModified"]  # aware datetime
                if last_modified < cutoff:
                    target += 1
                    age_days = (datetime.now(timezone.utc) - last_modified).days
                    print(f"  → {obj['Key']}  ({age_days}d old, {obj['Size']}B)")
                    if delete:
                        to_delete.append({"Key": obj["Key"]})
                        if len(to_delete) >= 1000:  # S3 batch limit
                            await client.delete_objects(
                                Bucket=bucket, Delete={"Objects": to_delete}
                            )
                            to_delete.clear()
                if target >= max_keys:
                    break

            if delete and to_delete:
                await client.delete_objects(
                    Bucket=bucket, Delete={"Objects": to_delete}
                )

            if target >= max_keys:
                print(f"⚠ max-keys 도달 ({max_keys}) — 추가 객체는 다음 실행으로")
                break

            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")

    if delete:
        print(f"\n✅ scanned={scanned} deleted={target}")
    else:
        print(f"\n✅ scanned={scanned} would_delete={target} (dry run)")
    return scanned, target


def main() -> None:
    parser = argparse.ArgumentParser(description="R2 bucket cleanup (BL-043)")
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="이 N 일 보다 오래된 객체 (default 30)",
    )
    parser.add_argument(
        "--prefix",
        default="uploads/",
        help="대상 키 prefix (default 'uploads/')",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="실제 삭제 (생략 시 DRY RUN)",
    )
    parser.add_argument(
        "--max-keys",
        type=int,
        default=10000,
        help="단일 실행에서 처리할 최대 객체 수 (default 10000)",
    )
    args = parser.parse_args()
    asyncio.run(
        cleanup_r2(args.days, args.prefix, args.delete, args.max_keys)
    )


if __name__ == "__main__":
    main()
