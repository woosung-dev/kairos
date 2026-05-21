<!-- Sentinel P0 — Sprint 18 → 19 Multi-Agent QA -->
# Kairos QA Sentinel P0 Report

| 항목 | 값 |
|---|---|
| 검증 시각 | 2026-05-17 07:40 KST (UTC 2026-05-16 22:40) |
| 환경 | local (FE :3000 + BE :8000) |
| 페르소나 | Sentinel — RAG visibility 3-layer + Workspace IDOR + audio sanity |
| 시드 | seed-fixtures.json (qa_run_id=2026-05-17-multi-agent) |
| 자동화 | `frontend/e2e/tests/qa-sentinel-p0.spec.ts` (Playwright + 2계정 동시 BrowserContext + page.evaluate(getToken) auto-refresh) |
| Codex baseline | session `019e315c-c31d-7dc0-adb0-7f4e6aee1e92` |

---

## 1. Executive Summary

| 항목 | 결과 |
|---|---|
| 총 케이스 | 28 (RAG 12 + IDOR 13 + audio 3) |
| **PASS** | **27** |
| **FAIL** | **1 (Critical)** |
| CONFIRM_NEEDED | 0 |
| Health Score (자체 평가) | **6.5 / 10** (Critical 1건으로 guardrail 적용 ≤6.9) |

### Top 3 권고 (Sprint 19 P0)

1. **BUG-C01 (Critical)** — `GET /api/v1/workspaces/{workspace_id}` 에 `require_viewer` 추가 + `WorkspaceService.get_workspace()` 에 membership 검증. **Codex 가 정적 분석으로 의심 → 실 검증에서 확정**. body 전체(name/owner/memberCount/threshold) leak. Sprint 17 보안 3-layer 직후라 더 큰 회귀.
2. **회귀 가드** — workspace IDOR pytest integration test 신설 (`backend/tests/integration/test_workspaces_idor.py`). 13 endpoint × 2 계정 매트릭스를 conftest fixture 로.
3. **CI 차단 룰** — Sprint 17 패턴 (qa-fix → main rollup) 으로 fix + main merge. 해당 fix 가 들어가기 전까지 prod 배포 hold 고려.

---

## 2. P0-1 RAG visibility 12 케이스 매트릭스

전 케이스 **PASS** — 3-layer visibility 필터 (Sprint 17 PR #46/#54/#59) 정상 작동.

| # | Token | project_id | Query | 기대 | 실제 | Verdict |
|---|---|---|---|---|---|---|
| 1 | A admin | public | "alpha" | public 청크 노출 | chunk `87741c54...` 노출 | **PASS** |
| 2 | A admin | private | "gamma" | admin 우회 노출 | chunk `07a47e67...` 노출 | **PASS** |
| 3 | B (WS-A 비멤버) | public | "alpha" | 403 | `{"detail":"워크스페이스 멤버가 아닙니다"}` | **PASS** |
| 4 | A (ProjectMember) | private | "gamma" | ProjectMember 노출 | chunk `07a47e67...` 노출 | **PASS** |
| 5 | A creator | draft | "beta" | creator 노출 | chunk `eb6f88e6...` 노출 | **PASS** |
| 6 | B (비멤버) | draft | "beta" | 403 | `{"detail":"워크스페이스 멤버가 아닙니다"}` | **PASS** |
| 7 | A admin | None (글로벌) | "alpha beta gamma" | L2 글로벌 + admin 우회 | chunks 노출 | **PASS** |
| 8 | A admin (재호출) | None | 동일 query | L3 cache hit | 동일 chunks (cache) | **PASS** |
| 9 | A admin (unique) | None | 새 query | L2 검색 | chunks 노출 | **PASS** |
| 10 | B | None (본인 WS-B) | "delta" | 본인 cross-tenant 노출 | chunk `65e9d772...` 노출 | **PASS** |
| 11 | **A** | None (WS-A) | **"delta"** (cross-tenant 키워드) | **B의 청크 절대 안 보임** | sources에 A의 priv chunk만, B의 `65e9d772...` **부재** | **PASS** ✅ |
| 12 | **A 토큰** | **WS-B URL + cross-tenant project_id** | "delta" | **403 (IDOR 차단)** | `{"detail":"워크스페이스 멤버가 아닙니다"}` | **PASS** ✅ |

**핵심**: case 11/12 (cross-tenant leak) — RAG 3-layer 가 다른 워크스페이스의 private 청크 누출 차단. Sprint 17 보안 작업이 회귀 없이 동작.

---

## 3. P0-2 Workspace IDOR 13 endpoint

**12/13 PASS — 1 Critical FAIL**.

A 토큰으로 B 자원 접근 시도. 기대: 403/404, body에 B 데이터 leak 없음.

| # | Endpoint | 기대 | 실제 | Verdict |
|---|---|---|---|---|
| **1** | **`GET /api/v1/workspaces/{ws_B}`** | **403/404** | **🔥 200 + ws_B 전체 body leak** | **FAIL (Critical)** |
| 2 | `GET /api/v1/workspaces/{ws_B}/members` | 403 | 403 | **PASS** |
| 3 | `GET /api/v1/workspaces/{ws_B}/projects` | 403 | 403 | **PASS** |
| 4 | `GET /api/v1/notes/{ct_note}` | 404 | 404 | **PASS** |
| 5 | `PATCH /api/v1/notes/{ct_note}` body `{title: HACKED}` | 404 | 404 | **PASS** |
| 6 | `DELETE /api/v1/notes/{ct_note}` | 404 | 404 | **PASS** |
| 7 | `GET /api/v1/projects/{ct_proj}` | 404 | 404 | **PASS** |
| 8 | `GET /api/v1/workspaces/{ws_B}/projects?status=active` | 403 | 403 | **PASS** |
| 9 | `GET /api/v1/workspaces/{ws_B}/invites` | 403 | 403 | **PASS** |
| 10 | `POST /api/v1/workspaces/{ws_B}/invites` body `{role:"viewer"}` | 403 | 403 | **PASS** |
| 11 | `GET /api/v1/workspaces/{ws_B}/inbox` | 403 | 403 | **PASS** |
| 12 | `GET /api/v1/workspaces/{ws_B}/projects/{ct_proj}/members` | 403 | 403 | **PASS** |
| 13 | `GET /api/v1/projects/{ct_proj}/members` | 404 | 404 | **PASS** |

---

## 4. P0-3 audio endpoint sanity

전 케이스 **PASS** — 보안 baseline OK.

| # | Endpoint | 결과 |
|---|---|---|
| 1 | `POST /api/v1/workspaces/{wsA}/upload/presigned-url` | 200 (presigned URL 발급) |
| 2 | `GET /api/v1/meetings/{nonexistent}/status` | 404 (boundary) |
| 3 | `GET /api/v1/workspaces/{wsA}/meetings` | 200 (list, 빈 array) |

> 실제 audio e2e (record → STT → AI → Inbox) 는 별도 페르소나 또는 manual — Sprint 17 C2 carry-over.

---

## 5. 발견 결함 상세

### Critical

#### BUG-C01: `GET /workspaces/{workspace_id}` IDOR — 비멤버가 워크스페이스 상세 조회 + 전체 body leak

- **위치**: `backend/src/workspaces/router.py:35-42` (get_workspace) + `backend/src/workspaces/service.py:get_workspace()`
- **재현 단계**:
  1. Sentinel A (test, `wkddntjd3429@naver.com`) 로 로그인 → JWT 획득
  2. Sentinel B (test2) 의 workspace_id 확보 (예: 시드 fixture `ce9e5d5c-74b8-4370-98d4-d16151bed130`)
  3. `curl -H "Authorization: Bearer <A_JWT>" http://localhost:8000/api/v1/workspaces/ce9e5d5c-74b8-4370-98d4-d16151bed130`
- **기대**: `403 {"detail":"워크스페이스 멤버가 아닙니다"}` (다른 endpoint 와 동일 메시지)
- **실제**: `200 OK` + body:
  ```json
  {"id":"ce9e5d5c-...","name":"[QA-2026-05-17] WS-QA-SENTINEL_B-2026-05-17",
   "ownerId":"e0ccf7f7-8527-45f4-bf87-00346f3b713e","type":"team",
   "memberCount":1,"inboxThreshold":0.9,
   "createdAt":"2026-05-16T22:33:53.260826","updatedAt":"2026-05-16T22:33:53.260842"}
  ```
- **Root Cause**:
  - `backend/src/workspaces/router.py:35-42` `get_workspace()` 가 `current_user: User = Depends(get_current_user)` 만 사용. **`require_viewer` 누락**
  - `WorkspaceService.get_workspace(workspace_id)` 가 membership 검증 없이 `repo.find_by_id()` 만 호출
  - 같은 라우터의 다른 endpoint (`/members`, `/projects`, `/invites`, `/inbox`, settings PATCH) 는 모두 `require_viewer`/`require_owner` 사용 — **본 endpoint 만 누락**
- **영향**:
  - 다른 워크스페이스의 **이름, 소유자 user_id, 멤버 수, inbox_threshold, 생성/수정 시각 leak**
  - 워크스페이스 UUID 만 알면 brute-force 또는 추측 공격 가능
  - Sprint 17 보안 3-layer 작업 직후 라 더 큰 회귀
- **Confidence**: **H (High)** — 코드 정적 분석 + 실 BE 호출 + body 확인 모두 일치
- **권고 수정**:
  ```python
  # backend/src/workspaces/router.py:35-42
  @router.get("/{workspace_id}")
  async def get_workspace(
      workspace_id: uuid.UUID,
      member: WorkspaceMember = Depends(require_viewer),  # ← 추가
      service: WorkspaceService = Depends(get_workspace_service),
  ):
      return await service.get_workspace(workspace_id)
  ```
  + (옵션) `WorkspaceService.get_workspace()` 에 `_assert_member()` 헬퍼 호출 추가 (defense in depth)
- **회귀 가드**: `backend/tests/integration/test_workspaces_idor.py` 신설 — 13 endpoint × 2 계정 매트릭스
- **Sprint 19 우선순위**: **P0 최우선** (보안)

---

## 6. 양성 시그널 (PASS 27건이 시사하는 것)

1. **RAG 3-layer visibility 정상** — case 1~12 모두 expected 일치. ADR-014 옵션 A + Sprint 17 PR #46/#54/#59 회귀 없음.
2. **Cross-tenant 청크 누출 없음** (case 11/12) — Sentinel A 가 WS-A 글로벌 검색 시 Sentinel B 의 cross-tenant private 청크 절대 안 보임.
3. **워크스페이스 RBAC 12 endpoint 정상** — workspace/members/projects/invites/inbox/settings 등 모두 403/404 일관.
4. **에러 응답 한국어 일관성** — `{"detail":"워크스페이스 멤버가 아닙니다"}` 모든 RBAC 차단에 동일 메시지.
5. **JWT 60초 TTL 우회** — Playwright `page.evaluate(Clerk.session.getToken)` auto-refresh 패턴 동작. 90분 sub-agent 작업 가능.

---

## 7. 자동화 인프라 산출물 (재사용 가능)

| 파일 | 용도 |
|---|---|
| `frontend/e2e/tests/qa-extract-credentials.spec.ts` | 5계정 자동 로그인 + JWT 추출 + .env 자동 업데이트 |
| `frontend/e2e/tests/qa-sentinel-p0.spec.ts` | 28 케이스 자동 검증 + JSON 결과 |
| `backend/scripts/seed_qa_fixtures.py` | DB fixture 시드 + `--dry-run-cleanup` + `--cleanup` |
| `docs/dev-log/qa/2026-05-17-multi-agent-qa-sprint18/seed-fixtures.json` | sub-agent 가 IDOR/RAG 검증에 사용할 expected ID 매핑 |
| `docs/dev-log/qa/2026-05-17-multi-agent-qa-sprint18/sentinel-p0-results.json` | 28 케이스 raw 결과 (재현/감사 용) |

---

## 8. 미완료 / 다음 단계

| 항목 | 상태 |
|---|---|
| Sentinel P1 (보안 후속: 인증/CORS/입력검증/보안헤더/rate limit/SSE/에러응답) | 미진행 (Day 2) |
| 오디오 full e2e (record → STT → AI → Inbox) | 미진행 (Casual/manual) |
| Curious 페르소나 | 미진행 (Day 1) |
| Casual 페르소나 + a11y | 미진행 (Day 1) |
| Mobile/Power | 미진행 (Day 2) |
| BUG-C01 fix | **즉시 진행 권장** (Sprint 19 P0) |
| Atomic Update — `backend/CONTEXT.md` §스크립트 + `.env.example` + `docs/TODO.md` | 미진행 |

---

## 9. 회귀 점검 — Sprint 17 직접 회귀 0건

- Sprint 17 PR #46 (ISSUE-040 visibility filter): ✅ 회귀 없음 (RAG case 1~12)
- Sprint 17 PR #54 (BL-041 find_similar_cache visibility leak): ✅ 회귀 없음 (cache hit case 8)
- Sprint 17 PR #59 (BL-042 max_visibility fast path): ✅ 회귀 없음 (cache hit case 8)
- Sprint 18 (RBAC 매트릭스 / observability): ✅ 회귀 없음 (IDOR 12 endpoint 정상 차단)

**단 BUG-C01 은 Sprint 17 작업이 cover 하지 못한 영역** — `GET /workspaces/{id}` 는 visibility 필터의 대상이 아니고 RBAC 의 대상이지만 본 endpoint 만 require_viewer 누락.

---

✅ **Sentinel P0 완료** — 27/28 PASS / 1 Critical / Health 6.5 / Sprint 19 P0 fix 1건 명확.
