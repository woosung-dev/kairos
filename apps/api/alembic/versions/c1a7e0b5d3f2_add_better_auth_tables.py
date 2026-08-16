"""add better auth core tables and users.auth_user_id

Revision ID: c1a7e0b5d3f2
Revises: 7f6b8c9d0e1f
Create Date: 2026-08-16 00:00:00.000000

ADR-031 Clerk → Better Auth 전환.

★이 리비전은 100% 가산/완화형이다 (신규 테이블 · 신규 컬럼 · NOT NULL 해제).
  구 api 이미지가 이 스키마 위에서 그대로 동작한다 → **롤백이 이미지 태그 되돌리기만으로 끝난다.**
  `users.clerk_id` 는 여기서 지우지 않는다. 지우는 것은 컷오버 +7일 뒤 별도 리비전이다
  (`docs/development/migrations.md` 2단계 배포 규약). 그 7일이 롤백 창이자,
  "누가 누구였는지" 를 식별해 레거시 행에 새 auth id 를 이식할 수 있는 창이다.

★이 리비전의 DDL 은 손으로 쓴 것이 아니다. Better Auth CLI 산출물을 그대로 옮겼다:

    cd apps/web && npx @better-auth/cli generate --config src/lib/auth.ts --output <file>

원문 SQL 을 `op.execute()` 로 그대로 실행하는 이유 — Better Auth 는 자기 테이블을 자기 어댑터로
읽고 쓴다. `op.create_table()` 로 옮겨 적으면 컬럼 타입/기본값이 미세하게 어긋나도 alembic 은
통과시키고 런타임에서야 터진다. 산출물을 원문 그대로 두면 Better Auth 버전 업 시 CLI 를 다시
돌려 diff 를 눈으로 비교할 수 있다.

★컬럼명이 camelCase("emailVerified", "userId")인 것도 의도다. 이 테이블들은 Better Auth 런타임이
소유하며 우리 코드는 조회하지 않는다. 스키마 소유권(ADR-031 D4)은 alembic 에 있지만 네이밍 규약은
라이브러리를 따른다 — 컬럼명을 snake_case 로 뒤집으려면 모든 필드에 `fields` 매핑을 걸어야 하고
그게 버전 업마다 드리프트 원인이 된다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c1a7e0b5d3f2"
down_revision: Union[str, Sequence[str], None] = "7f6b8c9d0e1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Better Auth CLI 1.6.29 산출물 (auth.ts 의 modelName 오버라이드 반영 — auth_ 접두사)
_CREATE_STATEMENTS = [
    'create table "auth_user" ('
    '"id" text not null primary key, '
    '"name" text not null, '
    '"email" text not null unique, '
    '"emailVerified" boolean not null, '
    '"image" text, '
    '"createdAt" timestamptz default CURRENT_TIMESTAMP not null, '
    '"updatedAt" timestamptz default CURRENT_TIMESTAMP not null)',
    'create table "auth_session" ('
    '"id" text not null primary key, '
    '"expiresAt" timestamptz not null, '
    '"token" text not null unique, '
    '"createdAt" timestamptz default CURRENT_TIMESTAMP not null, '
    '"updatedAt" timestamptz not null, '
    '"ipAddress" text, '
    '"userAgent" text, '
    '"userId" text not null references "auth_user" ("id") on delete cascade)',
    'create table "auth_account" ('
    '"id" text not null primary key, '
    '"accountId" text not null, '
    '"providerId" text not null, '
    '"userId" text not null references "auth_user" ("id") on delete cascade, '
    '"accessToken" text, '
    '"refreshToken" text, '
    '"idToken" text, '
    '"accessTokenExpiresAt" timestamptz, '
    '"refreshTokenExpiresAt" timestamptz, '
    '"scope" text, '
    '"password" text, '
    '"createdAt" timestamptz default CURRENT_TIMESTAMP not null, '
    '"updatedAt" timestamptz not null)',
    'create table "auth_verification" ('
    '"id" text not null primary key, '
    '"identifier" text not null, '
    '"value" text not null, '
    '"expiresAt" timestamptz not null, '
    '"createdAt" timestamptz default CURRENT_TIMESTAMP not null, '
    '"updatedAt" timestamptz default CURRENT_TIMESTAMP not null)',
    'create table "auth_jwks" ('
    '"id" text not null primary key, '
    '"publicKey" text not null, '
    '"privateKey" text not null, '
    '"createdAt" timestamptz not null, '
    '"expiresAt" timestamptz)',
    'create index "auth_session_userId_idx" on "auth_session" ("userId")',
    'create index "auth_account_userId_idx" on "auth_account" ("userId")',
    'create index "auth_verification_identifier_idx" on "auth_verification" ("identifier")',
]

_DROP_TABLES = [
    "auth_jwks",
    "auth_verification",
    "auth_account",
    "auth_session",
    "auth_user",
]


def upgrade() -> None:
    """Better Auth 코어 5테이블 + users.auth_user_id (전부 가산/완화)."""
    for statement in _CREATE_STATEMENTS:
        op.execute(statement)

    # clerk_id 는 NOT NULL 이라 신규 INSERT(auth_user_id 만 채움)가 실패한다.
    # NOT NULL 해제는 "완화" 라 구 이미지에는 영향이 없다 — 구 이미지는 항상 값을 넣는다.
    # sa.String() 을 쓰는 이유 — 주변 리비전들은 sqlmodel.sql.sqltypes.AutoString() 을 쓰지만
    # 그건 pyright 가 잡는 패턴이고(기존 8개 파일에 이미 오류가 떠 있다), AutoString 은 그냥
    # sa.String 서브클래스라 Postgres DDL 출력이 VARCHAR 로 동일하다. 새 부채를 늘리지 않는다.
    op.alter_column("users", "clerk_id", existing_type=sa.String(), nullable=True)
    op.add_column("users", sa.Column("auth_user_id", sa.String(), nullable=True))
    # ★인덱스 이름이 계약이다. get_current_user 의 lazy seed 가 쓰는
    #   `ON CONFLICT (auth_user_id)` 는 index inference 로 이 UNIQUE 인덱스를 찾는다.
    #   Postgres 는 partial 이 아닌 UNIQUE 인덱스에서 NULL 을 서로 distinct 로 보므로
    #   auth_user_id IS NULL 인 레거시 행이 여러 개 있어도 충돌하지 않는다.
    op.create_index("ix_users_auth_user_id", "users", ["auth_user_id"], unique=True)


def downgrade() -> None:
    """★운영 DB 에서 실행 금지 — 전 사용자의 인증 자격이 사라진다.

    로컬/테스트 재현용으로만 둔다. 인덱스는 테이블과 함께 사라지므로 별도 drop 하지 않는다.
    clerk_id 의 NOT NULL 복구는 넣지 않는다 — NULL 행이 이미 있으면 실패하기 때문이다.
    """
    op.drop_index("ix_users_auth_user_id", table_name="users")
    op.drop_column("users", "auth_user_id")
    for table in _DROP_TABLES:
        op.execute(f'drop table if exists "{table}" cascade')
