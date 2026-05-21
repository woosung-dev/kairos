# Upload 도메인 Depends() 조립 — UploadValidator 주입
"""router/service.py에 Depends import 금지 (헌법 §3 follow)."""
from src.upload.service import UploadValidator


def get_upload_validator() -> UploadValidator:
    """upload 검증기 기본 인스턴스 (settings 기반). 테스트는 override."""
    return UploadValidator()
