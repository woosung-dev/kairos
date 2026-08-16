# apps/backend/tests/common/test_exceptions.py
"""common/exceptions.py — NotFoundError/AlreadyExistsError/UnauthorizedError/ForbiddenError.

FastAPI HTTPException 서브클래스 상태 코드 + 메시지 회귀 가드.
"""
import pytest
from fastapi import HTTPException

from src.common.exceptions import (
    AlreadyExistsError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)


class TestNotFoundError:
    def test_404_status(self):
        err = NotFoundError("사용자")
        assert err.status_code == 404

    def test_korean_resource_in_detail(self):
        err = NotFoundError("회의")
        assert "회의" in err.detail
        assert "찾을 수 없습니다" in err.detail

    def test_subclass_of_http_exception(self):
        err = NotFoundError("X")
        assert isinstance(err, HTTPException)


class TestAlreadyExistsError:
    def test_409_status(self):
        err = AlreadyExistsError("멤버")
        assert err.status_code == 409

    def test_korean_resource_in_detail(self):
        err = AlreadyExistsError("멤버")
        assert "멤버" in err.detail

    def test_subclass_of_http_exception(self):
        err = AlreadyExistsError("X")
        assert isinstance(err, HTTPException)


class TestUnauthorizedError:
    def test_401_status(self):
        err = UnauthorizedError()
        assert err.status_code == 401

    def test_korean_detail(self):
        err = UnauthorizedError()
        assert err.detail == "인증이 필요합니다"

    def test_subclass_of_http_exception(self):
        assert isinstance(UnauthorizedError(), HTTPException)


class TestForbiddenError:
    def test_403_status(self):
        err = ForbiddenError()
        assert err.status_code == 403

    def test_korean_detail(self):
        err = ForbiddenError()
        assert err.detail == "권한이 없습니다"

    def test_subclass_of_http_exception(self):
        assert isinstance(ForbiddenError(), HTTPException)


class TestRaiseAndCatch:
    """FastAPI 라우터 패턴 검증 — raise NotFoundError() → catch as HTTPException."""

    def test_raise_not_found_caught_as_http_exception(self):
        with pytest.raises(HTTPException) as exc_info:
            raise NotFoundError("리소스")
        assert exc_info.value.status_code == 404

    def test_raise_forbidden_caught_as_http_exception(self):
        with pytest.raises(HTTPException) as exc_info:
            raise ForbiddenError()
        assert exc_info.value.status_code == 403
