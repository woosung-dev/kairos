<!-- Sprint 15 Stage 4 코드 완료 후 인계 — R8 14일 진행 / dogfooding / 다음 세션 -->

# Sprint 15 Stage 4 Done Handoff (2026-05-14)

> **목적**: Sprint 15 Stage 4 코드 + Day 0 1차 spike 완료 후 신규 세션 인계. 다음 세션 = R8 14일 retro 또는 fix iter 2 또는 Sprint 16 진입.
>
> **다음 세션 첫 read**: 본 doc → memory (`project_sprint15_stage4_done.md`).

---

## §1. 현재 상태 (2026-05-14 종료 시점)

### 1.1 브랜치

`sprint-15/personal-workspace` — **21 commits ahead origin/main, not pushed**.

| Phase | Commit count |
|-------|-------------|
| Pre-Stage 4 (handoff + grill + plan + patch + ADR) | 8 |
| Stage 4 (T0/Day0/T-1/R2/R1/R3/R4/R5/R6/R-CRON/R7 + env scaffold + spike 결과) | 13 |
| **Total** | **21** |

### 1.2 Stage 4 commit 매핑

| Commit | Task | Test |
|--------|------|------|
| `94f2033` | T0 | docs only |
| `4aae0ae` | Day 0 spike script + outreach scaffold | n/a |
| `fda22c7` | T-1 fixtures | 1 RED |
| `b3f5606` | R2 alembic + memory module | 6 schema |
| `554ea6b` | R1 BE memory API BackgroundTask | 10 |
| `3fa8922` | R3 recall + I-9 atomic | 4 |
| `fc3b927` | R4 FE /memory page | tsc 0 |
| `2b3c385` | R5 personal seed + invariant | 2 |
| `159a8fb` | R6 promote 1-button | 4 |
| `0555c28` | R-CRON cleanup endpoint | 4 |
| `07ae8c1` | R7 metrics + admin page | 4 |
| `462cc29` | env scaffold + samples/ | n/a |
| `057865c` | Day 0 1차 spike 결과 | n/a |

### 1.3 검증 통과

- BE 전체: **144 pass / 2 pre-existing fail** (services/test_transcription.py mp3 환경, Sprint 15 무관)
- FE tsc: **0 errors**
- BE startup: health 200, /memory 401 (auth), R-CRON valid token 200, days=0 422
- alembic upgrade head: local DB에 memory_items / promotion_audit / memory_ai_calls / memory_query_embedding_cache / memory_events + workspaces.type 신설 완료

### 1.4 Day 0 1차 spike 결과 (text-only)

- text 3/3 success
- e2e p50/p95 = 5528ms / 6590ms (60s threshold 1 order 여유)
- cost / tester / week = $0.0026 (3 orders 여유)
- Gemini distill 4.8s → R1 BackgroundTask 정량 정당화
- Gemini EOL probe: 표면 신호 없음

---

## §2. R8 14일 stagger gate

R8 = 코드 X, founder manual + retro 후 결정.

| Day | Gate | 통과 조건 | Fail action |
|-----|------|----------|-------------|
| 0 | Outreach 발송 | 80건 (Best) / 50 (Medium) / 30 (Min) | 30 미달 → 즉시 cold expansion |
| 1 | Booking gate | ≥3 (cumulative) | <3 → cold expansion (LinkedIn / Reddit / 유료 panel) |
| 3 | Completed gate | ≥2 demos completed | <2 → Sprint freeze, Sprint 16 = outreach-only |
| 6 | Activation gate | 2/3 demos에서 Day-2 active (capture ≥3 + recall ≥1) | <2/3 → wedge re-evaluation |
| 14 | Retro | Best/Medium/Min 분기 | Min만 통과 시 Sprint 16 = "Build freeze + outreach sprint" |

> R8 outreach 로그 = `docs/dev-log/sprint-15-r8-outreach.md`
> 인터뷰 결과 + Sprint 16 결정도 동일 doc에 추가

---

## §3. Founder pending (manual)

| 작업 | 시간 | 우선 | 의존 |
|------|-----|------|------|
| 1. Local dogfooding 5 시나리오 | ~1h | 즉시 | alembic upgrade head 적용됨 |
| 2. R8 outreach 80건 발송 | ~2h | 즉시 | 없음 |
| 3. Audio 7 sample 녹음 + 2차 spike | ~45분 | 선택 | 없음 |
| 4. Clerk Production key 발급 | ~10분 | R8 Day 3 직전 | 없음 |

### 3.1 Local dogfooding 5 시나리오

```bash
# 사전
cd backend && uv run alembic upgrade head  # 적용됨, 재실행 idempotent
cd backend && uv run uvicorn src.main:app --reload &
cd frontend && pnpm dev

# 브라우저
http://localhost:3000

# 시나리오
1. /memory 진입 → 사이드바 Memory + NEW pill 보이는지
2. FAB(+) → CaptureSheet → 텍스트 capture → 202 + processing
3. polling → status=active + distilled_json 채워지는지
4. 검색 → recall result (vector 또는 keyword fallback)
5. 결과 카드 [팀으로 올리기] → PromoteModal → team ws 선택 → 복제 OK
6. /admin/recall-metrics → 5 metric 노출 (founder Clerk ID gate)
```

### 3.1.a BE-only 자동화 smoke (시간 절감)

`backend/scripts/dogfood_smoke.py` — 5+1 시나리오 BE 직접 호출. ~10분 → ~30초.

```bash
# Clerk JWT 추출 (브라우저 devtools → Application → Cookies → __session 또는 Clerk dashboard)
export CLERK_JWT=eyJ...

cd backend && uv run uvicorn src.main:app --reload &
cd backend && uv run python scripts/dogfood_smoke.py
```

step 1~6 pass/fail + 누적 elapsed 출력. FE 시각 검증 (사이드바 NEW pill / FAB / Modal)은 별도 브라우저 확인. 본 smoke = BE coverage only.

### 3.2 Audio sample 녹음 가이드

`backend/scripts/samples/README.md` 참조. 7개 audio (chrome 10s/60s/5min, ios 10s/60s, ko_filler 60s, silent 10s). 녹음 후:

```bash
cd backend && uv run python scripts/sprint15_day0_spike.py
# 결과 → docs/dev-log/sprint-15-cost-spike.md §3.1 / §3.3에 audio 결과 paste
```

### 3.3 R8 outreach 시작

`docs/dev-log/sprint-15-r8-outreach.md` §2 message template paste. 3 채널 동시:
- 인디해커즈 Discord/Slack #show-and-tell — 20건
- X DM Notion/Mem.ai 팔로워 — 20건
- warm_intro Korean founder network — 10건
- HN-Show 또는 IH-Show — 1 post
- cold expansion (LinkedIn / Reddit r/SaaS) — 30 preload

각 발송마다 outreach.md §3 표에 기록.

---

## §4. PR push 정책

- 자동 commit OK (이번 세션 13 commit 자동 진행)
- **PR push만 사용자 승인** (handoff §6.1)
- 단일 PR (R8 14일 retro 완료 후) — plan §5.4
- 지금 push 굳이 X — R8 결과 반영해야 PR description 의미 있음

---

## §5. 다음 세션 시나리오

### A. R8 retro (Day 14 시점)
- founder가 outreach.md에 14일 결과 paste
- 인터뷰 5명 응답 + behavioral signal 확인
- Best/Medium/Minimum 자동 분기
- Sprint 16 결정 (Promotion API build / outreach-only / pivot)
- 단일 PR push

### B. Fix iter 2 (Day 3 dogfooding bug 발견 시)
- 발견 bug 본 doc에 추가
- codex 재검토 또는 inline patch
- atomic commit

### C. Sprint 16 진입 (early)
- R8 결과 Best/Medium 통과 시
- Promotion API 정식 build (S17-T-AD16-IMPL → S16으로 승격)
- Gemini EOL ADR-019 작성 (2026-05-28 진입 시점, EOL 6/17까지 ~20일)

---

## §6. Sprint 17+ defer

| ID | 항목 | 트리거 |
|----|------|--------|
| S17-T-AD16-IMPL | Promotion API 정식 implementation | R8 success |
| S17-T-AD17A | cross-ws RAG opt-in | Sprint 18+ |
| S17-T-AD18A | Promotion review queue | 다중 admin team 시 |
| S17-T-EMBED-RETRY | embedding 실패 retry queue | R8 cost spike fail 시 |
| S17-T-WS-NORMALIZE | 기존 16 frontend site refactor | Sprint 17 capacity |
| **S17-T-GEMINI-EOL** | Gemini 2.5 Flash EOL → 2.5 Pro / Flash 2.0 ADR-019 | 2026-05-28 Sprint 16 진입 시 |
| S17-T-PROMOTION-REFRAME | ADR-016 AD-41 본문 patch | post-R8 결과 |
| S17-T-RECALL-BM25 | BM25 ranking 도입 | token overlap 한계 시 |
| S18-T-RAG-XWS | cross-ws RAG SQL IN expand | Sprint 18 |

---

## §7. 핵심 lessons (Stage 4)

1. **Subagent-driven 매우 효과적** — R1/R3/R4/R6 4건 atomic commit 성공. base plan + patch 2-doc 참조 + first failing test + acceptance 명시 prompt 패턴 작동.
2. **Pyright "could not be resolved" stale cache noise는 무시 OK** — runtime tests pass면 cache invalidation 문제. IDE 재시작 시 해소.
3. **alembic upgrade head local manual 필수** — Docker entrypoint 자동이지만 `uvicorn` 직접 띄우면 X. 본 세션 R-CRON 500 발생으로 학습.
4. **memory_events DB-backed metrics** — Cloud Run stateless 정합. 모듈-level deque 폐기.
5. **promote_audit `memory_id` 필드** — plan에 `source_memory_id`로 잘못 표기됐으나 R2 모델은 `memory_id`. subagent가 모델 우선으로 자체 정정.
6. **patch doc 우선 적용 strategy 작동** — `2026-05-14-sprint15-plan-patch.md` 15 must-fix 모두 inline 적용 성공.
7. **Day 0 spike text-only로도 충분 검증** — Gemini distill 4.8s 발견이 R1 BackgroundTask 정량 정당화. audio branch는 founder 시간 vs validation depth 트레이드오프.

---

## §8. 진입 입력

다음 세션 진입 시:

```bash
git status                                                                # 21 ahead, clean
cat docs/dev-log/2026-05-14-sprint15-stage4-done-handoff.md               # 본 doc
cat ~/.claude/projects/.../memory/project_sprint15_stage4_done.md         # memory
cat docs/dev-log/sprint-15-r8-outreach.md                                 # R8 진행 상태
cat docs/dev-log/sprint-15-cost-spike.md                                  # spike 결과
```

R8 진행 상태에 따라 시나리오 A/B/C 선택.

---

**STATUS**: Stage 4 코드 + Day 0 1차 spike DONE. R8 14일 stagger 진행 (founder manual). 단일 PR push는 retro 후.
