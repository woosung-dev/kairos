# 웹 푸시 구독 SQLModel 테이블 (ENT-001, pwa.md §5.1)
"""사용자 단위 리소스 — workspace_id 가 없다 (B-2 예외).

대신 Repository 의 모든 조회·삭제가 `user_id` WHERE 를 강제한다 (push/CONTEXT.md).
endpoint 는 푸시 서비스 capability URL 이라 로그·응답에 내보내지 않는다.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Text, Uuid
from sqlmodel import Field, SQLModel, UniqueConstraint


class PushSubscription(SQLModel, table=True):
    __tablename__ = "push_subscriptions"
    __table_args__ = (
        # endpoint 단위 upsert(ON CONFLICT) 대상 — 같은 기기 재구독 시 행이 현재 사용자로 rebind 된다
        UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # 내부 users.id (auth_user.id 아님). 사용자 삭제 시 구독도 함께 지운다
    user_id: uuid.UUID = Field(
        sa_column=Column(
            Uuid,
            ForeignKey(
                "users.id",
                ondelete="CASCADE",
                name="fk_push_subscriptions_user_id_users",
            ),
            nullable=False,
            index=True,
        )
    )
    endpoint: str = Field(sa_column=Column(Text, nullable=False))
    # base64url — 디코드 65바이트(0x04 시작) / 16바이트. 검증은 schemas.py
    p256dh: str = Field(sa_column=Column(Text, nullable=False))
    auth: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # upsert·rebind 마다 갱신
    updated_at: datetime = Field(default_factory=datetime.utcnow)
