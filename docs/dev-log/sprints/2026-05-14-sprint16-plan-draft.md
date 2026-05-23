<!-- Sprint 16 plan draft — R8 결과 분기 + Phase B Gemini swap + Promotion API + Voice note -->

# Sprint 16 Plan Draft (2026-05-14 작성 → 2026-05-28 진입 시 확정)

> **상태**: Draft. R8 14일 retro (2026-05-28) 결과에 따라 §3 Best/Medium/Min 분기 활성화.
>
> **진입 조건**: Sprint 15 단일 PR push 완료 + R8 결과 §3 분기 매트릭스 적용.
>
> **참조**: ADR-019 (Gemini EOL) · ADR-016 (Personal↔Team IA) · docs/TODO.md §Sprint 16 후보 · docs/dev-log/sprints/sprint-15-r8-outreach.md §6 Final Result.

---

## §1. 입력 (Sprint 15 종료 시점 가정)

- Sprint 15 PR pushed + merged (26+ commits → main)
- Sprint 15 R8 outreach 결과 doc 완성 (`docs/dev-log/sprints/sprint-15-r8-outreach.md §6`)
- 인터뷰 N명 응답 + behavioral signal 측정 완료
- ADR-019 Phase A spike validated (커밋 `a95d9e1`+`676556f`+`2cee665`+`f926ede`)
- Gemini 2.5-flash EOL까지 잔여 ~20일 (2026-06-17)
- 누적 dogfooding 결과 + bug log (있다면)

---

## §2. Sprint 16 고정 항목 (R8 결과 무관 진행)

### 2.1 ADR-019 Phase B — Gemini 2.5-flash → 3.1-flash-lite 코드 swap

**우선순위**: P0 (EOL 회피 hard deadline)

**Trigger**: Sprint 16 첫 commit

**구현 (6 spot 단일 commit)**:
```
backend/src/services/ai_processing.py:18        GEMINI_MODEL = "gemini-3.1-flash-lite"
backend/src/memory/service.py:64                GEMINI_MODEL = "gemini-3.1-flash-lite"
backend/scripts/sprint15_day0_spike.py:54       baseline 제거 + candidate만 유지
backend/tests/services/test_ai_processing.py:69,84  docstring + assertion 갱신
docs/architecture/ai-pipeline.md:23,151         rule + code sample 갱신
.ai/stacks/fastapi/backend.md                   Tech Stack table 갱신
```

**Verification**:
- BE 144 pass 유지
- `/memory` capture e2e → distill latency p50 측정 → 5.76x speedup 검증
- R7 admin page metrics 비교 (전/후)

**Time**: ~2h (단일 commit, 검증 포함)

### 2.2 Sprint 15 carry-over (있다면 dogfooding bug fix)

R8 진행 중 발견된 bug iter 2 (있다면) 우선 close. Sprint 15 PR 머지 전 fix 또는 Sprint 16 첫 patch.

### 2.3 핸드오프 문서 갱신

- `docs/dev-log/2026-05-14-sprint15-stage4-done-handoff.md` → Sprint 15 종료 마크
- `docs/TODO.md` §Sprint 15 → [x] 표시, §Sprint 16 → 활성 표시
- ADR-019 status: Phase A validated → Accepted (Phase B 적용 후)
- `MEMORY.md` Sprint 16 진입 status 추가

---

## §3. R8 결과 분기 (2026-05-28 retro 시 활성)

### 3.A — Best (Day-7 retained 3+ / $10 결제 의향 1+)

**해석**: Recall demand 검증 ✅. Personal workspace MVP가 외부에 가치 입증. v1.6 Promotion + v2 음성 메모 정식 진입.

**Sprint 16 범위** (8~10일):
- S16-T1: Promotion FE — 모든 item type (memory/note/meeting/action) "Promote to Team..." 모달 (Sprint 15 R6 1-button 확장)
- S16-T2: Promotion BE API — 메타데이터 + 1536d 임베딩 복제, tombstone 유지
- S16-T3: Promotion audit log + 헌법 I-18 lock-in (constitution 갱신)
- S16-T4: `/new` 페이지에 "음성 메모" 탭 (Meeting과 분리)
- S16-T5: VoiceNote 모델 (Meeting과 별개) + STT + Gemini distill + 태그
- S16-T6: Personal에서 음성 메모 1차 진입 시나리오 확정

**Risk**: 5축 동시 진입 → 우선 T1~T3 (Promotion) 먼저 commit, T4~T6 (Voice) 후속.

### 3.B — Medium (Day-7 retained 2+ / Day-2 activation 2/3+)

**해석**: Recall 동작 + 일부 retention. Best 대비 wedge 강도 부족. Promotion 정식 build 보류, Phase B + Sprint 15 안정화 우선.

**Sprint 16 범위** (5~7일):
- §2.1 Phase B 완료
- Sprint 15 R6 1-button promote 안정화 (edge case 보완, audit 강화)
- R7 metrics 추가 (recall_quality_score / day_2_retention_rate 자동 산출)
- R8 second wave outreach (additional 50건 — wedge 검증 N 증대)

**보류**: Promotion 정식 build (S16-T1~T3) → Sprint 17 재평가.

### 3.C — Minimum (Day-7 retained 0~1 / activation <2/3)

**해석**: Wedge 신호 부족. Recall demand 가설 1차 검증 실패. Build freeze + outreach sprint로 전환.

**Sprint 16 = "Outreach + Wedge re-evaluation sprint"** (10~14일):
- §2.1 Phase B만 진행 (EOL 회피 minimal change)
- 코드 변경 ❌ (capture/recall/promote 모두 frozen)
- Pivot 분석: founder + 다음 후보 wedge 3개 brainstorm
  - 후보 A: Quick capture (recall 없이 capture-only 강화, Apple Notes 대체)
  - 후보 B: Meeting-back wedge (Sprint 14 이전 회의 중심 복귀)
  - 후보 C: Cross-app capture (Slack/Notion plugin)
- R8 outreach 100건 추가 (cold expansion 활성: LinkedIn / Reddit / 유료 panel)
- Sprint 17 = pivot 또는 wedge re-validation (Day 0 spike re-run)

---

## §4. 시간 예산 (Sprint 16 = 2 weeks)

| 시나리오 | 코드 작업 | 외부 outreach / interview | 분석 / doc |
|---------|----------|--------------------------|-----------|
| Best | 8~10일 | 2일 (retention loop) | 2일 |
| Medium | 5~7일 | 4일 (wave 2 outreach + interview) | 3일 |
| Min | 1~2일 (Phase B only) | 8~10일 | 2~3일 (pivot analysis) |

---

## §5. 리스크

| ID | 리스크 | 분기 | 완화 |
|----|--------|-----|------|
| R-S16-1 | Phase B output 회귀 (3.1-flash-lite 품질 저하) | 전 분기 | spike 검증 통과 — Rollback 조건 (ADR-019 §Rollback) trip wire |
| R-S16-2 | Best 분기에서 5축 동시 진입 overflow | Best | T1~T3 → T4~T6 순차 commit, mid-sprint 중간 retro |
| R-S16-3 | Min 분기 pivot 결정 지연 (외부 의견 부재) | Min | pivot brainstorm = founder solo 진행, "decision-by-default" 1주 후 자동 선택 |
| R-S16-4 | Gemini EOL +20일 잔여 — Phase B 지연 시 hard miss | 전 분기 | Sprint 16 첫 commit 못 박음, Day 1까지 swap 완료 |
| R-S16-5 | 음성 메모 STT 비용 spike (Best) | Best | Day 0 spike audio sample 7개 결과 확인 후 진입, $2/tester/week 한계 monitoring |

---

## §6. 외부 의존 (founder pending)

- Clerk Production key 발급 (Sprint 14 carry-over) — Sprint 16 시작 전 필수
- R8 outreach 80건 완료 (Sprint 15 manual) — retro input
- Audio sample 7개 녹음 + Day 0 2차 spike (Best 분기 진입 시 필수)
- Sprint 15 단일 PR push 승인 (사용자) — Sprint 16 진입 trigger

---

## §7. Sprint 17+ defer (Sprint 16 종료 시점 재평가)

- S17-T-AD17A: cross-ws RAG opt-in (R-13 헌법 신설)
- S17-T-AD18A: Promotion review queue (다중 admin team)
- S17-T-EMBED-RETRY: embedding 실패 retry queue
- S17-T-WS-NORMALIZE: 기존 16 frontend site refactor
- S17-T-PROMOTION-REFRAME: ADR-016 AD-41 본문 patch (post-R8)
- S17-T-RECALL-BM25: BM25 ranking (token overlap 한계 시)
- S18-T-RAG-XWS: cross-ws RAG SQL IN expand

---

## §8. 진입 입력 (Sprint 16 첫 세션)

```bash
# 1. R8 결과 확인 → 분기 결정
cat docs/dev-log/sprints/sprint-15-r8-outreach.md  # §6 Final Result 표 확인

# 2. 본 plan §3 분기 매트릭스 적용 → §2 + §3.A/B/C 선택

# 3. Phase B 첫 commit 진입 (전 분기 공통)
# backend/src/services/ai_processing.py:18 swap

# 4. ADR-019 status Accepted 마크 (Phase B 검증 통과 후)
```

---

## §9. Plan lifecycle

- **2026-05-14**: 본 draft 작성 (ADR-019 Phase A 직후)
- **2026-05-28**: R8 retro 후 §3 분기 lock-in → "Sprint 16 plan (final)" 신설 또는 본 doc rename
- **Sprint 16 종료 시**: 본 doc archive, Sprint 17 plan draft 신설

---

## §10. Open questions (Day 14 retro 시 클리어)

1. R8 80건 실제 sent 수 (Best/Medium/Min 분기 결정)
2. demos completed 수 + Day-7 retained 수
3. "$10 결제 의향" yes 수
4. Sprint 15 dogfooding bug log (있다면 Sprint 16 첫 task)
5. founder 추가 wedge 후보 (Min 분기 시 brainstorm input)
