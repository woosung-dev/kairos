# Post-Swap Delta Stub — Phase B (gemini-2.5-flash → gemini-3.1-flash-lite)

> **gemini F2 수락**: 모델 스왑 전후 AI 품질 5 시나리오 baseline → Sprint 24 T-2 (스왑 후 측정) 에서 diff.
> ADR-019 Phase B 데드라인: 2026-05-28.

---

## 베이스라인 수집 시점

**언제 채워야 하나**: Sprint 24 T-1 (Gemini 6 spot swap) **직전**. 가능한 한 swap 시점에 가깝게.
**도구**: Sprint 24 entry script (별도 작성 예정). 동일 입력을 baseline + post-swap 모두 fetch.

---

## 5 시나리오

### DELTA-1. RAG 답변 품질
- **입력**: 동일 회의 1개 인덱싱 후 5개 질문 (한국어, 길이 다양)
  - Q1: "이 회의에서 결정된 액션은?" (action 추출)
  - Q2: "발표자가 누구였나?" (factoid)
  - Q3: "프로젝트 일정은 어떻게 변경되나?" (synthesis)
  - Q4: "5월 안에 해야 할 일?" (date filter)
  - Q5: "철수가 한 말 중 중요한 것?" (entity + opinion)
- **baseline 응답** (T-1 직전 캡쳐):
  ```json
  {
    "Q1": "(answer text)",
    "Q2": "(answer text)",
    "Q3": "(answer text)",
    "Q4": "(answer text)",
    "Q5": "(answer text)"
  }
  ```
- **post-swap 응답** (T-2 직후 캡쳐): 동일 schema
- **Delta 평가**:
  - Length delta (±%)
  - Semantic similarity (cosine, optional)
  - 정성 평가 (better/same/worse 자기보고)

### DELTA-2. 회의 요약 길이/완전성
- **입력**: 동일 회의 transcript (5분 분량 sample)
- **baseline**: gemini-2.5-flash 요약 결과 (3-section: 요약 / 액션 / 결론)
- **post-swap**: gemini-3.1-flash-lite 동일 입력
- **평가**:
  - Section count 일관성
  - 요약 length delta
  - 액션 count delta
  - 사실 누락 (manual review)

### DELTA-3. 액션 아이템 추출 정확도
- **입력**: 5 transcript sample (action 아이템 명시적 포함)
- **baseline**: extracted actions (assignee / due / content / priority)
- **post-swap**: 동일
- **평가**: precision/recall (manual ground truth 사용)

### DELTA-4. 한국어 처리 (이모지/존댓말/방언)
- **입력**:
  - Sample A: "어제 회의에서 김PM이 ~할 거에요 🙂" (이모지 + 한국어)
  - Sample B: "회의 끝났습니데이" (방언)
  - Sample C: "오늘 미팅 cancel ㅠㅠ" (영한 혼용 + 한국어 이모티콘)
- **baseline**: 각 sample 의 처리 결과 (정상 파싱 vs 깨짐)
- **post-swap**: 동일
- **평가**: 한국어 의미 보존 / 이모지 마크업 변경 / 방언 정상 인식

### DELTA-5. Inbox 자동 분류 confidence
- **입력**: 5 회의 + 5 노트 (각 다른 프로젝트 가능성)
- **baseline**: 자동 분류 결과 (project_id 추천 + confidence 점수)
- **post-swap**: 동일
- **평가**:
  - 동일 항목에 대한 추천 일관성
  - confidence 점수 평균 변화
  - 자동 확정 (confidence ≥ threshold) 비율

---

## Baseline 수집 절차 (T-1 직전 실행)

1. 본 stub 파일 복제 → `post-swap-delta-T1-baseline.md`
2. 5 시나리오 입력 데이터 fixtures 작성 (test 데이터, real workspace 미사용)
3. Gemini 2.5-flash 호출 → 결과 JSON 으로 저장
4. T-1 swap 실행 (코드 PR)
5. 동일 fixtures + 동일 입력 → Gemini 3.1-flash-lite 호출
6. `post-swap-delta-T2-result.md` 작성 + diff 표 정리
7. 결과를 `docs/dev-log/2026-05-28-sprint24-phase-b/post-swap-delta-report.md` 에 통합

---

## 성공 기준 (Sprint 24 Phase B gate)

- **Critical**: DELTA-1 (RAG) 정성 평가 "worse" 가 1건 미만
- **High**: DELTA-3 (액션 추출) precision/recall -10% 이내
- **Medium**: DELTA-2 / DELTA-4 / DELTA-5 변화 ±20% 이내

기준 위반 시: Phase B 일시 중단 + 모델 fallback 또는 prompt tuning 이후 재swap.

---

## 측정 도구 권장

- pytest fixture: `backend/tests/llm/test_post_swap_delta.py` (T-1 직전 추가)
- Gemini API direct call (Real not Mock) — Live key 사용
- 결과 JSON 자동 비교 스크립트

---

## Status

- **Baseline (Phase A)**: ⏳ NOT_CAPTURED (T-1 직전 수집)
- **Post-swap (Phase B)**: ⏳ NOT_MEASURED (T-2 시 수집)
