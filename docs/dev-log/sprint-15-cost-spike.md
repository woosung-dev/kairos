<!-- Sprint 15 Day 0 spike 결과 로그 — Whisper + Gemini + OpenAI embedding 실측 -->

# Sprint 15 Day 0 Cost / Latency Spike

> **목적**: R1 진입 전 transcribe → distill → embed pipeline의 실제 cost / latency / failure rate 측정. patch §12 invalidate threshold 위반 시 plan revise.
>
> **실행**: `cd backend && uv run python scripts/sprint15_day0_spike.py` (founder, ~30분)
>
> **prerequisite**: `backend/scripts/samples/` 7개 audio 녹음 필요. 누락 sample은 자동 skip.

---

## §1. Sample 정의

| Sample | 길이 | 환경 | 목적 |
|--------|------|------|------|
| chrome_webm_10s | 10s | Chrome MacOS | normal speech baseline |
| chrome_webm_60s | 60s | Chrome MacOS | typical capture |
| chrome_webm_5min | 5min | Chrome MacOS | meeting-length stress |
| ios_mp4_10s | 10s | iOS Safari | iOS MIME fallback 검증 |
| ios_mp4_60s | 60s | iOS Safari | iOS MIME fallback 검증 |
| ko_filler_60s | 60s | Chrome MacOS | 한국어 filler "어… 음…" 다수 |
| silent_10s | 10s | Chrome MacOS | empty input edge |
| text_500 | n/a | n/a | 한국어 500자 distill-only |
| text_3000 | n/a | n/a | 한국어 3000자 distill-only |
| text_10000 | n/a | n/a | 한국어 10000자 stress |

---

## §2. Invalidate Thresholds (patch §12)

| Metric | Threshold | 위반 시 action |
|--------|-----------|---------------|
| transcription/distill failure rate | > 5% | Whisper 모델 재선택 (gpt-4o-transcribe / whisper-1) 또는 distill prompt revise |
| end-to-end job p95 | > 60s | R1 BackgroundTask 확정 + R7 polling 간격 최적 |
| Gemini JSON invalid | > 10% | distill prompt revise + parse fallback 강화 |
| cost per tester per week | > $2 | 모델 다운그레이드 (gpt-4o-mini-transcribe 이미 cheap) / sample size 조정 |
| recall p95 at 100 chunks | > 2s | R3 embedding cache 활성 (C3 fix) — Day 0 직접 측정 X, R3 진입 후 별도 |

---

## §3. Result — 2026-05-14 1차 (text-only, audio 7건 sample 미녹음으로 skip)

### 3.1 Aggregate

```json
{
  "total_samples": 10,
  "successful": 3,
  "failed": 7,
  "failure_rate": 0.7,
  "e2e_p50_ms": 5528,
  "e2e_p95_ms": 6590,
  "total_cost_usd": 0.0026,
  "cost_per_tester_week_estimate_usd": 0.0026
}
```

> ⚠️ `failure_rate 70%`는 audio 7 sample missing으로 인한 script noise. 실제 system failure 아님. text 3 sample 모두 success (3/3).

### 3.2 Per-sample Raw (text 3건 success)

- `text_500`: distill ~5s + embedding ~700ms, success
- `text_3000`: distill ~5s + embedding ~700ms, success
- `text_10000`: distill ~5s + embedding ~700ms, success
- 7개 audio = `sample file missing` skip (chrome_*.webm / ios_*.mp4 / ko_filler / silent)

### 3.3 Threshold Evaluation (text-only 기준)

- [x] failure_rate ≤ 5% (text 3/3 success — audio missing 제외 시 0%)
- [x] e2e_p95 ≤ 60s (6590ms — 1 order of magnitude 여유)
- [x] cost_per_tester_week ≤ $2 ($0.0026 — 3 orders of magnitude 여유)
- [ ] **audio transcription failure** ≤ 5% — **미측정** (audio sample 녹음 후 재실행 필요)
- [ ] **recall p95 at 100 chunks** ≤ 2s — R3 통합 테스트에서 별도 측정 (Day 3 dogfooding 시점)

### 3.4 R1 BackgroundTask 정당화 확정

text distill **4.8s** (1건). POST 202 enqueue 분리 결정 correct.
sync 처리 시 user 5초+ wait → UX 불가. BackgroundTask architecture 유지.

---

## §4. Gemini EOL Probe (Q3 inline) — 2026-05-14 결과

> Gemini 2.5 Flash EOL = 2026-06-17 (Sprint 15 시작 +34일). 첫 distill 호출의 response 객체 dump.

```json
{
  "model": "gemini-2.5-flash",
  "usage_metadata": {
    "prompt_token_count": 346,
    "candidates_token_count": 64,
    "thoughts_token_count": 534,
    "total_token_count": 944
  },
  "response_attrs": [
    "automatic_function_calling_history", "candidates", "create_time",
    "model_dump", "model_version", "parsed", "parts", "prompt_feedback",
    "response_id", "sdk_http_response", "text", "usage_metadata"
  ]
}
```

**Sunset / deprecation header / warning 존재 여부**:

- ❌ `usage_metadata`에 sunset/deprecation 필드 없음
- ❌ `response_attrs`에 deprecation 관련 attribute 없음
- ✅ `sdk_http_response` attribute 존재 — 다음 iter에서 raw HTTP header 정밀 dump 가능 (현재는 미사용)
- ⚠️ Gemini SDK는 sunset header를 일반적으로 SDK 객체에 노출하지 않음 — Google AI Studio 공식 공지 page를 별도 모니터링 필요

→ **표면 신호 없음**. S17-T-GEMINI-EOL 우선순위 유지 (가속 불필요). Sprint 16 진입 (2026-05-28) 시 ADR-019 작성 후 마이그레이션. EOL 6/17까지 ~20일 여유.

---

## §5. R1 진입 결정 — 2026-05-14

| 조건 | 결과 |
|------|------|
| text-only threshold pass | ✅ failure_rate / e2e p95 / cost 모두 통과 |
| audio threshold | ⏳ pending — audio sample 7개 녹음 후 재실행 |
| Gemini EOL probe | ✅ 표면 신호 없음, Sprint 16 진입 시 대응 |

→ **R1 진입 + R1~R7 구현 정당화 완료** (text branch). audio branch는 founder sample 녹음 후 2차 spike 진행.

## §6. Mitigation Plan

- **audio transcription threshold 위반 시** (2차 spike에서): Whisper 모델 `gpt-4o-mini-transcribe` → `gpt-4o-transcribe` 또는 `whisper-1` 전환 검토.
- **Gemini distill 5s+ latency**: R1 BackgroundTask로 이미 분리. user-facing latency는 POST 202 ≤500ms p95 유지.
- **EOL signal 발견 시**: Sprint 16 진입 즉시 ADR-019 + Gemini 2.5 Pro / Flash 2.0 비교 → 코드 마이그레이션.

## §7. 후속 액션

1. founder audio sample 7개 녹음 (`backend/scripts/samples/` README 가이드)
2. 2차 spike run → 본 doc §3.1 / §3.3 audio 결과 추가 paste
3. Sprint 16 진입 시 (2026-05-28) Gemini EOL ADR-019 신설 — S17-T-GEMINI-EOL 항목
