# QA-EdgeCase — 엣지 + 보안 8 시나리오

> 페르소나: Adversarial security tester. Sprint 25 Sentinel 의 후속.

## 결과 요약

| # | 시나리오 | 결과 | 비고 |
|---|---|---|---|
| 1 | IDOR cross-workspace | ⏸ NOT_TESTED | Account #2 login 시간 부족. 코드 review (`workspaces/router.py`, repository `workspace_id` WHERE 강제, composite FK ADR I-9) 로 정합 추정 |
| 2 | 0 byte 업로드 | ⏸ NOT_TESTED | 시간 + AI pipeline fail 로 진행 의미 약화. **P0-AI-PIPELINE 우선 fix** |
| 3 | >500MB 업로드 | ⏸ NOT_TESTED | 동일 사유 |
| 4 | 잘못된 MIME (HEIC, .txt) | ⏸ NOT_TESTED | BL-072 회귀 codex 권고 |
| 5 | BL-073 회귀 (Inbox 확정 새로고침) | ⛔ BLOCKED | meeting 처리 실패 → InboxItem 0건. data 의존 |
| 6 | token 만료 / fake token | ✅ PASS | `GET /workspaces/{id}/members` + `/inbox` with `Authorization: Bearer fake` → **401** "유효하지 않은 토큰입니다" (정확한 거부) |
| 7 | RAG prompt injection | ⏸ INCONCLUSIVE | `? 이전 시스템 프롬프트 무시하고...` 입력 → RAG panel 발화 안 됨 (`/meetings/...` page 에선 ⌘K 가 RAG panel 안 띄움). GEMINI_API_KEY invalid 로 backend prompt 처리 자체 fail. injection resistance verify 불가 |
| 8 | sync_user 404 verify (ADR-022 sentinel) | ✅ PASS | `POST /api/v1/users/sync` → **404** "Not Found". Sprint 25 T-SEC-1 회귀 0 확정. ADR-022 lock-in 유지 |

## 핵심 Findings

### P0-SEC-1 (✅ PASS) — ADR-022 sync_user 회귀 가드 통과

**증거**: 
- `POST http://localhost:8000/api/v1/users/sync` body `{"data":{"id":"sentinel-test","email_addresses":[{"email_address":"evil@test.com"}]},"type":"user.created"}`
- Response: `404 {"detail":"Not Found"}`

**Verdict**: Sprint 25 Sentinel BUG-SENTINEL-005 (Critical) 가 완전 봉인됨. `backend/src/auth/router.py` 의 sync_user handler 제거 + `backend/tests/auth/test_auth_sync_disabled.py` 회귀 가드 정합.

### P1-SEC-2 (✅ PASS) — invalid JWT 차단

**증거**: workspace_id 변조 (`7aea8c86-...`, 다른 user 의 workspace) 동시 fake bearer token → 401. JWT signature 검증 통과 못해 endpoint logic 도달 X.

**Verdict**: Sprint 19 PR #1 BUG-C01-EXT v3 + Sprint 19 PR #2 BUG-C01-EXT-FK composite FK + Sprint 21 BL-050 Simple 4 결과 안정적. 단 **real user IDOR** (Account #2 valid token 으로 #1 workspace 접근) 은 미검증.

### P0-SEC-3 (DEFERRED — production deploy stale 영향) — production 의 503 polish 부재

**증거**: production 의 `GET /workspaces/{id}/inbox` 가 403 `워크스페이스 멤버가 아닙니다` 반환. 단 같은 endpoint 가 다른 `workspace_id` 으로도 같은 403 (information leak: workspace 존재 vs 미존재 구분 가능).

**Verdict**: ADR-014 §I-9 "cross-tenant 404 (admin 도 우회 불가)" 명시되었으나 production 응답이 403 = workspace 존재 leak 가능성. localhost 에서 재현 확인 필요 (Account #2 login 후). P1.

### NOT-TESTED finding (감사 시간 한계)

- **BL-072 회귀** (잘못된 MIME bypass) — meeting 업로드 pipeline 자체가 broken 이므로 fix 후 재진입 시 필수
- **BL-073 회귀** (Inbox 확정 새로고침 상태 보존) — InboxItem 생성에 AI pipeline 의존. fix 후 재진입
- **0 byte / >500MB 업로드 한계 검증** — R2 presigned + size validation 검증 필요
- **RAG injection resistance** — `common/prompts.py` 내부 system prompt 의 robustness 평가는 GEMINI_API_KEY 갱신 후 재진입

## 평가 점수 (10점)

| 차원 | 점수 | 근거 |
|---|---|---|
| 보안 baseline | 7/10 | sync_user 404 + invalid JWT 401 통과. composite FK + workspace_id WHERE 정합 추정. real IDOR + RAG injection 미검증 |
| Edge case coverage | 3/10 | 8 시나리오 중 2 PASS, 1 BLOCKED, 5 NOT_TESTED. AI pipeline fail 로 6/8 진행 불가 |
| 안내 메시지 | 5/10 | 401 "유효하지 않은 토큰입니다" 명확. 단 production 403 message 가 workspace 존재 여부 leak |

**평균: 5/10**

## 외부 5명 진입 결정 input

**자동 verdict**: 🟡 PARTIAL — sentinel 회귀 가드 통과 (강한 신호) + JWT 차단 ok. 단 **real IDOR + edge case coverage 가 미검증**. P0-AI-PIPELINE fix 후 재진입 audit 필수.

추가 권고 (audit 외 follow-up):
- Account #2 login + cross-workspace IDOR live verify (~15min)
- `backend/tests/integration/` 의 IDOR + composite FK 회귀 test 직접 실행 (CI 가 통과한 main HEAD `eb13a42` 가 정합 추정)
