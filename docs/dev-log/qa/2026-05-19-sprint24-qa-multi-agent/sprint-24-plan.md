# Sprint 24 Plan — Multi-Agent QA P0/P1 Fix Bundle (Wave 2)

> **상태**: Wave 1 closed (PR #99, 2026-05-20). Wave 2 = QA P0/P1 16 tasks 진입.
> **데드라인**: 2026-05-28 (Gemini 모델 EOL — Phase B swap `003908a` 로 이미 충족).
> **가용 시간**: 8일 (2026-05-20 ~ 2026-05-28).

---

## 0. Pre-Sprint Closure (이미 main 적용)

> Sprint 24 entry plan 작성 시점에 누락된 선행 작업. 본 plan 의 잔여 작업은 §1 이하.

### Phase B Gemini swap — closed (`003908a`, 2026-05-15, PR #32)
- `backend/src/services/ai_processing.py:18` `GEMINI_MODEL = "gemini-3.1-flash-lite"` ✓
- `backend/src/memory/service.py:68` 동일 ✓
- `docs/architecture/ai-pipeline.md` rule + code sample ✓
- `docs/architecture/rag-pipeline.md` 다이어그램 + 비교 표 ✓

→ 기존 T-1 (Gemini swap, 3h) 은 Sprint 24 진입 전 closure. **T-2 Post-Swap Delta 측정 (2h) 만 잔여**.

### Wave 1 promote 정합성 보강 — closed (`b1c777b`, 2026-05-20, PR #99)
- **BL-063** Meeting promote 시 source ActionItem 자동 복제 (target ws WorkspaceMember 검증 + assignee None reset)
- **BL-064** Note promote chunk 0 + plain_text → BG `embed_note_async` schedule + `ItemPromotionAudit.embedding_status` lifecycle + polling endpoint
- **BL-066** Sprint 23 D1 (WorkspaceSwitcher) / D3 (Inbox dismiss) 정적 분석 verify — closed. Playwright reproduce 는 BL-068/069 carry-over.
- 산출물: 387 pytest PASS + Codex 4 cycle APPROVE + Gemini review 2 finding 100% 수락 (`ac7fcdd`)

→ Sprint 24 본 plan 의 잔여 = **T-2 Delta 측정 + Multi-Agent QA P0/P1 fix bundle (16 tasks)**.

---

## 1. 목표 (1줄)

Multi-Agent QA 가 발견한 P0/P1 dogfood-blocking 결함 fix + Phase B Post-Swap Delta 측정 (Phase B swap `003908a` 및 promote 정합성 `b1c777b` 는 Pre-Sprint Closure §0).

---

## 2. 범위

### In-Scope (Wave 2)
- T-2: ADR-019 Phase B Post-Swap Delta 측정 (~2h, T-1 swap 은 Phase 0 closure)
- P0 Critical bundle: T-AI-DATE + T-RAG-MOCK-REMOVE (~2.5h)
- P0 High: T-OBN-05 (~2h)
- P1 High bundle: T-PROJ-LIST + T-NOTE-DETAIL + T-CMD-K-FIX + T-RAG-TIME-FILTER + T-AUDIT-VIEW (~12h)
- 헌법 위반: T-N+1 BL-006 cross-domain import 해소 (~3h)
- Production 차단: T-N+4 BL-T2-003 Whisper 4hr+ chunk 분할 (~4h)
- 회귀 안전망: T-N+2 composite FK fixture (~2h)

**총 Wave 2 P0+P1 ≈ 18.5~27h** (T-1 3h closed 제외, Mobile 결과로 +α 가능)

### Out-of-Scope (Sprint 25 carry)
- T-LAND-01/02: Landing wedge headline + use case (마케팅 sprint 별도 권장)
- BL-T2 P2 묶음 (input/security headers): T-N+3
- Power P2: BUG-POW-002 (Inbox bulk), BUG-POW-004 (zip export), BUG-POW-007 (API PAT)
- Casual P2/P3: BUG-CASUAL-002/003/004
- a11y P2: T-A11Y-SKIP/A11Y-CC/MOBILE-NAV (UX 폴리시 별도 sprint)

---

## 3. 작업 분해 (T-N)

> 상세 evidence-matrix.md "Sprint 24 task T-N" 참조. 본 섹션은 narrative.

### Phase 1 — ADR-019 Phase B Post-Swap Delta (2026-05-21, 2h)
- **~~T-1 Gemini swap~~** — **closed** (`003908a`, 2026-05-15, PR #32). 상세 §0 Pre-Sprint Closure.
- **T-2 Post-Swap Delta 측정** (2h): post-swap-delta-stub.md 의 5 시나리오 baseline 수집 → swap 후 재측정 → delta report. 기준 위반 (DELTA-1 worse 1건 / DELTA-3 precision-recall -10% 초과 / DELTA-2/4/5 ±20% 초과) 시 revert PR + prompt tuning.

### Phase 2 — P0 Critical bundle (2026-05-21~22, 2.5h)
- **T-AI-DATE** (1.5h): AI 액션 추출 prompt에 `현재 연도={current_year}` 컨텍스트 + 미래 일자 검증 안전망 (`assert deadline_date.year >= current_year`)
- **T-RAG-MOCK-REMOVE** (1h): `frontend/src/features/rag/components/search-scope.tsx:31-37` MOCK_SELECTABLE_SOURCES 제거 + 실 API 연동 또는 empty state

### Phase 3 — P0 High (2026-05-22, 2h)
- **T-OBN-05** (2h): Sprint 22 OBN-01~04 FE UI 발화 fix. 신규 가입자가 dashboard 진입 시 onboarding step UI 실제 render 검증. Curious dogfood 재시연 필수.

### Phase 4 — P1 High bundle (2026-05-23~25, 12h)
- **T-PROJ-LIST** (2h): `frontend/src/app/(app)/projects/page.tsx` 신설 (list page). BE `/api/v1/projects` 이미 존재.
- **T-NOTE-DETAIL** (3h): `frontend/src/app/(app)/notes/[id]/page.tsx` 신설. NoteExportButton 100% 도달 가능하게.
- **T-CMD-K-FIX** (1h): dashboard 추천 질문 onClick → ⌘K 흐름 호출
- **T-RAG-TIME-FILTER** (2h): `backend/src/embeddings/repository.py` search() time_range SQL clause 추가
- **T-AUDIT-VIEW** (4h): ItemPromotionAudit read endpoint + Settings audit 탭 (admin only)

### Phase 5 — 헌법 + Production (2026-05-26~27, 7h)
- **T-N+1 BL-006** (3h): memory→embeddings 직접 import 제거. pipeline_service 위임 + I-21 _apply_hnsw_session_params 분리
- **T-N+4 BL-T2-003** (4h): Whisper 4hr+ chunk 분할. ffmpeg duration 분할 + 병렬 Whisper + offset 보존

### Phase 6 — 회귀 안전망 + 마무리 (2026-05-28, 2h+)
- **T-N+2 composite FK fixture** (2h): SCN-FK-01~12 자동화 + CI 통합
- 통합 테스트 + PR review + merge

---

## 4. 검증 기준

### 신규 테스트 (commit별 산출물)
- T-AI-DATE: `test_ai_action_date_with_year_context.py` — 연도 미명시 input + 현재 연도 context → 올바른 연도 추출
- T-RAG-MOCK-REMOVE: visual regression test (Playwright snapshot)
- T-OBN-05: Playwright `frontend/e2e/tests/onboarding-step-render.spec.ts`
- T-PROJ-LIST + T-NOTE-DETAIL: Playwright sidebar click → 페이지 정상 도달
- T-RAG-TIME-FILTER: pytest `test_rag_time_range_sql_clause.py`
- T-AUDIT-VIEW: pytest + Playwright (admin only)
- T-N+1 BL-006: ruff custom rule 또는 import-linter

### 회귀
- 기존 379 pytest + 15 Playwright spec 모두 PASS
- composite FK 12 SCN 자동화 fixture 통합

### Dogfooding
- Curious 시나리오 mini-redo (신규 가입 → AI 요약 → RAG /ask) — 3 P0/P1 fix 확인
- Granola TTFV 비교 재측정 (선택)

### Sentry / 메트릭
- Phase B swap 후 Gemini API latency 5.76x 검증 (ADR-019 Phase A spike 일치)
- Sentry error rate 변화 (FE/BE)

---

## 5. 위험 + 완화책

| 위험 | 영향 | 완화책 |
|---|---|---|
| Phase B Gemini 3.1-flash-lite 품질 저하 (Delta 측정 fail) | swap revert PR 필요 (003908a 되돌리기) | T-2 Post-Swap Delta 측정 critical 1건 worse 시 일시 revert → prompt tuning → 재swap |
| T-OBN-05 fix가 dogfood 재현 어려움 (Curious 계정 reuse) | 신규 가입 흐름만 발화 | E2E 테스트 + 별도 incognito 검증 + storageState clear |
| T-NOTE-DETAIL 디자인 의존 (DESIGN.md follow) | UI 작업 시간 +α | meetings detail 페이지 패턴 reuse |
| BL-006 lazy import 해소 시 순환 의존 발견 | T-N+1 시간 +α | pipeline_service.py 신규 wrapper 추가 (헌법 §4 권장 패턴) |
| BL-T2-003 ffmpeg chunk 분할 라이브 테스트 (4hr+ audio) | 테스트 비용/시간 | mock audio + Whisper 30min chunk 단위 stub |
| 시간 부족 (Wave 2 P0+P1 18.5h+, 8일 / 5~6 working days = 충분하나 promotion + review) | 일부 P1 carry | T-AUDIT-VIEW 또는 T-RAG-TIME-FILTER 우선 carry 후보 |

---

## 6. 자의 결정 라벨 (사용자 검토 권장)

| 라벨 | 결정 | 근거 |
|---|---|---|
| [확인 필요] T-LAND-01/02 별도 sprint | Sprint 24 out-of-scope | 마케팅/copy 작업 — eng sprint 와 분리 권장 |
| [확인 필요] T-N+3 BL-T2 5건 묶음 carry | Sprint 25 | input/security 폴리시 — 차단 요인 아님 |
| [확인 필요] T-N+5 BL-T2-005 carry | Sprint 25 | 테스트 fixture 만 |
| [확인 필요] T-A11Y-* 별도 sprint | a11y polish sprint | WCAG compliance 별도 트랙 |
| [확인 필요] BUG-CURIOUS-003 fix 검증 방법 | Curious mini-redo or 새 Clerk 계정 | 신규 가입 흐름만 발화 |

---

## 7. 예상 일정

| 날짜 | 작업 | 누적 시간 |
|---|---|---|
| ~~2026-05-20~~ | ~~T-1 Gemini swap (3h)~~ — **closed `003908a` 2026-05-15 (Phase 0)** | — |
| 2026-05-21 | T-2 Delta 측정 (2h) + T-AI-DATE + T-RAG-MOCK-REMOVE (2.5h) | 4.5h |
| 2026-05-22 | T-OBN-05 (2h) + T-PROJ-LIST (2h) | 8.5h |
| 2026-05-23 | T-NOTE-DETAIL (3h) + T-CMD-K-FIX (1h) | 12.5h |
| 2026-05-24 | T-RAG-TIME-FILTER (2h) + T-AUDIT-VIEW (4h) | 18.5h |
| 2026-05-25 | T-N+1 BL-006 (3h) | 21.5h |
| 2026-05-26 | T-N+4 BL-T2-003 (4h) | 25.5h |
| 2026-05-27 | T-N+2 composite FK fixture (2h) + 통합 dogfood | 27.5h |
| 2026-05-28 | PR review + merge + Phase B 데드라인 ✅ (이미 충족) | 마무리 |

여유 시간 = ~13h (Mobile 결과 +α, T-A11Y/T-LAND/T-VOCAB 등 cherry-pick 가능, T-1 closure 로 +3h 여유 추가).

---

## 8. Mobile 결과 보강 예정

> Day 3 Mobile sub-agent 완료 시 본 plan에:
> - Mobile P0/P1 발견이 있으면 Phase 2~4 사이 삽입
> - BUG-CASUAL-005 BottomNav 44pt cross-verify 결과 → T-MOBILE-NAV 우선순위 조정

---
