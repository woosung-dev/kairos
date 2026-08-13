"""ADR-026 Fernet 암호화 유틸과 설정 validator 회귀 테스트."""
import logging
from dataclasses import dataclass

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.common import crypto
from src.common.exceptions import EncryptionError
from src.core.config import Settings


@dataclass
class _CryptoSettings:
    integrations_encryption_key: SecretStr | None


def _set_crypto_key(monkeypatch: pytest.MonkeyPatch, key: str) -> None:
    monkeypatch.setattr(
        crypto,
        "get_settings",
        lambda: _CryptoSettings(integrations_encryption_key=SecretStr(key)),
    )


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", "whsec_xxx")
    monkeypatch.setenv("R2_ACCOUNT_ID", "test_account")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test_key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test_secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-xxx")


def test_encrypt_decrypt_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key().decode()
    _set_crypto_key(monkeypatch, key)

    ciphertext = crypto.encrypt_string("연동 refresh token")

    assert crypto.decrypt_string(ciphertext) == "연동 refresh token"


def test_encrypt_same_plaintext_uses_different_ciphertexts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_crypto_key(monkeypatch, Fernet.generate_key().decode())

    first = crypto.encrypt_string("같은 평문")
    second = crypto.encrypt_string("같은 평문")

    assert first != second


def test_decrypt_with_different_key_raises_encryption_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_crypto_key(monkeypatch, Fernet.generate_key().decode())
    ciphertext = crypto.encrypt_string("보호할 값")
    _set_crypto_key(monkeypatch, Fernet.generate_key().decode())

    with pytest.raises(EncryptionError):
        crypto.decrypt_string(ciphertext)


def test_decrypt_corrupted_ciphertext_raises_encryption_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_crypto_key(monkeypatch, Fernet.generate_key().decode())
    ciphertext = crypto.encrypt_string("보호할 값")
    replacement = "A" if ciphertext[-1] != "A" else "B"
    corrupted = f"{ciphertext[:-1]}{replacement}"

    with pytest.raises(EncryptionError):
        crypto.decrypt_string(corrupted)


def test_decrypt_hmac_tampered_ciphertext_raises_encryption_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_crypto_key(monkeypatch, Fernet.generate_key().decode())
    ciphertext = crypto.encrypt_string("보호할 값")
    middle_index = len(ciphertext) // 2
    replacement = "A" if ciphertext[middle_index] != "A" else "B"
    tampered = (
        f"{ciphertext[:middle_index]}{replacement}{ciphertext[middle_index + 1:]}"
    )

    with pytest.raises(EncryptionError):
        crypto.decrypt_string(tampered)


def test_valid_fernet_key_passes_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("INTEGRATIONS_ENCRYPTION_KEY", key)

    settings = Settings(_env_file=None)

    assert settings.integrations_encryption_key is not None
    assert settings.integrations_encryption_key.get_secret_value() == key


def test_invalid_fernet_key_warns_without_blocking_boot(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("INTEGRATIONS_ENCRYPTION_KEY", "a" * 40)

    with caplog.at_level(logging.WARNING, logger="src.core.config"):
        settings = Settings(_env_file=None)

    assert settings.integrations_encryption_key is not None
    assert any(
        "INTEGRATIONS_ENCRYPTION_KEY is invalid" in record.message
        for record in caplog.records
    )


def test_empty_environment_fernet_key_becomes_none_without_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("INTEGRATIONS_ENCRYPTION_KEY", "")

    with caplog.at_level(logging.WARNING, logger="src.core.config"):
        settings = Settings(_env_file=None)

    assert settings.integrations_encryption_key is None
    assert not any(
        "INTEGRATIONS_ENCRYPTION_KEY" in record.getMessage()
        for record in caplog.records
    )


def test_explicit_none_fernet_key_passes_validator_without_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _set_required_env(monkeypatch)

    with caplog.at_level(logging.WARNING, logger="src.core.config"):
        settings = Settings(_env_file=None, integrations_encryption_key=None)

    assert settings.integrations_encryption_key is None
    assert not any(
        "INTEGRATIONS_ENCRYPTION_KEY" in record.getMessage()
        for record in caplog.records
    )
