<!-- 다음 단계 — discovery-first 1-pager (codex 2회 검토 후 lean화, 0-user solo founder) -->

# Kairos 다음 단계 — discovery-first (2026 H2)

> 2026-06-17. codex 2회 검토 후 **lean 1-pager로 축소** — 0-user solo founder 단계엔 전략 문서 1개면 충분(과잉 프로세스 컷).
> 잔여 부채/기능 52건 상세 = `docs/REFACTORING-BACKLOG.md` + 2026-06-01 deep-review `docs/dev-log/qa/2026-06-01-deep-review/report.md` §5. 본 문서는 **"지금 무엇을 / 무엇을 안 할지"** 만.

## 목표

ADR-024 종료 기준 = **paid customer 1명**. 0-user 단계의 진짜 병목은 코드가 아니라 **prospect 부재**. → 다음은 엔지니어링이 아니라 **고객 발견 + 가치 검증**.

## 다음 한 가지 (the ONE thing)

**실제 prospect 3명에게 12분 CODE walkthrough + 그중 1명의 실 데이터로 L3 concierge 결과물(회의 N건 → 지식문서, dev 가 수동 작성)을 만들어 "계속 쓰겠나 / 돈 내겠나"(paid ask)까지 간다.** 빌드가 아니라 검증.

## 이번 단계 to-do (최소만)

| # | 할 일 | owner | 비고 |
|---|---|---|---|
| 1 | prospect 3명 outreach + walkthrough 예약 | 사용자 | Sprint 15 R8 80채널 활용 |
| 2 | **L3 concierge** — 1 워크스페이스 손으로 요약해 반응·지불의사 확인 | dev + 사용자 | 빌드 0, 가장 싼 paid-신호 검증 |
| 3 | **최소 prod 데모복구** — Cloud Run `/health` 200 + 핵심 5 엔드포인트 smoke (crash-loop 해소만) | 사용자(배포·결제) + dev(절차) | runbook/Sentry gold-plating **금지** |
| 4 | 외부 링크 열기 전 **최소 가드** — rate-limit(RAG≤30/upload≤10) + CORS 화이트리스트 | dev | 나머지 하드닝 defer |
| 5 | 1p **interview rubric + paid-ask 문구** | dev | Sentry measurement system 불필요 |

## 지금 하지 않을 것 (defer → 백로그)

- **A-W2 아키텍처 deepening** (audit 도메인 / CSP nonce / RAG 병렬 / DI 통일 / memory 모듈 / timezone / alembic FK) — 5명 dogfooding 전 ROI 낮음. (`REFACTORING-BACKLOG` BL-S27e-C/D/F, BL-001/007/008/009/012/062)
- **AW1 나머지 하드닝** (upload streaming / client singleton / deps lock-check / flaky 격리) — prospect 사용을 막는 증거 없으면 보류. (Sprint 29 carry: flaky `test_embedding_regenerate` 간헐 2-fail)
- **L4 풀 구현 + 정식 decision-gate ADR** — 데이터/신호 없는 지금은 프로세스 부채. **build-gate = paid 신호 후**, 그때 thin prototype 0.5~1d timebox 로 de-risk (manual concierge 가 더 저렴). L4 = moat(ADR-010)이나 timeline risk — 신호 후 ADR 정식화.
- **measurement packet**(Sentry event checklist 등) — interview rubric 1p 로 대체.

## 분기 조건 (walkthrough/dogfooding 후 — ADR-024 회수 옵션)

| 결과 | 다음 |
|---|---|
| **3+ 활성(capture 5+/recall 3+) + 1+ 지불의사** | L3 풀빌드 + L4 build-gate 평가(thin prototype) + 하드닝 본격(A-W1/W2) |
| **1~2 활성** | onboarding UX 개선 + 재시도 |
| **0 활성** | product pivot (PRD v3.1 office-hours 재검토) |

## 외부/운영 (owner = 사용자, dev 단독 불가)

prod 재배포 결정(**P0**, 위 #3 — crash-loop 05-25~ `memory project_prod_backend_deploy_drift`) · GitHub Actions 결제 복구 · Clerk Production+Svix(GA, ADR-024) · Sentry DSN · Cloud Run min-instance · Clerk key rotation · prod DB cleanup · 외부 5명 모집 + F4 인터뷰.
