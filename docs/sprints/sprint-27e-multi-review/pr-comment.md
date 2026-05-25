# Sprint 27e — 4-Reviewer Multi-Agent Audit

> 보안 / 성능 / 테스트커버리지 / 아키텍처 4 전문 reviewer 의 통합 감사. Sprint 27d (product/UX GO 8.02) 후속 기술 deep audit. baseline `1b24898`.

## Verdict: **NEEDS-FIX** — 차단 결함 6건 fix 후 GO

| Reviewer | 차단 | 비차단 | 합계 |
|---|---:|---:|---:|
| 보안 | 4 (P0×2 deps + P1×2 JWT/cron) | 7 | 11 |
| 성능 | 0 | 15 (P1×5 + P2×6 + P3×4) | 15 |
| 테스트 | 2 (보안헤더 가드 + race) | 8 + 추가 권고 14 | 10 |
| 아키텍처 | 0 | 7 (P1×1 + P2×3 + P3×3) | 7 |
| **합계** | **6** | **37** | **43** |

**GO 조건 4/4 미충족 → NEEDS-FIX**. 차단 6건 fix (~4h) 후 외부 5명 dogfooding 또는 production 진입.

---

## 🔴 차단 결함 (6건) — production 진입 전 fix 필수

### 🔴 BUG-S27e-SEC-1 — `@clerk/nextjs@7.0.8` middleware route protection bypass (Blocking, **critical**)

**file**: `frontend/package.json` + `frontend/src/proxy.ts:15-19`
**reviewer**: 보안 전문가
**OWASP**: A06:2021 Vulnerable and Outdated Components
**Advisory**: GHSA-vqx2-fgx2-5wq9 (critical)

```text
critical  Official Clerk JavaScript SDKs: Middleware-based route protection bypass
Package: @clerk/nextjs   Vulnerable: >=7.0.0 <7.2.1   Patched: >=7.2.1
```

본 프로젝트 `frontend/src/proxy.ts`:

```ts
export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect();   // ← advisory 가 지시하는 우회 패턴 직격
  }
});
```

**권장 fix**:

```bash
cd frontend && pnpm up @clerk/nextjs@^7.2.1
pnpm audit | grep -E "critical|GHSA-vqx2"   # 0건 확인
```

**영향도**: 외부 사용자 1명이 advisory PoC 익히면 dashboard / 메모 / 회의 / 액션 등 protected route 인증 우회 가능. Personal/Team 무관.

**회귀 가드**: `pnpm audit --audit-level critical` nightly CI + e2e 미인증 cookie 로 `/dashboard` 접근 시 sign-in redirect spec.

---

### 🔴 BUG-S27e-SEC-2 — `next@16.2.2` 다중 high CVE (Blocking)

**file**: `frontend/package.json`
**reviewer**: 보안 전문가
**OWASP**: A06:2021

```text
high  Next.js Middleware/Proxy bypass in App Router + Pages
high  Next.js SSRF
high  Next.js DoS in Server Components
low   Cache poisoning (RSC cache-busting collision)
Vulnerable: >=16.0.0 <16.2.5   Patched: 16.2.5
```

**권장 fix**:

```bash
cd frontend && pnpm up next@^16.2.5
pnpm build && pnpm test
```

**영향도**: SEC-1 의 middleware bypass + SSRF 결합 시 인증 우회 후 내부 cloud metadata (169.254.169.254) 노출 가능. BE RBAC 가드는 정적 분석 100% 적용이라 BE 데이터 leak 까지는 아니지만 FE 라우트 보호 = 0.

---

### 🔴 BUG-S27e-SEC-3 — JWT issuer/audience 검증 누락 (Blocking, ADR-024 cutover 직격)

**file**: `backend/src/auth/dependencies.py:111-124`
**reviewer**: 보안 전문가
**OWASP**: A02 + A07

```python
# 현 코드
claims = jwt.decode(
    token,
    signing_key.key,
    algorithms=["RS256"],
    options={"verify_aud": False},  # ❌ audience 검증 비활성
)
# issuer 미전달 → iss claim 검증 안 됨
```

JWKS URL 은 `https://creative-boxer-79.clerk.accounts.dev/.well-known/jwks.json` 하드코드. ADR-024 (Clerk Production supersedes ADR-022) cutover 시 swap 필요.

**권장 fix**:

```python
# core/config.py
class Settings(BaseSettings):
    clerk_jwks_url: str
    clerk_jwt_audience: str | None = None
    clerk_jwt_issuer: str

# auth/dependencies.py
claims = jwt.decode(
    token,
    signing_key.key,
    algorithms=["RS256"],
    audience=settings.clerk_jwt_audience,
    issuer=settings.clerk_jwt_issuer,
)
```

**영향도**: ADR-024 production 전환 직후 dev token / 다른 Clerk 앱 token cross-account 통과 가능. 외부 5명 dogfooding (동일 instance) 자체엔 영향 적으나 cutover 직격.

**회귀 가드**: `tests/auth/test_jwt_verification.py` — wrong issuer / wrong aud token reject.

---

### 🔴 BUG-S27e-SEC-4 — `cron_secret_token` 평문 fallback (Blocking, **data loss risk**)

**file**: `backend/src/core/config.py:39`
**reviewer**: 보안 전문가
**OWASP**: A05:2021 Security Misconfiguration

```python
# 현 코드
cron_secret_token: SecretStr = SecretStr("dev-cron-secret-CHANGE-ME-IN-PROD")
```

production env 누락 시:

```bash
curl -X POST \
  -H "X-Cron-Token: dev-cron-secret-CHANGE-ME-IN-PROD" \
  https://kairos-api-imrsiyibaa-du.a.run.app/api/v1/admin/memory/r2-cleanup?days=365
```

→ 모든 사용자 voice 메모 R2 객체 무차별 삭제. audit log 없음.

**권장 fix**:

```python
# core/config.py
cron_secret_token: SecretStr  # default 제거 — 필수 env

@field_validator("cron_secret_token")
@classmethod
def _no_default_in_prod(cls, v: SecretStr, info: ValidationInfo) -> SecretStr:
    if info.data.get("app_env") == "production" and "CHANGE-ME" in v.get_secret_value():
        raise ValueError("CRON_SECRET_TOKEN must be set in production")
    return v
```

**영향도**: production 배포 시 env miss 1회 누락 → 다인 voice 메모 데이터 손실. **단일 사용자가 다인 데이터 파괴 가능 → 차단**.

**회귀 가드**: `tests/core/test_config_validation.py` + lifespan 진입 시 기본값 매치 startup fail.

---

### 🔴 BUG-S27e-TEST-1 — Sprint 27d 보안 헤더 4종 회귀 가드 0건 (Blocking)

**file**: `backend/src/main.py:103-108` + `frontend/next.config.ts:5-15` (코드는 OK, 테스트가 없음)
**reviewer**: 테스트 커버리지

Sprint 27d BUG-S27d-4 fix 가 4종 헤더 (`X-Frame-Options=DENY`, `X-Content-Type-Options=nosniff`, `Referrer-Policy=strict-origin-when-cross-origin`, `Permissions-Policy=camera=()...`) 추가. **`grep -rn "X-Frame-Options\|Referrer-Policy" backend/tests frontend/e2e` 모두 hit 없음**. middleware reorder / next.config.ts 정리 시 헤더 누락이 CI 에서 감지 불가.

**권장 fix — BE pytest 2 case**:

```python
# backend/tests/test_security_hardening.py
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

@pytest.mark.asyncio
async def test_security_headers_present_on_404(public_client):
    """404 응답에서도 헤더가 보장되어야 한다."""
    response = await public_client.get("/api/v1/nonexistent-path")
    assert response.status_code == 404
    assert response.headers.get("x-frame-options") == "DENY"
```

**권장 fix — FE e2e**:

```typescript
// frontend/e2e/tests/security-headers.spec.ts
test("home / page returns 4 security headers", async ({ page }) => {
  const response = await page.goto("/");
  const headers = response!.headers();
  expect(headers["x-frame-options"]).toBe("DENY");
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  expect(headers["permissions-policy"]).toContain("camera=()");
});
```

**영향도**: 외부 5명 dogfooding 진입 후 clickjacking / MIME sniffing 회귀 잡을 방법 없음.

---

### 🔴 BUG-S27e-TEST-2 — lazy seed 진정한 concurrent race 미검증 (Blocking)

**file**: `backend/tests/auth/test_personal_workspace_race.py` (자체 주석 "sequential 만 검증")
**reviewer**: 테스트 커버리지

Sprint 27c BL-S27c-1 lazy seed fix (`auth/dependencies.py:158-221`) 의 진정한 동시 race 가 미검증. 현 spec 은 sequential INSERT idempotency 만. asyncio.gather 별개 connection 케이스 carry-over.

**권장 fix**:

```python
# backend/tests/auth/test_personal_workspace_race_concurrent.py (신설)
@pytest.mark.asyncio
async def test_lazy_seed_concurrent_race(db_session_factory, sample_clerk_token):
    """별개 connection 동시 lazy seed → Personal workspace 1개만 생성 (회귀 가드)."""
    async def call_get_current_user():
        async with db_session_factory() as session:
            user_repo = UserRepository(session)
            ws_repo = WorkspaceRepository(session)
            await _resolve_user_and_seed(sample_clerk_token, user_repo, ws_repo)

    # 5개 task 동시 실행 (asyncio.gather)
    await asyncio.gather(*[call_get_current_user() for _ in range(5)])

    # then: Personal workspace 1개만 생성
    async with db_session_factory() as session:
        ws_repo = WorkspaceRepository(session)
        wss = await ws_repo.list_personal_for_user(user_id)
        assert len(wss) == 1, f"Expected 1 Personal workspace, got {len(wss)}"
```

**영향도**: 동시 5 요청 (FE fan-out 패턴) 시 Personal workspace 중복 생성 회귀 잡을 방법 없음. Sprint 27c P0 fix 의 회귀 무방비.

---

## ⚙️ 차단 결함 fix 순서 권고

| # | ID | 작업 | 예상 |
|:-:|---|---|:-:|
| 1 | SEC-1 + SEC-2 | `pnpm up @clerk/nextjs@^7.2.1 next@^16.2.5` + build | 1h |
| 2 | SEC-4 | `cron_secret_token` default 제거 + validator | 30분 |
| 3 | SEC-3 | JWT audience + issuer + Settings + 2 case test | 1h |
| 4 | TEST-1 | BE pytest 2 case + FE e2e 1 spec | 1h |
| 5 | TEST-2 | asyncio.gather concurrent integration | 1h |

**총 ~ 4h**. 단일 PR 권장.

---

## 🟡 비차단 (37건) — BL-S27e-A~F 6 묶음 carry

<details>
<summary>BL-S27e-A — 보안 hygiene (SEC-5/6/7/11)</summary>

- BUG-S27e-SEC-5: audit_events 테이블 신설 (role 변경 / member remove / invite create / workspace settings 4 endpoint)
- BUG-S27e-SEC-6: rate-limit (slowapi — RAG ≤ 30/min, upload ≤ 10/min, capture ≤ 60/min)
- BUG-S27e-SEC-7: CORS allow_methods + allow_headers 화이트리스트
- BUG-S27e-SEC-11: `logging.warning(authz_failure)` + Cloud Run log alert (ADR-022 재검토 동반)
</details>

<details>
<summary>BL-S27e-B — 보안 hardening (SEC-8/9/10)</summary>

- BUG-S27e-SEC-8: RAG prompt `<<<SOURCE_BLOCK>>>` 구분자 + system prompt 명시
- BUG-S27e-SEC-9: R2 file_key filename slugify + NFC + 길이 200
- BUG-S27e-SEC-10: `astral-sh/setup-uv@v3` SHA 통일
</details>

<details>
<summary>BL-S27e-C — 성능 P1 cluster (PERF-1~5) — 외부 진입 후 일정 규모 즉시 발현</summary>

- BUG-S27e-PERF-1: R2 boto3 client singleton (BL-008 정량화)
- BUG-S27e-PERF-2: meetings/actions/inbox `workspace_id` composite covering 인덱스 3건 (alembic)
- BUG-S27e-PERF-3: upload `await file.read()` → streaming `upload_fileobj` (OOM 위험)
- BUG-S27e-PERF-4: Gemini `asyncio.wait_for(timeout=30)` + tenacity + half-open circuit breaker
- BUG-S27e-PERF-5: SSE `request.is_disconnected()` per-yield check
</details>

<details>
<summary>BL-S27e-D — 성능 P2 cluster (PERF-6~11)</summary>

- BUG-S27e-PERF-6: scoped cache invalidation (`sources::jsonb @>`) — promote ws 전체 wipe 회피
- BUG-S27e-PERF-7: `MemoryQueryEmbeddingCache` 7일 cleanup cron + partial expression index
- BUG-S27e-PERF-8: `embedding_chunks.created_at` partial expression index
- BUG-S27e-PERF-9: inbox `find_by_ids_in_workspace(IN clause)` N+1 해소
- BUG-S27e-PERF-10: `next/font/local` self-host (LCP -200~500ms)
- BUG-S27e-PERF-11: tiptap + dnd-kit `next/dynamic({ ssr: false })`
</details>

<details>
<summary>BL-S27e-E — 테스트 + 정량 (TEST-3~10 + 권고 케이스 14)</summary>

- BUG-S27e-TEST-3: `vitest.config.ts` `coverage.include: ['src/**']` + FE service/util/store unit
- BUG-S27e-TEST-4: workspaces 모듈 branch 4% → invite_service branch case
- BUG-S27e-TEST-5: invite accept happy-path e2e (`invite-accept.spec.ts`)
- BUG-S27e-TEST-6: 회의 retry e2e (M-3 carry)
- BUG-S27e-TEST-7: upload mime e2e (proxy + presigned)
- BUG-S27e-TEST-8/9/10: 거대 입력 / 유니코드 / Personal+Team 동시 운영 통합
</details>

<details>
<summary>BL-S27e-F — 아키텍처 + governance (ARCH-1~7)</summary>

- BUG-S27e-ARCH-1: OnboardingService I-1 위반 — Repository 경유 + typed `session.exec()`
- BUG-S27e-ARCH-2: `services/transcription.py` DTO 분리 + 호출자 ORM 변환
- BUG-S27e-ARCH-3: `backend/src/audit/` 신설 (16 모듈 — common → audit 분리)
- BUG-S27e-ARCH-4: 헌법 §4.1/§4.3 모듈 수 갱신 (BE 13→15 + FE 11→14) + directory-map.md
- BUG-S27e-ARCH-5: `RagService._advance_onboarding` Demeter — hook callable 주입 (ARCH-1 해소 동반)
- BUG-S27e-ARCH-6: `common/promote_helpers.py` 확장 (3 helper) — 5 도메인 promote 50 LOC 미만
- BUG-S27e-ARCH-7: BL-005 "✅ 완료 (Sprint 19 PR #1 C10)" 마크
</details>

---

## ✅ Sprint 27d 대비 신규성 (regression 없음 verified)

- 27d PASS 재확인: IDOR (BE RBAC 100%), upload mime, 보안 헤더 4종, RAG cross-tenant (visibility filter).
- **신규 발견**: dependency CVE 2건 (npm 생태계 신규 advisory) + JWT 검증 미흡 + cron 평문 + 보안 헤더 회귀 가드 부재 + lazy seed concurrent race 미검증 + R2 singleton (BL-008 정량) + Gemini timeout + DB workspace_id 인덱스.
- 27d verdict (GO 8.02 product) 와 본 verdict (NEEDS-FIX 기술) 충돌 X.

---

## 산출물

- `docs/sprints/sprint-27e-multi-review/security-findings.md`
- `docs/sprints/sprint-27e-multi-review/performance-findings.md`
- `docs/sprints/sprint-27e-multi-review/test-coverage-findings.md`
- `docs/sprints/sprint-27e-multi-review/architecture-findings.md`
- `docs/sprints/sprint-27e-multi-review/integrated-report.md`
- `docs/sprints/sprint-27e-multi-review/report.html`
