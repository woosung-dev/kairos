<!-- Sentinel P0 — Sprint 18 → 19 Multi-Agent QA (BUG-C01 fix 후 v2) -->
# Kairos QA Sentinel P0 Report (v2 — fix 후 재검증)

| 항목 | 값 |
|---|---|
| 검증 시각 | 2026-05-17 19:20 KST (UTC 2026-05-17 10:20) — fix 후 재실행 |
| 1차 발견 시각 | 2026-05-17 07:40 KST (참조: `qa-report-pre-fix.md`) |
| 환경 | local (FE :3000 + BE :8000) |
| 페르소나 | Sentinel — RAG visibility 3-layer + Workspace IDOR + audio sanity |
| 시드 | `seed-fixtures.json` (`qa_run_id=2026-05-17-multi-agent`) |
| 자동화 | `frontend/e2e/tests/qa-sentinel-p0.spec.ts` (Playwright + 2계정 동시 BrowserContext + page.evaluate(getToken) auto-refresh) |
| Fix 커밋 | `19eb363` fix(workspaces): GET /workspaces/{id} require_viewer 누락 IDOR (BUG-C01) |
| 회귀 테스트 | `backend/tests/workspaces/test_workspace_idor.py` 2/2 PASS |
| Codex baseline | session `019e315c-c31d-7dc0-adb0-7f4e6aee1e92` (1차 발견) + `019e3518-21aa-7060-b76f-1543ea8f6e1e` (v2 리뷰) |

---

## 1. Executive Summary

| 항목 | v1 (pre-fix) | **v2 (post-fix)** |
|---|---|---|
| 총 케이스 | 28 | **28** |
| PASS | 27 | **28** |
| FAIL | 1 (Critical = BUG-C01) | **0** |
| CONFIRM_NEEDED | 0 | **0** |
| Health Score (Sentinel 자체) | 6.5 / 10 (guardrail ≤6.9 적용) | **10.0 / 10** (guardrail 미적용) |

### 핵심
- **BUG-C01 완전 해소**. RAG visibility 3-layer (Sprint 17 PR #46/#54/#59) + 새로 추가된 `require_viewer` 게이트 모두 정상 작동.
- 추가 발견 결함 **0건**. 1차 baseline (Sprint 17 closeout) 대비 회귀 0.

---

## 2. 발견 → Fix → 재검증 회고

### 2.1 발견 (1차)
- **Codex consult**가 정적 분석으로 의심: `backend/src/workspaces/router.py` `GET /workspaces/{workspace_id}` 가 `require_viewer` 없이 `get_current_user`만 사용 → membership 미검증.
- Sentinel-P0 spec 이 실 검증 → P0-2.1 케이스가 **HTTP 200**으로 B 워크스페이스 body 전체(name/owner/memberCount/threshold) leak 확인.
- Severity: **Critical**. Sprint 17 보안 3-layer 직후라 더 큰 회귀 가능성.

### 2.2 Fix (`19eb363`)
- `backend/src/workspaces/router.py` — `GET /workspaces/{workspace_id}` 에 `require_viewer` 데코레이터 추가.
- `backend/tests/workspaces/test_workspace_idor.py` 신설 — 회귀 테스트 2 케이스 (`test_get_workspace_idor_non_member_403` + `test_get_workspace_member_200`).

### 2.3 재검증 (v2)
- **회귀 테스트**: `pytest tests/workspaces/test_workspace_idor.py -v` → **2/2 PASS** (1.24s).
- **Sentinel-P0 spec 재실행**: 28/28 PASS, 0 Critical (1m 42s).
- 특히 P0-2.1 (`GET /workspaces/{ws_b_id}` with A 토큰) → **HTTP 403** ("워크스페이스 멤버가 아닙니다"), B 데이터 leak 0.

### 2.4 교훈
- Codex consult의 정적 분석 의심 → Sentinel-P0 spec 실 검증 → fix → 재검증의 **닫힌 루프**가 1세션 안에 완료됨. 이 패턴을 Sprint 19 4축 (b)(Multi-Agent QA 후속) 에 표준화.
- `require_viewer` 누락이 1 endpoint에 한정되지 않을 가능성. Sprint 19에서 13 endpoint 매트릭스 확장 + 다른 도메인 router (`meetings/notes/inbox/actions`) 동일 패턴 점검 필요.

---

## 3. P0-1 RAG visibility 12 케이스

전 케이스 **PASS** — 3-layer visibility 필터 정상 작동 (v1과 동일, 회귀 0).

| # | Token | project_id | Query | 기대 | Verdict |
|---|---|---|---|---|---|
| 1 | A admin | public | "alpha" | public 청크 노출 | **PASS** |
| 2 | A admin | private | "gamma" | admin 우회 노출 | **PASS** |
| 3 | B (WS-A 비멤버) | public | "alpha" | 403 | **PASS** |
| 4 | A (ProjectMember) | private | "gamma" | ProjectMember 노출 | **PASS** |
| 5 | A creator | draft | "beta" | creator 노출 | **PASS** |
| 6 | B (비멤버) | draft | "beta" | 403 | **PASS** |
| 7 | A admin | None (글로벌) | "alpha beta gamma" | L2 글로벌 + admin 우회 | **PASS** |
| 8 | A admin (재호출) | None | 동일 query | L3 cache hit | **PASS** |
| 9 | A admin (unique) | None | 새 query | L2 검색 | **PASS** |
| 10 | B | None (본인 WS-B) | "delta" | 본인 cross-tenant 노출 | **PASS** |
| 11 | A | None (WS-A) | "delta" | B의 청크 절대 안 보임 | **PASS** ✅ |
| 12 | A 토큰 + WS-B URL | cross-tenant project_id | "delta" | 403 (IDOR 차단) | **PASS** ✅ |

상세: `sentinel-p0-results.json` (executed_at: `2026-05-17T10:20:42Z`).

---

## 4. P0-2 Workspace IDOR 13 endpoint (★ 변경 영역)

**v1: 12/13 PASS (1 Critical = BUG-C01 P0-2.1)**
**v2: 13/13 PASS** ✅

| # | Endpoint | A→B 시도 | v1 | v2 |
|---|---|---|---|---|
| 1 | `GET /workspaces/{ws_b}` | B 워크스페이스 상세 | **200 LEAK** (Critical) | **403** ✅ |
| 2 | `GET /workspaces/{ws_b}/members` | B 멤버 목록 | 403 | 403 |
| 3 | `GET /workspaces/{ws_b}/projects` | B 프로젝트 목록 | 403 | 403 |
| 4 | `GET /meetings/{m_b}` | B meeting 상세 | 404 | 404 |
| 5 | `GET /meetings/{m_b}/status` | B meeting 상태 | 404 | 404 |
| 6 | `GET /meetings/{m_b}/export` | B meeting export | 404 | 404 |
| 7 | `GET /notes/{n_b}` | B note 상세 | 404 | 404 |
| 8 | `PATCH /notes/{n_b}` | B note 수정 | 403 | 403 |
| 9 | `DELETE /notes/{n_b}` | B note 삭제 | 403 | 403 |
| 10 | `GET /notes/{n_b}/export` | B note export | 403 | 403 |
| 11 | `POST /inbox/{i_b}/classify` | B inbox classify | 403 | 403 |
| 12 | `POST /inbox/{i_b}/dismiss` | B inbox dismiss | 403 | 403 |
| 13 | `POST /projects/{ws_a}/items` body `{project_id: ws_b_proj}` | cross-workspace 참조 | 404 | 404 |

**검증 통과**: 응답 body에 B의 어떤 필드(title/content/owner_id/memberCount/threshold)도 leak 없음.

**남는 의심** (Sprint 19 P1 후보):
- 404 응답들이 실제로 "리소스 없음" vs "권한 없음" 구분 가능성 — timing side-channel 위험. 일관된 403으로 통일 검토.
- meetings/notes 도메인 router에 `require_viewer` 가 모든 endpoint에 일관 적용되었는지 매트릭스 점검 필요.

---

## 5. P0-3 audio 파이프라인 sanity 3 케이스

| # | 시나리오 | 기대 | 실제 | Verdict |
|---|---|---|---|---|
| 1 | `POST /upload/sign` (회의 오디오 업로드 signed URL) | 200 + URL | 200 | **PASS** |
| 2 | `GET /meetings/{미존재 id}/status` | 404 | 404 | **PASS** |
| 3 | `GET /meetings` (목록) | 200 | 200 | **PASS** |

UI 의존 시나리오 (실 업로드 + STT + AI 처리 polling)는 Step 4 페르소나 smoke에서 검증 예정.

---

## 6. Sprint 19 P0/P1 후보 (사용자 triage용)

### P0 (이번 세션 Step 6에서 Sprint 19 plan 4축 (b) 등재)

- **BUG-C01-EXT** (확장 점검): `meetings/router.py`, `notes/router.py`, `inbox/router.py`, `actions/router.py` 의 모든 endpoint에 `require_viewer` 또는 `require_member` 일관 적용되었는지 매트릭스 점검 + 통합 회귀 테스트.

### P1

- **IDOR 응답 일관화**: 404 vs 403 timing side-channel 차단. 모든 cross-tenant 시도는 403 통일 + 응답 시간 정규화.
- **회귀 테스트 확장**: 13 endpoint × 2계정 매트릭스를 pytest integration test로 신설 (`backend/tests/integration/test_workspace_idor_matrix.py`).

### P2

- spec PASSWORD ENV화 (이번 세션 Step 2에서 임시 수정 완료, Step 3 commit 포함). Sprint 19에서 다른 spec/script도 같은 패턴 점검.

---

## 7. 자동 산출물

- `sentinel-p0-results.json` (v2, executed_at `2026-05-17T10:20:42Z`)
- `sentinel-p0-results-pre-fix.json` (v1 archive, executed_at `2026-05-17T...`)
- `qa-report-pre-fix.md` (v1 archive)
- `traces/BLOCKER-jwt-expired.txt` (v1 진행 중 JWT 만료 BLOCKER 분석 기록)
- `seed-fixtures.json` (시드 fixture 매핑)

---

> 다음 단계: Step 3 QA harness 커밋 → Step 4 4 페르소나 smoke → Step 5 Sentinel-P1 → Step 6 통합 HTML + Sprint 19 plan → Step 7 PR.
