# ADR-022: Clerk webhook SKIP + `/api/v1/users/sync` endpoint 비활성화 (Pre-GA 운영 정책)

> **날짜:** 2026-05-21
> **상태:** Accepted (2026-05-21 Sprint 25 T-SEC-1 commit `d614214` 적용 완료)
> **작성자:** Claude Opus 4.7 (1M context) + 사용자 (정책 결정)
> **관련:** Sprint 25 plan `docs/dev-log/qa/2026-05-21-sprint25-multi-agent-qa/sprint-25-plan.md` · memory `project_gcp_migration_jetaime_dev_done.md` (2026-05-21 GCP 이전 + 사용자 SKIP 결정 lock-in) · `backend/src/auth/router.py` (sync handler 제거) · `backend/src/auth/service.py` (sync_user 메서드 제거) · `backend/src/auth/CONTEXT.md` §5/§6 · 회귀 가드 `backend/tests/auth/test_auth_sync_disabled.py` · ADR-014 Service Boundary
> **워크플로우:** `.ai/templates/workflow.md` Stage 4 (코드) — Stage 1 ADR 산출은 본 ADR 자체

---

## 배경 (Context)

### 사건 트리거 — Sprint 25 Multi-Agent QA (2026-05-21)

Sentinel 페르소나의 적대적 검증에서 BUG-SENTINEL-005 (Critical):
- `POST /api/v1/users/sync` endpoint 가 인증 / Svix 서명 검증 부재
- 임의 페이로드로 user row 생성 또는 기존 row 덮어쓰기 가능 — PoC 실측 200 OK
- production DB 에 더미 row `user_QA20260521_sentinel_test_doNotUse` 잔존 (T-CLEANUP-1 별도 정리)

`backend/src/auth/router.py:24` 에 `# TODO: Svix 서명 검증 추가` 주석이 있었으나 미구현 상태였음 — 라우터 자체는 살아있고 검증만 부재인 채로 production 노출.

### 현 상태 (2026-05-21 기준)

| 항목 | 값 | 비고 |
|---|---|---|
| Clerk 인스턴스 | **Development 만** (`pk_test_*` / `sk_test_*`) | dashboard 에 Production 옵션 없음 (사용자 미발급) |
| Clerk webhook 등록 endpoint | 옛 로컬 ngrok URL + path `/api/webhooks/clerk` | backend 의 `/api/v1/users/sync` 와 path 불일치 → **실제 호출 0건** |
| sync_user 핸들러 동작 흔적 | 0건 (Sprint 5 RBAC 도입 이후 production log 검증) | webhook 미수신 = lazy seed 의 user 동기화로 충분 |
| user.created 동기화 | `auth/dependencies.py:get_current_user` lazy seed (JWT claims 기반) | 첫 인증 요청 시 1회 user row 생성 |
| user.updated 동기화 (이름/이메일 변경) | **stale 허용** | Clerk dashboard 변경이 BE 에 미반영 — 현재 사용자 0건 호소 |
| 사용자 결정 (2026-05-21) | Clerk Production 발급 + webhook 등록 + Svix 검증 추가 **모두 SKIP** | GA launch 시 별도 sprint |

### 옵션 비교

| 옵션 | 작업량 | 보안 영향 | 사용자 결정 |
|---|---|---|---|
| **A (채택). endpoint 비활성화 + 회귀 가드** | 1h (Sprint 25 T-SEC-1) | IDOR 공격면 0 | Pre-GA 결정 정합 |
| B. Svix 검증 즉시 추가 | 4-6h + Clerk webhook 재등록 + dev/prod 분기 | OK, 그러나 webhook 자체가 동작 흔적 0 → 작업가치 낮음 | 결정 후 SKIP |
| C. handler 유지 + 인증 추가 | 2-3h, 부분 fix | endpoint 살아있으면서 mis-config 시 회귀 위험 잔존 | 거부 |

### 자의 결정 라벨

- **AD-CW-1**: endpoint 핸들러 + service 메서드 **완전 제거** (HTTPException raise 가 아닌). 자의 = `app.include_router(auth_router)` 는 유지하되 sync 라우트만 제거 → `/api/v1/users/me`, `/users/me/onboarding` 등 다른 라우트 정상 회귀. dead code 가 IDE/리뷰어 에게 "곧 다시 활성" 신호 전달 위험 차단 (대신 ADR-022 + CONTEXT.md §5 lock-in 으로 의도 명시).
- **AD-CW-2**: 회귀 가드 4 case **TDD 우선** (`tests/auth/test_auth_sync_disabled.py`). 자의 = 단순 핸들러 삭제는 미래 어느 PR 에서든 무심코 부활할 수 있음. POST → 404/405 + `/users/me` 라우트 정상 + `/users` prefix 살아있음 verify. 회귀 시 즉시 fail.
- **AD-CW-3**: ADR-022 + auth/CONTEXT.md §5 불변식 + endpoints.md 의 sync 항목 **strikethrough 표기** (삭제 아님). 자의 = "왜 없는지" 의 archeology context 가 GA launch 시 재도입 결정에 필수. 삭제 시 PR 리뷰어 / 신규 contributor 가 "왜 없는 endpoint 인지" 묻게 되고 reverse-engineer 비용 발생.

---

## 결정 (Decision)

### 1. `/api/v1/users/sync` endpoint 비활성화

`backend/src/auth/router.py`:
- `sync_user` handler 제거
- `Request` import + `get_auth_service` import 제거 (orphan)
- `/me` 핸들러만 유지

`backend/src/auth/service.py`:
- `AuthService.sync_user` 메서드 제거
- `get_or_create_user` (lazy seed 용) + `to_response` 만 유지

`backend/src/auth/CONTEXT.md`:
- §5 핵심 불변식 추가: "Clerk webhook endpoint 부재 — sync handler 제거됨"
- §6 노출 엔드포인트: ~~`POST /sync`~~ strikethrough + Sprint 25 T-SEC-1 reference

### 2. Clerk Production 인스턴스 발급 SKIP

- 사용자 결정 (2026-05-21) — GA launch 시점 별도 sprint
- Development Clerk key (`pk_test_*` / `sk_test_*`) 로 production 운영 유지
- BUG-CASUAL-001 (Clerk dev URL 노출) 은 정책 재분류 (Pre-GA UX 신호 → T-GTM-6 sign-up 페이지 "베타 멤버 전용" 텍스트로 완화)

### 3. user.updated 변경 동기화 = stale 허용

- 사용자가 Clerk dashboard 에서 이름/이메일 변경 시 BE `users.display_name` / `users.email` 갱신 0건
- 호소 0건 (현재 사용자 base 가 작아 영향 미미)
- 호소 발생 시점에 webhook 등록 + Svix 검증 + sync handler 재도입 (별도 sprint)

### 4. 회귀 가드

`backend/tests/auth/test_auth_sync_disabled.py` 4 case:
- `POST /api/v1/users/sync` → 404/405/410
- 빈 본문도 차단
- `/api/v1/users/me` 라우트 정상 (401)
- `/api/v1/users` prefix 자체 살아있음 (다른 라우트 정상)

---

## 결과 (Consequences)

### 긍정

- IDOR 공격면 즉시 0 — 1h 작업으로 BUG-SENTINEL-005 Critical 해소
- 사용자 의도적 SKIP 결정과 코드 일관성 lock-in (회귀 reverse-engineering 비용 차단)
- GA launch 재도입 시 endpoint 재신설 + Svix 검증 + Clerk dashboard webhook 재등록 = atomic step (별도 sprint)

### 부정 (수용)

- user.updated stale — 사용자가 Clerk 에서 이름/이메일 변경 시 BE 미반영. 호소 발생 시점에 본 ADR 재검토.
- "왜 sync endpoint 없는지" 신규 contributor 학습 cost (ADR-022 + CONTEXT.md §5 + endpoints.md strikethrough 로 완화)

### 회수 옵션 (GA launch 시점)

본 ADR 의 결정은 GA launch 시점에 reverse 가능:
1. Clerk Production 인스턴스 발급 (`pk_live_*` / `sk_live_*`)
2. `sync_user` handler + `AuthService.sync_user` 재신설 (Sprint 5 이전 git history 참조)
3. **Svix 서명 검증 의무** (재도입 시 미검증 endpoint 부활 금지 — pre-flight lint 또는 CI gate 권고)
4. Clerk dashboard → Webhooks → Add Endpoint (`https://kairos-api-imrsiyibaa-du.a.run.app/api/v1/users/sync`)
5. `tests/auth/test_auth_sync_disabled.py` 제거 + 신규 `test_auth_sync_with_svix.py` 작성

---

## 관련

- Sprint 25 T-SEC-1 (commit `d614214`) — endpoint 비활성화 + 회귀 가드
- Sprint 25 Multi-Agent QA Sentinel BUG-SENTINEL-005 (`docs/dev-log/qa/2026-05-21-sprint25-multi-agent-qa/qa-sentinel/report.md`)
- Sprint 25 plan (`docs/dev-log/qa/2026-05-21-sprint25-multi-agent-qa/sprint-25-plan.md`) §"Wave 1 — P0"
- memory `project_gcp_migration_jetaime_dev_done.md` (사용자 결정 lock-in)
- ADR-014 Service Boundary (auth 도메인 책임)
- `backend/src/auth/CONTEXT.md` §5 (불변식) + §6 (노출 엔드포인트)
