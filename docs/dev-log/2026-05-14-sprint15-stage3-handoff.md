<!-- Sprint 15 Stage 3 진입 인계 — 신규 세션 brief (Stage 0+1+2 완료 후) -->

# Sprint 15 Stage 3 Kickoff Handoff (2026-05-14)

> **목적**: Sprint 15 Stage 0+1+2 완료 후 신규 세션 인계. 다음 세션이 본 doc + Stage 1 design doc + memory만으로 Stage 3 진입 가능.
>
> **다음 세션 첫 read**: 본 doc §6 read 순서 → §5 Stage 3 진입 instructions.

---

## §1. 현재 상태 (2026-05-14 종료 시점)

### 브랜치 + commits

`sprint-15/personal-workspace` (origin/main 분기, 4 commits ahead, **not pushed**).

| Commit | Stage | 내용 |
|--------|-------|------|
| `d7faee1` | pre-Stage 0 | handoff doc cherry-pick (D-1 해소) |
| `ff4c011` | pre-Stage 0 | I-17 → I-18 slot 정정 9건 (D-2 해소) |
| `0cce48c` | Stage 0 | grill v3 산출 doc — `docs/dev-log/2026-05-14-constitution-grill-v3.md` (6 Q + 헌법 patch 본문 lock-in) |
| `c7d2fcb` | Stage 2 | DESIGN.md Recall-first patch (Workspace Types + Recall UI) |

### Stage 1 artifact (uncommitted, ~/.gstack에 lock-in)

`~/.gstack/projects/woosung-dev-kairos/woosung-sprint-15-personal-workspace-design-20260514-090026.md` — 520줄 design doc. Status APPROVED (2026-05-14 user D11=A). Spec review 2 iter / 6 issues fixed / 8.5+/10. **Stage 3 진입 시 가장 중요한 source of truth**.

---

## §2. Stage 1 핵심 결정 — Recall-first wedge pivot

**CRITICAL PIVOT** (Codex 2nd opinion Premise 5 revision 수용):

기존 plan (Sprint 15 진입 prompt): S15-T1~T7 Personal workspace infra + Sprint 16 v1.6 Promotion wedge
→ **신규 plan**: **S15-R1~R8 Recall-first prototype**. v0 Recall (capture + AI distill + 재호출) = wedge. Promotion = retention/expansion feature, v1 wedge 아님 → Sprint 17+ defer.

근거: 6 forcing Q 답 패턴 (외부 user 0 + persona 검증 0 + dogfooding 깊이 0 + future-fit 가설) + Codex evidence pattern (10명/7일/3 unprompted/1 paying) → wedge sharper.

---

## §3. Stage 2 design system patch (DESIGN.md)

DESIGN.md §Workspace Types + §Recall UI 섹션 신규.
- Restrained philosophy 유지 (1 accent #3ECFB4 + neutrals). 색상 신규 0.
- Personal/Team 구분 = `Lock` icon + text-muted (Personal) / `Users` icon + text-accent (Team). Caption 11px Geist Mono pill badge.
- Recall card 기존 surface + border + radius-md (6px) 패턴 재사용.
- Promote 1-button = ghost variant (retention feature 위상). 클릭 후 modal CTA만 primary.
- `/memory` page layout + feature flag `NEXT_PUBLIC_RECALL_ENABLED` 정의.

---

## §4. Sprint 15 R1~R8 task spec (Stage 1 design doc §1 추출)

총 build ~11h + 14일 stagger.

| ID | 작업 (핵심) | Effort | Acceptance criteria 위치 |
|----|------------|--------|------------------------|
| **R1** | BE `/memory` API (capture voice + text → Whisper → Gemini distill → store) | 2.5h | design doc §1 R1 row |
| **R2** | DB `memory_items` table + alembic | 1h | design doc §1 R2 row |
| **R3** | BE recall endpoint (vector + keyword fallback) + 헌법 I-9 4-C atomic patch | 1.5h | design doc §1 R3 row |
| **R4** | FE `/memory` page (녹음 + 텍스트 + 검색 + Personal/Team 탭) | 2h | design doc §1 R4 row + DESIGN.md §Recall UI |
| **R5** | BE Personal workspace lazy seed + UNIQUE partial index + service-layer invariant assertion (alembic + 코드 atomic, CONTEXT-MAP I-19 본문은 Sprint 17+) | 1.5h | design doc §1 R5 row + §4 ADR-016 status update |
| **R6** | FE Promote 1-button (ghost variant) + modal | 1h | design doc §1 R6 row + DESIGN.md §Promote |
| **R7** | Instrumentation (metrics only, OTel 아님) | 1.5h | design doc §1 R7 row |
| **R8** | PERSONA-002/003 outreach 3 채널 + 5명 인터뷰 + 7일 testing | 2-3일 + 7일 | design doc §1 R8 row + §Success Criteria |

### Schedule stagger (Day 1~14)

- **Day 1-3**: R1~R5 build + R8 outreach 동시 시작
- **Day 3 end**: R1~R3 quality gate (founder capture ≥5 + recall thumbs-up ≥3). Fail 시 R6~R7 block + R3 fix 우선
- **Day 4-5**: R6+R7 build + 1st PERSONA 인터뷰
- **Day 6-12**: PERSONA 5명 testing window + founder dogfooding 병행
- **Day 13-14**: 인터뷰 결과 종합 + success criteria 평가 + Sprint 16 결정

### Success Criteria 3 tiers (design doc §Success Criteria)

- **Best**: PERSONA 5명 + 3명+ unprompted + 1명+ paying signal + Promote ≤30% of recall
- **Medium**: PERSONA 2~4명 + 2명+ unprompted
- **Minimum (founder + 1)**: 외부 응답 ≤1명 시 자동 전환 (Day 7 SLA)

### Outreach SLA

- Day 0: 3 채널 동시 시작 (인디해커즈 / X DM / HN-Show 또는 IH-Show)
- Day 3: 0/5 응답 시 cold outreach 채널 확장 (LinkedIn / Reddit r/SaaS / 본인 트위터 친구 DM)
- Day 7: 1/5 이하 응답 시 success criteria = Minimum 자동 전환

---

## §5. Stage 3 진입 instructions

`.ai/templates/workflow.md` Stage 3 정의 그대로:

1. **`design-shotgun`** — 3 핵심 화면 mockup (각 화면 3-5 variant)
   - 화면 1: Workspace switcher (Personal/Team 시각 구분 + Notion 패턴)
   - 화면 2: `/memory` page (capture row + 검색 + Personal/Team 탭 + result list)
   - 화면 3: Promote modal (target team workspace select + audit row preview)

2. **`brainstorming`** — 5 화면 우선순위 (R1~R8 task별 wireframe + edge case)
   - capture flow (voice 녹음 / 텍스트 입력 / 파일 size validation / Whisper fail)
   - distill 결과 view (suggested_visibility 자동 선택 + 사용자 override UI)
   - recall query input + 결과 (vector vs keyword fallback signal)
   - 1st-time onboarding (feature flag ON 시 사이드바에 /memory 신규 메뉴 첫 진입)
   - PERSONA testing demo flow (외부 5명에게 보여줄 시나리오)

3. **`writing-plans`** — Sprint 15 R 구현 plan 상세 (`docs/dev-log/sprint-15-plan.md` 신규)
   - R1~R8 각각 implementation 단계 (TDD test cases 먼저 listing)
   - Generator-Evaluator subagent 패턴 (Sprint 14 8단계 참조)
   - Vertical Slice task 분해 (BE → DB → FE 단일 흐름)

4. **`/codex`** — 적대적 plan 검토
   - Sprint 15 plan에 hidden complexity 발견
   - PERSONA outreach 채널 best practice (Codex 시각)
   - Whisper API quota / Gemini distill cost 사전 측정

산출:
- `docs/dev-log/sprint-15-plan.md` (writing-plans 출력)
- `~/.gstack/projects/woosung-dev-kairos/designs/sprint-15-mockups/` (design-shotgun 산출)
- Stage 4 진입 입력 = R1 TDD test cases (먼저 작성) → impl

---

## §6. 다음 세션 첫 read 순서

| 순서 | 파일 | 역할 |
|------|------|------|
| 1 | `~/.gstack/projects/woosung-dev-kairos/woosung-sprint-15-personal-workspace-design-20260514-090026.md` | Stage 1 design doc — **가장 중요한 source of truth**. Recall-first wedge plan 상세. |
| 2 | `docs/dev-log/2026-05-14-sprint15-stage3-handoff.md` | 본 doc — Stage 3 진입 brief |
| 3 | `docs/dev-log/2026-05-14-constitution-grill-v3.md` | Stage 0 grill — 헌법 patch 본문 (I-9 patch / I-18 신설 / I-19 신설) |
| 4 | `DESIGN.md` §Workspace Types + §Recall UI | Stage 2 design system patch |
| 5 | `docs/dev-log/2026-05-14-sprint15-handoff.md` | 원본 Sprint 15 진입 brief (Stage 0 진입 전 인계, history 보존) |
| 6 | (필요 시) `docs/dev-log/016-personal-team-ia.md` | ADR-016 (Personal↔Team IA) — 단 implementation 우선순위는 Stage 1에서 reframe |

memory 또는 grep으로 확인 가능:
- `project-sprint15-stages-0-1-2-done` memory entry (auto-load via MEMORY.md)

---

## §7. 정책 + lessons (handoff §5 + Stage 1 추가)

### 사용자 정책 (변경 없음)

- 자동 커밋 OK. PR만 사용자 승인.
- workflow.md 직접 read 우선 (mattpock lesson — 추측 답변 금지).
- atomic doc update 강제 ([[feedback_atomic_doc_update]]).

### Lessons learned (over-correction 경계, 본 세션 + Stage 1 추가)

1. **Sprint 14 패턴 anchor 금지** — Sprint 14 = fix, Sprint 15 = v3.0 위 1차 구현 + Recall-first pivot이라 risk profile 다름.
2. **PRD v3.0 thesis pivot ≠ verified thesis** — 외부 user 0 + persona 검증 0 + dogfooding 깊이 0 = thesis 크기 vs evidence 크기 mismatch. **Codex 2nd opinion이 이를 sharper challenge로 surface**. → 신규 세션에서도 Codex 또는 외부 voices 활용 적극 권장.
3. **mattpock = `.ai/templates/workflow.md` Stage 0**. 사용자 own slang. 추측 답변 금지 → workflow.md 직접 참조 우선.
4. **Build vs validate trade-off 인지** — Q4 A 선택 시 self-contradiction 인지 위 진행. parallel validation track (S15-R8 PERSONA outreach)이 build와 atomic.
5. **Atomic doc + 코드** — 헌법 I-9 patch는 S15-R3 commit과 atomic. I-19 코드 (서비스 layer assertion)는 S15-R5 commit과 atomic. CONTEXT-MAP 본문 등재는 Sprint 17+ 정식 신설 시.

### Stage 3에서 회피할 위험

- **design-shotgun에서 색상 신규 추가 유혹** → DESIGN.md Restrained philosophy 유지 (Stage 2 patch 정합)
- **brainstorming에서 6 input architecture 부활 유혹** → Stage 1 design doc Codex challenge 정합: voice + text only, 나머지 4 inputs (file/email/messaging/handwriting) skip
- **writing-plans에서 Promotion API spec 과대화** → Promotion = ghost button + 1 audit row 만. Multi-team/chain/review queue 등 Sprint 17+ defer

---

## §8. 잔여 PR / merge / push

- 현 commits (`d7faee1` / `ff4c011` / `0cce48c` / `c7d2fcb`) = **not pushed**. origin에 미반영.
- Stage 4 R1~R8 구현 commit과 함께 단일 PR로 main에 merge 예정.
- 다음 세션 진입 시 push 여부 사용자 결정 (Stage 3 산출 commit 이후 자연스러운 push 시점).

---

**STATUS**: Stage 0+1+2 DONE. Stage 3 진입 준비 완료.
