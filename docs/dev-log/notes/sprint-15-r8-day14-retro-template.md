<!-- Sprint 15 R8 14일 stagger Day 14 retro template — founder paste-ready -->

# Sprint 15 R8 Day 14 Retro Template

> **사용법**: 2026-05-28 (R8 Day 14) 시점에 본 doc을 fill-in. 결과 채운 후 `sprint-15-r8-outreach.md §6` 표 + 본 doc로 Sprint 16 분기 결정.
>
> **결정 분기 매트릭스**: `docs/dev-log/sprints/2026-05-14-sprint16-plan-draft.md §3`

---

## §1. Outreach 발송 결과 (Day 0~14 누적)

| Channel | Target | Sent | Replied | Booked | Completed | Retained | Note |
|---------|--------|-----:|--------:|-------:|----------:|---------:|------|
| warm_intro Korean | 10 | __ | __ | __ | __ | __ | |
| 인디해커즈 Discord/Slack | 20 | __ | __ | __ | __ | __ | |
| X DM Notion/Mem.ai 팔로워 | 20 | __ | __ | __ | __ | __ | |
| HN-Show / IH-Show | 1 post | __ | __ | __ | __ | __ | 댓글 수 / upvote |
| Cold expansion (LinkedIn / Reddit) | 30 | __ | __ | __ | __ | __ | Day 1+ 활성화 시 |
| **합계** | **81** | **__** | **__** | **__** | **__** | **__** | |

---

## §2. Funnel 결과 (patch §11 P-R8 target 대비)

| Stage | Target | Best | Medium | Minimum | Actual | 통과 |
|-------|--------|-----:|-------:|--------:|-------:|------|
| Sent | 80 / 50 / 30 | 80 | 50 | 30 | __ | __ |
| Booked | 8 / 5 / 3 | 8 | 5 | 3 | __ | __ |
| Completed | 5 / 3 / 2 | 5 | 3 | 2 | __ | __ |
| Day-2 active (capture ≥3 + recall ≥1) | 5/5 / 3/5 / 2/3 | 5 | 3 | 2 | __ / __ | __ |
| Day-7 retained (active capture ≥1/day) | 3 / 2 / 1 | 3 | 2 | 1 | __ | __ |
| "$10 결제 의향" yes | 1+ | 1 | 0 | 0 | __ | __ |

---

## §3. SLA Gate 통과 기록 (Day-by-day)

| Day | Gate | Target | Actual | Pass | Action triggered |
|-----|------|--------|--------|------|------------------|
| 1 | 누적 bookings | ≥3 | __ | __ | __ |
| 3 | 누적 completed | ≥2 | __ | __ | __ |
| 6 | Day-2 activation | 2/3 이상 | __ / __ | __ | __ |
| 14 | Day-7 retained + $10 yes | Best/Medium/Min 분기 | __ | __ | Sprint 16 분기 결정 |

---

## §4. 인터뷰 응답 요약 (PERSONA N명)

> B7 fix — behavioral questions 4종

### Q1. "지난 7일 중 Kairos 없었으면 어느 메모를 어디서 찾았을지 구체적 예시 1개?"

| PERSONA | 응답 요약 | demand signal 강도 (1~5) |
|---------|----------|--------------------------|
| P-1 (__) | __ | __ |
| P-2 (__) | __ | __ |
| P-3 (__) | __ | __ |
| P-4 (__) | __ | __ |
| P-5 (__) | __ | __ |

### Q2. "이 기능 계속 쓰기 위해 월 $10 결제할 의향? Yes/No"

- yes: __명 / __명
- no: __명 (이유 요약)
- maybe: __명 (조건 요약)

### Q3. "다음 주에도 5개 이상 capture할 약속 가능?"

- yes: __명 / __명
- 약속 불가: __명 (이유)

### Q4. "Notion / Apple Notes 대비 가장 짜증났던 1가지?"

| 응답 | 카테고리 | 빈도 |
|------|---------|-----:|
| __ | __ | __ |

(bonus) "unprompted 이거 없으면 불편" signal 발견자: __명

---

## §5. Behavioral signal 집계

| Signal | 정의 | 발견 수 | Best 기준 (1+) | Medium 기준 (0+) |
|--------|------|--------:|---------------:|------------------:|
| $10 결제 의향 yes (Q2) | 명시적 결제 의사 | __ | __ | __ |
| 5+ capture 약속 yes (Q3) | 미래 행동 commit | __ | __ | __ |
| Day-7 active capture | 실제 행동 | __ | __ | __ |
| Unprompted complaint (Q1) | 메모 손실 구체 예시 | __ | __ | __ |
| Unprompted "이거 없으면 불편" | 자발적 evangelism | __ | __ | __ |

---

## §6. 발견된 bug / friction

| ID | Severity | 영역 | 설명 | Sprint 16 처리 |
|----|----------|------|------|----------------|
| B-D14-1 | __ | __ | __ | __ |
| B-D14-2 | __ | __ | __ | __ |

> Sprint 16 Day 1 첫 작업 = D14 bug close (Phase B와 묶음).

---

## §7. Sprint 16 결정 (분기 lock-in)

### 7.1 분기 매트릭스 적용

```
Day-7 retained __ + $10 yes __ + Day-2 activation __/__ →
  □ Best     (retained 3+ / $10 yes 1+)
  □ Medium   (retained 2+ / activation 2/3+)
  □ Minimum  (retained 0~1 / activation <2/3)
```

### 7.2 Sprint 16 범위 결정

**Best 선택 시**:
- ☐ S16-T1 Promotion FE 모달 (모든 item type 확장)
- ☐ S16-T2 Promotion BE API 정식 build (메타+임베딩 복제)
- ☐ S16-T3 Promotion audit log + I-18 lock-in
- ☐ S16-T4 `/new` 음성 메모 탭
- ☐ S16-T5 VoiceNote 모델 + STT + distill + 태그
- ☐ S16-T6 Personal 음성 메모 1차 시나리오
- 공통: ADR-019 Phase B Gemini swap (Sprint 16 첫 commit)

**Medium 선택 시**:
- ☐ ADR-019 Phase B Gemini swap
- ☐ Sprint 15 R6 1-button promote 안정화 (edge case)
- ☐ R7 metrics 추가 (recall_quality_score / day_2_retention_rate)
- ☐ R8 wave 2 outreach (+50건, wedge 검증 N 증대)

**Minimum 선택 시** (= Outreach + Wedge re-evaluation sprint):
- ☐ ADR-019 Phase B Gemini swap (EOL 회피만)
- ☐ 코드 변경 freeze
- ☐ Pivot brainstorm — 후보 wedge 3개 + founder 분석
- ☐ R8 outreach +100건 (cold expansion 활성)
- ☐ Sprint 17 = pivot 또는 wedge re-validation

### 7.3 결정 (Day 14 시점 채움)

```
선택: ____________________
근거: ____________________
Sprint 16 시작일: 2026-05-28 (Day 14 익일)
Sprint 16 종료 예정: 2026-06-__
```

---

## §8. 후속 액션 체크리스트

- [ ] 본 doc §1~§7 fill-in 완료
- [ ] `docs/dev-log/sprints/sprint-15-r8-outreach.md §6` 표 업데이트
- [ ] PR description (`docs/dev-log/sprint-15-pr-description-draft.md`) §"R8 외부 검증 결과" 채움
- [ ] D14 bug (있다면) atomic commit
- [ ] 사용자 push 승인 → `git push origin sprint-15/personal-workspace`
- [ ] `gh pr create` (PR description draft 사용)
- [ ] Sprint 16 plan final = `2026-05-14-sprint16-plan-draft.md` → `2026-05-28-sprint16-plan.md` rename
- [ ] ADR-019 status: Phase A validated → Accepted (Phase B 적용 후)

---

## §9. Lessons 누적 (Day 14 시점)

본 R8 14일 stagger에서 얻은 lessons. 다음 wedge validation sprint 시 참조.

1. __ (예: "outreach response rate가 channel별로 N% 차이 — 다음엔 X 우선")
2. __
3. __

→ 반복 패턴 (3회 이상) → `.ai/project/lessons.md` 또는 `.ai/common/` 승격 검토.
