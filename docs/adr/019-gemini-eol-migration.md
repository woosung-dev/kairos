# ADR-019: Gemini 2.5 Flash EOL 마이그레이션 → gemini-3.1-flash-lite

> **날짜:** 2026-05-14 (draft) → 2026-05-15 Phase B accepted (EOL D-33 압박으로 Sprint 16 일정보다 앞당김)
> **상태:** **Accepted** (Phase A spike 2026-05-14 validated + Phase B 코드 swap 2026-05-15 적용 완료)
> **작성자:** Claude Opus 4.7 (1M context) + 사용자
> **관련:** PRD v3.0 §AI Pipeline · ADR-014 Service Boundary · ADR-020 pgvector HNSW/halfvec (Sprint 16 별도 commit — 코드 swap 충돌 회피) · `docs/architecture/ai-pipeline.md` · `git history` · TODO P0 `S17-T-GEMINI-EOL`
> **워크플로우:** Sprint 15 R8 14일 stagger 진행 중. EOL 2026-06-17 D-33 압박으로 R8 demo 완료 (2026-05-28) 전 swap 결정 (AD-49 정정 = AD-57로 별도 라벨).

---

## 배경

### EOL 사실

- 현재 사용 모델: `gemini-2.5-flash` (Kairos 전체 AI distill / summary / structure 파이프라인)
- **EOL 날짜**: 2026-06-17 (Google AI Studio 공식)
- **남은 기간** (2026-05-14 기준): 34일
- Sprint 16 진입 예정일 (2026-05-28) 기준 잔여 ~20일 — Sprint 16 첫 commit으로 swap 필수

### 트리거 사건

1. **2026-05-14 Day 0 1차 spike 결과** (`git history §4`):
   - Gemini SDK 응답 객체에 surface deprecation/sunset 신호 없음
   - `usage_metadata` / `response_attrs` / `sdk_http_response` 어디에도 signal 부재
   - 표면 신호 부재 ≠ EOL 무효 → Google AI Studio 공식 공지 (2026-06-17) 그대로 유효
2. **2026-05-07 gemini-3.1-flash-lite GA 출시**:
   - 2.5 Flash quality 유지
   - 2.5x faster TTFT + 45% output speed
   - $0.25/$1.50 per 1M (input/output) — 2.5-flash ($0.30/$2.50) 대비 ~17% / ~40% 절감
   - 1M context, 64K output, multimodal (text/image/audio/video/PDF) 동일
   - knowledge cutoff 2025-01

### 자의 결정 라벨

- **AD-47**: 후보 모델 `gemini-3.1-flash-lite` (GA) 채택. 자의 = SLA 있는 GA + cost ↓ + latency ↑↑ + quality 동등 4축 모두 win. preview tier (`gemini-3.1-flash-lite-preview`)는 same underlying model이나 deprecation 위험 회피.
- **AD-48**: Multi-vendor abstraction (LiteLLM / OpenRouter) **도입하지 않음**. 자의 = MVP premature abstraction + Repository 추상화 부담 + Kairos 단일 모델 정책 (CLAUDE.md "Gemini 고정") 일관성.
- **AD-49**: 코드 swap은 **Sprint 16 첫 commit**. 자의 = R8 14일 demo 진행 중 모델 변경 = 외부 demo 결과 오염 위험. demo 종료 (Day 14 = 2026-05-28) 후 즉시 적용.
- **AD-50**: Embedding 모델 (`text-embedding-3-small`)은 본 ADR scope 외. 자의 = 별도 lifecycle, EOL 신호 없음, 마이그레이션 시 별도 ADR 필요.
- **AD-57** (2026-05-15 정정): AD-49 정정 — Sprint 16 머지 (2026-05-14 PR #30) 완료 후 main 깨끗 + R8 미시작 (founder outreach 80 미진척) 확인. 외부 demo 오염 가능성 부재 + EOL D-33 압박 → Phase B를 2026-05-28 기다리지 않고 2026-05-15 즉시 진입. 자의 = "외부 demo 결과 오염 위험" 가정이 실제 R8 미시작 상태로 무효화됨.

---

## 결정

### 1. Target 모델

- ID: `gemini-3.1-flash-lite` (GA, 2026-05-07 출시)
- SDK: `google-genai` (현재 사용 중, 변경 X)
- 호출 패턴: 현재 `client.aio.models.generate_content(model=..., contents=...)` 동일 유지
- JSON schema: distill 출력 (`title` / `atomic_notes` / `suggested_visibility`) 동일

### 2. Migration trigger

- **시점**: Sprint 16 첫 commit (2026-05-28)
- **선행 조건**: Sprint 15 R8 14일 stagger 완료 + 단일 PR push 완료 (외부 demo 결과 오염 차단)
- **롤백 조건**: §Rollback 참조

### 3. 코드 변경 위치 (6 spots, 단일 commit)

| # | 파일 | 라인 | 변경 |
|---|------|-----|------|
| 1 | `backend/src/services/ai_processing.py` | 18 | `GEMINI_MODEL = "gemini-3.1-flash-lite"` |
| 2 | `backend/src/memory/service.py` | 64 | `GEMINI_MODEL = "gemini-3.1-flash-lite"` |
| 3 | `backend/scripts/sprint15_day0_spike.py` | 54 | 본 ADR 후속 spike script 확장에서 처리 |
| 4 | `backend/tests/services/test_ai_processing.py` | 69, 84 | docstring + assertion 갱신 |
| 5 | `docs/architecture/ai-pipeline.md` | 23, 151 | rule + code sample 갱신 |
| 6 | `.ai/stacks/fastapi/backend.md` | Tech Stack table | `gemini-2.5-flash` → `gemini-3.1-flash-lite` |

단일 commit message:

```
feat(ai): Gemini 2.5-flash → 3.1-flash-lite migration (ADR-019)

EOL 2026-06-17 대응. distill latency 4.8s → ~2.4s 예상.
cost $0.30/$2.50 → $0.25/$1.50 per 1M (17%/40% 절감).
quality 동등, schema 동일.

verification: pytest 144 pass / R7 metrics latency 측정.
```

---

## Consequences (Positive) — 2026-05-14 spike 실측

1. **EOL 회피**: 2026-06-17 이후 서비스 중단 위험 제거
2. **Latency 개선 (실측)**: distill p50 **5231ms → 908ms = 5.76x speedup** (예측 2.5x 초과). 이유: 3.1-flash-lite default thinking mode off (thoughts_token_count 294 → null). distill task에 thinking 불필요.
3. **Cost 절감 (실측)**: $0.0025/tester/week → $0.0020/tester/week = **20% 절감**. 토큰 절약 (thoughts off) + 단가 절감 합산.
4. **Schema 동등성 (실측)**: 3/3 sample 모두 `{title, atomic_notes, suggested_visibility}` 필드 존재 (schema_match_rate=1.0).
5. **SLA**: GA 모델 → 다음 EOL까지 12개월+ 안정성
6. **단일 모델 정책 유지**: Repository 추상화 / multi-vendor 부담 없음
7. **EOL probe**: 두 모델 응답에 sunset/deprecation 신호 없음 — 공식 공지만 신뢰

---

## Consequences (Negative / 위험) — 2026-05-14 spike 후 갱신

1. ~~**Output JSON schema 불일치 위험**~~: spike에서 3/3 schema 일치 확인 → **해소됨**
2. **Thinking mode default off**: 3.1-flash-lite는 default thinking off (spike 측정). distill 같은 단순 요약 task는 영향 없으나, 향후 복잡 reasoning이 필요한 use case (예: RAG re-ranking, 다단계 추론) 추가 시 thinking 명시 활성 필요 가능. 현재 Kairos에는 해당 없음.
3. **Knowledge cutoff 2025-01**: 2.5-flash와 동일 수준이므로 distill task (입력 데이터 그대로 요약)에는 영향 없음
4. ~~**Token usage 변화 가능성**~~: spike에서 baseline 717 tokens → candidate 390 tokens = **45% 감소** (thoughts off 효과). cost 우호적 → **위험 아님으로 재분류**.
5. **GA 모델 자체 EOL**: 12개월 후 또 다른 마이그레이션 필요 가능 — 정상 lifecycle, ADR 패턴 재사용으로 비용 최소화

---

## Alternatives Considered

| # | 후보 | 이유 | 채택 X 사유 |
|---|------|------|-------------|
| A1 | `gemini-3.1-flash` (full) | 더 높은 quality | distill task에 over-spec, cost ↑↑ |
| A2 | `gemini-2.5-pro` | 같은 family 2.5 잔존 | EOL 함께 가능성, cost ↑↑↑, latency ↑ |
| A3 | `gemini-3-flash` | newer family | flash-lite 대비 cost 메리트 X, distill에는 동등 |
| A4 | `gemini-3.1-flash-lite-preview` | same underlying model | preview tier deprecation 위험, GA로 대체 가능 |
| A5 | Multi-vendor (LiteLLM / OpenRouter) | vendor lock-in 회피 | MVP premature abstraction, Kairos 단일 모델 정책 위반 |
| A6 | EOL 직전 (2026-06-15) swap | demo 결과 오염 최소화 | 너무 늦음, 검증 시간 부족 |

---

## Implementation

### Phase A — 본 ADR 후속 spike (2026-05-14, ✅ DONE)

1. ✅ Day 0 spike script 확장: `GEMINI_MODELS` list (commit 676556f)
2. ✅ text 3 sample × 2 모델 = 6 distill success, audio 7 sample은 founder 녹음 후 별도 진행
3. ✅ `model_comparison` 섹션 (latency_delta_ms / cost_delta_usd / output_equivalence) 출력 검증
4. ✅ 결과 paste 완료: `git history §3.5` (commit 2cee665)

### Phase B — ✅ DONE (2026-05-15, AD-57 정정으로 앞당김)

1. ✅ §3 6 spots 코드 + docs 동일 PR 적용 (브랜치 `sprint-17/adr-019-phase-b-gemini-swap`)
2. ✅ `cd backend && uv run pytest -q` → **155 pass / 2 pre-existing fail / 1 skipped** (회귀 0건. fail 2건 = `tests/services/test_transcription.py` ffmpeg 8.1.1 mock mp3 fixture 호환 이슈, main 동일)
3. ⏳ `uvicorn` /memory capture distill latency 측정 = 사용자 dogfooding 단계 (PR 머지 후)
4. ✅ 본 ADR status = Draft → **Accepted** 갱신 (본 patch)
5. ✅ Atomic Update 매트릭스: `CONTEXT-MAP.md` I-3 / `backend/CONTEXT.md` B-4 / `backend/src/memory/CONTEXT.md` I-3 / `AGENTS.md` 기술 스택 + AI 제약 / `.ai/stacks/fastapi/backend.md` / `README.md` / `docs/architecture/ai-pipeline.md` rule + code sample / `docs/architecture/rag-pipeline.md` 다이어그램 + 비교 표 동시 patch

---

## Verification

### Spike (Phase A)

- output JSON schema 동등성: 두 모델 모두 `{title, atomic_notes, suggested_visibility}` 필드 존재
- distill latency p50/p95 비교 (3.1-flash-lite < 2.5-flash 확인)
- cost per call 비교 (3.1-flash-lite < 2.5-flash 확인)
- failure rate < 5% (두 모델 모두)

### Production swap (Phase B, 2026-05-15)

- ✅ BE pytest 155 pass (회귀 0건). 2 fail = pre-existing ffmpeg mp3 fixture (main 동일 검증).
- ⏳ BE startup health 200 = 사용자 로컬/배포 검증 단계
- ⏳ /memory capture → 202 + processing → polling → status=active + distilled_json schema 동등 = 사용자 dogfooding 단계
- ⏳ R7 metrics (admin page) latency 비교 (전후 ratio ≥ 1.5x) = PR 머지 + 사용자 1-2회 capture 후

---

## Rollback

다음 중 하나 발생 시 ADR-019 status = Rejected, 후보 재선정:

1. spike output JSON schema 불일치 (3개 필드 중 하나라도 누락 / 형식 차이)
2. distill failure rate > 5%
3. cost delta가 예상 방향과 반대 (3.1-flash-lite cost > 2.5-flash cost)
4. Production swap 후 R7 metrics latency 개선 없음 또는 회귀
5. Day 1 dogfooding output 품질 명백 저하

→ 대안 진입 순서: A1 (3.1-flash) → A3 (3-flash) → A2 (2.5-pro)

---

## 참조

- Google AI Studio Gemini 3.1 Flash-Lite GA: 2026-05-07 (blog.google + cloud.google.com)
- OpenRouter benchmark: $0.25 / $1.50 per 1M tokens
- Artificial Analysis: 2.5x faster TTFT + 45% output speed vs 2.5 Flash
- 본 프로젝트: `git history §4` Gemini EOL probe 결과
- 본 프로젝트: `docs/TODO.md:250` S17-T-GEMINI-EOL P0 항목
