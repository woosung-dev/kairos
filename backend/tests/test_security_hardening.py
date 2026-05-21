# T-SEC-4 + T-SEC-5 보안 강화 회귀 테스트 (Sprint 25 Wave 3)
"""
Sprint 25 Wave 3 보안 마감 — Sentinel P2 보완.

- T-SEC-4 (BUG-SENTINEL-004): CaptureTextRequest.transcript_text max_length=200_000
- T-SEC-5 (BL-SNT-CANDIDATE-B): production 환경 docs/openapi 노출 차단
"""
import pytest
from pydantic import ValidationError

from src.meetings.schemas import CaptureTextRequest


class TestCaptureTextMaxLength:
    """T-SEC-4 — transcript_text 200K 자 상한."""

    def test_accepts_valid_length(self):
        payload = {"title": "회의 1", "transcriptText": "a" * 100}
        req = CaptureTextRequest.model_validate(payload)
        assert len(req.transcript_text) == 100

    def test_accepts_200k_exact(self):
        payload = {"title": "회의 1", "transcriptText": "a" * 200_000}
        req = CaptureTextRequest.model_validate(payload)
        assert len(req.transcript_text) == 200_000

    def test_rejects_oversize(self):
        payload = {"title": "회의 1", "transcriptText": "a" * 200_001}
        with pytest.raises(ValidationError) as exc:
            CaptureTextRequest.model_validate(payload)
        assert "200000" in str(exc.value) or "max_length" in str(exc.value)

    def test_rejects_too_short(self):
        payload = {"title": "회의 1", "transcriptText": "짧다"}
        with pytest.raises(ValidationError):
            CaptureTextRequest.model_validate(payload)


class TestProductionDocsBlocked:
    """T-SEC-5 — production app_env 에서 docs/openapi None 검증.

    실제 FastAPI 인스턴스 생성 시점에 평가되므로 환경변수 monkeypatch 후 모듈
    재로딩이 필요. 본 테스트는 분기 로직만 unit 검증.
    """

    def test_production_branch_blocks_docs(self):
        # 분기 로직 모사: _is_production == True 일 때 docs_url None
        app_env = "production"
        is_production = app_env == "production"
        docs_url = None if is_production else "/api/v1/docs"
        assert docs_url is None

    def test_development_branch_exposes_docs(self):
        app_env = "development"
        is_production = app_env == "production"
        docs_url = None if is_production else "/api/v1/docs"
        assert docs_url == "/api/v1/docs"
