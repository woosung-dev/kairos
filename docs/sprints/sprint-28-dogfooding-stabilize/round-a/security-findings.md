# Sprint 28 Round A — Security 정적 audit

> baseline `3e41893` · Sprint 27e Round 1 PR #109 + Round 2 PR #110 + QA dynamic verify PR #111 머지 후 main · branch `sprint-28/dogfooding-stabilize` · 검사 일시 2026-05-25 KST · 환경: 정적 분석 + `pnpm audit` + `uv lock --check` + 26 pytest run, FE/BE 실 동작 호출 X (dynamic verify 는 Round B 담당) · production/Sentry/Clerk Production audit SKIP (사용자 정책)
>
> 도구: Read / Grep / pnpm audit (JSON+human) / uv sync --dry-run / uv lock --check / 정적 RBAC 그래프 · MCP Playwright / browser / live network 호출 X (Round A 제약)

---

## 1. Sprint 27 carry list 자기 영역 verify

Sprint 27e Round 1 (PR #109) + Round 2 (PR #110) + QA dynamic verify (PR #111) 로 fix 적용된 6 + 4 차단 결함을 모두 file:line 재검증.

| ID | Sprint 27 분류 | Sprint 28 검증 (file:line + 도구) | 결과 |
|---|---|---|:-:|
| **BUG-S27e-SEC-1** (Clerk CVE GHSA-vqx2-fgx2-5wq9) | P0 차단 → Round 1 RESOLVED | `frontend/package.json:19` `"@clerk/nextjs": "^7.4.1"` (≥7.2.1 patched) + `pnpm audit --audit-level critical` = **0 critical** | ✅ verified |
| **BUG-S27e-SEC-2** (Next.js 16.2.2 → 16.2.5+ 다중 CVE) | P0 차단 → Round 1 RESOLVED | `frontend/package.json:33,56` `"next": "16.2.6"` + `"eslint-config-next": "16.2.6"` (≥16.2.5 patched) + middleware/Proxy bypass + SSRF advisory 모두 사라짐 | ✅ verified |
| **BUG-S27e-SEC-3** (JWT issuer + audience 검증) | P1 차단 → Round 1 RESOLVED | `backend/src/auth/dependencies.py:117-129` `decode_kwargs` 빌더 + `issuer=settings.clerk_jwt_issuer` 강제 + `InvalidIssuerError` 별도 catch (line 142-144) + `InvalidAudienceError` (line 145-146) + `core/config.py:37,39` Settings 추가 | ✅ verified |
| **BUG-S27e-SEC-4** (cron token 평문 fallback) | P1 차단 → Round 1 RESOLVED | `backend/src/core/config.py:8` `_CRON_TOKEN_DEV_FALLBACK` 상수화 + `:92-109` `_validate_cron_token` validator + memory `admin_router.py:22` `hmac.compare_digest` constant-time 유지 | ✅ verified |
| **BUG-S27e-TEST-1** (보안 헤더 회귀 가드) | P0 차단 → Round 1 BE RESOLVED + Round 2 FE CI gate `BUG-S27e-TEST-r2-1` 보강 | BE 회귀 가드 `tests/test_security_hardening.py::TestSecurityHeadersRegression` 2/2 PASS / FE `e2e/tests/security-headers.spec.ts` 49 line 정합 (Round 2 verify) | ✅ verified (BE) |
| **BUG-S27e-TEST-2** (lazy seed concurrent race) | P0 차단 → Round 1 RESOLVED | `backend/src/auth/dependencies.py:193-206` raw `INSERT ... ON CONFLICT (clerk_id) DO NOTHING` + tests `auth/test_personal_workspace_race_concurrent.py` N=5/10 testcontainers PASS | ✅ verified |
| **BUG-S27e-SEC-r2-2** (JWT non-dev 우회 차단) | Round 2 차단 (cutover 직전) → Round 2 PR #110 RESOLVED | `core/config.py:84-88` `_is_non_dev_env(app_env, environment)` 통합 staticmethod + `:114-125` `_no_dev_issuer_in_non_dev` validator (staging 도 거부) + `:129-141` `_require_audience_in_non_dev` validator (None default 거부) | ✅ verified |
| **BUG-S27e-SEC-r2-3** (cron token 약한 token + staging 우회) | Round 2 차단 (cutover 직전) → Round 2 PR #110 RESOLVED | `core/config.py:92-109` `_validate_cron_token` validator — `_is_non_dev_env` + dev fallback 거부 + `len(val) < 32` 명시 raise | ✅ verified |
| **BUG-S27e-SEC-r2-4** (`_is_production` vs validator 분기 inconsistency) | Round 2 차단 (cutover 직전) → Round 2 PR #110 RESOLVED | `core/config.py:84-88` `_is_non_dev_env` 통합 + `:18-21,59` `environment` 필드를 `cron_secret_token` 보다 앞에 배치 (Pydantic V2 field_validator 정의 순서 의존) — validator + main.py 분기 통합 | ✅ verified (main.py 의 `_is_production` 은 OR + lower 유지하나 같은 OR 패턴) |
| **BUG-QA-1** (lazy seed fast path) | Round 2 Post-Merge dogfooding-blocker → PR #111 RESOLVED | `auth/dependencies.py:185-186` `if user is not None and user.onboarding_step >= 1: return user` — onboarding_step ≥ 1 user 는 lazy seed 3 INSERT 모두 skip | ✅ verified (인증·보안 측면 — race-safe 유지 + fast path 안전) |
| **BUG-QA-2** (JWT 1분 expiry leeway) | Round 2 Post-Merge dogfooding-blocker → PR #111 RESOLVED | `auth/dependencies.py:123-127` `"leeway": 10` decode_kwargs 명시. 10s clock skew 허용. token 만료 직후 short window 통과 → 정상 사용자 401 다발 회복 | ✅ verified |
| BL-S27e-G | Round 2 RESOLVED 마크 (REFACTORING-BACKLOG.md:174-184) | `docs/REFACTORING-BACKLOG.md:174` `BL-S27e-G — Production cutover hardening (...) ✅ 완료 (Sprint 27e Round 2, 2026-05-25)` 명시 — Sprint 27 carry list 와 정합 | ✅ verified |

**verify 합계**: 12/12 PASS (회귀 0건). pytest 4 파일 26/26 PASS (3.35s).

```
$ cd backend && uv run pytest -q tests/test_config.py tests/auth/test_jwt_verification.py \
    tests/test_security_hardening.py tests/auth/test_personal_workspace_race_concurrent.py
26 passed, 35 warnings in 3.35s
```

---

## 2. 신규 발견 매트릭스

신규 = Sprint 27 audit (Round 1/2/QA verify) 가 catch 못 한 영역에서 본 audit 가 처음 식별한 보안 위험. 단순 carry (BL-S27e-A/B/H 등) 는 §1/§4 에서 다루고 본 §2 에는 등재하지 않음.

| ID | OWASP | 심각도 (P0/P1/P2/P3) | 차단 | file:line | 발견 | 권장 fix |
|---|---|:-:|:-:|---|---|---|
| **BUG-S28-SEC-1** | A06 | **P1** | NO (CI hygiene, production 안전) | `.github/workflows/test.yml:23,163` + `nightly-e2e.yml:56` + `r2-cleanup.yml:33` | CI 의 `uv sync` 호출이 모두 **bare** — production Dockerfile 만 `uv sync --frozen --no-dev` 적용. BL-S27e-H carry (Sprint 27e Round 2 r2-10) 권고가 production-side 만 cover, CI drift 감지 갭. `uv.lock` 변경 미반영 PR 가 CI 통과 가능 + transitive major bump CI 무감지. | `uv sync --frozen` (또는 `--locked`) 강제 + 별도 step `uv lock --check` 추가 (lock-pyproject mismatch fail-fast) |
| **BUG-S28-SEC-2** | A08 | P2 | NO | `.github/workflows/r2-cleanup.yml:28` `astral-sh/setup-uv@v3` | Sprint 27e SEC-10 BL-S27e-B carry 의 실 상태 verify. 다른 yml 3개 (`test.yml:18,157`, `nightly-e2e.yml:50`, `deploy.yml:30,34,74`) 는 모두 SHA pin 적용 (`@e4db8464...` 등) — r2-cleanup 만 tag pin 잔존. R2 bucket destructive op 권한 가진 워크플로우 = supply chain compromise blast radius 큼 (delete_object). | `astral-sh/setup-uv@e4db8464a088ece1b920f60402e813ea4de65b8f  # v4` 로 통일 (다른 yml 패턴 복제) |
| **BUG-S28-SEC-3** | A09 | P2 | NO | `backend/src/auth/dependencies.py:140-150` | JWT 검증 실패 6 경로 (ExpiredSignature / InvalidIssuer / InvalidAudience / InvalidToken / 일반 Exception / 토큰 형식) 가 모두 `raise HTTPException` 만, log 출력 0. 외부 5명 진입 시 `InvalidIssuerError` (cross-account 시도) / `InvalidAudienceError` (audience 위조) / `ExpiredSignatureError` 빈도 forensic 0. Sentry SKIP path (ADR-022) 의 r2-7 (Round 2 P2 carry) 의 진짜 발현 지점 — 별도 P2 등재 가치. | `logger = logging.getLogger(__name__)` module-level + 4 except 분기에 `logger.warning("auth.jwt.invalid_issuer", extra={"actor": ...})` 1 line × 4. `auth.jwt.*` prefix 로 Cloud Run log filter 자동 분류 |
| **BUG-S28-SEC-4** | A05 | P3 | NO | `backend/src/core/config.py:24` + `:70` `cors_origins: str` | `cors_origins` 가 단순 csv string 으로 split, validator 없음. (a) trailing space (b) trailing slash (c) scheme 없는 host (`localhost:3000` vs `http://localhost:3000`) (d) `*` / `null` 같은 위험 값 (e) 빈 string 모두 통과. `ALLOWED_ORIGINS = [o.strip()...]` 의 strip() 외 0 sanitize → SEC-r2-11 carry 실 상태. `_attach_cors:126` 에서 `origin in ALLOWED_ORIGINS` 단순 비교라 trailing slash 1 char 차이로 wildcard 통과 / 차단 다 가능. | `@field_validator("cors_origins")` — 각 항목 `urlparse` 검증 + scheme + host 분리 + `*` / `null` 거부 |
| **BUG-S28-SEC-5** | A04 | P3 | NO | `backend/src/common/r2.py:41,46,100` | presigned URL `ExpiresIn=3600` (1시간) 하드코드 — 업로드 path 와 다운로드 path 동일. 업로드는 1시간 (브라우저 retry / 큰 파일 wave 허용) 합리적, **다운로드 URL 의 1시간 = 유출 시 1시간 무차별 fetch 가능** (음성 메모 / 회의 transcript 가 외부 캐시 / 로그 / Sentry breadcrumb 새면 1h 사용). 별도 hardcode → 환경별 조정 불가. | `get_download_url(...)` 의 `ExpiresIn` 을 settings 또는 caller-supplied (default 300s 권장, 미디어 stream 도 충분) 로 분리 + caller 가 명시 short-lived URL 권한 가짐 |
| **BUG-S28-SEC-6** | A09 (정책 errata) | P3 | NO | `backend/src/main.py:46-55` `_scrub_pii_hook` + `:59-67` Sentry init | `_scrub_pii_hook` 가 Sentry `before_send` 에서 `request["data"]` 의 dict 필드만 scrub — `transcript / email / password / audio_url`. **(a) URL query string 내 `?audio_url=...` / `?email=...` 미scrub** (b) `event["extra"]` / `event["breadcrumbs"]` / `event["contexts"]` 미scrub (c) `request.get("data")` 가 list (multipart) 또는 string body 면 dict 가정 fail (d) `event["user"]` 만 email/ip scrub — `event["request"]["headers"]["Authorization"]` JWT raw 통과 가능. ADR-022 Sentry SKIP 정책 상태에선 영향 0 — but `sentry_dsn` 환경에 한 번이라도 설정되는 순간 발현. SEC-11 carry 의 hidden risk. | `before_send` hook 보강 — URL query 정규화 + `event["extra"]/["contexts"]/["breadcrumbs"]` 동일 4 field scrub + Authorization header redact (`[REDACTED]` 치환) + body list/string fallback |
| **BUG-S28-SEC-7** | A07 | P3 | NO | `backend/src/auth/dependencies.py:23-71` `_JWT_CLAIMS_CACHE` | JWT cache (Sprint 24 Wave 2 추가) 의 hash key = `sha256(token)`. Codex F-1 fix 로 cache TTL ≤ token exp 보장됨 (line 64-71). 그러나 **token revocation (Clerk session 로그아웃) 시점 BE 측 revoke 신호 없음** — 같은 token 의 60s TTL 안 캐시는 hit 되어 통과. dev exp = 60s 라 영향 작으나, production cutover (ADR-024) 후 Clerk Production exp 가 1h 등 길어지면 logout → 60s cache TTL 남는 동안 stale token 통과 가능. r2-8 (Round 2 P2 JWT cache DoS) 와 별개 risk. | (a) cache TTL 을 `min(60s, exp-now, 30s)` 로 더 짧게 + (b) Clerk webhook ADR-024 cutover 시 `session.revoked` 이벤트 hook 으로 cache evict (ADR-024 GA 시점 함께) |

---

## 3. 차단 결함 상세

**차단 0건.** §1 verify 12/12 PASS + §2 신규 7건 모두 P1/P2/P3 비차단 (외부 5명 dogfooding 진입 자체에는 영향 없음).

가장 우선 처리 권고는 **BUG-S28-SEC-1** (CI `--frozen` 강제, ~10분 fix). dep drift / supply chain attack 의 첫 방벽이 production Dockerfile 만 가지고 CI 가 없어 CI 패스 의미가 약함. 본 sprint 안 처리 권고.

---

## 4. 비차단 carry 권고 (BL-S28-* 신규 / BL-S27e-* 갱신)

| BL ID | 묶음 | 출처 | 권고 |
|---|---|---|---|
| **BL-S28-SEC-A 신규** | CI hygiene | BUG-S28-SEC-1 | BL-S27e-H 의 production 측 권고 + 본 sprint CI 측 권고를 단일 묶음. `uv sync --frozen` (또는 `--locked`) + `uv lock --check` step + (선택) `pnpm install --frozen-lockfile` (이미 적용 verified) 일관성 점검 — 10분 fix |
| **BL-S28-SEC-B 신규** | Supply chain | BUG-S28-SEC-2 | BL-S27e-B (SEC-10) carry 의 실 상태 ([r2-cleanup.yml:28] 1줄). 다른 yml 3개 패턴 복제 — 5분 fix |
| **BL-S28-SEC-C 신규** | A09 forensic | BUG-S28-SEC-3 | BL-S27e-A (SEC-11) carry 의 진짜 발현 지점. JWT 4 except 분기에 `logger.warning("auth.jwt.*", extra={...})` 추가 — 10분 fix + pytest 4 case |
| **BL-S28-SEC-D 신규** | CORS hardening | BUG-S28-SEC-4 | SEC-r2-11 carry 의 실 상태. `cors_origins` field_validator + `urlparse` 검증 + `*` / `null` 거부 — 15분 fix |
| **BL-S28-SEC-E 신규** | R2 presigned URL hardening | BUG-S28-SEC-5 | 1h hardcode 분리. `get_download_url(file_key, expires_in=300)` 시그니처 변경 + 호출자 4곳 회귀 검증 — 30분 fix |
| **BL-S28-SEC-F 신규** | Sentry PII scrub 강화 | BUG-S28-SEC-6 | ADR-022 Sentry SKIP 유지 정책 하에선 발현 0, but cutover 시점 prerequisite. `_scrub_pii_hook` 보강 — 20분 fix + pytest 6 case (각 leak path) |
| **BL-S28-SEC-G 신규** | JWT cache revocation | BUG-S28-SEC-7 | ADR-024 Clerk Production cutover 직격 결함 (production exp 길어지면 발현). BL-S27e-A audit_events / SEC-11 logging 와 함께 묶음 — 30분 fix (cache TTL 단축) + Sprint 29+ Clerk webhook hook (ADR-024 deferred) |
| **BL-S27e-A 갱신** | 보안 hygiene cluster | Sprint 27e Round 1+2 carry | SEC-5 audit_events + SEC-6 rate-limit + SEC-7 CORS allow_methods/headers + SEC-11 logging.warning + r2-6 admin audit + r2-7 JWT 실패 log. **본 sprint 의 BL-S28-SEC-C/D 가 일부 흡수** (logger.warning JWT + cors validator) — 잔여 audit_events 도메인 신설 + slowapi rate-limit + CORS allow_methods/headers 화이트리스트 ~1d |
| **BL-S27e-B 갱신** | 보안 hardening | Sprint 27e Round 1+2 carry | SEC-8 prompt 구분자 + r2-9 3 prompt 모두 + SEC-9 filename slugify + SEC-10 GHA SHA pin. **본 sprint 의 BL-S28-SEC-B 가 SEC-10 흡수**. 잔여 prompt 구분자 3 prompt + filename slugify ~30분 |
| **BL-S27e-H 갱신** | backend dep upper-bound | Sprint 27e Round 2 r2-10 | **본 sprint 의 BL-S28-SEC-A 가 CI 측 일부 흡수**. production Dockerfile (`uv sync --frozen --no-dev`) 측 verify 완료. 잔여 = pyproject.toml upper-bound 명시 (17 dep) 또는 옵션 (a) `uv.lock` 만 신뢰 + CI `--frozen` 강제 — 본 sprint BL-S28-SEC-A 처리 시 `(c) uv lock --check` 까지 자동 해소 |

---

## 5. Summary

- 차단 0건 (외부 5명 dogfooding 진입 self 차단 0)
- 신규 발견 P1 1건 (CI `--frozen` 미강제) / P2 2건 (GHA SHA pin r2-cleanup + JWT 실패 log) / P3 4건 (CORS validator, R2 expiry hardcode, Sentry PII scrub 잔재, JWT cache revocation)
- Round 27e carry 자기 영역 verify **12/12 PASS** (회귀 0건) — `pnpm audit critical 0` + 26 pytest PASS + 헌법 §4.1/§4.3 모듈 수 정합 verified
- ADR-024 cutover hardening 4건 모두 RESOLVED 재확인 (PR #110)
- BL-S27e-G RESOLVED 마크 verified (REFACTORING-BACKLOG.md:174)

### 외부 5명 dogfooding 진입 verdict (Security only) — **GO**

근거:
- Round 27 차단 6 + Round 2 차단 3 + QA verify 차단 2 모두 RESOLVED-verified
- 신규 7건 모두 P1/P2/P3 비차단 (production safety net + Sentry-disabled-path + CI hygiene 영역)
- production Dockerfile (`uv sync --frozen --no-dev`) 와 메인 보안 모델 (Clerk JWT issuer+audience + cron token 32B + 보안 헤더 4종 + rate-safe lazy seed) 모두 활성 + 회귀 가드 적용
- 본 audit 의 모든 신규 결함 = "외부 5명 진입 시 추가 발견" 이 아닌 "hygiene + forensic + cutover prerequisite" 영역

### 권고

1. **본 sprint 안 처리 권고** (총 ~1h 합산):
   - **BUG-S28-SEC-1** CI `uv sync --frozen` + `uv lock --check` step — 10분 (production parity)
   - **BUG-S28-SEC-2** `astral-sh/setup-uv@<SHA>` — 5분 (SHA pin 통일)
   - **BUG-S28-SEC-3** JWT 4 except logger.warning — 10분 + pytest 4 case (forensic baseline)
   - **BUG-S28-SEC-4** `cors_origins` field_validator — 15분 (defense-in-depth)
2. **Sprint 29+ carry** (외부 5명 진입 후, cutover 직전):
   - BUG-S28-SEC-5 R2 download URL expiry 분리
   - BUG-S28-SEC-6 Sentry `_scrub_pii_hook` 보강 (ADR-022 retract 시점 prerequisite)
   - BUG-S28-SEC-7 JWT cache revocation hook (ADR-024 cutover 시점)
3. **BL-S27e-A** (audit_events + rate-limit) — architecture deepening sprint 동반 진행 권고 (1d) — 외부 5명 진입 후 abuse 탐지 baseline

### Sprint 27e Round 1+2 audit 대비 본 audit 의 신규성

- Sprint 27e 가 catch 못 한 **CI 측 dep drift 갭** (BL-S27e-H 가 production Dockerfile 만 verified, CI bare `uv sync` 검출)
- Sprint 27e SEC-11 carry 의 진짜 발현 지점 verify — JWT 4 except 분기 log 0 (auth/dependencies.py:140-150)
- Sprint 27e SEC-10 carry 의 실 상태 verify — `r2-cleanup.yml:28` 1줄만 미pin 잔존
- Sprint 27e SEC-r2-11 (CORS 형식 검증) carry 의 실 상태 verify — `cors_origins` field_validator 0개
- R2 presigned URL expiry 1h 다운로드 path 별도 발견 (upload 와 동일 hardcode — 본 audit 신규)
- Sentry `_scrub_pii_hook` URL query / breadcrumbs / Authorization header 미scrub — ADR-022 SKIP 정책 하에선 잠재 risk (cutover 시점 prerequisite, 본 audit 신규)
- JWT cache revocation hook 부재 — Clerk Production exp 길어지면 발현 (dev exp 60s 라 영향 0, 본 audit 신규)
