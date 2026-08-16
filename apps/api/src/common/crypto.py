"""ADR-026 연동 secret 암호화 유틸."""
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from src.common.exceptions import EncryptionConfigurationError, EncryptionDecryptionError
from src.core.config import get_settings

__all__ = ["decrypt_string", "encrypt_string"]


@lru_cache(maxsize=1)
def _get_fernet(key_value: str) -> Fernet:
    """현재 키에 대한 Fernet 인스턴스 하나를 재사용한다."""
    return Fernet(key_value.encode())


def _get_configured_fernet() -> Fernet:
    """호출 시점 설정의 연동 암호화 키로 Fernet을 만든다."""
    key = get_settings().integrations_encryption_key
    if key is None:
        raise EncryptionConfigurationError("연동 암호화 키가 설정되지 않았습니다")

    try:
        return _get_fernet(key.get_secret_value())
    except ValueError as exc:
        raise EncryptionConfigurationError("연동 암호화 키가 유효하지 않습니다") from exc


def encrypt_string(plaintext: str) -> str:
    """문자열을 Fernet으로 암호화한다."""
    return _get_configured_fernet().encrypt(plaintext.encode()).decode()


def decrypt_string(ciphertext: str) -> str:
    """Fernet 암호문을 문자열로 복호화한다."""
    try:
        return _get_configured_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise EncryptionDecryptionError("암호문을 복호화할 수 없습니다") from exc
