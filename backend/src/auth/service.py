# Clerk 사용자를 조회·생성하고 응답 dict로 직렬화하는 도메인 서비스
"""Auth 서비스 — AsyncSession import 금지."""
from src.auth.models import User
from src.auth.repository import UserRepository


class AuthService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def get_or_create_user(
        self,
        clerk_id: str,
        email: str,
        display_name: str,
        avatar_url: str | None = None,
    ) -> User:
        """Clerk ID로 사용자 조회, 없으면 생성."""
        user = await self.repo.find_by_clerk_id(clerk_id)
        if user is None:
            user = User(
                clerk_id=clerk_id,
                email=email,
                display_name=display_name,
                avatar_url=avatar_url,
            )
            user = await self.repo.save(user)
            await self.repo.commit()
        return user

    @staticmethod
    def to_response(user: User) -> dict:
        """User → camelCase 응답 dict."""
        return {
            "id": str(user.id),
            "clerkId": user.clerk_id,
            "displayName": user.display_name,
            "email": user.email,
            "avatarUrl": user.avatar_url,
        }
