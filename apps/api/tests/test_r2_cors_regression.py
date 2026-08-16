# apps/api/tests/test_r2_cors.regression.py
"""R2 버킷 CORS 정책 검증 — 브라우저 직접 PUT 허용 여부.

Regression: ISSUE-R2-CORS-001 — 프로덕션 R2 버킷에 CORS 정책 미설정으로
https://kairos-zeta-ebon.vercel.app 에서 파일 업로드 시 브라우저 CORS 차단 발생.
Found by /qa on 2026-05-12.
Report: .gstack/qa-reports/qa-report-kairos-zeta-ebon-vercel-app-2026-05-12.md
"""
import os
import boto3
import pytest


REQUIRED_ORIGINS = [
    "https://kairos-zeta-ebon.vercel.app",
    "http://localhost:3000",
]


@pytest.fixture(scope="module")
def r2_client():
    """실제 R2 클라이언트 — 환경 변수 필수."""
    account_id = os.environ.get("R2_ACCOUNT_ID")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    if not all([account_id, access_key, secret_key]):
        pytest.skip("R2_* 환경 변수가 없어 스킵 (integration 전용)")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )


@pytest.fixture(scope="module")
def bucket_name():
    return os.environ.get("R2_BUCKET_NAME", "nexus-core-storage")


def test_r2_bucket_cors_allows_vercel_origin(r2_client, bucket_name):
    """R2 버킷 CORS 정책이 Vercel 도메인 PUT 요청을 허용해야 한다."""
    try:
        response = r2_client.get_bucket_cors(Bucket=bucket_name)
        cors_rules = response.get("CORSRules", [])
    except r2_client.exceptions.ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchCORSConfiguration", "NoSuchBucket"):
            pytest.fail(
                f"R2 버킷 {bucket_name!r}에 CORS 정책이 없습니다. "
                "브라우저에서 직접 PUT 요청이 차단됩니다."
            )
        raise

    allowed_origins: set[str] = set()
    allowed_methods: set[str] = set()
    for rule in cors_rules:
        allowed_origins.update(rule.get("AllowedOrigins", []))
        allowed_methods.update(rule.get("AllowedMethods", []))

    # Vercel 도메인이 허용되는지 확인
    for origin in REQUIRED_ORIGINS:
        assert origin in allowed_origins or "*" in allowed_origins, (
            f"R2 CORS에 {origin!r}이 없습니다. "
            f"현재 허용 목록: {allowed_origins}"
        )

    # PUT 메서드가 허용되는지 확인
    assert "PUT" in allowed_methods, (
        f"R2 CORS에 PUT 메서드가 없습니다. 현재: {allowed_methods}"
    )
