<!-- Sprint 15 단일 PR description draft — Day 14 retro 후 push 시 paste -->

# Sprint 15 PR Description Draft

> **사용법**: Day 14 retro 후 `gh pr create` 시 본 doc을 paste.
> **타이틀** (70자 이내): `Sprint 15: Personal workspace + Memory module + Recall-first wedge`
> **base**: `main`  |  **head**: `sprint-15/personal-workspace`  |  **commits**: 28+ (retro doc / fix iter 추가 시 변동)

---

## PR Title (paste-ready)

```
Sprint 15: Personal workspace + Memory module + Recall-first wedge (R1~R8 + ADR-016/019)
```

---

## PR Body (paste-ready, gh pr create HEREDOC)

```markdown
## Summary

Sprint 15는 Kairos를 회의 도구에서 **AI 메모리 레이어 + Personal↔Team IA**로 피벗하는 첫 PR. PRD v3.0 §0+§2+§3.6 + 부록 A lock-in.

- **Personal workspace** (1인 격리, 팀 초대 불가) 자동 시드 + switcher
- **Memory module** (text+voice capture → distill → recall → promote) 신설 — `/api/v1/workspaces/{ws}/memory/*`
- **Recall-first wedge** prototype — search-first FAB UX, vector + keyword fallback
- **R8 14일 stagger** (founder manual outreach, retro 결과 별도 paste)
- **ADR-016** Personal↔Team IA + Promotion = 복제 + tombstone (AD-40~46)
- **ADR-019 (Phase A)** Gemini 2.5-flash EOL 마이그레이션 prep — 3.1-flash-lite GA 5.76x speedup / 20% cost 절감 검증

## 핵심 구현

### BE — Memory 도메인 신설 (`backend/src/memory/`)
- `models.py` MemoryItem + PromoteAudit + MemoryAiCall + MemoryQueryEmbeddingCache + MemoryEvent + workspaces.type
- `router.py` POST capture (202) / GET recall / GET metrics / GET detail (polling) / POST promote (202)
- `admin_router.py` /admin/memory/r2-cleanup (Cron secret token gate, Cloud Scheduler 호환)
- `service.py` BackgroundTask 분리 (distill 4.8s sync UX 차단) + I-9 workspace 격리 강제
- alembic migration `a1b2c3d4e5f6_sprint15_memory_workspace_type.py`

### FE — Memory page + Capture/Recall/Promote UI
- `/memory` 페이지 (B3 search-first FAB UX, recall 결과 카드)
- `CaptureSheet` (text + MediaRecorder MIME negotiation — Chrome webm / iOS mp4)
- `PromoteModal` (1-button promote to team workspace + audit row)
- `/admin/recall-metrics` (founder Clerk ID gate, R7 5 metric 노출)

### 추가 컴포넌트
- Personal workspace lazy seed (`auth/dependencies.py`) + race-safe (UNIQUE 충돌 retry)
- ProjectMember invariant (personal ws 단독 1명 보장)
- R2 30일 voice cleanup (Cloud Scheduler endpoint)
- DB-backed metrics (`memory_events` 테이블, Cloud Run stateless 호환)

### 헌법 (CONTEXT-MAP.md)
- I-18 신설: Promotion은 항상 복제 + tombstone, 이동 금지
- I-19 신설: Personal workspace는 1인 격리, 팀 초대 불가
- I-9 강화 (workspace 격리, memory recall에 적용)
- R-13는 Sprint 18+ ADR-017로 defer (cross-ws RAG)

### ADR
- **ADR-016**: Personal↔Team IA (Option D 채택, AD-40~46)
- **ADR-019 (draft, Phase A validated)**: Gemini 2.5-flash → 3.1-flash-lite 마이그레이션. Phase B 코드 swap = Sprint 16 첫 commit (Gemini EOL 2026-06-17 회피)

## 검증 결과

- **BE pytest**: 144 pass / 2 pre-existing fail (services/test_transcription.py mp3 환경 — Sprint 15 무관)
- **FE tsc**: 0 errors
- **alembic upgrade head**: local + dev DB 적용 OK (memory_items / promote_audit / memory_ai_calls / memory_query_embedding_cache / memory_events / workspaces.type 신설)
- **Day 0 spike (text)**: text 3/3 success, e2e p95 6590ms (60s threshold 1 order 여유), $0.0026/tester/week
- **ADR-019 Phase A spike**: 3.1-flash-lite distill p50 908ms (5.76x speedup) / cost 20% 절감 / schema 3/3
- **R8 14일 stagger**: 별도 retro 결과 paste (`docs/dev-log/sprint-15-r8-outreach.md §6`)

## R8 외부 검증 결과 (TBD — R8 14일 stagger 진행 예정)

> **현재 상태**: R8 outreach 미시작 (Day 0 이전). 14일 stagger 종료 후 본 PR 댓글로 결과 추가 예정.
> **Sprint 16 분기 결정**: `docs/dev-log/2026-05-14-sprint16-plan-draft.md §3` Best/Medium/Min 매트릭스 기반.
> **머지 정책**: 본 PR은 **draft** 상태로 push. R8 결과 확인 후 ready for review → main 머지 결정.
> **메트릭 추적**: `docs/dev-log/sprint-15-r8-outreach.md §6` Final Result 표 + `docs/dev-log/sprint-15-r8-day14-retro-template.md` §7 fill-in.

## Files changed (요약)

- `backend/src/memory/*` (신설 8 file): models / router / service / repository / schemas / exceptions / admin_router / dependencies
- `backend/scripts/sprint15_day0_spike.py` + `dogfood_smoke.py` (자동화 2종)
- `backend/migrations/.../a1b2c3d4e5f6_*.py` (alembic)
- `frontend/src/app/(app)/memory/page.tsx` + `(app)/admin/recall-metrics/page.tsx`
- `frontend/src/features/memory/*` (api / hooks / types / 3 component)
- `docs/dev-log/` (ADR-019 + sprint-15-plan + plan-patch + Stage 0/1/2/3/4 handoff + brainstorm + codex-review + cost-spike + r8-outreach + sprint-16-plan-draft)
- `CONTEXT-MAP.md` I-18/I-19 추가
- `DESIGN.md` Workspace Types + Recall UI patches

## Test plan

- [ ] BE `pytest tests/` → 144 pass 확인
- [ ] FE `pnpm tsc --noEmit` → 0 errors
- [ ] Migration: `alembic upgrade head` idempotent 재실행
- [ ] Local dogfood: `python scripts/dogfood_smoke.py --token $CLERK_JWT` → 5+1 step pass
- [ ] FE 브라우저: /memory FAB → CaptureSheet → polling → recall → PromoteModal → team ws 복제
- [ ] /admin/recall-metrics founder Clerk gate (다른 user 접근 시 redirect 또는 404)
- [ ] Cloud Scheduler dry-run: `POST /api/v1/admin/memory/r2-cleanup?days=30` with X-Cron-Token

## 후속 (Sprint 16+)

- **Sprint 16 첫 commit**: ADR-019 Phase B 코드 swap (`gemini-2.5-flash` → `gemini-3.1-flash-lite`, 6 spot 단일 commit)
- **Sprint 16 분기**: R8 결과 기반 Best/Medium/Min (`docs/dev-log/2026-05-14-sprint16-plan-draft.md §3`)
- **Sprint 17+ defer**: cross-ws RAG (ADR-017) / Promotion review queue (ADR-018) / BM25 ranking / Embedding retry queue

## Breaking changes

- 없음. workspaces.type 신설 컬럼 default='team'으로 기존 row 호환.
- Memory 도메인은 신설 모듈, 기존 API 영향 X.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## gh pr create 실행 예시 (Day 14 retro 후)

```bash
# 1. R8 retro 결과 §R8 외부 검증 결과 섹션 채우기 (Best/Medium/Min)
# 2. push (사용자 승인 후)
git push -u origin sprint-15/personal-workspace

# 3. PR 생성 (위 PR Body 그대로 paste — HEREDOC)
gh pr create --base main --title "Sprint 15: Personal workspace + Memory module + Recall-first wedge (R1~R8 + ADR-016/019)" --body "$(cat docs/dev-log/sprint-15-pr-description-draft.md | sed -n '/^## PR Body/,/^---$/p' | sed '1,3d;$d' | tail -n +1)"
```

또는 더 간단:
```bash
gh pr create --base main --title "..." --body-file <(awk '/^```markdown$/,/^```$/' docs/dev-log/sprint-15-pr-description-draft.md | sed '1d;$d')
```

---

## 체크리스트 (push 전)

- [ ] Stage 5-4 design-review 완료 (P0 fix / P1+ BL 등재)
- [ ] Stage 5-6 qa Exhaustive Health ≥8/10
- [ ] BE 144 pass 재확인
- [ ] FE tsc clean 재확인
- [ ] alembic upgrade head 적용 확인 (prod DB 별도)
- [ ] PR description §"R8 외부 검증 결과" TBD placeholder 갱신 (R8 14일 진행 예정 명시)
- [ ] Docs sync 섹션 첨부 — `git diff --stat docs/ backend/**/CONTEXT.md CONTEXT-MAP.md` 결과
- [ ] 사용자 push 승인 (`PR push만 사용자 승인` 정책)
- [ ] `gh pr create --draft` flag 강제 (R8 결과 전까지 머지 X)

## R8 결과 후 (별도 세션)

- [ ] R8 14일 stagger 진행 + retro template fill-in
- [ ] `docs/dev-log/sprint-15-r8-day14-retro-template.md` §6/§7 작성
- [ ] PR 댓글로 R8 결과 paste (또는 §"R8 외부 검증 결과" 본문 갱신)
- [ ] Sprint 16 분기 결정 (Best/Medium/Min) → `2026-05-14-sprint16-plan-draft.md` rename `2026-05-28-sprint16-plan.md`
- [ ] PR draft → ready for review → main 머지
