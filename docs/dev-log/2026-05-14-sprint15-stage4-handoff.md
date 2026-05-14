<!-- Sprint 15 Stage 4 진입 인계 — 신규 세션 brief (Stage 0+1+2+3 완료 후) -->

# Sprint 15 Stage 4 Kickoff Handoff (2026-05-14)

> **목적**: Sprint 15 Stage 3 완료 후 신규 세션 인계. 다음 세션이 본 doc + plan + patch + memory만으로 Stage 4 R1~R8 진입 가능.
>
> **다음 세션 첫 read**: §5 read 순서 → §4 Stage 4 진입 instructions.

---

## §1. 현재 상태 (2026-05-14 종료 시점)

### 1.1 브랜치 + commits

`sprint-15/personal-workspace` (origin/main 분기, **7 commits ahead, not pushed**).

| Commit | Stage | 내용 |
|--------|-------|------|
| `d7faee1` | pre-Stage 0 | handoff doc cherry-pick (D-1 해소) |
| `ff4c011` | pre-Stage 0 | I-17 → I-18 slot 정정 9건 (D-2 해소) |
| `0cce48c` | Stage 0 | grill v3 산출 doc (헌법 patch 본문 lock-in) |
| `c7d2fcb` | Stage 2 | DESIGN.md Recall-first patch |
| `c9a774e` | Stage 3 handoff | Stage 3 진입 인계 doc |
| `5716850` | Stage 3 Q2+Q3 | brainstorm + sprint-15-plan |
| `173b556` | Stage 3 Q4 | codex review + FIX iter 1 patch |

push 시점 = Stage 4 R1~R8 완료 후 단일 PR 생성 시. 현재는 보존.

### 1.2 Stage 3 산출 위치

| Q | 산출 | path |
|---|------|------|
| Q1 design-shotgun | approved.json (A1+B3+C1) + 9 mockup | `~/.gstack/projects/woosung-dev-kairos/designs/sprint-15-mockups-20260514/` |
| Q2 brainstorm | 5 화면 wireframe + 5 Open Q lock-in | `docs/dev-log/2026-05-14-sprint15-brainstorm.md` |
| Q3 plan | sprint-15-plan R1~R8 (2477줄) | `docs/dev-log/sprint-15-plan.md` |
| Q4 codex | 20 finding 적대적 검토 | `docs/dev-log/2026-05-14-sprint15-codex-review.md` |
| Q4 patch | FIX iter 1 (15 must-fix inline) | `docs/dev-log/2026-05-14-sprint15-plan-patch.md` |

---

## §2. Stage 3 핵심 결정 (Stage 4 진입 시 반드시 인지)

### 2.1 Approved variants

- **A1** Workspace switcher personal-first dropdown
- **B3** /memory page **search-first FAB** capture (Opus pick vs UI/UX B1 분기에서 B3 채택 — recall이 페이지 본질 가정)
- **C1** Promote modal dropdown + 즉시 promote (ghost button 위상 정확)

### 2.2 5 Open Q lock-in

| ID | 결정 |
|----|------|
| O-A | recall source memo Top **3** |
| O-B | keyword fallback rank = **token overlap count** (BM25 = S17+ defer) |
| O-C | "would miss this?" survey = **인터뷰 only** (in-app modal 0) |
| O-D | PERSONA outreach = **인디해커즈 1st → X DM 2nd → HN-Show 3rd** |
| O-E | voice audio = **R2 store + 30일 TTL** |

### 2.3 codex 적대적 검토 결과 (FIX iter 1)

20 finding 중 **15 must-fix** patch doc inline. critical:

- **A3** R1 acceptance 변경: 202 + processing 즉시 + BackgroundTask transcribe→distill→embed
- **A6** capture 후 embedding 경로 추가 (vector recall 0건 막기)
- **A4** Gemini 2.5 Flash EOL 2026-06-17 — ADR + Day 0 deprecation check
- **A12** T-1 fixtures + ffmpeg Dockerfile 신규 task (T0 다음, R1 이전)
- **C1** Whisper 비용 10× 정정 — `gpt-4o-mini-transcribe` $0.003/min × 5min × 50 = $0.75
- **C4** latency metric 분리 (enqueue p95 ≤500ms / transcribe ≤45s / distill ≤3s / embedding ≤1s / recall ≤2s)
- **C5** Day 0 spike scope 구체화 (10-sample, iOS/한국어/silent/3000자 등)
- **C7** memory_events DB table (Cloud Run stateless 정합, in-memory tracker 폐기)
- **B1+B2+B3** outreach funnel 80 sent → 8 booked → 5 completed → 3 retained, Day 1 booking gate, Minimum redefine

### 2.4 over-correction guardrails 유지

- Sprint 14 패턴 anchor 금지
- PRD v3.0 thesis pivot ≠ verified thesis (외부 user 0)
- DESIGN.md Restrained philosophy (색상 신규 0)
- voice + text only (6-input architecture 부활 X)
- Promotion = ghost button + audit row 1개 (multi-team/chain/review queue S17+ defer)

---

## §3. Stage 4 Task 순서 (revised, patch 적용 후)

| 순서 | Task | 산출 |
|------|------|------|
| 1 | **Day 0 parallel** | (1) R8 outreach 80건 (warm_intro 10 + indie_kr 20 + x_dm_kr 20 + cold 30) (2) Day 0 cost spike 10 sample 실측 (`backend/scripts/sprint15_day0_spike.py`) — founder time ~1h + script run |
| 2 | **T0** | ADR-016 AD-41 reframe + docs/TODO.md Gemini EOL P0 추가 |
| 3 | **T-1** ⚠️ NEW | conftest fixtures (auth_user/memory_client/personal_ws/team_ws/seed_memory) + Dockerfile ffmpeg install |
| 4 | **R2** | alembic memory_items + workspaces.type + promotion_audit + **backfill SQL** + memory_ai_calls + memory_query_embedding_cache + memory_events |
| 5 | **R1** | BE memory capture API — **BackgroundTask architecture** (202 + processing, transcribe→distill→embed 분리) + normalize_audio (ffmpeg) + memory_ai_calls usage tracking |
| 6 | **R3** | BE recall endpoint — vector + keyword fallback + pgvector Vector type binding + embedding query cache + I-9 atomic patch (CONTEXT-MAP) |
| 7 | **R4** | FE /memory page B3 layout + MediaRecorder MIME negotiation + capture sheet + recall result card |
| 8 | **R5** | BE personal lazy seed + ON CONFLICT race fix + ProjectMember invariant + I-19 코드 atomic |
| 9 | **R6** | FE Promote modal C1 + BE promote endpoint + audit row |
| 10 | **R-CRON** ⚠️ NEW | R2 30일 cleanup admin endpoint + GCP Cloud Scheduler setup |
| 11 | **R7** | memory_events DB-backed metrics + founder admin page |
| 12 | **R8 진행** | Day 1+ booking gate + Day 3 completed gate + Day 6 activation gate + Day 14 retro |

### 3.1 Day 3 quality gate (revised)

- founder dogfooding capture ≥5, recall thumbs-up ≥3 → R6/R7 진입
- Demos booked < 2 → Sprint freeze + outreach-only pivot (Sprint 16 redefine)

---

## §4. Stage 4 진입 instructions

### 4.1 First failing test

```bash
cd backend && pytest tests/memory/test_api.py::test_post_memory_text_returns_202_processing -v
# Expected: FAIL — fixtures (auth_user/memory_client/personal_ws) + memory module 미존재
```

→ T-1 fixtures (patch §2) 우선 → R2 alembic → R1 BackgroundTask → 이후 sequence

### 4.2 Day 0 spike script first run

```bash
# Stage 4 진입 즉시 (founder time ~1h)
cd backend && python scripts/sprint15_day0_spike.py
# 결과 → docs/dev-log/sprint-15-cost-spike.md
# Invalidate thresholds (patch §12):
#  - transcription failure > 5%
#  - end-to-end job p95 > 60s
#  - Gemini JSON invalid > 10%
#  - cost per tester per week > $2
#  - recall p95 at 100 chunks > 2s
```

### 4.3 R8 Day 0 outreach (parallel, founder manual)

3 채널 동시 시작:
- 인디해커즈 Discord/Slack #show-and-tell (20건)
- X DM Notion/Mem.ai 팔로워 (20건)
- HN-Show 또는 IH-Show 1 post
- warm_intro Korean founder network (10건)
- cold expansion preload (LinkedIn / Reddit r/SaaS 30건)

outreach 로그: `docs/dev-log/sprint-15-r8-outreach.md`

opening template (patch §11 B4 fix):
```text
혹시 창업 아이디어/결정 메모를 Notion, Apple Notes, DM에 흩어놓고 나중에 못 찾는 편인가요?
7일짜리 작은 prototype을 테스트 중입니다. 30분만 화면공유로 써보고, 마음에 안 들면 바로 끊어도 됩니다.
조건: 최근 7일 안에 실제로 다시 찾고 싶었던 메모/생각이 있어야 합니다.
```

### 4.4 Execution mode

writing-plans skill `execution handoff` 정합:

| 옵션 | 의미 |
|------|------|
| **Subagent-Driven** (추천) | `superpowers:subagent-driven-development` — fresh subagent per task + two-stage review |
| Inline Execution | `superpowers:executing-plans` — 단일 세션 + checkpoint review |

Subagent-Driven 추천 근거: R1~R8 = 14일 stagger + 12+ commits 예상 → context window 부담 ↓, isolation 강화.

---

## §5. 다음 세션 첫 read 순서

| 순서 | 파일 | 역할 |
|------|------|------|
| 1 | `docs/dev-log/sprint-15-plan.md` | **base plan** — R1~R8 TDD test cases + Vertical Slice |
| 2 | `docs/dev-log/2026-05-14-sprint15-plan-patch.md` | **FIX iter 1 patch** — 15 must-fix 적용 (patch 우선) |
| 3 | `docs/dev-log/2026-05-14-sprint15-stage4-handoff.md` | 본 doc — Stage 4 진입 brief |
| 4 | `docs/dev-log/2026-05-14-sprint15-codex-review.md` | codex 20 finding 원본 근거 (참고용) |
| 5 | `docs/dev-log/2026-05-14-sprint15-brainstorm.md` | 5 화면 wireframe + 5 Open Q lock-in |
| 6 | `~/.gstack/projects/woosung-dev-kairos/woosung-sprint-15-personal-workspace-design-20260514-090026.md` | Stage 1 design doc — wedge spec 근거 |
| 7 | `DESIGN.md` §Workspace Types + §Recall UI + §Promote Modal | Stage 2 design system patch |
| 8 | `~/.gstack/projects/woosung-dev-kairos/designs/sprint-15-mockups-20260514/approved.json` | A1+B3+C1 select 결정 |

memory auto-load via MEMORY.md:
- `project-sprint15-stage3-done` (가장 최신, Stage 4 진입 입력)

---

## §6. 정책 + lessons

### 6.1 사용자 정책

- 자동 commit OK. PR push만 사용자 승인.
- workflow.md 직접 read 우선 (mattpock lesson).
- atomic doc update 강제.

### 6.2 atomic commit map (Stage 4)

- **R3 commit**: BE recall endpoint + CONTEXT-MAP.md I-9 4-C inline patch + embeddings/service.py:create_chunk assertion — 단일 commit
- **R5 commit**: alembic add_workspace_type + auth/dependencies.py ON CONFLICT seed + UNIQUE partial index + ProjectMember invariant — 단일 commit. CONTEXT-MAP I-19 본문 등재는 Sprint 17+
- **R6 commit**: promote API + audit row + embedding bgtask + DESIGN.md Promote Modal CTA 검증 — 단일 commit

### 6.3 Lessons learned (Stage 3 추가)

1. **patch doc 분리 traceable**: base plan + patch 함께 참조하는 model이 inline edit보다 cleaner. plan 본문에 patch 참조 라인 한 줄만 추가.
2. **Opus + ui-ux-pro-max 2 평가자 분기 surface**: B1 vs B3 같은 분기 시 사용자에게 명시. 자동 결정 금지.
3. **codex 적대적 검토 mandate**: writing-plans 후 mandatory. Sprint 14 over-correction 회피.
4. **Gemini 2.5 Flash EOL 2026-06-17 인지**: Sprint 15 시작 +34일. Sprint 16 진입 시 EOL 대응 ADR 필요.
5. **사용자가 "잘 모르겠다" 표현 시**: 옵션 표 + 추천 + 결정 force surface. 무한 대기 X.

### 6.4 회피 위험

- **R1 진입 직전 plan 본문만 보고 시작 X**: patch doc 필수 read. 안 보면 A3 (2s p95) + A6 (embedding 경로 부재) 잡을 수 없음.
- **B3 search-first FAB UI 시 capture 묻힘 risk**: 1st-time onboarding empty state arrow + pulse animation 필수 (patch §7 wireframe).
- **MediaRecorder Safari/iOS**: A1 fix — MIME negotiation 안 하면 iOS 외부 PERSONA 첫 capture에서 텍스트로 떨어짐.

---

## §7. 잔여 task carry-over

### 7.1 Sprint 14 carry-over (여전히)

- Clerk Production key 발급 — R8 외부 5명 PERSONA testing 전 founder manual 작업

### 7.2 Sprint 17+ backlog (Stage 0+1+2+3에서 결정)

memory entry + Stage 0 grill v3 §8.1~§8.3 + Stage 1 design doc §11 + patch doc §3 정합. 주요:

- S17-T-AD16-IMPL: ADR-016 정식 implementation
- S17-T-AD17A: ADR-017 (cross-ws RAG opt-in)
- S17-T-AD18A: ADR-018 (Promotion review queue)
- S17-T-EMBED-RETRY: 임베딩 실패 retry queue
- S17-T-WS-NORMALIZE: 기존 16 frontend site refactor
- S17-T-GEMINI-EOL: Gemini 2.5 Flash → 2.5 Pro / Flash 2.0 마이그레이션 ADR ⚠️ NEW
- S17-T-PROMOTION-REFRAME: ADR-016 AD-41 본문 patch
- S17-T-RECALL-BM25: BM25 ranking 도입 (token overlap 한계 시) ⚠️ NEW
- S18-T-RAG-XWS: cross-ws RAG SQL IN expand

---

**STATUS**: Stage 0+1+2+3 DONE. 7 commits ahead origin/main not pushed. Stage 4 진입 준비 완료.

**다음 세션 진입 시 즉시 실행**:
1. `git status` — 7 commits, clean tree 확인
2. read sequence §5
3. Stage 4 first action — T-1 fixtures + Day 0 spike + R8 outreach 3 채널 parallel
