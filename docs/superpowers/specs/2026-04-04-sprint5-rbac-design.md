# Sprint 5 설계: RBAC + 초대 시스템

**날짜:** 2026-04-04
**Sprint:** 5 (Week 9-10)
**목표:** 내부 팀 5명이 워크스페이스에 초대받아 역할별로 사용 가능한 수준.

---

## 1. 배경 및 의사결정

### ADR-007: 권한 모델 + 가격 모델 결정

**검토한 5가지 방안:**

| 방안 | 설명 | 점수 | 판정 |
|------|------|:---:|:---:|
| 1. 단순 RBAC | 워크스페이스 레벨만 | 44 | MVP 최소 |
| **2. RBAC + 프로젝트 멤버십** | 워크스페이스 + 프로젝트 공개 범위 | **53** | **최종 목표** |
| 3. ReBAC (Zanzibar) | 관계 기반 세밀 권한 | 46 | 과잉 설계 |
| 4. ABAC/PBAC | 정책 기반 속성 권한 | 41 | 과잉 설계 |
| 5. Creator 기반 (Coda식) | 생성자만 과금 | 42 | Kairos 가치 불일치 |

**결정:** Sprint 5는 **방안 1** (워크스페이스 RBAC) 구현. **방안 2**는 Sprint 6+에서 확장.

**가격 모델 결정:** per-seat + AI 사용량 캡 (Slite식)

| 플랜 | 가격 | 멤버 | 회의/월 | RAG/유저/월 | 저장 |
|------|------|:---:|:---:|:---:|:---:|
| Free | $0 | 5명 | 5건 | 50회 | 1GB |
| Pro | $10/user | 무제한 | 30건 | 300회 | 50GB |
| Business | $20/user | 무제한 | 100건 | 1,000회 | 500GB |
| Enterprise | 커스텀 | 무제한 | 무제한 | 무제한 | 무제한 |

> 가격 인프라(Stripe 연동, 사용량 추적)는 Sprint 5 범위 **밖**. 여기서는 방향만 확정.

### 비용 분석 근거

- RAG 질문 1건: ~$0.0005 (무시할 수준)
- 회의 인제스트 1건(30분): ~$0.18 (Whisper가 핵심 원가)
- 모든 유료 시나리오에서 89%+ 마진 확인
- RAG 횟수 제한은 비용 방어가 아닌 **인지적 업셀 장치**

---

## 2. Sprint 5 구현 범위

### 포함 (In Scope)

1. **역할 검증 미들웨어** — 모든 보호 엔드포인트에 역할 기반 접근 제어
2. **초대 링크 생성/수락** — 워크스페이스 초대 flow
3. **멤버 관리 API** — 역할 변경, 멤버 제거
4. **FE 멤버 관리 UI** — 설정 페이지에서 멤버 목록/초대/역할 변경

### 제외 (Out of Scope — Sprint 6+)

- 프로젝트 멤버십 / Guest 역할 / Private 프로젝트 (방안 2 확장)
- Stripe 연동 / 플랜 관리 / 사용량 추적
- 이메일 초대 알림 (SMTP 인프라)
- SSO/SAML

---

## 3. 역할 체계

### 4단계 역할

| 역할 | 레벨 | 권한 |
|------|:---:|------|
| **Owner** | 4 | 전체 관리: 워크스페이스 삭제, 멤버 역할 변경(Owner 제외), 모든 CRUD |
| **Admin** | 3 | 멤버 초대/제거, 모든 콘텐츠 CRUD, 프로젝트 Archive |
| **Member** | 2 | 본인 생성 콘텐츠 CRUD (`created_by_id = 본인`), 다른 콘텐츠 읽기, RAG 질문 |
| **Viewer** | 1 | 읽기 전용: 콘텐츠 조회, RAG 질문만 가능 |

### 역할별 API 접근 매트릭스

| 행위 | Owner | Admin | Member | Viewer |
|------|:---:|:---:|:---:|:---:|
| 워크스페이스 설정 변경 | ✅ | ❌ | ❌ | ❌ |
| 멤버 초대/제거 | ✅ | ✅ | ❌ | ❌ |
| 멤버 역할 변경 | ✅ | ❌ | ❌ | ❌ |
| 회의 업로드 | ✅ | ✅ | ✅ | ❌ |
| 프로젝트 생성 | ✅ | ✅ | ✅ | ❌ |
| 프로젝트 Archive | ✅ | ✅ | ❌ | ❌ |
| 노트 작성 | ✅ | ✅ | ✅ | ❌ |
| 타인 콘텐츠 편집 | ✅ | ✅ | ❌ | ❌ |
| 타인 콘텐츠 삭제 | ✅ | ✅ | ❌ | ❌ |
| 본인 콘텐츠 편집/삭제 | ✅ | ✅ | ✅ | ❌ |
| 콘텐츠 조회 | ✅ | ✅ | ✅ | ✅ |
| RAG 질문 | ✅ | ✅ | ✅ | ✅ |
| 액션 아이템 상태 변경 | ✅ | ✅ | ✅ | ❌ |

---

## 4. 백엔드 아키텍처

### 4.1 역할 검증 미들웨어

기존 `get_current_user()` 의존성에 **역할 검사 레이어**를 추가.

```python
# auth/dependencies.py — 추가

class RoleChecker:
    """최소 역할 요구 검증. Depends()로 사용."""
    def __init__(self, min_role: str):
        self.min_role = min_role
    
    async def __call__(
        self,
        workspace_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
    ) -> WorkspaceMember:
        repo = WorkspaceMemberRepository(session)
        member = await repo.find_by_workspace_and_user(workspace_id, current_user.id)
        if member is None:
            raise HTTPException(403, "워크스페이스 멤버가 아닙니다")
        if ROLE_LEVEL[member.role] < ROLE_LEVEL[self.min_role]:
            raise HTTPException(403, f"{self.min_role} 이상 권한이 필요합니다")
        return member

# 역할 레벨 상수
ROLE_LEVEL = {"viewer": 1, "member": 2, "admin": 3, "owner": 4}

# 사전 정의 의존성
require_viewer = RoleChecker("viewer")
require_member = RoleChecker("member")
require_admin = RoleChecker("admin")
require_owner = RoleChecker("owner")
```

**라우터 적용 패턴:**

```python
# meetings/router.py 예시
@router.post("", status_code=202)
async def create_meeting(
    workspace_id: uuid.UUID,
    data: CreateMeetingRequest,
    member: WorkspaceMember = Depends(require_member),  # Member 이상만
    service: MeetingService = Depends(get_meeting_service),
):
    ...
```

### 4.2 초대 링크 시스템

**새 모델: `WorkspaceInvite`**

```python
class WorkspaceInvite(SQLModel, table=True):
    __tablename__ = "workspace_invites"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    code: str = Field(index=True, unique=True)  # nanoid 12자리
    role: str = "member"  # 초대 시 부여할 역할
    created_by_id: uuid.UUID = Field(foreign_key="users.id")
    max_uses: int | None = None  # null = 무제한
    use_count: int = 0
    expires_at: datetime | None = None  # null = 만료 없음
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**초대 flow:**

```
[Admin] POST /workspaces/{id}/invites → {code, inviteUrl}
  → inviteUrl = https://kairos.app/invite/{code}

[초대받은 사용자] GET /invite/{code}
  → Clerk 로그인 (미로그인 시)
  → POST /workspaces/join/{code}
  → WorkspaceMember 생성 (role = invite.role)
  → 리다이렉트 → /
```

### 4.3 새 API 엔드포인트

| 메서드 | 경로 | 최소 역할 | 설명 |
|--------|------|----------|------|
| `GET` | `/workspaces/{id}/members` | viewer | 멤버 목록 |
| `PATCH` | `/workspaces/{id}/members/{memberId}` | owner | 역할 변경 |
| `DELETE` | `/workspaces/{id}/members/{memberId}` | admin | 멤버 제거 |
| `POST` | `/workspaces/{id}/invites` | admin | 초대 링크 생성 |
| `GET` | `/workspaces/{id}/invites` | admin | 초대 링크 목록 |
| `DELETE` | `/workspaces/{id}/invites/{inviteId}` | admin | 초대 링크 비활성화 |
| `GET` | `/invites/{code}` | (인증불필요) | 초대 정보 조회 |
| `POST` | `/invites/{code}/accept` | (인증필요) | 초대 수락 |

### 4.4 기존 엔드포인트 역할 검증 추가

| 도메인 | 엔드포인트 | 현재 | 변경 |
|--------|-----------|------|------|
| meetings | POST (업로드) | 인증만 | **require_member** |
| meetings | GET (목록/상세) | 인증만 | **require_viewer** |
| projects | POST/PATCH/DELETE | 인증만 | **require_member** (생성), **require_admin** (삭제) |
| projects | POST archive | 인증만 | **require_admin** |
| inbox | POST classify/dismiss | 인증만 | **require_member** |
| notes | POST/PATCH/DELETE | 인증만 | **require_member** |
| actions | POST/PATCH | 인증만 | **require_member** |
| rag | POST ask | 인증만 | **require_viewer** |
| upload | POST presigned-url | 인증만 | **require_member** |

### 4.5 DB 마이그레이션

```sql
-- Alembic migration: add_workspace_invites

CREATE TABLE workspace_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    code VARCHAR(12) NOT NULL UNIQUE,
    role VARCHAR(10) NOT NULL DEFAULT 'member',
    created_by_id UUID NOT NULL REFERENCES users(id),
    max_uses INTEGER,
    use_count INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_invites_code ON workspace_invites(code);
CREATE INDEX idx_invites_workspace ON workspace_invites(workspace_id);
```

기존 `workspace_members` 테이블은 변경 없음 (이미 `role` 컬럼 존재).

---

## 5. 프론트엔드

### 5.1 새 페이지/컴포넌트

| 경로/컴포넌트 | 설명 |
|-------------|------|
| `/settings/members` | 멤버 목록 + 역할 뱃지 + 역할 변경 드롭다운 + 제거 버튼 |
| `/settings/invites` | 초대 링크 목록 + 생성 버튼 + 링크 복사 + 비활성화 |
| `/invite/[code]` | 초대 수락 페이지 (워크스페이스 이름 + 초대자 + 수락 버튼) |
| `features/members/` | 새 도메인 모듈 (api, hooks, types, components) |

### 5.2 기존 UI 변경

| 위치 | 변경 |
|------|------|
| **사이드바 하단** | 설정 ⚙️ 아이콘 추가 → `/settings/members` |
| **Header** | 워크스페이스 이름 옆 멤버 수 뱃지 |
| **콘텐츠 CRUD 버튼** | Viewer 역할이면 편집/삭제 버튼 숨김 |
| **업로드 버튼** | Viewer이면 비활성화 |

### 5.3 역할 정보 전달

`get_current_user()` 응답에 `workspaceRole` 필드 추가. FE에서 Zustand로 캐시.

```typescript
// store/auth.ts (새로 추가)
interface AuthState {
  user: User | null;
  workspaceRole: "owner" | "admin" | "member" | "viewer" | null;
}
```

---

## 6. 확장 로드맵 (Sprint 6+)

| Sprint | 범위 |
|--------|------|
| **6** | 프로젝트 멤버십 (Public/Private) + Guest 역할 |
| **7** | 결제 연동 (포트원 + 토스페이먼츠) + 플랜 관리 + 사용량 추적 |
| **8+** | SSO/SAML, 감사 로그, 이메일 초대 알림 |

### 결제 아키텍처 방향 (후순위 — PMF 달성 후)

> 결제 인프라는 Sprint 5 범위 밖. 아래는 방향 기록만.

**3단계 확장 전략:**
1. **즉시 (Sprint 7+):** 포트원+토스(한국) + PayPal(글로벌, 한국법인으로 가입 가능)
2. **PMF 후:** Stripe Atlas(Delaware LLC $500) → Stripe Billing 추가, PayPal은 보조로 유지
3. **Scale:** 세금계산서+무통장입금(한국 대기업) + Invoice+Wire(글로벌 대기업)

**코드 설계 원칙:** PG-agnostic `PaymentProvider` 추상화로 설계하여 Stripe 추가 시 Provider 클래스만 구현.

**가격표 (확정):**

| 플랜 | 가격 | 멤버 | 회의/월 | RAG/유저/월 | 저장 |
|------|------|:---:|:---:|:---:|:---:|
| Free | $0 | 5명 | 5건 | 50회 | 1GB |
| Pro | $10/user | 무제한 | 30건 | 300회 | 50GB |
| Business | $20/user | 무제한 | 100건 | 1,000회 | 500GB |
| Enterprise | 커스텀 | 무제한 | 무제한 | 무제한 | 무제한 |

---

## 7. 완료 기준

- [ ] 모든 기존 API에 역할 검증 미들웨어 적용
- [ ] 초대 링크 생성 → 수락 → 멤버 추가 flow 동작
- [ ] `/settings/members` 페이지에서 멤버 목록/역할 변경/제거 가능
- [ ] Viewer가 콘텐츠 편집/업로드 시도 시 403 반환
- [ ] Owner가 타 멤버 역할을 변경할 수 있음
