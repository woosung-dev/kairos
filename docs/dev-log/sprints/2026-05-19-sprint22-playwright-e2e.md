# Sprint 22 Playwright E2E 8 시나리오 결과

> 2026-05-19, Sprint 22 expressive-squirrel
> branch: `sprint-22/onboarding-e2e-obs`
> baseURL: `http://localhost:3003` (local dev)

## 결과 표

| # | Scenario | Spec | 상태 | Notes |
|---|---|---|---|---|
| **G1** | signup → workspace 자동 생성 → Step 1/4 | `home.spec.ts` | ✅ **보강 적용** | `data-testid=onboarding-banner` + `[1-4]/4` text assertion |
| **G2** | 첫 프로젝트 생성 → Step 2/4 | `first-project.spec.ts` | ✅ **NEW** | mutation invalidate (E16) 후 banner step ≥ 2 또는 isCompleted hide 검증 |
| **G3** | 회의 STT + Distillation → Step 3/4 | `meeting-upload.spec.ts` (HEAVY) | ⚠️ **보강 carry-over** | 기존 spec 유지. progress assertion 추가는 Sprint 23 CO |
| **G4** | RAG ask → citation + Step 4/4 → banner hide | `rag-citation.spec.ts` | ⚠️ **skip 유지** | SSE mock 정합성 디버깅 필요 — Sprint 23 CO (sub-agent stall point) |
| **G5** | action 완료 → 통계 갱신 | `qa-sentinel-p0.spec.ts` | ⚠️ **보강 carry-over** | 기존 P0 spec 유지 |
| **G6** | 두 번째 user 초대 → multi-user IDOR | `invite-page-regression.spec.ts` + `qa-sentinel-p0` | ⚠️ **보강 carry-over** | 기존 spec 유지 |
| **G7** | logout → login → state 보존 | `auth-relogin.spec.ts` | ✅ **NEW** | localStorage `activeWorkspaceId` 보존 검증. user-menu testid 부재 시 skip 가드 |
| **G8** | meeting export discoverability + Markdown download | `meeting-export.spec.ts` | ✅ **NEW** | "내보내기" 라벨 visible + dropdown → Markdown/JSON 옵션 검증 (BUG-C04 해소) |

## Summary

- **NEW 3 spec**: G2 / G7 / G8 (`first-project.spec.ts`, `auth-relogin.spec.ts`, `meeting-export.spec.ts`)
- **보강 1 spec**: G1 (`home.spec.ts` 의 onboarding banner assertion)
- **Carry-over (Sprint 23+)**:
  - G3/G5/G6 progress N/4 assertion 보강 — runtime 실행 가능한 fixture 확보 후
  - G4 SSE mock 디버깅 (skip 해제) — citation badge 렌더 path 정합성 확인
- **회귀**: `pnpm typecheck` → 0 error (Sprint 22 신규 spec 포함)

## 실행 가이드 (Stage 6 closeout 단계)

```bash
cd frontend
# 백엔드 + 프론트 dev 서버 기동
# (별도 터미널에서 backend: cd backend && uv run uvicorn src.main:app --port 8000)
pnpm dev  # localhost:3003 기동

# E2E 실행
pnpm exec playwright test
```

예상 PASS = 기존 11 spec + NEW 3 (G2/G7/G8) + 보강 1 (G1). 8 시나리오 중 G4 skip 유지, G3 HEAVY 조건부.

## Codex 1차 finding 반영 (참고)

- F1/F2 (lazy seed step=1 + commit placement) → BE event hook 통합 완료 (Task 2 E8)
- F3 (meeting.created_by_id) → step=3 trigger 정확화 완료 (Task 2 E10)
- F4 (backend/src/main.py) → router include 위치 정정 (Task 2 E7)
- F5 (src.common.database) → DI provider 정정 (Task 2 E6)
- F6 (PR2_MANAGED_COLUMNS) → drift gate 정확화 (Task 1 E4)
- F7 (RagService session) → embedding_repo.session 재사용 (Task 2 E11)
