# Wave 4 재진입 audit — P0 3건 모두 fix verified ✅

> 2026-05-23 Sprint 27c P0 fix (Wave 1-3) 적용 후 재진입 audit. 외부 5명 진입 unlocking.

## 통합 verdict

🟢 **READY** — 모든 P0 fix verified. 외부 5명 진입 1주 hard cap 시작 가능.

## P0 fix verify 결과

### P0-S27c-1 — Race condition fix ✅

| 측정 | 이전 (Wave 1 fix 전) | 현재 |
|---|---|---|
| Account #3 (c@e.com) localhost dashboard 진입 | 500 (`/workspaces` + `/members` + `/projects`) | **200** |
| BE log | `IntegrityError: duplicate key "ix_users_clerk_id"` | INFO 정상 |
| pytest `tests/auth/test_get_current_user_race.py` | N/A (테스트 부재) | **3 passed** |
| pytest `tests/auth/` 전체 regression | — | **40 passed** |

**Fix**: `backend/src/auth/dependencies.py:160-178` — User INSERT 에 `ON CONFLICT (clerk_id) DO NOTHING` + re-fetch (workspace INSERT 패턴 정합).

### P0-S27c-2 — GEMINI_API_KEY 재발급 ✅

| 측정 | 이전 (Wave 2 전) | 현재 |
|---|---|---|
| 회의 업로드 후 status | 실패 | **완료** |
| AI 요약 표시 | 없음 (오류) | 본문 + 핵심 결정사항 + 주제 |
| Embedding 청크 생성 | 0 (실패로 skip) | **2개** |
| Action items 추출 | 0 (실패로 skip) | 0 (audio 자체에 액션 X — 정상) |
| BE log | `ClientError: 400 API_KEY_INVALID` | `INFO: 액션 아이템 0개 추출 완료 / 임베딩 2개 생성` |

**Fix**: 사용자가 Google AI Studio 에서 새 GEMINI_API_KEY 발급 + `backend/.env` line 10 갱신 + BE restart.

**산출물 evidence** (`Wave 4 retry — 새 GEMINI key` meeting):
- 요약: "금일 회의에서는 현재 프로젝트의 진행 현황을 점검하고, 이에 따른 다음 스프린트 계획을 수립하였습니다..."
- 핵심 결정사항: "다음 스프린트 계획 확정"
- 주제: 프로젝트 현황 리뷰 · 다음 스프린트 계획
- 트랜스크립트 전체 보기 (RAG 임베딩 base ready)

### P0-S27c-3 — Landing screenshot fix ✅

| 측정 | 이전 (Wave 3 fix 전) | 현재 |
|---|---|---|
| Sign-out 상태 landing console errors | 3 (`_next/image?url=/landing/screenshots/...` 400) | **0** |
| Direct `/landing/screenshots/*.png` | 307 Clerk sign-in redirect | 200 |
| Image optimizer | 400 "valid image 아님" | 200 |

**Fix**: `frontend/src/proxy.ts:10` — `isPublicRoute` matcher 에 `/landing(.*)` 추가. Clerk middleware 가 정적 자원 protect 차단.

**Screenshot evidence**:
- `screenshots/qa-f/11-landing-screenshots-fixed.png` — 3 screenshot 모두 정상 표시
- `screenshots/qa-f/12-meeting-complete-after-fix.png` — AI 요약/결정사항/주제 표시

## 부수 verified (Wave 4 진행 중)

### Real IDOR cross-tenant (Sprint 19 BUG-C01-EXT fix 정합)
Account #1 valid JWT + Account #2 workspace_id (`51bebd65-...`) → **5 endpoint 모두 403** ("워크스페이스 멤버가 아닙니다"). composite FK + workspace_id WHERE 정합. 

### 헌법 I-9 cross-tenant 응답 정합
존재 workspace vs nonexistent UUID → **동일 403 + 같은 body** = workspace 존재 여부 leak 없음. 본 audit 1차 추정 ("403 message workspace 존재 leak" P2-S27c-9) = **false alarm 취소**.

### Stale localStorage finding 신규 (Wave 4 verify 중 발견)
**Bug**: `localStorage.kairos-workspace.activeWorkspaceId` 가 logout/login 후에도 이전 user 의 workspace_id 잔존. Account #1 login 했는데 stale = Account #3 workspace_id 사용 → 모든 호출 403 → "/new" 페이지에서 "워크스페이스 멤버가 아닙니다" 표시. dashboard 진입은 graceful fallback (list 호출 후 retry) 동작, 다른 페이지는 fallback X.

**Fix 권고**: Clerk `signOut()` hook 에 `localStorage.removeItem('kairos-workspace')` 추가 또는 Zustand persist 의 onRehydrate 에 user_id verification 가드. **BL-S27c-12 (P1)** 신규 등재.

## 외부 5명 진입 결정 (audit plan §5 자동 적용)

| 조건 | 충족 여부 | trigger |
|---|---|---|
| P0 ≥ 1건 (3+ agent 합의) | ❌ 0건 (모두 fix verified) | — |
| CTO 보안 < 5 / 운영 < 3 | ❌ 운영 7/10 grade up (race fix 후) | — |
| CEO 차별점 < 5 | ❌ 6/10 | — |
| General-User 이탈 ≥ 3 | ❌ 0건 (P0 fix 후 모든 마찰 해소) | — |
| 평균 점수 < 5 | ❌ 6.5+/10 grade up | — |

**Final verdict**: 🟢 **READY — 1주 안 외부 5명 진입 (hard cap)**

## 사용자 액션 (외부 5명 진입 전, 마지막 prerequisite)

1. **production 배포** (Cloud Run + Vercel):
   - `backend/src/auth/dependencies.py` race fix → Cloud Run revision 재배포
   - `frontend/src/proxy.ts` landing fix → Vercel auto-deploy
   - GEMINI_API_KEY → Cloud Run secret 동기화 (사용자 작업 완료 확인 필요)
2. **production verify** (~5분): a@e.com 또는 새 fresh 계정 production login → dashboard 200 + 회의 업로드 → status 완료 확인
3. **외부 5명 모집 시작** (R8 outreach 80 활용, 1주 hard cap)

## 후속 (Sprint 28+)

- BL-S27c-4~12 (P1/P2 9건) 는 외부 5명 dogfooding 중 발견된 신규 finding 과 합쳐서 별도 sprint
- Sprint 28 = paid customer 1명 (ADR-024 종료 신호)
