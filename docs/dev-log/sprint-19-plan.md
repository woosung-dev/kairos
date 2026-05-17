# Sprint 19 Plan (초안 — Multi-Agent QA 결과 반영판)

> 생성: 2026-05-17
> 입력: Sprint 18 closeout + BUG-C01 fix (`19eb363`) + Multi-Agent QA Sentinel-P0/P1 + 4 페르소나 smoke + Codex consult 리뷰 (session `019e3518`)
> 본 plan = 사용자 triage용 **초안**. 최종 BL/ISSUE 등재는 사용자 승인 후.

---

## 0. 목표

Sprint 18에서 발견 + 즉시 fix 된 **BUG-C01 (workspace IDOR)** 후속 가드 + Multi-Agent QA 후속 결함 + 미완료 캐리오버 BL 우선순위 처리.

**4축**:
1. **(a) Sprint 18 캐리오버 BL** — 미완료 BL 24+건 중 우선순위 ★★★만 추려서
2. **(b) Multi-Agent QA 후속 결함** — Sentinel-P0/P1 + 4 페르소나 Critical/High
3. **(c) Mobile QA 결과 반영** — Mobile 페르소나 결과 + Sprint 18 mobile carry-over
4. **(d) 온보딩 / Granola 비교 개선** — Curious 페르소나 + Granola.ai 비교 인사이트

---

## 1. 범위 (In / Out)

### In (Sprint 19)
- BUG-C01 후속 매트릭스 점검 (BUG-C01-EXT) — 다른 도메인 router `require_viewer/member` 일관성
- IDOR 응답 일관화 (404 vs 403 timing side-channel)
- 회귀 가드 (통합 IDOR 테스트 매트릭스)
- 4 페르소나 smoke 결과 Top 5 Critical/High fix
- Mobile carry-over (BL-017 Mobile FAB collision)
- 온보딩 첫인상 / TTFV 개선 (Curious 결과)

### Out (Sprint 19 외)
- 대규모 리팩토링 (BL-001 / BL-013)
- memory 모듈 8건 (BL-005~012) — 별도 Sprint
- pgvector 측정 / 운영 (BL-024~026 production 측정만 별도)
- DESIGN.md 결정 의존 (BL-037 / BL-045)

---

## 2. 4축 작업 분해

### (a) Sprint 18 캐리오버 BL — P0/P1만 추림

| BL | 제목 | 우선순위 | Sprint 19 inclusion |
|---|---|---|---|
| BL-017 | Mobile FAB collision with bottom nav | ★★★ | **P1** — Mobile 페르소나 검증 결과와 묶어서 fix |
| BL-016 | PromoteModal 동명 workspace 구분 | ★★ | **P2** |
| BL-019 | Recall metrics 신선도 + sparkline | ★★ | **P2** (단독 spec 필요) |
| BL-024 | pg_prewarm 정책 (Cloud Run cold start) | ★★★ | **P1** (production 측정과 묶음) |
| BL-026 | 측정 강화 nDCG/precision/EXPLAIN | ★★ | **P2** |
| BL-028 | memory/service.py BackgroundMemoryService 분할 | ★★ | **P2** (Sprint 20 후보) |
| 기타 | BL-001 / BL-005~012 / BL-013 / BL-020 / BL-022 / BL-023 / BL-025 / BL-032 / BL-033 / BL-037 / BL-045 | ★ ~★★ | **Out** |

### (b) Multi-Agent QA 후속 결함 — Sentinel + 4 페르소나

#### Sentinel-P0 후속 (이미 BUG-C01 fix 완료)
- **BUG-C01-EXT (P0)**: meetings/notes/inbox/actions router에 `require_viewer` 또는 `require_member` 일관 적용되었는지 매트릭스 점검 + 통합 회귀 테스트 (`backend/tests/integration/test_workspace_idor_matrix.py`)
- **P1 IDOR 응답 일관화**: 404 vs 403 timing side-channel 차단. 모든 cross-tenant 시도 403 통일 + 응답 시간 정규화

#### Sentinel-P1 결함 (38 케이스 / 8 영역, Score 6.6/10, 통합 Sentinel 8.0/10)

| Severity | ID | 요약 | 권장 fix | 추정 |
|---|---|---|---|---|
| **High** | BUG-P1-03 | RAG ask `question="   "` → HTTP 500 (Pydantic strip 누락) | whitespace validator 1줄 | 30min |
| **High** | BUG-P1-05 | CSP/HSTS/X-Frame/nosniff/Referrer/Permissions 전체 누락 + `X-Powered-By: Next.js` 노출 | 보안 헤더 baseline 6종 + Next.js 헤더 제거 | 4h |
| Medium | BUG-P1-02 | 422 응답 `detail[].input` 에 사용자 입력 echo (30KB 측정) | Pydantic error_response 변환 | 1h |
| Medium | BUG-P1-04 | XSS payload LLM 응답에 백틱 echo → FE markdown 렌더 방식 점검 필요 | FE markdown sanitize 검증 | 2h |
| Medium | BUG-P1-06 | 60 동시 burst 100% 200 → rate limit 미적용 | SlowAPI rate limit middleware | 2h |
| Low | BUG-P1-01 | 만료 vs 무효 토큰 메시지 비일관 UX | 에러 메시지 통일 | 30min |
| Low | ISSUE-P1-07 | Pydantic 422 / 500 기본 메시지 영어 잔존 | i18n 처리 | 1h |

**즉시 fix Top 3** (Sprint 19 P0/P1):
1. BUG-P1-05 보안 헤더 baseline (~4h, P0 — 외부 공격 표면)
2. BUG-P1-03 whitespace 500 (~30min, P1 — 사용자 신뢰)
3. BUG-P1-06 rate limit (~2h, P1 — DoS 방어 baseline)

**Sentinel 안전성 확인 (강점, Sprint 19 회귀 가드 baseline)**:
- prompt injection: 시스템 프롬프트 leak 0
- SQL injection: DB query 안전
- Secret / file path leak: 0 (`/users/me` + 404/403 응답 모두 clean)
- SSE `event: done` 정상 종료 + cache hit 정상
- 한국어 IDOR 에러 메시지 일관 (`"워크스페이스 멤버가 아닙니다"`)

#### 4 페르소나 smoke 결함 (30 결함 / Composite raw 4.3/10)

| 페르소나 | C | H | M | L | 합 | Health |
|---|---|---|---|---|---|---|
| Curious | 0 | 2 | 4 | 2 | 8 | 5.0 |
| Casual | 0 | 2 | 5 | 2 | 9 | 4.0 |
| Mobile | 0 | 2 | 3 | 1 | 6 | 4.4 |
| Power | 0 | 3 | 3 | 1 | 7 | 3.4 |
| **합** | **0** | **9** | **15** | **6** | **30** | — |

**Top 5 Sprint 19 후보** (★중복 발견 = P0 격상):

| ID | 요약 | 페르소나 | 추정 | Sprint 19 |
|---|---|---|---|---|
| **BUG-C02** | `/projects` 404 (BottomNav primary + dashboard 카드) ★중복★ | Mobile H-1 + Casual H-2 | 2-4h | **P0** |
| **BUG-C03** | `/meetings` 404 (meeting list view 부재) | Casual H-1 | 4-6h | **P0** |
| ISSUE-018 | Cmd+K 시퀀스 단축키 안내만 있고 핸들러 미연결 | Power H-1 | 1-2h | P1 |
| ISSUE-019 | Inbox 벌크 작업 0 (checkbox 0 / 전체선택 0) | Power H-2 | 4-8h (신규 기능) | P1 |
| BUG-C04 | Export UI 누락 (API endpoint 2개 존재) | Power H-3 | 2-4h | P1 |

**보조 발견**:
- a11y color-contrast: 4 페이지 49 노드 위반 (inbox 27 노드 최다) — `ISSUE-A11Y-NNN` 후보
- BUG-C01 fix(`19eb363`) cross-tenant IDOR 정상 동작 ✅ (Power API 검증으로 재확인)

### (c) Mobile QA 결과 반영 (BL-017 + Mobile 페르소나)

Mobile 페르소나 결과 + Sprint 18 mobile carry-over 통합 fix 사이클:

| ID | 요약 | 소스 | Sprint 19 |
|---|---|---|---|
| BUG-C02 | `/projects` 404 (BottomNav 첫 진입점) | Mobile H-1 (★중복) | **P0** (위 §2(b) 합쳐서 처리) |
| BL-017 | Mobile FAB collision with bottom nav | Sprint 15 carry-over | P1 |
| (M-1) | 모바일 키보드 가림 (`/new` 회의 제목 input iOS) — 좌표 미측정 | Mobile [확인 필요] | P2 (재측정 후 등재) |

mobile 전용 fix 사이클로 묶음 (1 PR).

### (d) 온보딩 / Granola 비교 개선 (Curious 페르소나)

**Granola 대비 핵심 gap**:
- 랜딩 시각자료: Kairos **0** vs Granola **88 image / 3 video**
- 가치 제안 5초 첫인상: 명확성 약함
- 가입 마찰 단계 수: TBD (Curious 보고서 상세)

| ID | 요약 | 추정 | Sprint 19 |
|---|---|---|---|
| ISSUE-OBN-01 | 랜딩 히어로 영역 시각자료 추가 (스크린샷 + 짧은 영상) | 1-2주 (디자인 + 콘텐츠) | **P0** (외부 페이지 핵심) |
| ISSUE-OBN-02 | 가치 제안 헤드라인 명확화 (Curious 5초 첫인상 기반) | 4-8h | P1 |
| ISSUE-OBN-03 | TTFV 단축 (가입 → 첫 가치 도달 클릭 수 감소) | 1주 (UX flow 재설계) | P1 |
| ISSUE-OBN-04 | Granola 차별점 명시 (Recall 검색 / RAG / 한국어 UX) | 4h (랜딩 카피) | P2 |

### (c) Mobile QA 결과 반영

> _Sub-agent A Mobile 페르소나 결과 받은 후 채움._

Sprint 18 mobile carry-over (BL-017 + TODO.md "mobile 반응형 QA") + 이번 Mobile smoke 결과 통합:
- viewport 회귀 (375/393/412)
- 터치 타겟 < 44pt 케이스 → fix
- BottomNav / FAB collision 해소
- 모바일 키보드 흐름 (input focus 시 화면 가림)

### (d) 온보딩 / Granola 비교 개선

> _Sub-agent A Curious 페르소나 결과 받은 후 채움._

Curious 페르소나 5초/30초/1분 첫인상 + Granola.ai landing/onboarding 비교 → ISSUE-OBN-NNN:
- 첫인상 가치 제안 명확화 (랜딩 헤드라인)
- TTFV 단축 (가입 → 첫 가치 도달 클릭 수 감소)
- Granola.ai 대비 차별점 강조 부분

---

## 3. 검증 기준

- BUG-C01-EXT 완료 = 회귀 테스트 `test_workspace_idor_matrix.py` N 케이스 PASS + 응답 시간 균질 측정
- 4 페르소나 Top Critical/High fix 완료 = Sentinel-P0 spec + 페르소나 보고서 재실행 → Critical 0 확인
- Mobile fix 완료 = viewport 회귀 spec PASS + Sprint 18 mobile spec 회귀 0
- 온보딩 개선 = Curious 페르소나 재검증 (5초 첫인상 명확성 + 가입~첫 가치 클릭 수 감소)

---

## 4. 위험 + 완화

| 위험 | 가능성 | 완화 |
|---|---|---|
| BUG-C01-EXT가 다른 도메인에서 비슷한 패턴 발견 → 범위 폭발 | M | 매트릭스 점검 단계에서 발견 즉시 plan 갱신 + 사용자 confirm |
| Multi-Agent QA 결과가 예상보다 많은 결함 → Sprint 일정 초과 | H | (b)(c) 우선순위 Top 5만 Sprint 19 진입, 나머지 Sprint 20 carry-over |
| BL 캐리오버 24+건 중 우선순위 선택의 주관성 | M | 사용자 triage 단계에서 ★★★만 P1 후보 등재, ★★는 P2/Out |
| Mobile 테스트 환경 (실 디바이스 미존재) | M | viewport simulation으로 한계 인정 + production 측정 BL 보강 |

---

## 5. 자의 결정 라벨

- [확인 필요] BUG-C01-EXT 점검 범위 — 4 도메인 (meetings/notes/inbox/actions) 모두 vs Top 2만
- [확인 필요] Sentinel-P0/P1 spec을 CI 게이트로 격상 vs 로컬 manual 유지
- [확인 필요] BL-024 pg_prewarm은 production 측정 데이터 없이 spec 만들기 가능한가
- [확인 필요] Sentinel-P1 G.3 SSE BE uvicorn cleanup 정확 동작 (BE 로그 verification 후속 필요)
- [확인 필요] Sentinel-P1 D.3 HSTS prod 환경 직접 검증 (local http 한정 PASS)
- [확인 필요] BUG-P1-04 XSS payload LLM echo — FE markdown 렌더 sanitize 방식 점검 우선순위
- [가정] Sprint 19 ~2주 sprint. 8-10 PR. Sprint 18 closeout 패턴 재사용.
- [가정] 사용자가 4축 모두 우선시 결정 (이번 세션 plan-mode AskUserQuestion 응답). Out 항목은 Sprint 20 이후 carry-over.

---

## 6. 예상 일정 (~2주, 8-10 PR)

| Day | 작업 |
|---|---|
| 1-2 | BUG-C01-EXT 매트릭스 점검 + 회귀 테스트 작성 |
| 3-4 | 4 페르소나 Top 5 Critical/High fix |
| 5-6 | Mobile fix 사이클 (BL-017 + viewport 회귀) |
| 7-8 | 온보딩 개선 (랜딩 + TTFV) |
| 9 | (a) 캐리오버 BL 1-2건 (BL-024 또는 BL-019) |
| 10 | Sprint 19 closeout (verification + retro) |

---

## 7. Sprint 19 PR 단위 (잠정)

- PR #1: BUG-C01-EXT 매트릭스 + `test_workspace_idor_matrix.py`
- PR #2: IDOR 응답 일관화 (404 → 403 + 응답 시간 정규화)
- PR #3-5: 4 페르소나 Top 5 fix (영역별 분리)
- PR #6: Mobile fix (BL-017 + viewport 회귀)
- PR #7: 온보딩 개선 (랜딩 헤드라인 + TTFV 단축)
- PR #8: BL-024 pg_prewarm 또는 BL-019 Recall metrics
- PR #9: Sprint 19 closeout + verification report

---

## 8. 사용자 triage 행동 항목

이 plan을 받은 후 다음을 사용자가 결정:

1. (a) 캐리오버 BL Top 우선순위 — BL-017 / BL-024 / BL-019 외에 추가할 항목 있는가
2. (b) 4 페르소나 Top 5 결함 중 어느 것을 P0/P1로 격상할 것인가
3. (c) Mobile 영역 fix 범위 — viewport 회귀 spec만 vs UX 깊이
4. (d) 온보딩 개선 우선순위 — 랜딩 헤드라인 vs TTFV 단축 vs Granola 차별점
5. 자의 결정 라벨 [확인 필요] 5건 응답
6. PR 단위 분할 vs 통합 (Sprint 18 rollup 패턴 vs 작은 PR)
