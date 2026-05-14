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

## §3. Result (TBD — founder script run 후 채워넣기)

### 3.1 Aggregate

```json
{
  "total_samples": 0,
  "successful": 0,
  "failed": 0,
  "failure_rate": 0.0,
  "e2e_p50_ms": 0,
  "e2e_p95_ms": 0,
  "total_cost_usd": 0.0,
  "cost_per_tester_week_estimate_usd": 0.0
}
```

### 3.2 Per-sample Raw

```json
[]
```

### 3.3 Threshold Evaluation

- [ ] failure_rate ≤ 5% ?
- [ ] e2e_p95 ≤ 60s ?
- [ ] cost_per_tester_week ≤ $2 ?

---

## §4. Gemini EOL Probe (Q3 inline)

> Gemini 2.5 Flash EOL = 2026-06-17. 스크립트 첫 distill 호출에서 response 객체 dump.

```json
{}
```

**Sunset / deprecation header / warning 존재 여부**: TBD

→ 존재 시 S17-T-GEMINI-EOL 우선순위 ↑, Sprint 16 진입 전 ADR-019 가속.

---

## §5. R1 진입 결정

| 조건 | 결과 |
|------|------|
| 모든 threshold pass | TBD → R1 진입 OK |
| 위반 1+ | TBD → 본 doc §6에 mitigation plan 기록 후 R1 진입 |

---

## §6. Mitigation Plan (위반 시 작성)

(TBD — 위반 발생 시 작성)
