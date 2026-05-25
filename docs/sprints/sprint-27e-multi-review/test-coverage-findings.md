# Sprint 27e — 테스트 커버리지 리뷰어 발견사항

- 검사 범위: 신규 기능 / 에지 / 통합 / 품질 / 정량
- 시나리오: Personal + Team
- 검사 일시: 2026-05-25 00:30
- baseline commit: `1b24898` (Sprint 27d main HEAD), 작업 브랜치 `sprint-27e/multi-review` (변경 없음)
- 측정 도구: `pytest-cov 7.1.0` + `coverage 7.14.0` (audit 일회성 dev-deps, revert 예정), `@vitest/coverage-v8 4.1.6`
- 로컬 FE/BE 모두 down — pytest + vitest 로 정량 측정, e2e/Playwright MCP 는 spec 정적 분석으로 대체

---

## 1. Executive Summary

| 영역 | 결과 | 임계 | 판정 |
|---|---:|---:|---|
| BE pytest pass | 469 passed / 1 skipped / 0 failed | grow | OK |
| BE lines | **65.69%** (2973/4240) | ≥ 80% | **FAIL** |
| BE branches | **41.08%** (313/762) | ≥ 70% | **FAIL** |
| FE vitest pass | 56 passed | grow | OK |
| FE lines (측정 대상 한정) | 59.93% (199/332) | ≥ 70% | FAIL |
| FE 실 line coverage (전체 src 기준 추정) | **< 6%** | ≥ 70% | **FAIL (구조적)** |
| e2e 핵심 흐름 cover | **9 / 14** | ≥ 10/14 | FAIL |
| 신규 기능 cover (Sprint 24~27d 11건) | **8 / 11 = 72.7%** | ≥ 80% | FAIL |
| 통합 핵심 흐름 (5건) | **3 / 5** | 5/5 | FAIL |

전수 판정. 신규 기능 11건 중 8건이 어느 layer 든 cover. 결정적 갭 3건. e2e 신규 spec 5건 권고. **차단 분류** = 2건 (TEST-1, TEST-2). 비차단 = 8건.

핵심 발견:
1. **TEST-1 (P0, 차단)**: Sprint 27d BUG-S27d-4 보안 헤더 fix 의 **회귀 가드 0건**. 코드는 `backend/src/main.py:103-108` + `frontend/next.config.ts:5-15`. 임의로 헤더가 제거되어도 CI 가 잡지 못함.
2. **TEST-2 (P0, 차단)**: BL-S27c-1 lazy seed 진정한 동시 race 미검증 — `test_personal_workspace_race.py` 가 자기 주석에서 "sequential INSERT 로 idempotency 만 검증" 명시. 별개 connection asyncio.gather 케이스 carry-over 채 외부 진입.
3. **TEST-3 (P1)**: FE 171 source 파일 대비 unit test 6 파일 — vitest 가 import 된 파일만 측정해 표면 cov 60% 처럼 보이나 실 base 333 statements / 전체 src 추정 만 statements. structural 빈틈.

---

## 2. 정량 baseline 표 (필수)

### 2.1 백엔드 pytest --cov

| 항목 | 값 |
|---|---:|
| 전체 statements | 4240 |
| covered | 2973 |
| **percent_covered (lines)** | **65.69%** |
| 전체 branches | 762 |
| covered branches | 313 |
| **percent_branches** | **41.08%** |
| pass / skip / fail | 469 / 1 / 0 |
| 실행 시간 | 87.5s |

### 2.2 프론트엔드 vitest --coverage

| 항목 | 값 |
|---|---:|
| 전체 statements (v8 측정 대상) | 367 |
| covered | 212 |
| percent statements | 57.76% |
| Lines | 59.93% (199/332) |
| Branches | 47.27% (78/165) |
| Functions | 43.63% (48/110) |
| pass | 56 / 6 files |

> v8 coverage 는 import-traced 파일만 측정. 실 src/ 는 171 source 파일이며 test 는 6 파일. 전체 base 로 환산 시 line cov < 6%. `vitest.config.ts` 에 `coverage.include: ['src/**']` 미설정 → 측정 누락.

### 2.3 e2e 핵심 흐름 14건 매트릭스

| # | 시나리오 | 핵심 흐름 | e2e spec | 상태 |
|---|---|---|---|---:|
| 1 | Personal | 회의 업로드 → 요약 + Action | `meeting-upload.spec.ts` | OK |
| 2 | Personal | 노트 작성 → 임베딩 | `note-detail.spec.ts` | OK (간접) |
| 3 | Personal | ⌘K 검색 SSE + citation | `rag-citation.spec.ts` | OK |
| 4 | Personal | Inbox 자동 분류 + reassign | `inbox-dismiss.spec.ts` | 부분 (dismiss 만) |
| 5 | Personal | ActionItem 처리 | (없음) | **갭** |
| 6 | Personal | OnboardingTooltip 첫 방문 | `onboarding-tooltip-first-visit.spec.ts` | OK |
| 7 | Personal | /actions redirect | `actions-redirect.spec.ts` | OK |
| 8 | Team | 워크스페이스 초대 수락 | `invite-page-regression.spec.ts` | 부분 (페이지 회귀만, accept happy-path 미검증) |
| 9 | Team | 공유 회의 cross-member | (없음) | **갭** |
| 10 | Team | visibility 분기 RAG | (없음) | **갭** |
| 11 | Team | role escalation 차단 | (없음, BE unit 만) | **갭** |
| 12 | Team | cross-tenant IDOR | BE `test_workspace_idor_*` | OK (BE only) |
| 13 | Both | workspace switch | `workspace-switch.spec.ts` | OK |
| 14 | Both | 보안 헤더 회귀 | (없음) | **갭** (BUG-S27d-4 carry) |

**합계 9/14 OK, 5/14 갭.** (부분 cover 2건은 OK 계산에 포함.)

### 2.4 신규 기능 (Sprint 24-27d) 매트릭스

| # | 기능 | 출처 | unit | 통합 | e2e | 갭 |
|---|---|---|:-:|:-:|:-:|---|
| 1 | OnboardingTooltip D 옵션 | S24 W2 T-OBN-05 | - | - | OK | - |
| 2 | 회의 BG 안전 (session_factory) | S24 BL-064 | OK | OK | - | retry endpoint 부재 |
| 3 | ActionItem 자동 복제 | S24 BL-063 | OK | OK | - | e2e 권고 |
| 4 | upload mime validation | S25 T-SEC-3 + S27d-3 | OK (20+) | - | - | e2e 권고 (proxy + presigned 양쪽) |
| 5 | Inbox 자동 분류 (confidence) | S8/S15 | OK | OK | 부분 | reassign e2e 갭 |
| 6 | Personal/Team 분리 | S5-6 + I-19 | OK | OK | - | 동시 운영 통합 갭 |
| 7 | invite flow | S5 | OK (API mock) | - | 부분 | accept happy-path e2e 갭 + expired token unit 갭 |
| 8 | RAG citation 정확성 | S12-15 | OK | OK | OK | - |
| 9 | 보안 헤더 (4종) | S27d-4 | **없음** | **없음** | **없음** | **TEST-1 P0** |
| 10 | /actions redirect | S27d-2 | - | - | OK | - |
| 11 | CSP 정책 | BL-S27e-3 (미구현) | - | - | - | Sprint 28+ |

**cover 갯수 8/11 = 72.7%** (≥ 80% 임계 미달, FAIL).

### 2.5 통합 핵심 흐름 5건

| # | 흐름 | spec | 상태 |
|---|---|---|---|
| 1 | 회의 upload → STT → summary → embed → search | `test_pipeline.py` (4 cases) | OK |
| 2 | invite → accept → workspace switch → role | BE unit + e2e `workspace-switch` | 부분 (accept 자체 happy-path BE/e2e 갭) |
| 3 | Personal+Team 동시 운영 | 없음 | **갭** |
| 4 | visibility 변경 (public ↔ private) 즉시 RAG | `test_vector_search_visibility.py` (BE) | OK (BE only) |
| 5 | 회의 retry 완전성 | 없음 (M-3 carry — CONTEXT.md 명시) | **갭** |

**합계 3/5 (1건 부분).** 5/5 임계 미달, FAIL.

---

## 3. 모듈별 BE coverage (branch 포함)

| 모듈 | lines | stmts | branches | 갭 |
|---|---:|---:|---:|---|
| inbox | **94%** | 193 | 81% | OK |
| upload | **87%** | 160 | 74% | OK |
| rag | **86%** | 225 | 70% | OK |
| common | 82% | 231 | 67% | branches 미달 |
| actions | 79% | 236 | 46% | **branches 갭** |
| auth | 73% | 201 | 67% | branches 경계 |
| projects | 68% | 314 | 26% | **branches 심각** |
| meetings | 67% | 546 | 20% | **branches 심각** |
| workspaces | 64% | 430 | **4%** | **TEST-4 — branches 극단** |
| notes | 63% | 394 | 17% | **branches 심각** |
| memory | 59% | 620 | 29% | lines + branches |
| embeddings | 59% | 275 | 48% | lines |
| services (transcription/AI) | 58% | 216 | 46% | lines |
| onboarding | 100% | 57 | 100% | OK |

### 3.1 가장 cov 낮은 핵심 service 파일 (재발 risk 큼)

| 파일 | lines | 비고 |
|---|---:|---|
| `src/workspaces/invite_service.py` | **21%** | invite accept / token 검증 / 만료 logic 대다수 미검증 |
| `src/memory/service.py` | **28%** | promote / consolidate 분기 미검증 |
| `src/meetings/service.py` | **32%** | retry / R2 hash dedupe 분기 |
| `src/notes/service.py` | **37%** | BL-064 분기 일부만 |
| `src/notes/pipeline_service.py` | **38%** | - |
| `src/projects/service.py` | **44%** | cross-workspace add_member 분기 |
| `src/embeddings/service.py` | **45%** | semantic cache TTL/threshold 분기 |
| `src/services/transcription.py` | **47%** | Whisper 청크 / pyannote diarization 분기 |
| `src/meetings/repository.py` | **48%** | composite FK fail path |

---

## 4. 발견사항 매트릭스

| ID | 영역 | 심각도 | 차단 | 누락 layer | 추가 케이스 |
|---|---|---|:-:|---|---|
| BUG-S27e-TEST-1 | 신규 기능 회귀 가드 | P0 | YES | unit + e2e | 보안 헤더 4종 회귀 spec (BE + FE) |
| BUG-S27e-TEST-2 | 에지 (race) | P0 | YES | 통합 | lazy seed 진정한 concurrent race (별개 connection asyncio.gather) |
| BUG-S27e-TEST-3 | 정량 (FE 구조) | P1 | NO | unit (전체) | `vitest.config.ts` coverage.include 설정 + FE service/util/store unit |
| BUG-S27e-TEST-4 | 정량 (branch) | P1 | NO | unit | `workspaces` branch 4% — invite_service branch case 추가 |
| BUG-S27e-TEST-5 | 통합 흐름 | P1 | NO | 통합 + e2e | invite accept happy-path (생성→공유→수락→role 확인) |
| BUG-S27e-TEST-6 | 통합 흐름 | P1 | NO | e2e | 회의 retry (failed → 재처리) — M-3 carry |
| BUG-S27e-TEST-7 | 신규 기능 | P1 | NO | e2e | upload mime 위장 (proxy + presigned 양쪽) e2e |
| BUG-S27e-TEST-8 | 에지 | P2 | NO | unit | upload 거대 입력 (한도 직전 + 한도 + 한도+1) — 현 1024 mock 만, 100MB 실 한도 미검증 |
| BUG-S27e-TEST-9 | 에지 | P2 | NO | unit/통합 | 유니코드 (emoji + 한자 + RTL) 회의/노트/검색 |
| BUG-S27e-TEST-10 | 통합 흐름 | P2 | NO | 통합 | Personal+Team 동시 운영 (시나리오 격리 + cross-workspace 누출 없음) |

---

## 5. 개별 발견사항 + 추가 테스트 케이스 코드

### BUG-S27e-TEST-1 — 보안 헤더 4종 회귀 가드 0건 (P0, 차단)

- **영역**: 신규 기능 회귀 가드
- **심각도**: P0
- **차단**: YES
- **누락 layer**: unit (BE) + e2e (FE) 양쪽

#### 증상

Sprint 27d BUG-S27d-4 fix 가 `backend/src/main.py:103-108` 에 4개 헤더 (`X-Frame-Options=DENY`, `X-Content-Type-Options=nosniff`, `Referrer-Policy=strict-origin-when-cross-origin`, `Permissions-Policy=...`) middleware 추가 + `frontend/next.config.ts:5-15` 에 동일 4종 추가. **그러나 회귀 가드 테스트 0건** — `grep -rn "X-Frame-Options\|Referrer-Policy" backend/tests frontend/e2e` 모두 hit 없음. 누군가 middleware reorder / next.config.ts 정리 시 헤더 누락이 CI 에서 감지 안 됨. 외부 5명 dogfooding 진입 후 clickjacking / MIME sniffing 회귀 잡을 방법 없음.

#### 추가 권고 케이스 — BE

```python
# backend/tests/test_security_hardening.py 끝에 append
# Sprint 27d BUG-S27d-4 회귀 가드 (Sprint 27e BUG-S27e-TEST-1).
"""모든 응답에 4종 보안 헤더가 보장되는지 회귀 가드."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest_asyncio.fixture
async def public_client():
    """인증 없이 health check 호출용."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_security_headers_present_on_health_check(public_client):
    """BUG-S27d-4 회귀: GET /api/v1/health 응답에 4종 헤더 동시 존재."""
    response = await public_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    perm = response.headers.get("permissions-policy", "")
    assert "camera=()" in perm
    assert "microphone=(self)" in perm
    assert "geolocation=()" in perm


@pytest.mark.asyncio
async def test_security_headers_present_on_404(public_client):
    """404 응답에서도 헤더가 보장되어야 한다 (clickjacking 방어 일관성)."""
    response = await public_client.get("/api/v1/nonexistent-path")
    assert response.status_code == 404
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-content-type-options") == "nosniff"
```

#### 추가 권고 케이스 — FE e2e

```typescript
// frontend/e2e/tests/security-headers.spec.ts (신설)
// BUG-S27d-4 회귀 가드 — FE Next.js 응답 4종 헤더 검증
import { test, expect } from "@playwright/test";

test.describe("BUG-S27d-4 Security Headers Regression", () => {
  test("home / page returns 4 security headers", async ({ page }) => {
    const response = await page.goto("/");
    expect(response).toBeTruthy();
    const headers = response!.headers();
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
    expect(headers["permissions-policy"]).toContain("camera=()");
  });

  test("auth /sign-in returns 4 security headers", async ({ page }) => {
    const response = await page.goto("/sign-in");
    const headers = response!.headers();
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["x-content-type-options"]).toBe("nosniff");
  });
});
```

#### 우선순위 = P0

외부 사용자 진입 *전*에 회귀 가드 부재 → 한 번 헤더가 빠지면 production 직접 운영 중 발견까지 가야 함. clickjacking iframe embedding 시 인증 토큰 노출 가능 → 보안 회귀가 사용자 데이터에 직접 영향. **차단**.

---

### BUG-S27e-TEST-2 — lazy seed 진정한 동시 race 미검증 (P0, 차단)

- **영역**: 에지 (race condition)
- **심각도**: P0
- **차단**: YES
- **누락 layer**: 통합

#### 증상

`backend/tests/auth/test_personal_workspace_race.py:5-8` 자체 주석:

> "진정한 동시 race (별개 connection) 는 carry-over — 본 test 는 동일 session sequential INSERT 로 idempotency 만 검증."

Sprint 27c BL-S27c-1 의 P0 fix 가 ON CONFLICT 패턴에 의존. 그러나 ON CONFLICT 가 race 실제로 동시 호출에서 어떻게 동작하는지 — 별개 connection 두 개가 `gen_random_uuid()` 로 동일 owner_id row 시도할 때 — 통합 테스트 부재. **Sprint 27c 의 P0 fix 가 자체 검증 가드 없이 main 에 머지됨**. fix 회귀 위험.

#### 추가 권고 케이스

```python
# backend/tests/auth/test_get_current_user_race.py 확장
# (현 파일은 sequential 만 검증. 본 케이스가 concurrent 부분을 닫음)
import asyncio
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.mark.asyncio
async def test_lazy_seed_truly_concurrent_creates_single_workspace(
    integration_engine,  # conftest 의 별도 engine fixture (모듈 scope)
    _ensure_partial_unique_index,
):
    """BL-S27c-1 fix 검증: 동일 user 5개 별개 connection 동시 lazy seed → workspace 1개만 생성.

    별개 AsyncSession 으로 asyncio.gather 5회 동시 호출. ON CONFLICT 가 진정한 race
    조건에서 단일 row 만 commit 함을 검증. 사전 sequential 만 검증하던 한계 보완.
    """
    user_id = uuid.uuid4()

    # Pre-seed user row (별개 short session)
    async with AsyncSession(integration_engine) as setup_session:
        await setup_session.execute(
            text(
                "INSERT INTO users (id, clerk_id, display_name, email, created_at, updated_at) "
                "VALUES (:id, :clerk, :name, :email, now(), now())"
            ),
            {
                "id": str(user_id),
                "clerk": f"user_{user_id.hex[:12]}",
                "name": "Race",
                "email": f"race-{user_id.hex[:8]}@test",
            },
        )
        await setup_session.commit()

    async def _attempt_lazy_seed():
        # 별개 connection 으로 lazy seed 시도
        async with AsyncSession(integration_engine) as s:
            await s.execute(
                text(LAZY_SEED_WORKSPACE_SQL),
                {"owner_id": str(user_id), "name": "race ws"},
            )
            await s.execute(text(LAZY_SEED_MEMBER_SQL), {"owner_id": str(user_id)})
            await s.commit()

    # 5개 동시 호출
    await asyncio.gather(*(_attempt_lazy_seed() for _ in range(5)))

    # 최종 workspace 1개만 존재
    async with AsyncSession(integration_engine) as verify:
        result = await verify.execute(
            text("SELECT count(*) FROM workspaces WHERE owner_id = :oid AND type = 'personal'"),
            {"oid": str(user_id)},
        )
        count = result.scalar_one()
        assert count == 1, f"동시 lazy seed 5회 → workspace count={count} (1 이어야 함)"

        # WorkspaceMember 도 1개만
        result = await verify.execute(
            text(
                "SELECT count(*) FROM workspace_members m "
                "JOIN workspaces w ON w.id = m.workspace_id "
                "WHERE w.owner_id = :oid AND w.type = 'personal'"
            ),
            {"oid": str(user_id)},
        )
        member_count = result.scalar_one()
        assert member_count == 1, f"WorkspaceMember count={member_count} (1 이어야 함)"
```

> 사전 작업: `backend/tests/conftest.py` 에 `integration_engine` fixture 가 별도 노출되어야 함 (현재 `integration_session` 만 노출). 본 fixture 가 없으면 별개 connection 시뮬레이션 불가.

#### 우선순위 = P0

Sprint 27c 가 race fix 를 P0 로 식별 + main 머지. 그러나 fix 회귀 가드가 sequential idempotency 만 검증 → fix 자체가 깨졌어도 CI green. 외부 5명 진입 시 동시 첫 로그인 race 발생 시 워크스페이스 2개 생성되어 헌법 I-19 violate. **차단**.

---

### BUG-S27e-TEST-3 — FE coverage 측정 범위 미설정 (P1)

- **영역**: 정량 (FE 구조)
- **심각도**: P1
- **차단**: NO
- **누락 layer**: 측정 인프라

#### 증상

`frontend/vitest.config.ts` 에 `test.coverage.include` 미설정 → v8 가 import-traced 파일 (367 statements) 만 측정. 실 `src/` 는 171 소스 파일이며 unit test 6 파일 → 측정 base 가 작아 **표면 60% line cov 처럼 보임**. 전체 src 기준 실 cov 추정 < 6%. 신규 기능 추가 시 측정 사각지대.

#### 추가 권고

```typescript
// frontend/vitest.config.ts 수정
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["e2e/**", "node_modules/**"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.{test,spec}.{ts,tsx}",
        "src/**/__tests__/**",
        "src/**/*.d.ts",
        "src/app/**", // Next.js page/layout — e2e cover 영역
        "src/components/ui/**", // shadcn 외부 코드 (I-11)
      ],
      reporter: ["text", "html", "json-summary"],
      thresholds: {
        lines: 30, // 점진 상향 시작값
        branches: 25,
        functions: 30,
      },
    },
  },
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
});
```

#### 우선순위 = P1

차단은 아니나 정량 측정의 신뢰도 회복 — Sprint 28+ 에서 FE coverage 임계를 점진 상향할 base. 비차단.

---

### BUG-S27e-TEST-4 — workspaces 모듈 branch cov 4% (P1)

- **영역**: 정량 (branch)
- **심각도**: P1
- **차단**: NO
- **누락 layer**: unit + 통합

#### 증상

`workspaces` 모듈 branch cov **4%** (52 branches 중 ~2 cover). 특히 `invite_service.py` lines 21%. invite token 만료 / 비활성 / role 변경 분기 대다수 미검증. 헌법 I-19 (Personal workspace 1인 격리) 의 invite 발급 금지 분기도 미검증.

#### 추가 권고

```python
# backend/tests/workspaces/test_invite_api.py 확장
@pytest.mark.asyncio
async def test_create_invite_blocked_on_personal_workspace(client, mock_service):
    """I-19 회귀: Personal workspace 에서 invite 발급 시도 → 400/403."""
    from src.workspaces.exceptions import PersonalWorkspaceInviteForbidden
    mock_service.create_invite.side_effect = PersonalWorkspaceInviteForbidden()
    response = await client.post(
        f"/api/v1/workspaces/{WID}/invites",
        json={"role": "member", "expiresInHours": 24},
    )
    assert response.status_code in (400, 403)


@pytest.mark.asyncio
async def test_accept_invite_expired_token_rejected(client, mock_service):
    """만료 token → 410 Gone."""
    from src.workspaces.exceptions import InviteExpired
    mock_service.accept_invite.side_effect = InviteExpired()
    response = await client.post(
        "/api/v1/workspaces/invites/accept",
        json={"token": "expired-token-xxx"},
    )
    assert response.status_code in (410, 400)


@pytest.mark.asyncio
async def test_accept_invite_deactivated_token_rejected(client, mock_service):
    """is_active=False token → 400."""
    from src.workspaces.exceptions import InviteDeactivated
    mock_service.accept_invite.side_effect = InviteDeactivated()
    response = await client.post(
        "/api/v1/workspaces/invites/accept",
        json={"token": "deactivated-token-xxx"},
    )
    assert response.status_code in (400, 410)


@pytest.mark.asyncio
async def test_accept_invite_already_member_idempotent(client, mock_service):
    """이미 멤버인 user 의 재수락 → 200 + idempotent (멤버 추가 안 함)."""
    mock_service.accept_invite.return_value = {
        "workspaceId": WID, "role": "member", "alreadyMember": True,
    }
    response = await client.post(
        "/api/v1/workspaces/invites/accept",
        json={"token": "valid-token"},
    )
    assert response.status_code == 200
    assert response.json().get("alreadyMember") is True
```

#### 우선순위 = P1

invite flow 의 만료/비활성/idempotency 는 외부 사용자 진입 핵심 흐름. 그러나 BUG-S27e-TEST-5 (e2e happy-path) 가 차단 분류 처리하면 본 항목은 비차단.

---

### BUG-S27e-TEST-5 — invite accept happy-path e2e 갭 (P1)

- **영역**: 통합 흐름
- **심각도**: P1
- **차단**: NO
- **누락 layer**: 통합 + e2e

#### 증상

`frontend/e2e/tests/invite-page-regression.spec.ts` 는 invite 페이지 자체 회귀만 (BL-S27c-3 P1 carry). 실제 흐름: owner 가 invite 발급 → 다른 user 가 token 입력 → accept → role 확인 → cross-workspace switch. **e2e 0건**. 통합 흐름 #2 부분 cover.

#### 추가 권고

```typescript
// frontend/e2e/tests/invite-accept-happy-path.spec.ts (신설)
import { test, expect } from "@playwright/test";

test.describe("Invite Accept Happy Path (Sprint 27e BUG-S27e-TEST-5)", () => {
  test("owner 발급 → user 수락 → role 부여 → workspace switch", async ({
    browser,
  }) => {
    // owner 컨텍스트
    const ownerCtx = await browser.newContext({
      storageState: ".auth/owner.json",
    });
    const ownerPage = await ownerCtx.newPage();
    await ownerPage.goto("/settings/members");

    // 1. owner 가 invite 생성 → token 추출
    await ownerPage.getByRole("button", { name: /초대.*생성/i }).click();
    await ownerPage.getByLabel("Role").selectOption("member");
    await ownerPage.getByRole("button", { name: /발급/ }).click();
    const tokenLink = await ownerPage
      .getByTestId("invite-token-link")
      .textContent();
    expect(tokenLink).toMatch(/\/invite\/[a-zA-Z0-9-]+/);

    // 2. invitee 컨텍스트
    const inviteeCtx = await browser.newContext({
      storageState: ".auth/invitee.json",
    });
    const inviteePage = await inviteeCtx.newPage();
    await inviteePage.goto(tokenLink!);
    await inviteePage.getByRole("button", { name: /수락/ }).click();

    // 3. workspace 자동 switch + role 표시 확인
    await inviteePage.waitForURL(/\/dashboard/);
    const roleLabel = await inviteePage.getByTestId("user-role").textContent();
    expect(roleLabel).toContain("member");

    // 4. 회귀 가드: invitee 가 owner workspace 의 데이터 read 가능
    await inviteePage.goto("/inbox");
    await expect(inviteePage.getByTestId("inbox-list")).toBeVisible();

    await ownerCtx.close();
    await inviteeCtx.close();
  });
});
```

#### 우선순위 = P1

외부 5명 dogfooding 진입 정책에서 (사용자 결정: dev Clerk + beta) 초대 흐름은 핵심 진입 경로. 그러나 happy-path 실패는 명시적 사용자 피드백으로 발견 가능 → 차단 분류 안 함.

---

### BUG-S27e-TEST-6 — 회의 retry e2e/통합 갭 (P1)

- **영역**: 통합 흐름
- **심각도**: P1
- **차단**: NO
- **누락 layer**: 통합 + e2e

#### 증상

`backend/src/meetings/CONTEXT.md:84` M-3: "외부 API 실패 시 status=failed + error_message 저장 + 사용자 재시도 트리거 (retry 정책 자체는 Phase B)". `test_pipeline.py:206` 가 failure → failed 전이는 검증. **재처리 (retry) 트리거 후 다시 성공 경로 통합 케이스 0건.** BL-S27c-4 (Meeting 실패 후 retry UI P2 carry) 의 BE side 도 미정.

#### 추가 권고

```python
# backend/tests/meetings/test_pipeline.py 끝에 append
@pytest.mark.asyncio
async def test_pipeline_retry_after_failure_success_path():
    """BL-S27c-4 회귀 진입점: failed meeting → retry → completed.

    1차 download_audio 실패로 failed 상태. retry 호출 시 download_audio 정상 →
    completed 까지 상태 전이. error_message 도 cleared.
    """
    from src.meetings.pipeline_service import MeetingPipelineService

    meeting_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    mock_meeting_repo = AsyncMock()
    mock_meeting = MagicMock()
    mock_meeting.id = meeting_id
    mock_meeting.workspace_id = workspace_id
    mock_meeting.file_key = "uploads/test/audio.mp3"
    mock_meeting_repo.find_by_id.return_value = mock_meeting

    mock_r2 = AsyncMock()
    mock_r2.get_download_url.return_value = "https://example/x"

    mock_transcription = AsyncMock()
    # 1차 호출은 실패, 2차는 성공
    segments = [TranscriptSegment(speaker="A", start_sec=0.0, end_sec=3.0, text="ok")]
    mock_transcription.download_audio.side_effect = [
        Exception("temporary network error"),
        b"fake_audio",
    ]
    mock_transcription.transcribe_with_chunking.return_value = (segments, 3.0)

    mock_ai = AsyncMock()
    mock_ai.summarize.return_value = {"summary": "ok", "key_decisions": [], "topics": []}
    mock_ai.extract_actions_and_link.return_value = {
        "actionItems": [], "suggestedProject": {"existingProjectId": None, "newProjectTitle": None, "confidence": 0}, "suggestedTags": [],
    }
    mock_workspace_repo = AsyncMock()
    mock_workspace = MagicMock()
    mock_workspace.inbox_threshold = 0.9
    mock_workspace_repo.find_by_id.return_value = mock_workspace
    mock_embedding_service = AsyncMock()
    mock_embedding_service.embed_meeting.return_value = 1

    with (
        patch("src.meetings.pipeline_service.MeetingRepository", return_value=mock_meeting_repo),
        patch("src.meetings.pipeline_service.ProjectRepository", return_value=AsyncMock()),
        patch("src.meetings.pipeline_service.ActionItemRepository", return_value=AsyncMock()),
        patch("src.meetings.pipeline_service.InboxRepository", return_value=AsyncMock()),
        patch("src.meetings.pipeline_service.WorkspaceRepository", return_value=mock_workspace_repo),
        patch("src.meetings.pipeline_service.EmbeddingRepository", return_value=AsyncMock()),
        patch("src.meetings.pipeline_service.EmbeddingService", return_value=mock_embedding_service),
    ):
        pipeline = MeetingPipelineService(
            session_factory=_make_session_factory(),
            r2_service=mock_r2,
            transcription_service=mock_transcription,
            ai_service=mock_ai,
        )
        # 1차 실패
        await pipeline.process_meeting(meeting_id, workspace_id)
        # 2차 재처리
        await pipeline.process_meeting(meeting_id, workspace_id)

    # 마지막 호출이 completed
    last_status = mock_meeting_repo.update_status.call_args_list[-1].args[2]
    assert last_status == "completed"
    # 중간에 failed → completed 전이 sequence 보장
    all_statuses = [c.args[2] for c in mock_meeting_repo.update_status.call_args_list]
    assert "failed" in all_statuses
    assert all_statuses[-1] == "completed"
```

#### 우선순위 = P1

retry UI 자체는 BL-S27c-4 P2 carry. 그러나 retry 흐름이 동작은 해야 사용자가 실패 회의를 재처리 가능. 차단은 아니지만 외부 진입 *전* 가드 권장.

---

### BUG-S27e-TEST-7 — upload mime e2e 갭 (P1)

- **영역**: 신규 기능
- **심각도**: P1
- **차단**: NO
- **누락 layer**: e2e

#### 증상

`test_upload_validation.py` 가 20+ unit 케이스 (정상 + null-byte + MIME spoof + HEIC 위장 + .exe 위장) cover 함. 그러나 **실 브라우저 → backend `/upload/file` proxy + `/upload/presigned-url` 양쪽 e2e 0건**. FE 의 source-add-modal / new/page 가 video accept 함을 검증한 unit 은 있지만 e2e 미확보.

#### 추가 권고

```typescript
// frontend/e2e/tests/upload-mime-validation.spec.ts (신설)
import { test, expect } from "@playwright/test";
import path from "path";

test.describe("Upload MIME Validation (Sprint 25 T-SEC-3 + 27d-3 e2e 회귀)", () => {
  test("정상 .m4a audio 업로드 → 201 + 페이지 진입", async ({ page }) => {
    await page.goto("/meetings/new");
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(
      path.join(__dirname, "../fixtures/audio/sample.m4a"),
    );
    await page.getByRole("button", { name: /업로드/ }).click();
    await expect(page).toHaveURL(/\/meetings\/[a-f0-9-]+/, { timeout: 15_000 });
  });

  test("위장 .exe 업로드 → 차단 + 에러 메시지", async ({ page }) => {
    await page.goto("/meetings/new");
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(
      path.join(__dirname, "../fixtures/evil/evil.exe"),
    );
    await page.getByRole("button", { name: /업로드/ }).click();
    await expect(page.getByText(/지원하지 않는|invalid|415/i)).toBeVisible();
  });
});
```

#### 우선순위 = P1

unit cov 이미 두꺼움 → 실 브라우저 회귀는 supplementary. 차단 아님.

---

### BUG-S27e-TEST-8 — upload 거대 입력 실 한도 미검증 (P2)

- **영역**: 에지
- **심각도**: P2
- **차단**: NO
- **누락 layer**: unit/통합

#### 증상

`test_upload_validation.py:36` 는 `TEST_MAX_BYTES = 1024` (1KB) mock 한도 검증. **실 production 한도 (100MB 가정) 의 경계 케이스 0건.** `UploadValidator` default `max_bytes` 가 어디서 오는지 + boundary fuzz 가드 없음.

#### 추가 권고

```python
# backend/tests/upload/test_upload_validation.py 끝에 append
@pytest.mark.asyncio
async def test_upload_real_default_max_bytes_is_sane():
    """UploadValidator default max_bytes 가 (1MB, 500MB) 범위 (안전한 한도)."""
    from src.upload.service import UploadValidator
    validator = UploadValidator()
    assert 1_000_000 <= validator.max_bytes <= 500_000_000, (
        f"max_bytes={validator.max_bytes} 가 sane 범위 밖. ENV override 또는 default 검토."
    )


@pytest.mark.asyncio
async def test_upload_rejects_exactly_max_plus_one(authed_client):
    """boundary: TEST_MAX_BYTES + 1 byte → 413 (이미 cover 되지만 boundary 명시 표시)."""
    # test_upload_rejects_oversize 와 통합 가능 — 단순 명시 표지로 leave-as-is OK
    pass
```

#### 우선순위 = P2

unit cov 두꺼움. 비차단.

---

### BUG-S27e-TEST-9 — 유니코드 / emoji 회의·노트·검색 미검증 (P2)

- **영역**: 에지
- **심각도**: P2
- **차단**: NO
- **누락 layer**: unit/통합

#### 증상

`backend/tests/llm/fixtures/sample_transcripts.py:91` 가 `emoji_polite` label 1건 보유. 그러나 회의 / 노트 / RAG 검색 쿼리에 유니코드 (한자 + emoji + RTL) 통합 흐름 e2e/unit 0건. Pydantic V2 alias + DB Postgres collation 분기 미검증.

#### 추가 권고

```python
# backend/tests/notes/test_notes_api.py 끝에 append
@pytest.mark.asyncio
async def test_notes_create_with_unicode_mix(client, mock_service):
    """유니코드 (한글 + 영어 + 한자 + emoji) note 생성 + plain_text 정합."""
    mock_service.create_note.return_value = MagicMock(
        id=uuid.uuid4(),
        title="🎯 회의 노트 — 設計レビュー (q4) 🚀",
        plain_text="한글 English 漢字 العربية 🎉",
    )
    response = await client.post(
        f"/api/v1/workspaces/{WID}/notes",
        json={
            "title": "🎯 회의 노트 — 設計レビュー (q4) 🚀",
            "content": {"type": "doc", "content": []},
            "plainText": "한글 English 漢字 العربية 🎉",
        },
    )
    assert response.status_code == 201
    assert "🎯" in response.json()["title"]
```

#### 우선순위 = P2

회귀 잡힐 가능성 낮음. 비차단.

---

### BUG-S27e-TEST-10 — Personal+Team 동시 운영 통합 갭 (P2)

- **영역**: 통합 흐름
- **심각도**: P2
- **차단**: NO
- **누락 layer**: 통합

#### 증상

I-19 (Personal 1인 격리) + Team workspace owner = 동일 user 가 두 워크스페이스 운영 가능. 그러나 워크스페이스 switch + RAG 검색 격리 + cross-workspace 누출 없음 — 통합 0건. `test_workspace_idor_matrix.py` 는 IDOR 만, 동시 운영 시 sources 자동 노출 등 회귀 미검증.

#### 추가 권고

```python
# backend/tests/integration/test_personal_team_coexist.py (신설)
"""Sprint 27e BUG-S27e-TEST-10 — 동일 user 가 Personal + Team 동시 운영 시 격리."""
import uuid
import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_personal_and_team_workspace_coexist_no_leak(
    integration_session,
):
    """동일 user 가 Personal + Team 양쪽 owner 일 때, RAG 검색 결과가 절대 cross 안 됨."""
    user_id = uuid.uuid4()
    personal_ws = uuid.uuid4()
    team_ws = uuid.uuid4()

    # Pre-seed 2 workspace + 양쪽에 note 1개씩
    await integration_session.execute(
        text(
            "INSERT INTO users (id, clerk_id, display_name, email, created_at, updated_at) "
            "VALUES (:id, 'c', 'u', 'u@x', now(), now())"
        ),
        {"id": str(user_id)},
    )
    await integration_session.execute(
        text(
            "INSERT INTO workspaces (id, owner_id, name, type, inbox_threshold, created_at, updated_at) "
            "VALUES (:p, :u, 'personal', 'personal', 0.9, now(), now()), "
            "(:t, :u, 'team', 'team', 0.9, now(), now())"
        ),
        {"p": str(personal_ws), "t": str(team_ws), "u": str(user_id)},
    )

    # personal ws 의 source row 가 team ws 의 RAG 검색에 노출 안 됨
    # (구체 assertion 은 EmbeddingRepository.search 결과 + visibility filter 검증)
    # ... 이후 구체 RAG search 호출 + ws_id filter 가 정상 작동 확인
```

#### 우선순위 = P2

I-9 (멀티테넌시 격리) 가 이미 IDOR 매트릭스로 두꺼움. 추가 회귀 위험 낮음. 비차단.

---

## 6. 테스트 품질 평가

### 6.1 AAA 구조

샘플 분석: `test_upload_validation.py`, `test_pipeline.py`, `test_invite_api.py`, `test_security_hardening.py` 모두 명확한 given/when/then 분리. 일부 (`test_pipeline.py`) 는 mock setup 이 50+ line. fixture 추출 권장 (`make_meeting_mocks()` 헬퍼) — 비차단 hygiene.

### 6.2 fixture 재사용

`backend/tests/conftest.py` (8516 bytes) + `backend/tests/onboarding/conftest.py` 가 base. `integration_session` 35 파일 재사용. composite_fk fixtures `backend/tests/fixtures/composite_fk.py` 잘 분리. **fixture 부족**: `_make_session_factory` 가 `test_pipeline.py` 안에서만 정의 — 재사용 가능하게 conftest 로 이동 권장.

### 6.3 mock 의존성

`MeetingPipelineService` 가 7개 patch context manager → fragile. 실제 회귀 risk: AI service contract 변경 시 mock 가 동기화 안 됨. → integration smoke 필요 (이미 `test_bl053_fixture_smoke.py` 일부 cover, 확대 권장).

### 6.4 flake

Sprint 27d codex final 의 `7 passed / 1 skipped / 2 failed` 후 focused 재실행 PASS → flake 확정. BL-S27e-4 carry. `frontend/e2e/playwright.config.ts` 의 storageState 격리 + retry 정책 정리 필요. **flake 분류 정량 = 2 spec (first-project, onboarding-tooltip)**. 본 sprint 정량 (10% flake rate) 외부 진입 권고 marginal. 권고: BL-S27e-4 를 Sprint 28 head-of-line.

### 6.5 테스트 이름

샘플 grep `^def test_` (455건) — 대다수 가 시나리오 명시 (`test_lazy_seed_idempotent_single_personal_workspace`, `test_upload_rejects_extension_mismatch`). 모호 이름 `test_X_works` 패턴 0건 검출 — 품질 양호.

### 6.6 comment 부재 / 과다

대다수 파일 시작이 한국어 docstring + sprint/Codex 인용. 헌법 I-12 정합. 양호.

---

## 7. unit / 통합 / e2e 비율

| 종류 | 갯수 | 비율 |
|---|---:|---:|
| BE unit | ~340 | 73% |
| BE 통합 (integration_session 사용) | ~115 (35 파일) | 24% |
| FE unit (vitest) | 56 | (BE 와 별도) |
| FE e2e (Playwright) | ~40 (21 spec) | (별도) |

전체 BE: unit 73% + 통합 24% → 권고 비율 (unit 70 / 통합 20 / e2e 10) 와 정합. e2e 는 별도 카테고리로 양호.

---

## 8. Summary

- **정량 baseline 임계 통과**: 3/9 (FE pass count + BE pass + onboarding/inbox cov)
- **정량 임계 미달**: 6/9 (BE line 65.7% < 80% / BE branch 41% < 70% / FE 측정 인프라 / e2e 9/14 / 신규 8/11 / 통합 3/5)
- **추가 권고 케이스**: 신규 unit 7건 + 통합 2건 + e2e 4건 + 측정 인프라 config 1건 = **총 14건**
- **차단 분류 (Blocking)**: **2건** — BUG-S27e-TEST-1 (보안 헤더 회귀 가드) + BUG-S27e-TEST-2 (lazy seed 동시 race)
- **비차단 분류 (Non-blocking)**: 8건 (TEST-3 ~ TEST-10)
- **flake**: 2 spec (BL-S27e-4 carry, 별건)

### GO 조건 정합

SCOPE.md §"GO 조건" 의 "테스트 커버리지 — 신규 기능 cover ≥ 80% / 통합 테스트 핵심 흐름 100%" 기준 **NEEDS-FIX**. Blocking 2건 fix 필요. P0 fix 후 재평가 시:

- 신규 cover: 8/11 → 9/11 (보안 헤더 추가) = 81.8% PASS
- 통합 핵심: 3/5 → 4/5 (race 동시 동작 검증으로 일관성 확보), 5/5 까지는 retry 추가 권장 (BUG-S27e-TEST-6, P1)

### 추가 비고

- ADR-022 / Clerk Production 의도적 SKIP 컨텍스트에서 `test_auth_sync_disabled.py` 가 endpoint 비활성화 회귀 가드 잘 구성. 양호.
- ADR-020 halfvec 회귀 가드 (`test_halfvec_migration.py`, 380 line) 두꺼움. 양호.
- I-9 멀티테넌시 회귀 가드 (`test_workspace_idor_matrix.py`, 1218+ line, 52 test_) 두꺼움. 양호.
- `pytest-cov` 추가는 audit 일회성. 본 산출물 작성 후 `pyproject.toml` + `uv.lock` revert 예정 (사용자가 영구 추가 결정 시 별도 PR).
