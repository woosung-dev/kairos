# Cross-Check — agy + 메인 세션 직접 검증

> Sprint 25 Multi-Agent QA 통합 보고서 도메인 관점 검증
> agy CLI 호출 시도: 2026-05-21 (KST), 11분 응답 지연 → hang 판정 → kill (exit 144)
> 보강: 메인 세션이 docs/REFACTORING-BACKLOG.md / CONTEXT-MAP.md / docs/dev-log/ 직접 read로 도메인 검증
> session: cosmic-knitting-island

## agy 호출 결과

- 호출 모드: `agy --print --print-timeout 8m`
- 결과: 11분 25초 동안 출력 0줄 → hang 판정, 강제 종료 (exit 144)
- 원인 추정: 8m timeout 초과 또는 plugin 의존 응답 막힘. 메인 세션이 도메인 검증 직접 수행.

## 메인 세션 직접 검증 결과

### 검증 항목 1 — 우선순위 RAG/도메인 합리성

**확인**: codex review의 partial flip 권고가 도메인 관점에서도 정합.
- BUG-SENTINEL-005 (sync_user 무서명): `backend/src/main.py:132` 실제 `app.include_router(auth_router)` 공개 라우팅 확인. Critical 유지 정합.
- TRUST/PRICING P0 → P1 flip: 베타 단계 Pre-GA 상태에서 시스템 보안 < 마케팅 신뢰의 우선순위가 맞음. RAG/도메인과는 무관한 GTM 영역.

**결론**: codex 권고 채택. + **2026-05-21 추가 정정**: 사용자 Clerk Production 발급 SKIP 결정 반영으로 Wave 1 = BUG-SENTINEL-005 **1건만** (endpoint 비활성화 권고). BUG-CASUAL-001은 Out-of-Sprint 정책 재분류.

### 검증 항목 2 — BL-068/069 carry-over 정합성

**확인**: `docs/REFACTORING-BACKLOG.md:1724-1750`에 BL-068 + BL-069 모두 등재.
- BL-068: "D1 WorkspaceSwitcher Playwright/manual reproduce (Sprint 24 BL-066 carry)"
- BL-069: "D3 Inbox dismiss Playwright/manual reproduce (Sprint 24 BL-066 carry)" — Sprint 23 `928fc7c` D3 fix 가 현 코드 정합 반영됨
- 묶음 권고: "Sprint 25+ e2e Clerk infrastructure (BL-068 동반)"

**결론**: 통합 매트릭스의 P3 등재 정합. BUG-CASUAL-001 (Clerk Prod 발급) 해소 후 동반 verify 흐름이 BACKLOG와 일치.

### 검증 항목 3 — ADR-019 Phase B 회귀 누락 영역

**확인**: memory `project_sprint15_adr019_phase_a_done.md` + Sprint 24 Wave 2 post-swap delta 보고서 (`docs/dev-log/2026-05-20-sprint24-wave2/`) 베이스라인 존재.
- Phase B 적용: Sprint 16 첫 commit `003908a`
- delta 결과: better 4/same 1/worse 0 PASS (DELTA-1), DELTA-3 due_date hallucinate 회귀 → Phase 2 T-AI-DATE 계획

**누락**: 본 Sprint 25 Multi-Agent QA는 LLM 직접 호출(Distill/Extract Actions)을 실증하지 않음. 인증 게이트 안쪽 → Playwright + Clerk Prod 도입 시 동반 검증 필요.

**조치**: Sprint 25 Wave 2/3에 "ADR-019 Phase B post-swap LLM 직접 호출 실증" task 추가. BUG-CASUAL-001 fix 후 e2e 흐름에서 동반 verify.

### 검증 항목 4 — CONTEXT-MAP.md §4.2 도메인 경계 위반 가능성

**확인**: `CONTEXT-MAP.md:121-190` §4.2 의존 방향 + memory pipeline_service BL-006 closed (Sprint 24 Wave 2, 2026-05-20).
- `MemoryPipelineService.save_memory_chunk` embeddings 호출 격리 → 헌법 §4.2 정합
- I-21 (Sprint 16 ADR-020) 벡터 검색 세션 변수 강제 → `_apply_hnsw_session_params(session)` 정합

**위반 가능성**:
- BUG-SENTINEL-005 fix 시 `backend/src/auth/router.py` Webhook 검증 함수를 추가하면 → 도메인 경계 검토 필요 (auth domain vs common webhook util). 정합 유지하려면 `backend/src/auth/dependencies.py`에 `verify_svix_signature` 함수 + `backend/src/auth/webhooks.py` 분리 권고.
- BUG-SENTINEL-003 fix 시 upload validation 강화 → `backend/src/upload/` 도메인 내부 처리, 위반 없음.

**조치**: Sprint 25 BUG-SENTINEL-005 task에 "헌법 §4.2 정합 검증" 서브태스크 추가.

## codex 권고 영역 (메인 세션 추가 검증)

codex가 지적한 누락 회귀 영역 4건에 대해 메인 세션이 추가 정합 검증:

| 영역 | 메인 세션 검증 결과 | Sprint 25 매핑 |
|------|----------------------|----------------|
| 인증 게이트 안쪽 CRUD/RBAC | 정적 정합 PASS, 실증 미진행 (Playwright 점유) | Wave 2 — BUG-CASUAL-001 fix 후 동반 |
| Webhook idempotency | **2026-05-21 정정**: 사용자 Clerk webhook SKIP 결정으로 무의미. endpoint 자체 비활성화로 해소. | Wave 1 — BUG-SENTINEL-005 endpoint 비활성화로 일괄 처리 |
| 더미 user 데이터 오염 정리 | production DB에 `user_QA20260521_sentinel_test_doNotUse` 1건 잔존 | Phase 4 cleanup task로 명시 |
| Upload 이후 R2/DB 정합성 | `backend/src/upload/router.py:42-56` R2 putObject + DB record 정합 검증 부재 | Wave 2 — BUG-SENTINEL-003 fix 시 동반 (트랜잭션 정합) |

## 최종 verdict

| 단계 | 결과 |
|------|------|
| agy 직접 호출 | hang (실패, exit 144) |
| 메인 세션 도메인 직접 검증 | **PASS** |
| codex review/challenge 권고 채택 | **partial flip 수용** (TRUST/PRICING → P1) |
| 통합 매트릭스 갱신 필요 | Yes (Phase 4에서 반영) |

## 조치 항목

1. integrated-defect-matrix.md에 P0 → P1 강등 + Security/Product/GTM 3축 점수 반영
2. Sprint 25 plan Wave 1 = BUG-SENTINEL-005 **endpoint 비활성화 1건만**으로 압축 (사용자 Clerk Prod SKIP 결정 반영)
3. Sprint 25 Wave 2/3에 누락 회귀 4건 명시 등재 (인증 안쪽 CRUD/RBAC, webhook idempotency, 더미 user 정리, upload R2/DB 정합성)
4. BUG-SENTINEL-005 task에 "헌법 §4.2 정합 검증" 서브태스크 (auth/webhooks.py 분리 권고)
5. Sprint 25 Wave 2에 "ADR-019 Phase B post-swap LLM 직접 호출 실증" 추가

## agy 향후 처리

- agy hang은 plugin/MCP 의존 문제 가능성 → 별도 BL 등재 권고
- 본 cross-check에서는 메인 세션 직접 검증으로 도메인 정합성 확보됨, agy 응답 없이도 의사결정 가능
