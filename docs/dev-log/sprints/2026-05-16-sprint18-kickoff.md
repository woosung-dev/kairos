# Sprint 18 Kickoff (2026-05-16)

> Sprint 17 closeout 직후 진입. /loop qa-fix 워크플로우 유지.

## Sprint 17 carry-over 처리

| 항목 | 상태 |
|---|---|
| BL-040 RAG visibility production verify | PR #72 `verify-prod.sh` 로 entry 마련 |
| BL-036 perf production verify | 동일 — `scripts/verify-prod.sh` |
| BL-043 nightly heavy e2e | PR #69 (이미 머지, cron 활성) |
| BL-044 SourceAddModal upload | **Sprint 18 핵심 — 별도 dedicated PR 권장** (BE 도메인 신설 + R2 + FE) |
| BL-045 Satoshi 폰트 | PR #72 Fontshare 적용 완료 |
| ADR-019 Phase B verify | `memory/service.py:64` + `ai_processing.py:18` 확인 — Phase B 정착 |
| mobile 반응형 QA | PR #70 mobile-responsive.spec.ts 5 시나리오 |
| production observability | 본 PR — /ready endpoint + verify script |

## Sprint 18 진입 batch (현 PR)

본 PR (sub-branch `qa-fix-sprint18-observability-batch`) 변경:

1. **`/api/v1/ready` endpoint 신설** — DB connectivity 포함 readiness probe
   - 기존 `/health` 는 liveness (uvicorn 응답만)
   - 신규 `/ready` — `SELECT 1` 실제 DB connection 확인
   - BL-034 pool_pre_ping 효과 즉시 검증 가능
   - Cloud Run startup probe 대상으로 활용 가능 (deploy.yml 후속 검토)

2. **Sprint 18 kickoff doc** — 본 파일

## /loop 워크플로우 효율 개선 (사용자 피드백 반영)

이전 단점: 1 sub-branch 당 1 작업 → iteration 많음. 사용자 "한번에 모아서" 요청.

**개선**: 1 sub-branch 에 4-6 항목 batch. PR #72 polish (Satoshi + verify + README) 가 첫 시도. 본 PR 도 동일 패턴 (ready + dev-log).

지표: PR 수는 줄고 변경 범위 약간 커짐. review 부담 ↔ batch 응집도 trade-off.

## Sprint 18 잔여 우선순위

1. **BL-044 SourceAddModal upload** (P1, big) — BE source domain + R2 + FE wire-up
2. **production observability** — Sentry FE/BE 도입 (현재 ready endpoint 만)
3. **Cloud Run startup probe** — deploy.yml 에 `--startup-probe-http-get-path=/api/v1/ready` 추가
4. **R2 nightly cleanup** — BL-043 의 후속 (meeting-upload 누적 객체 정리)
5. **사용자 액션 항목** — production cold start 1차 deploy 후 verify-prod.sh 실측

## 참고

- Sprint 17 closeout: `docs/dev-log/sprints/2026-05-16-sprint17-closeout.md`
- BACKLOG: `docs/REFACTORING-BACKLOG.md` (BL-040~045 등재)
- /loop 워크플로우: `docs/dev-log/sprints/2026-05-16-sprint17-qa-fix-loop.md`
