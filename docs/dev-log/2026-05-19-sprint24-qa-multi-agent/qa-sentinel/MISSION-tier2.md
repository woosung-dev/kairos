# QA Sentinel — Day 1 Mission Part 2 (Tier 2 기능 엣지 + 회귀 + composite FK + D1~D4)

> Tier 1 (12건) 결과: 모두 PASS, Fail-Fast 미발동. 본 mission은 Tier 1 다음 단계.

---

## 정체성
QA Sentinel 페르소나 (Tier 1 와 동일). Exhaustive depth, 60-90분 cap (Tier 1 빠르게 끝났으므로 Tier 2도 fast-path 권장).

## 환경 (Tier 1 과 동일)
- Worktree: `/Users/woosung/project/agy-project/kairos-sprint24-qa-multi-agent`
- FE: `http://localhost:3000`, BE: `http://localhost:8000`
- 자격증명: `frontend/.env.local` E2E_OWNER_*, E2E_VIEWER_*

## 안전 게이트 (Tier 1 과 동일)
- §19 코드 수정 금지, Production BE 금지, 데이터 cleanup, PII 검수
- §20 Fail-Fast: Tier 2도 Critical 발견 즉시 STOP + Decision Required

## Anti-Stall
- 시작 후 2분: `qa-sentinel/tier2-functional/report.md` Write
- 매 5분 갱신
- 시나리오 5분 cap (정적 분석으로 처리 가능한 건 그대로 fast-path)

---

## 임무

51 시나리오 = Tier 2 27 + 회귀 8 + composite FK 12 + D1~D4 4.

### A. composite FK regression 매트릭스 (SCN-FK-01~12)
- 재현: `cd backend && uv run pytest tests/integration/test_workspace_integrity_audit.py -v`
- 출력 결과를 그대로 `verification.md` §7-4 12행에 매핑 (PASS/FAIL/Skip)
- 적대적 ID 조합 케이스 추가 필요 시: ws_a + project_b 조합 insert/update/query 명령 단순화 (psql 사용 가능)

### B. Sprint 19~23 회귀 8 시나리오
- **R1** Workspace IDOR 13ep: Tier 1 SCN-T1-04 결과 그대로 인용 (PASS)
- **R2** ProjectMember cross-ws 차단: Tier 1 SCN-T1-05 인용 (PASS)
- **R3** BL-052/053/054 SQLModel/AsyncSession import: `grep -rE 'from sqlalchemy import|.session.execute' backend/src/` 으로 잔재 확인
- **R4** BL-050 composite FK 4 entity: A 와 동일 결과 (composite FK pytest)
- **R5** OBN-01~04 신규 가입 → lazy personal seed: `backend/src/onboarding/service.py` + `backend/src/auth/dependencies.py` 정적 분석 + pytest `tests/onboarding/` 실행
- **R6** Sentry FE+BE conditional init + PII scrub: Tier 1 SCN-T1-09 (mock) 인용 + `instrumentation.ts` 분석
- **R7** D1~D4 PASS 후 §7-5 결과 인용 (Section C 결과 reuse)
- **R8** F1~F4 Sprint 22 carry-over: docs/dev-log/2026-05-19-sprint22-result-report.html 의 F1~F4 정의 확인 + `git log --oneline -- frontend/src backend/src` 최근 30 commits에서 F1~F4 fix commit 검출

### C. Sprint 23 D1~D4 PASS/FAIL (SCN-D1~D4)

#### SCN-D1 WorkspaceSwitcher context fix
- **정적 분석 우선**: `grep -rn "queryClient.clear\|invalidateQueries\|router.refresh" frontend/src/components/layout/` (WorkspaceSwitcher 컴포넌트 찾기)
- **Playwright optional**: `mcp__playwright__browser_navigate http://localhost:3000` → Clerk sign-in → workspace 전환 → DevTools network panel 확인
- 5분 cap 도달 시 정적 분석만으로 판정

#### SCN-D2 Settings Compact deep-link
- 정적 분석: `frontend/src/app/(authenticated)/settings/page.tsx` `searchParams.tab` 처리 확인
- `?tab=workspaces` 처리 코드 존재 확인

#### SCN-D3 Inbox dismiss
- 정적 분석: `frontend/src/features/inbox/` 또는 hooks/useInbox 의 queryKey 분석
- isProcessed: false 분기 확인

#### SCN-D4 ItemPromoteModal 4 도메인
- 정적 분석: `frontend/src/components/promote/ItemPromoteModal.tsx` 또는 비슷한 위치
- 4 도메인 promote endpoint 호출 확인 (meetings/notes/inbox/actions)
- BE: `grep -rn "@router.post.*promote" backend/src/` 4건 매치 확인

### D. Tier 2 기능 엣지 27 시나리오

#### D-1. 콘텐츠 파이프라인 7건
- **D-1-1** 0 byte 오디오 업로드: `curl -X POST :8000/api/v1/upload/sign -d '{"size":0,"name":"empty.mp3"}'` → 400 또는 422
- **D-1-2** 비지원 코덱 (WebM): file_key 확장자 검증 코드 grep (`backend/src/upload/router.py` 또는 `common/r2.py`)
- **D-1-3** 4시간+ 오디오: Whisper API timeout config 확인 (`backend/src/meetings/service.py`)
- **D-1-4** 빈 transcript: `grep -rn "transcript == ''" backend/src/meetings/` empty handling
- **D-1-5** 비ASCII transcript: 한국어 prompt 사용 (`backend/src/common/prompts.py`) 확인
- **D-1-6** AI 구조화 실패 fallback: `try/except` 패턴 in meetings/service.py + actions/service.py
- **D-1-7** InboxItem 자동 확정 실패 → 사용자 조정: Inbox status enum + autoProcessed=false 분기 분석

#### D-2. 장기 작업 4건
- **D-2-1** 202 polling 중단 후 재시도: `GET /api/v1/meetings/{id}/status` polling endpoint 확인 (멱등성)
- **D-2-2** 동일 파일 중복 업로드: hash 비교 코드 grep `backend/src/upload/` → 없으면 BL 신규 등재 후보
- **D-2-3** 처리 중 로그아웃: BG task가 user session 의존하지 않음을 확인 (session_factory 패턴)
- **D-2-4** 202 polling timeout: client side timeout 설정 + BG task 독립 실행 확인

#### D-3. Sentry 3건
- **D-3-1** Source map (Vercel 배포 자동): `frontend/sentry.client.config.ts` + `next.config.ts` 확인
- **D-3-2** Sentry rate limit: SDK 기본 rate limit 사용 (구성 변경 없음)
- **D-3-3** Breadcrumb 추적: Clerk + fetch instrumentation 활성 확인 (`@sentry/nextjs` 자동)

#### D-4. 온보딩 5건
- **D-4-1** 자동 personal workspace seed: `backend/src/auth/dependencies.py` lazy seed 분석
- **D-4-2** TTFV (가입 → 첫 meeting): onboarding_step progression 1→4 단계 정의
- **D-4-3** EmptyState 안내: `frontend/src/components/empty/` 또는 비슷한 위치 검토
- **D-4-4** Step idempotency: `WHERE onboarding_step < :target` 패턴 검증
- **D-4-5** Step 조회 API: `GET /api/v1/users/me/onboarding` 응답 schema 확인

#### D-5. 표준 잔여 8건
- **D-5-1** 입력 max_length (회의 title 등): Pydantic schema `max_length=` 검증
- **D-5-2** Whitespace trim: `.strip()` 호출 확인
- **D-5-3** Unicode handling: 한국어/이모지 정상 처리 확인 (정적)
- **D-5-4** SQL injection (UUID 만 받는 endpoint): Pydantic UUID 강제
- **D-5-5** CSP header: `backend/src/main.py` middleware 확인 → 없으면 BL 후보
- **D-5-6** X-Frame-Options: 동일
- **D-5-7** HSTS: 동일
- **D-5-8** Referrer-Policy: 동일

---

## 산출물

### `qa-sentinel/tier2-functional/report.md`
구조:
```markdown
# QA Sentinel Day 1 — Tier 2 + 회귀 + composite FK + D1~D4 보고서

## 시작/종료 시각
시작/종료/소요

## Composite 결과
- composite FK SCN-FK-01~12: N PASS / N FAIL
- 회귀 8: N PASS / N FAIL
- D1~D4: N PASS / N FAIL
- Tier 2 27: N PASS / N FAIL / N [확인 필요]
- 신규 BL 후보: N건

## SCN별 상세 (간략 — 정적 분석 결과 위주)
### A. composite FK SCN-FK-01~12
- pytest 출력 sample
- 12 시나리오 PASS/FAIL 표

### B. 회귀 R1~R8
...

### C. D1~D4
...

### D. Tier 2 (D-1 ~ D-5 카테고리)
...

## Critical Decision Required (FAIL 발견 시)
...

## 신규 BL 후보 정리
- BL-XXX: ... (재현/대안/영향 명시)

## 종료 검증
- git diff CLEAN
- 갱신 파일 list
- 다음 단계 권장 (Day 2 Curious + Casual)
```

### 동시 갱신
- `verification.md` §7-4 / §7-5 / "Sprint 19~23 회귀 8 시나리오" 표 결과 컬럼
- `evidence-matrix.md` "Composite FK SCN-FK-01~12" / "D1~D4 SCN-D1~D4" 표 BUG/Severity/trace/screenshot 컬럼

---

## 종료 절차
1. 모든 51 시나리오 결과 입력
2. `git diff --exit-code` 재실행
3. 마지막에 "신규 BL 후보 정리" 섹션 + 다음 단계 권장
