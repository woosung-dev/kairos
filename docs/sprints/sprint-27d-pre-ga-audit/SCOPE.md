# Sprint 27d — Pre-GA Multi-Perspective Audit (SCOPE)

> 외부 GA dogfooding 5명 진입 직전, 6명 평가 에이전트가 MCP Playwright 로 **로컬 환경** 을 driving 하며 잠복 결함을 발굴.
> 진입 GO/NO-GO 결정의 단일 진실 (Single Source of Truth).

---

## 0. 컨텍스트

**왜 이 작업이 필요한가**
- Sprint 27c P0 fix (PR #107, 457c994) main 머지 완료. race + landing 해소.
- Sprint 27b GA dogfooding 5명 진입 직전.
- 진입 후 60-80% 첫 진입 차단 위험은 P0-1/P0-3 으로 해소했으나, **lazy seed race 외 다른 결함이 잠복** 가능.
- 이전 Sprint 27c audit 는 사고실험 + 일부 실측 → 이번은 **MCP Playwright 자동 driving 으로 실측**.
- composite verdict ≥ 7.0 + IDOR leak 0 + 일반사용자 추천 yes + Solo-A-to-Z FAIL ≤ 5 → **5명 진입 GO**.

**환경 (로컬)**
- FE: `http://localhost:3000` (Next.js 16 dev server, 사용자 머신)
- BE: `http://localhost:8000/api/v1` (FastAPI + uvicorn, 사용자 머신)
- DB: Neon dev branch (`backend/.env` 의 `DATABASE_URL`)
- Clerk: dev instance (Production 미발급, ADR-022 webhook SKIP 유지)
- GEMINI_API_KEY: 사용자 갱신 대기 (없으면 AI 흐름 fail 으로 측정 진행 가능, 신뢰도만 부분 저하)
- seed fixture: `backend/scripts/seed_qa_fixtures.py` (5계정 SENTINEL A/B, CASUAL, MOBILE, POWER) 재사용

**참고 문서 절대경로**
- `/Users/woosung/project/agy-project/kairos/CONTEXT-MAP.md` — 헌법 (I-1~I-21)
- `/Users/woosung/project/agy-project/kairos/docs/requirements/prd.md` — 8개 사용자 플로우
- `/Users/woosung/project/agy-project/kairos/DESIGN.md` — 디자인 시스템
- `/Users/woosung/project/agy-project/kairos/.claude/CLAUDE.md` — 프로젝트 규칙
- `/Users/woosung/project/agy-project/kairos/docs/adr/` — 022 Clerk webhook SKIP, 023 D-6 lock-in
- `/Users/woosung/project/agy-project/kairos/frontend/e2e/` — 기존 14 e2e spec
- `/Users/woosung/project/agy-project/kairos/backend/scripts/seed_qa_fixtures.py` — fixture 생성

---

## 1. 공통 사전 작업 (모든 에이전트 필수)

1. 사전 컨텍스트 sync — 본 SCOPE.md + 본인 범위에 명시된 필수 문서 절대경로 모두 Read.
2. 본인 페르소나 시나리오를 1-2 단락으로 명문화 (산출물 머리에 기록).
3. MCP Playwright 로 실제 로컬 프로덕션 driving (FE 3000 / BE 8000).
4. **시간 cap 엄수** (45/30/60분, 에이전트별 명시).
5. 모든 console.error / network 4xx-5xx / 스크린샷 캡처.
6. 산출물: `docs/sprints/sprint-27d-pre-ga-audit/{agent-id}.md` + 스크린샷 (`docs/sprints/sprint-27d-pre-ga-audit/screenshots/{agent-id}-*.png`).
7. 산출물 마지막에 verdict 점수 (0-10) + GO/BLOCK 명시.

---

## 2. 6명 에이전트 정의

### 2.1. agent-1-qa-function — QA-Function (기능 관점 QA Lead)

**페르소나**: 시리즈 A B2B SaaS 의 QA Lead (5년차). 회귀/기능 정합성 우선.

**참고 문서 (필수)**
- `docs/requirements/prd.md` (8개 사용자 플로우)
- `CONTEXT-MAP.md` (11개 엔티티 + I-1/I-9/I-13/I-19/I-20/I-21)
- `frontend/e2e/` 14 spec 목록 (커버 영역 인지)

**테스트 범위**
- 8개 골든 플로우 end-to-end:
  1. Clerk 가입 → personal workspace lazy seed
  2. 회의 업로드 (`frontend/e2e/fixtures/test.m4a`) → 202 → polling → 완료 status
  3. 회의 자동 요약 (Gemini) → MeetingSummary 표시 [GEMINI key 없으면 fail 으로 기록]
  4. 회의 → 액션 아이템 자동 추출 → `/actions` 도달
  5. 노트 생성 → Tiptap → 500ms debounce 자동저장 → 임베딩 status
  6. RAG 검색 (⌘K) → SSE 스트리밍 + citation
  7. Inbox 자동 분류 → confidence ≥ 0.9 확정 / 미만 선택지
  8. Project CRUD + visibility 토글 (public/draft/private)
- 4단계 RBAC 표면 UI 노출만 (deep IDOR 은 #2 영역).
- 모든 메인 페이지 라우트 200 + console.error 0건.

**테스트 방식**
- MCP Playwright: `browser_navigate` + `browser_click` + `browser_fill_form` + `browser_snapshot`.
- 플로우별 시작/완료 timestamp 기록.
- 실패 시 trace + 스크린샷.

**verdict 기준 (0-10)**
- 골든 플로우 8개 fail 갯수 (각 -1점).
- Sprint 27c audit QA-Function 4.75/10 대비 개선 여부 명시.
- **cap: 45분**.

---

### 2.2. agent-2-qa-edgecase — QA-EdgeCase (보안/엣지케이스)

**페르소나**: 보안 테스터 (B2B SaaS 침투 5년 + 멀티테넌시 전문). Sentinel A/B 2계정 동시 실행.

**참고 문서 (필수)**
- `CONTEXT-MAP.md` I-9 (멀티테넌시 격리) + I-19 (Personal workspace 1인 격리)
- `docs/adr/022-clerk-webhook-skip.md` (sync_user SKIP 잔존 리스크)
- `frontend/e2e/qa-sentinel-p0.spec.ts` (12 case + 13 IDOR endpoint 기존 커버)
- `backend/scripts/seed_qa_fixtures.py` (Sentinel A/B fixture 재사용)

**테스트 범위**
- Cross-workspace IDOR — Sentinel A JWT 로 Sentinel B workspace 자원 호출 → 403/404.
- Cross-tenant private RAG leakage — A 가 B 의 private note 인용 X.
- Personal↔Team 경계 — Personal 에서 team invite/member 호출 거부 (I-19).
- Project visibility 분기 — viewer 가 draft 접근 → 차단.
- lazy seed race 회귀 가드 — 신규 가입 후 dashboard 첫 진입 5 API 동시 호출 → 500 0건.
- localStorage workspace drift — A logout → B login → stale workspace_id 403 graceful.
- File upload 검증 — 잘못된 mime / 100MB 초과 / empty file → 400/413.
- Rate limit & 동시성 — 중복 업로드, polling 폭주 → backend OK.
- A11Y 최소 — PopoverTrigger nativeButton (BL-S27c-8), 핵심 폼 키보드 nav.

**테스트 방식**
- MCP Playwright 2 context (Sentinel A / B) 동시.
- `browser_network_requests` 캡처 → status code 분포 검증.
- Clerk fresh JWT 60s TTL → `qa-extract-credentials.spec.ts` 패턴 차용.

**verdict 기준 (0-10)**
- IDOR 1개라도 leak 시 즉시 **0/10 + BLOCK 5명 진입**.
- visibility leak 0건 = 5/10 baseline.
- **cap: 45분**.

---

### 2.3. agent-3-cto — CTO (Tech Lead / 운영 readiness)

**페르소나**: 1인 풀스택 founder 의 외부 자문. "운영 readiness, 비용, observability, 부채" 우선.

**참고 문서 (필수)**
- `CONTEXT-MAP.md` (헌법 I-1~I-21)
- `docs/adr/` (특히 019 Phase B, 020 pgvector, 022 Clerk SKIP, 023 D-6)
- `docs/architecture/{ai,rag,cross-domain}-pipeline.md`
- `backend/src/auth/dependencies.py` (lazy seed 패턴, Sprint 27c P0-1 fix 반영)

**테스트 범위 (localhost 위주, production-specific 은 [optional])**
- lazy seed 부하 분해 — 신규 가입 후 dashboard 첫 진입의 network waterfall (어떤 API 가 병목?).
- 벡터 검색 P95 — RAG 질의 5회 latency 분포. (Gemini fail 시 fallback path 확인.)
- API 시그니처 — `/api/v1/workspaces/{wid}/...` prefix 정합성 (I-13).
- Sentry 연결 — 의도적 500 발생 → 로컬 BE 콘솔 + Sentry 이벤트 도달 (BE+FE 각각).
- 보안 헤더 — `curl -I http://localhost:3000` 으로 CSP/HSTS/X-Frame-Options.
- [optional production] Cloud Run cold start 5회 측정, gcloud revision 갱신 확인.
- 부채 hot spot — Sprint 27c BL-S27c-1~12 중 운영 임계 항목 (cold start, secret rotation, retry UI).

**테스트 방식**
- MCP Playwright + Bash 병행 (curl, gcloud 는 사용자 권한 필요 시 명시).
- network waterfall 캡처 → 분석.
- 산출물에 "남은 ATM/부채 표" 포함.

**verdict 기준 (0-10)**
- 운영 readiness 3/10 → 5/10 → 7/10 단계 평가.
- Sprint 27c CTO 5.6/10 대비 변동.
- **cap: 45분**.

---

### 2.4. agent-4-ceo — CEO (YC partner / 투자자)

**페르소나**: YC partner 또는 PMF 검증 컨설턴트. "차별점, retention signal, 활성화 funnel" 우선.

**참고 문서 (필수)**
- `docs/requirements/prd.md` (가치 제안 + persona)
- `docs/adr/011-persona-definition.md` (PERSONA-001 1인 풀스택 founder)
- `frontend/src/app/(landing)/` 또는 `/` 랜딩 페이지 (소스)
- ADR-023 D-6 (개인/팀 경계 lock-in, 시연 차별점)

**테스트 범위**
- 랜딩 페이지 신뢰도 5단계 visual scan — hero / screenshots (BL-S27c-3 회귀) / pricing / FAQ / footer.
- 첫 5분 funnel — landing → signup → 첫 가치 (AI 요약 또는 RAG) 도달 minute count.
- 차별점 명시성 — Personal→Team promote 흐름이 UI 에서 발견 가능 (D-6 핵심).
- Retention signal 5종 — S1 가입 / S2 첫 회의·노트 / S3 RAG 1회 / S4 promote 1회 / S5 7일 재방문. UI 가 어디서 끊기는지.
- Copy 적합성 — 1인 founder/PM 가 즉시 이해.
- 가격 페이지 신뢰 — `/pricing` 표시 + free tier 정의 명확.
- 모바일 첫 인상 — iPhone/Pixel viewport landing 가독성.

**테스트 방식**
- MCP Playwright `browser_navigate` + `browser_take_screenshot`.
- 스크린샷에 verdict 코멘트 인라인.
- "외부인 60초 첫 인상" + "5분 깊은 평가" 2단.

**verdict 기준 (0-10)**
- 차별점 명시성 6/10 (Sprint 27c) 대비 변동.
- "친구에게 추천할 의향" 1-10 scale.
- **cap: 45분**.

---

### 2.5. agent-5-general-user — 일반사용자 (문서 無, SNS/유튜버 추천 진입)

**페르소나**: 30대 PM 또는 1인 사이드 프로젝트 운영자. "유튜버 김X가 추천한 AI 회의 노트 도구" 라고 듣고 처음 접속.

**참고 문서**
- ❌ 없음 (의도적). PRD / CONTEXT-MAP / DESIGN 모두 SKIP.
- ✅ "유튜브 코멘트 1개" 만 mock 입력: "음성 메모 → 자동 요약 + 검색이 가능하다고 들었음. 무료라고 함."

**테스트 범위**
- 랜딩 → 가입 마찰 (클릭 수, 혼란 포인트).
- "세컨드 브레인" 가치 이해도 — 가입 후 첫 화면에서 "어디서 시작?" 즉시 명확한가.
- 첫 회의 업로드 시도 — 30초 안에 업로드 버튼 발견 못 하면 fail.
- AI 요약 만족도 — Gemini fail 시 즉시 이탈로 기록.
- 검색 자연스러움 — ⌘K 발견 + 자연어 질의.
- 이탈 trigger 명문화 — Sprint 27c 3개 (dev 도메인 / 500 / 회의 fail) 재발 여부.
- 모바일 우선 시도 — 30대 PM 모바일 첫 접속 가정.

**테스트 방식**
- MCP Playwright + "내레이션 모드" (마음 속 독백 캡처).
- 단계별 "혼란 점수 0-3" (0=명확, 3=막힘).
- 산출물: "유튜버 추천 보고 들어왔는데 (좋아요/싫어요) 이유는 ___" 형식.

**verdict 기준 (0-10)**
- "친구 1명에게 추천하겠다" yes/no.
- 이탈 trigger 발생 시 즉시 NOT-READY.
- **cap: 30분** (다른 에이전트보다 짧음 — 일반사용자는 30분 안에 결론).
- **순서: 진행 마지막** (앞 5개 에이전트 결과 영향 SKIP, 진짜 첫인상 보존).

---

### 2.6. agent-6-solo-personal — Solo-Personal-A-to-Z (개인 워크스페이스 전수 회귀)

**페르소나**: PERSONA-001 1인 풀스택 founder 본인. 팀 기능 완전 제외, **Personal workspace 한정**.

**참고 문서 (필수)**
- `frontend/src/app/` 라우트 트리 (전체 페이지 enumeration)
- `CONTEXT-MAP.md` I-19 (Personal workspace 1인 격리)
- `DESIGN.md` (페이지별 컴포넌트 + 모달 분류)

**테스트 범위 — Personal workspace 13개 페이지 전수**
1. `/` 랜딩
2. `/sign-in` / `/sign-up` Clerk
3. `/dashboard` 홈 + ⌘K
4. `/new` 회의 추가 (업로드 / 직접 녹음 / 노트)
5. `/meetings/[id]` 회의 상세 + Export
6. `/projects` + `/projects/[id]` 리스트/상세
7. `/notes` + `/notes/[id]` 리스트/Tiptap editor
8. `/inbox` Inbox + dismiss
9. `/actions` 액션 아이템 칸반
10. `/search` RAG 검색
11. `/memory` (활성 시) Recall UI
12. `/settings` (Personal 가시 탭만)
13. `/pricing` 가격

**페이지별 체크리스트 (각 페이지 동일)**
- 진입 200 + console.error 0
- 가시 버튼/링크 모두 1회 클릭
- 모든 모달 열기→닫기
- 페이지 내 CRUD 한 번 (생성/조회/수정/삭제)
- 빈 상태 / 로딩 / 에러 상태 3종
- 키보드 단축키 (⌘K, ⌘S 등)

**제외**: workspace switch, team invite, member CRUD, RBAC 분기, cross-workspace (모두 #2 영역).

**테스트 방식**
- MCP Playwright 단일 Personal 계정 (POWER fixture 재사용).
- 페이지 enumeration 후 순회 (`browser_navigate` 13회).
- 산출물 = 13×6 = **78 cells** PASS/FAIL/N-A 매트릭스.
- **#1 QA-Function 과 차이**: 골든플로우 E2E vs **페이지별 표면 전수** (모든 버튼/모달).

**verdict 기준 (0-10)**
- 78 cells 중 FAIL 갯수 → `10 - (FAIL/8)` 점.
- console.error 1회 발생 시 -1점 누적.
- **cap: 60분** (가장 광범위).

---

## 3. 진행 방식 (사용자 lock-in 대기)

| 옵션 | 설명 | 시간 |
|------|------|------|
| **A — 동시 6개** | MCP Playwright 세션 분리 가능한 만큼 병렬. 단점: 일반사용자 첫인상 격리 훼손 | ~1.5h |
| **B — 순차 6개** (권장 [가정]) | 1→2→3→4→6→5. 5번 마지막 = 앞 결과 영향 SKIP | ~4.5h |
| **C — Hybrid** | 1+2 병렬 → 3+4 병렬 → 6 단독 → 5 마지막 | ~3h |

> 권장: **B** (가장 안전, 산출물 검토 분산). 환경 여유 있으면 **C**.

---

## 4. MCP Playwright 사용 가이드

**도구 (deferred — 사용 전 ToolSearch 로 schema fetch)**
- `mcp__playwright__browser_navigate` — URL 이동
- `mcp__playwright__browser_snapshot` — DOM accessibility tree 캡처
- `mcp__playwright__browser_take_screenshot` — PNG 캡처 (수동 저장)
- `mcp__playwright__browser_click` — 요소 클릭
- `mcp__playwright__browser_fill_form` — 폼 채우기
- `mcp__playwright__browser_press_key` — 키 입력 (⌘K 등)
- `mcp__playwright__browser_console_messages` — console 메시지 dump
- `mcp__playwright__browser_network_requests` — 네트워크 요청 dump
- `mcp__playwright__browser_wait_for` — 텍스트/상태 대기
- `mcp__playwright__browser_resize` — viewport (mobile 375x812 등)
- `mcp__playwright__browser_evaluate` — JavaScript 실행 (Clerk JWT 추출 등)

**진입 패턴**
```
1. browser_navigate("http://localhost:3000/sign-in")
2. browser_snapshot()  → ref 확보
3. browser_fill_form([{ref, value: "fornerdsofficial@gmail.com"}, ...])
4. browser_click(submit ref)
5. browser_wait_for("dashboard 도달")
6. browser_console_messages() / browser_network_requests() → 캡처
```

**network 캡처 컨벤션**
- 각 시나리오 종료 시 한 번씩 `network_requests` dump → 4xx/5xx 자동 grep.
- `console_messages` 의 error level 만 산출물에 기록.

---

## 5. 산출물 포맷

각 에이전트별 `docs/sprints/sprint-27d-pre-ga-audit/{agent-id}.md`:

```markdown
# {agent-id} — {페르소나 이름} 평가 보고

## 메타
- 시작: 2026-MM-DD HH:MM
- 종료: 2026-MM-DD HH:MM
- 환경: localhost FE 3000 / BE 8000
- 페르소나 시나리오: ...

## 시나리오별 결과
### [1] {시나리오}
- 결과: PASS/FAIL/PARTIAL
- 증거: 스크린샷 `screenshots/{agent-id}-01.png`
- console.error: ...
- network 4xx/5xx: ...

## 발견 결함 (P0/P1/P2)
| ID | 우선순위 | 결함 | 재현 | 증거 |
|----|---------|------|------|------|

## verdict
- 점수: X.X/10
- GO / NO-GO / NEEDS-FIX
- BL-S27d-* 신규 등재 후보
```

---

## 6. 통합 → Verification

- 6 에이전트 산출물 → `docs/sprints/sprint-27d-pre-ga-audit/integrated-report.md`.
- **GO 조건** (4개 모두 충족):
  1. composite verdict ≥ 7.0/10
  2. IDOR leak 0건 (QA-EdgeCase)
  3. 일반사용자 추천 yes
  4. Solo-A-to-Z FAIL ≤ 5 cells
- 미달 시 → BL-S27d-* 등재 → Sprint 27d 진입 후 재 audit.
