# PWA PR-2 VAPID 설정 — 전부 optional + 형식 오류는 warn-only (pwa.md §5.7, C-18)
import logging

import pytest

from tests.fixtures.push import (
    TEST_VAPID_SUBJECT,
    generate_vapid_key_pair,
    push_loggers_enabled,  # noqa: F401 — pytestmark usefixtures 로 사용
)

pytestmark = pytest.mark.usefixtures("push_loggers_enabled")

_REQUIRED_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
    "R2_ACCOUNT_ID": "test",
    "R2_ACCESS_KEY_ID": "test",
    "R2_SECRET_ACCESS_KEY": "test",
    "R2_BUCKET_NAME": "test",
    "GEMINI_API_KEY": "test-gemini-key",
    "OPENAI_API_KEY": "sk-xxx",
}


def _settings(monkeypatch, **vapid: str | None):
    from src.core.config import Settings

    for name, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)
    for name in ("VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY", "VAPID_SUBJECT"):
        monkeypatch.delenv(name, raising=False)
    for name, value in vapid.items():
        if value is not None:
            monkeypatch.setenv(name, value)
    return Settings(_env_file=None)


def _vapid_warnings(caplog) -> list[str]:
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == "src.core.config" and r.levelno == logging.WARNING and "VAPID" in r.getMessage()
    ]


def test_vapid_defaults_to_none_without_warning(monkeypatch, caplog):
    """미설정이 기본 상태 — 3필드 None, 경고 0 (CI fake env 추가 불필요)."""
    with caplog.at_level(logging.WARNING):
        settings = _settings(monkeypatch)
    assert settings.vapid_public_key is None
    assert settings.vapid_private_key is None
    assert settings.vapid_subject is None
    assert _vapid_warnings(caplog) == []


def test_valid_vapid_config_loads_without_warning(monkeypatch, caplog):
    private_key, public_key = generate_vapid_key_pair()
    with caplog.at_level(logging.WARNING):
        settings = _settings(
            monkeypatch,
            VAPID_PUBLIC_KEY=public_key,
            VAPID_PRIVATE_KEY=private_key,
            VAPID_SUBJECT=TEST_VAPID_SUBJECT,
        )
    assert settings.vapid_public_key == public_key
    # B-11: 개인키는 SecretStr — 문자열화해도 값이 나오지 않는다
    assert settings.vapid_private_key is not None
    assert private_key not in str(settings.vapid_private_key)
    assert settings.vapid_private_key.get_secret_value() == private_key
    assert _vapid_warnings(caplog) == []


@pytest.mark.parametrize(
    ("overrides", "expected_fragment"),
    [
        ({"VAPID_PUBLIC_KEY": "not-a-key"}, "VAPID_PUBLIC_KEY"),
        ({"VAPID_PRIVATE_KEY": "AAAA"}, "VAPID_PRIVATE_KEY"),
        ({"VAPID_SUBJECT": "ops@kairos.test"}, "VAPID_SUBJECT"),
        ({"VAPID_SUBJECT": None}, "partially set"),
    ],
)
def test_invalid_vapid_config_warns_but_never_blocks_boot(
    monkeypatch, caplog, overrides, expected_fragment
):
    """C-18: 형식 오류·일부만 설정 → warning 만, 부팅(Settings 생성) 은 성공. 경고에 키 값 없음."""
    private_key, public_key = generate_vapid_key_pair()
    values: dict[str, str | None] = {
        "VAPID_PUBLIC_KEY": public_key,
        "VAPID_PRIVATE_KEY": private_key,
        "VAPID_SUBJECT": TEST_VAPID_SUBJECT,
    }
    values.update(overrides)
    with caplog.at_level(logging.WARNING):
        _settings(monkeypatch, **values)

    messages = _vapid_warnings(caplog)
    assert any(expected_fragment in m for m in messages), messages
    for message in messages:
        assert private_key not in message
        assert public_key not in message
