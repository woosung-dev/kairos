# ADR-021: Sentry Observability (FE + BE) 도입

> **날짜:** 2026-05-19
> **상태:** Accepted (2026-05-19 Sprint 22 Task 7 구현 완료 — commit `60e8266` BE + `10fdaf2` FE)
> **작성자:** Claude Opus 4.7 (1M context) + 사용자
> **관련:** Sprint 22 spec `git history` §4.3/§5.8/§7.2 · plan `git history` Task 7 · ADR-014 Service Boundary · ADR-019 Gemini Phase B · `backend/src/main.py` Sentry init · `frontend/instrumentation.ts` Next.js 16 hook
> **워크플로우:** `.ai/templates/workflow.md` Stage 4 (코드) — Stage 1 ADR 산출은 본 ADR 자체

---

## 배경 (Context)

### Sprint 22 = 첫 외부 user 온보딩

본 Sprint 의 명시 목표는 "첫 외부 user 가 가입 → 첫 회의 업로드 → RAG 인용 회수까지 막힘 없이" 완주하는 것. silent failure (5xx 에러 / Cloud Run cold start 실패 / FE 런타임 에러) 가 발생해도 user 가 알리지 않으면 founder 는 인지 불가. retention curve 의 0일차 churn 의 가장 큰 원인이 "에러 발생 후 user 가 떠나고 founder 는 모름" 인 상태를 차단해야 한다.

### 현 상태 (2026-05-19 기준)

| 항목 | 값 | 비고 |
|---|---|---|
| BE 에러 로깅 | `logging` 모듈 `INFO` 레벨 stdout → Cloud Run logs | 검색 가능하지만 알람 없음 |
| FE 에러 추적 | 없음 | 사용자 브라우저 콘솔 에러 가시성 0 |
| 5xx 알람 | 없음 | Cloud Run uptime check 만 (binary up/down) |
| FE 런타임 에러 추적 | 없음 | RSC error / Suspense fallback 무한 루프 등 인지 불가 |
| 트랜잭션 트레이스 | 없음 | RAG 쿼리 P95 latency 같은 SLI 측정 안 됨 |

### 후보 비교

| 도구 | 도입 시간 | FE+BE 통합 | PII 제어 | 가격 (월) | 결론 |
|---|---|---|---|---|---|
| **Sentry** | 2-3h | 기본 지원 (`@sentry/nextjs` + `sentry-sdk[fastapi]`) | `before_send` hook + `send_default_pii=False` | $0 (10k events) | **채택** |
| OpenTelemetry full | 8-12h | 가능하지만 collector + Tempo/Loki 필요 | 수동 redactor 작성 | 자체 호스팅 | 본 Sprint 부적합 (시간 초과) |
| Datadog APM | 4h | 가능 | 가능 | $15/host | 본 Sprint 단계 과잉 |
| Cloud Run native | 0h | 일부 | 없음 | $0 | 알람 정의 별도 필요 + FE 미커버 |

### 자의 결정 라벨 (본 산출에서 추가)

- **AD-OBS-1**: Sentry **FE+BE 동시** 도입. 자의 = Sprint 22 의 핵심 risk 가 FE-BE boundary (Clerk 인증 콜백 / RAG 쿼리 응답 / 업로드 presigned URL) 이므로 한쪽만 도입 시 사각지대 잔존. `@sentry/nextjs` 가 instrumentation.ts + withSentryConfig 로 source map upload + RSC error boundary 까지 turnkey 제공.
- **AD-OBS-2**: PII 스크럽 **`before_send` hook 필수**. 자의 = Kairos 의 핵심 PII 는 `transcript` (회의 녹취 텍스트), `email` (Clerk user identifier), `audio_url` (R2 presigned, GDPR sensitive). `send_default_pii=False` 만으로는 request body 의 transcript 필드는 그대로 흘러감 → 명시적 redact 필수. plan §7.1.3 의 4개 필드는 보수적 minimum set (필요 시 BL 등재 후 확장).
- **AD-OBS-3**: `traces_sample_rate=0.1` (10%). 자의 = $0 plan 의 월 10k events 한도 내 유지 + 트래픽 적은 dev 환경에서도 sampling artifact 가 적은 비율. error 는 항상 100% 수집 (Sentry 기본). production 트래픽 증가 시 0.05~0.01 로 조정 (BL-OBS-1 등재).
- **AD-OBS-4**: OpenTelemetry full instrumentation **carry-over**. 자의 = Sprint 22 의 2-3h 예산 내 불가능. Sentry 의 FastApiIntegration 이 이미 distributed trace context 를 OTLP 호환 형식으로 전파하므로, 향후 OTel collector 도입 시 동시 운영 가능. 별도 ADR 로 분리 (CO-1).
- **AD-OBS-5**: DSN 미설정 시 init **skip** (conditional `if settings.sentry_dsn`). 자의 = dev 환경 (.env 비어있음) 에서 import-time 실패 차단 + CI test 환경에서 Sentry 가 무관한 외부 호출 발생 안 함 + 본 ADR 채택 후에도 staging/production 만 DSN 주입.
- **AD-OBS-6**: FE 의 `NEXT_PUBLIC_VERCEL_ENV` 를 environment 라벨로 사용. 자의 = Vercel 이 자동 주입하는 환경변수 (development/preview/production) 와 정합. preview branch 별 issue 분리 가능 (Vercel preview deploy 마다 별도 environment 라벨).

---

## 결정 (Decision)

### 1. BE Sentry wire

**파일**: `backend/src/main.py` top-level + `backend/src/core/config.py` Settings

```python
# main.py
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        integrations=[FastApiIntegration()],
        send_default_pii=False,
        before_send=_scrub_pii_hook,  # transcript/email/password/audio_url redact
        traces_sample_rate=settings.sentry_traces_sample_rate,  # 0.1
        environment=settings.environment,  # development/staging/production
    )
```

`_scrub_pii_hook` 는 `event.request.data` dict 에서 4개 필드 pop + `event.user` 에서 email/ip_address pop.

### 2. FE Sentry wire (Next.js 16)

**파일** (5개 신설 + 1개 modify):

- `frontend/sentry.client.config.ts` — 브라우저 init
- `frontend/sentry.server.config.ts` — Node.js 런타임 init
- `frontend/sentry.edge.config.ts` — Edge 런타임 init
- `frontend/instrumentation.ts` — Next.js 16 `register()` hook + `onRequestError` (Sentry `captureRequestError` 위임)
- `frontend/next.config.ts` — `withSentryConfig` wrapper (source map upload silent)

Next.js 16 의 `Instrumentation.onRequestError` type 은 `(err, request: {path, method, headers}, context: RequestErrorContext)` 이고 Sentry 의 `captureRequestError` 와 1:1 호환 (`node_modules/next/dist/server/instrumentation/types.d.ts` + `node_modules/@sentry/nextjs/build/types/common/captureRequestError.d.ts` 확인).

### 3. ENV 분리

| 환경변수 | 위치 | 기본값 | 비고 |
|---|---|---|---|
| `SENTRY_DSN` | `backend/.env` | None (skip init) | SecretStr |
| `SENTRY_TRACES_SAMPLE_RATE` | `backend/.env` | 0.1 | float |
| `ENVIRONMENT` | `backend/.env` | "development" | Sentry 대시보드 필터 |
| `NEXT_PUBLIC_SENTRY_DSN` | `frontend/.env.local` | undefined | public (browser exposed) |
| `SENTRY_ORG` | `frontend/.env.local` | "kairos" | source map upload |
| `SENTRY_PROJECT` | `frontend/.env.local` | "kairos-fe" | source map upload |

### 4. Sampling 정책

- **Errors**: 100% (Sentry 기본, 별도 설정 불필요)
- **Traces**: 10% (`traces_sample_rate=0.1`)
- **Production 트래픽 증가 시**: 0.05 ~ 0.01 로 점진 하향 (BL-OBS-1 carry-over)

---

## 상태 (Status)

**Accepted** — 2026-05-19 Sprint 22 Task 7 구현 완료.

- E22 commit `60e8266` — BE wire + PII scrub
- E23 commit `10fdaf2` — FE wire (@sentry/nextjs 10.53 + Next.js 16 instrumentation)
- E24 commit — 본 ADR + ENV docs

회귀 결과:
- BE: `uv run pytest tests/ -q` → 352 passed, 1 skipped (baseline 325 + Task 1~6 신규 27 + 0 회귀)
- FE: `pnpm typecheck` → 0 error, `pnpm build` → 12/12 static pages OK

---

## 결과 (Consequences)

### Positive

1. **silent failure 가시화** — FE 런타임 에러 / BE 5xx 모두 Sentry 대시보드에서 실시간 확인 가능. 외부 user dogfooding 진입 가능 (Sprint 22 핵심 goal 달성).
2. **PII 안전 보장** — `before_send` hook + `send_default_pii=False` 이중 방어. transcript / email / audio_url 4 필드 명시 redact.
3. **Source map upload 자동** — `withSentryConfig` 가 Vercel build 시 source map 을 Sentry 에 업로드 (silent 모드 → 로그 출력 안 함). production 빌드의 minified stack 도 원본 라인 확인 가능.
4. **Vercel environment 자동 분리** — `NEXT_PUBLIC_VERCEL_ENV` 가 preview / production / development 자동 라벨링.
5. **OpenTelemetry 와 미래 공존** — FastApiIntegration 이 distributed trace context 를 OTLP 호환 형식으로 전파. CO-1 도입 시 별도 collector 만 추가하면 됨.

### Negative

1. **월 10k events 한도** — $0 plan 의 quota. 사용자 100명 이상 + traces 10% sampling 가정 시 1-2개월 내 도달 가능. quota 도달 시 Sentry 가 자동 drop → 알람 미수신 risk. BL-OBS-1 carry-over (production 진입 직전 paid plan 검토 또는 sampling 0.05 하향).
2. **FE bundle size +30KB gzipped** — `@sentry/nextjs` 의 자동 instrumentation 비용. 본 ADR 의 trade-off 로 수용.
3. **`SENTRY_DSN` env 누락 시 init skip** — staging/production 배포 시 env 주입 누락하면 silently 비활성 → 모니터링 0. 배포 체크리스트에 명시 (BL-OBS-2).
4. **PII redact list 가 명시적** — 신규 PII 필드 추가 시 `_scrub_pii_hook` 도 수동 갱신 필요. 자동화는 BL-OBS-3 (linter 또는 schema-driven redactor).

### Carry-over (BL-OBS-*)

- **BL-OBS-1**: Sentry quota 모니터링 + production sampling 정책 (Sprint 22 outreach 후 트래픽 측정 후).
- **BL-OBS-2**: 배포 체크리스트에 `SENTRY_DSN env injection` 명시 추가.
- **BL-OBS-3**: PII 필드 자동 발견 linter (transcript / email / audio_url 외 신규 필드 추가 시 경고).
- **CO-1**: OpenTelemetry full instrumentation 도입 (Sprint 23+, 8-12h 별도 ADR).

### 불변식 (Invariants)

- **I-OBS-1**: `send_default_pii=False` 는 절대 활성화 금지. PII 누출 1차 방어선.
- **I-OBS-2**: `before_send` hook 의 redact 필드 list 는 PII 추가 시 동시 갱신. 코드 리뷰 단계에서 검증.
- **I-OBS-3**: DSN 비어 있을 때 init skip 패턴 유지. dev/test 환경에서 Sentry 외부 호출 차단.

---

## 검증 (Verification)

본 ADR 채택의 실측 검증은 Sprint 22 dogfooding 후 1회 (Task 8.7 walkthrough) + Sprint 23 진입 시 대시보드 확인 (`git history` 신설 시).

체크리스트:
- [ ] Sentry 대시보드에 FE+BE event 실제 수신 (production DSN 주입 후)
- [ ] PII redact 작동 확인 (전송된 event JSON 에 transcript / email 필드 부재)
- [ ] Source map upload 성공 (production stack trace 의 라인 번호가 원본 ts 파일 라인 매칭)
- [ ] traces_sample_rate 0.1 효과 확인 (events 수 trends 모니터링)
