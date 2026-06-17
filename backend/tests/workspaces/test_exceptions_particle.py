# PersonalWorkspaceProtected 한국어 목적격 조사(을/를) 자동 선택 검증 (QA-0617-E)
"""받침 유무에 따라 '을'/'를' 이 올바르게 선택되는지 단위 검증.

기존 버그: f"{action}을(를) 수행할 수 없습니다" — 리터럴 '을(를)' 플레이스홀더가
그대로 노출됨. _object_particle 헬퍼로 받침 유무 판정 후 조사 선택.
"""
import pytest

from src.workspaces.exceptions import PersonalWorkspaceProtected, _object_particle


@pytest.mark.parametrize(
    "word,expected",
    [
        ("초대", "를"),       # 대 = 받침 없음 → 를
        ("멤버 추가", "를"),   # 가 = 받침 없음 → 를
        ("멤버 삭제", "를"),   # 제 = 받침 없음 → 를
        ("작업", "을"),       # 업 = 받침 있음(ㅂ) → 을
        ("권한 변경", "을"),   # 경 = 받침 있음(ㅇ) → 을
        ("멤버 추가 작업", "을"),  # 업 = 받침 있음 → 을
    ],
)
def test_object_particle(word, expected):
    assert _object_particle(word) == expected


def test_personal_workspace_protected_no_placeholder():
    """detail 메시지에 리터럴 '을(를)' 플레이스홀더가 남아있지 않아야 한다."""
    exc = PersonalWorkspaceProtected("초대")
    assert "을(를)" not in exc.detail
    assert exc.detail == "개인 워크스페이스에는 초대를 수행할 수 없습니다"
    assert exc.status_code == 403


def test_personal_workspace_protected_batchim_action():
    """받침 있는 action → '을'."""
    exc = PersonalWorkspaceProtected("권한 변경")
    assert exc.detail == "개인 워크스페이스에는 권한 변경을 수행할 수 없습니다"


def test_object_particle_non_hangul_fallback():
    """비-한글로 끝나면 안전하게 '를' fallback (영문/숫자 등)."""
    assert _object_particle("API") == "를"
    assert _object_particle("") == "를"
