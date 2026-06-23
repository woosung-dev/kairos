<!-- 다음 세션용 프롬프트 — Kairos 전체 제품+팀 멀티 에이전트 라이브 QA (ultracode, 7 페르소나 + anti-hollow-green + 분리 Evaluator) -->

# 신규 세션 프롬프트 — Kairos 전체 제품 + 팀 멀티 에이전트 라이브 QA

> 아래 `---` 사이 블록을 새 세션에 그대로 붙여넣으세요. ultracode 전제. 본 프롬프트는 2026-06-17 멀티 에이전트 팀 QA(main `3b3241c`) + 2026-06-18 팀 spine e2e 회귀(PR #128 머지, main `2d1ea43`)의 후속이며, 근거는 `docs/dev-log/qa/2026-06-17-multi-agent-qa/report.md`(커버리지 매트릭스) + `frontend/e2e/tests/team/`(T1~T18 회귀) + 7-페르소나 리서치에 grounded.

---

ultracode 모드로 진행한다. **목표: Kairos 전체 제품(전 기능 + 팀 멀티유저)을 7-페르소나 멀티 에이전트로 라이브 전수 QA하고, 확정 결함을 같은 세션에서 수정한다.** 단순 "동작 확인"이 아니라, **각 페르소나가 적대적 가설로 깊게 파고들어 라이브(실 2계정·실 AI 파이프라인)로 재현**하고, **Generator(7 페르소나) → Live Driver(Playwright MCP) → 별도 Evaluator(opus+codex) → 별도 Implementer(TDD)** 를 끝까지 분리한다. 리소스 상한 없음 — 가장 철저한 커버리지를 목표로 한다.

## 0. 왜 이 작업인가 (배경 — 이번엔 갭에 집중)

- 2026-06-17 팀 QA에서 팀/멀티테넌시 **spine**(초대/수락·RBAC 4-role·visibility·cross-tenant I-9·RAG private 누수·revocation·promote)을 라이브 검증 → 2026-06-18 **T1~T18 anti-hollow-green e2e 회귀로 영구 고정**(PR #128 머지). **spine은 이제 회귀로 가드되어 깨지면 자동 RED → 재검증 불필요(재보고 금지).**
- 따라서 이번 QA는 **회귀가 커버하지 못하는 영역**에 에너지를 집중한다:
  - ① **AI 콘텐츠 품질**: RAG 답변 정확도·citation `[N]` 정합성(2026-06-18 fix됨)·inbox 분류 정확도·distill/요약 품질·hallucination·SemanticCache 적중 정합.
  - ② **UI/UX 깊이**: 375/768/desktop 반응형·WCAG AA·카피 명료성(jargon/i18n 조사)·전 라우트 console.error 0·빈 상태/에러 상태.
  - ③ **N/A-deferred 갭**(직전 QA 미실행): 회의 오디오 파이프라인 콘텐츠 품질(STT/화자분리/요약)·온보딩 0→4 가입 플로우·export MD/JSON·viewer write-block 라이브·meeting/inbox/action promote 라이브.
  - ④ **엣지/스텁/에러 상태**: 미완 흐름·스텁("다른 프로젝트" 등)·data race·pagination 계약·long-content·timeout/500 처리.

## 1. Context Sync (순서대로 read)

1. `CONTEXT-MAP.md` §6 불변식(I-1~I-21) + §5 visibility (헌법 — 충돌 시 즉시 정렬).
2. `docs/dev-log/qa/2026-06-17-multi-agent-qa/report.md` — 직전 커버리지 매트릭스. **PASS 영역 = false-positive 필터(재보고 금지)** + N/A-deferred 갭 목록 + 노이즈 필터.
3. `frontend/e2e/tests/team/` (T1~T18) — spine 회귀 baseline. 세션 초반에 **먼저 green 확인**(아래 §6 명령) → spine 무손상 기준선.
4. `.ai/templates/workflow.md`(위험도 Lite/Standard/Heavy 게이트 + 증거 표준) → `qa` 스킬 → `.ai/integrations/with-superpowers.md`.
5. memory: `project_team_qa_20260617_done`(직전 결과·결함) · `project_team_spine_e2e_regression_done`(**재사용 gotcha**: RAG e2e timeRange 캐시-skip·ensureOwner clerkId 주입·\r\n SSE 파서·userId 매칭·CORS :3003) · `project_multi_agent_qa`(Sentinel/Curious/Casual 선례) · `feedback_e2e_trace_snapshot_first`(e2e 실패 시 trace page snapshot 먼저, `.first()` 금지·data-testid) · `feedback_e2e_selector_atomic_update` · `feedback_asyncpg_greenlet_precheck`.
6. **상태 verify 먼저**: main `2d1ea43`. **BE(:8000) 단일 프로세스 재시작**(`uv run --directory backend uvicorn src.main:app --host 127.0.0.1 --port 8000`, `--reload` 금지) + `backend/.env` CORS `:3003` 확인. FE `:3000`(수동 도그푸딩)/`:3003`(playwright). `.env.local` `QA_LOCAL_OWNER`(d@e.com)/`QA_LOCAL_MEMBER`(a@e.com). AI 키(GEMINI/OPENAI/R2/CLERK pk_test) 활성 = 실 파이프라인.

## 2. 위험도 = HEAVY → 게이트 강제

보안/RBAC/AI/DB 다수 영역 → **Heavy**. 게이트: `verification-before-completion → /codex + agy 교차 → /review → /qa Exhaustive → /ship → Monitor`. 확정 결함 수정은 **별도 Implementer 서브에이전트 TDD**(버그 지점 mock 금지). 증거 표준: FE 스크린샷 + `console.error` 0 / BE pytest + alembic dry-run / **회귀 무손상**(team e2e T1~T18 green + 전체 pytest). API 시그니처 변경 시 schemathesis + Playwright e2e 둘 다. doc routing: 불변식/격리 건드리면 `CONTEXT-MAP.md` Atomic Update. 플랜 = `docs/plans/active/<slug>.md`.

## 3. 에이전트 아키텍처 (Generator / Live Driver / 별도 Evaluator / 별도 Implementer)

**분리 = load-bearing**: Evaluator/Implementer는 Generator가 어떻게 설계했는지 모르는 fresh context. self-grading·버그 지점 mock 금지(QA-0617-A 재발 방지).

| 역할 | 스킬/툴 | 동시성 | 산출 |
|---|---|---|---|
| **Generator (7 페르소나)** | 코드 근거 체크리스트(페르소나별 적대 가설) | 병렬(Workflow parallel) | 페르소나 × 제품영역 체크리스트 |
| **Live Driver** | Playwright MCP, 2계정 직접 로그인(d@e.com/a@e.com), API+DB+UI 증거 | 직렬(공유 라이브 stack) | PASS/FAIL + 스크린샷/SSE/응답 증거 |
| **Evaluator (fresh)** | opus 인라인 6문항 게이트 + **/codex 교차** | 병렬 | 확정 결함 / 반증(false-positive) 분류 |
| **Implementer (별도)** | `test-driven-development` + `subagent-driven-development` | 직렬 | fix + 회귀 테스트(버그 지점 mock 금지) |

### 7 페르소나 (non-overlapping partition — spine 회귀 가드 전제로 깊이에 집중)

1. **SENTINEL (보안/적대)** — cross-tenant IDOR(I-9)·RBAC 4role×5action×3visibility 매트릭스·**soft-delete/archive 후 권한 잔존**·composite FK(I-17)·invite 만료/max_uses·personal 격리(I-19). *spine 기본은 T1~T18이 가드 → SENTINEL은 회귀가 안 건드린 변형(archive된 리소스 접근, 멤버 제거 후 잔존 ProjectMember, 동시성 변형)에 집중.*
2. **CURIOUS (엣지/완성도)** — 스텁/미완 흐름("다른 프로젝트" 등)·에러 상태(failed/processing/retry UI)·data race(lazy-seed 멱등·중복 멤버·orphan)·long-content overflow·pagination 계약(pageSize 준수).
3. **CASUAL (happy-path/UX)** — 신규 첫인상·카피 명료성(RAG→AI검색, promote→팀이동, `을(를)` 조사)·375/768 반응형·WCAG AA 대비·전 라우트 console.error 0·빈 상태 명료성.
4. **POWER (고급 흐름)** — 멀티프로젝트/멀티ws 전환·**promote 5도메인(memory/meeting/note/inbox/action) 라이브**·export MD/JSON·복합 필터(status/priority/project/time_range).
5. **CONTENT-SKEPTIC (AI 품질)** — RAG 답변 정확도·**citation `[N]` 정합(클릭→SourceViewer, 2026-06-18 fix 라이브 확인)**·inbox 분류 정확도·distill/요약 품질·hallucination·SemanticCache(0.93/7d) 적중 정합.
6. **ONBOARD (첫 실행)** — 신규 가입 0→4 단계·seed workspace·튜토리얼/툴팁·OnboardingBanner.
7. **MOBILE (반응형)** — 375px bottom-nav·768 sidebar collapse·modal/tooltip/이미지 overflow·`/new` 3-col 375px stack.

## 4. 커버리지 타깃 (갭 우선)

라우트 18종 × 페르소나 partition. 각 페르소나는 자기 영역을 **깊게**(적대 가설 → 라이브 재현). spine 회귀가 가드하는 항목은 baseline green 확인만 하고 **깊이/품질/UX/엣지**로 에너지 이동:
- **AI 파이프라인 품질**(CONTENT-SKEPTIC): 회의 업로드(풍부한 화자 샘플 있으면 STT/요약 품질, 없으면 기계 동작만) → distill L0~L2 → RAG 답변 근거·citation 정합 → promote 후 팀 검색성.
- **UI/UX**(CASUAL/MOBILE): 전 라우트 light/dark 스크린샷 + console.error 0 + 375/768/desktop + 카피.
- **deferred 갭**(POWER/CURIOUS): export MD/JSON·viewer write-block 라이브·meeting/inbox/action promote 라이브·온보딩 0→4(ONBOARD).
- **보안 깊이**(SENTINEL): 회귀 변형 엣지(archive 권한·orphan·concurrent 변형).

## 5. anti-hollow-green + false-positive 필터 (비협상)

- 실 2-토큰 라이브 관통(mock 금지). **버그 지점 mock 금지**(QA-0617-A 교훈 — 회귀 테스트도 실 seam만 stub).
- **재보고 금지(VERIFIED)**: cross-tenant I-9·visibility 3종·RAG private 누수 0·RBAC 캐시 즉시성·revocation·ws-switch·memory/note(chunked) promote — 모두 T1~T18 + 2026-06-17 report로 확정. 깨지면 회귀가 RED.
- **노이즈 필터(앱 결함 아님)**: Clerk `accounts.dev` CSP 경고·의도적 음성 API 프로브 4xx/5xx·프로젝트 제목 emoji(온보딩 seed data)·OPTIONS preflight.
- 새 결함은 **라이브 재현 + 회귀 테스트 동반** → 확정만 수정.

## 6. 환경/함정 + 회귀 baseline

```bash
# (a) spine 회귀 baseline 먼저 green 확인 (BE :8000 단일프로세스 + CORS :3003 + FE :3003)
cd frontend; set -a; . ./.env.local; set +a
E2E_RUN_TEAM=true E2E_API_URL=http://localhost:8000 \
  pnpm exec playwright test --project=team --workers=1   # T1~T18 green = spine 무손상

# (b) 전체 pytest baseline
uv run --directory backend pytest -q                      # 566+ pass
```
- BE `:8000` **단일 프로세스**(`--reload` 금지 — in-process RBAC 캐시 단일성). `backend/.env` `CORS_ORIGINS`에 `:3003` 포함 필수(없으면 preflight 400 노이즈).
- 포트 고정: FE `:3000`(수동 도그푸딩)/`:3003`(playwright) → BE `:8000` → 공유 Neon.
- **전용 admin/viewer dev 계정 부재**(deferred) — d@e.com(owner)/a@e.com(member) 2계정으로 owner가 B의 role 전환(member↔admin↔viewer)해 4-cell 전수.
- 팀 e2e 재사용 gotcha(memory `project_team_spine_e2e_regression_done`): RAG e2e는 `timeRange` 로 캐시 skip, 멤버 매칭은 userId(email 빈 lazy-seed), active ws는 localStorage `{activeWorkspaceId, ownerUserId:clerkId}` 주입.

## 7. 수용 기준 (done) / 산출물

- **페르소나별 커버리지 매트릭스**(기능 × role/페르소나 → PASS/FAIL/N/A) + 확정 결함(P0/P1) **라이브 재현 + 수정 + 회귀 테스트**(별도 Implementer).
- **회귀 무손상**: team e2e T1~T18 green + 전체 pytest pass + UI console.error 0 + `/codex` + `/review`.
- 격리/불변식 건드리면 `CONTEXT-MAP.md` Atomic Update. Git Safety(커밋·푸쉬·머지 각 승인).
- 리포트 `docs/dev-log/qa/2026-06-19-full-product-team-multi-agent-qa/report.md`(스크린샷 포함) + 메모리 closeout.

---

## 부록 — 7 페르소나 라이브 활동 예시 (Live Driver 참고)

- **SENTINEL**: 2계정 동시 + archive된 프로젝트 직접 ID 접근(404 기대)·멤버 제거 후 ProjectMember 잔존 여부·동시 invite-accept 변형·JWT/workspace_id mismatch.
- **CURIOUS**: inbox promote→dismiss 사이클 + cross-project 스텁·meeting 파이프라인 상태 전이·50+ 항목 pagination·note 0-chunk promote(QA-0617-A 회귀).
- **CASUAL**: 신규 가입 첫 플로우·375px `/new` 3-col stack·전 18라우트 console.error+light/dark 스크린샷·avatar a11y name.
- **POWER**: 멀티ws 전환·promote 5도메인 라이브·export MD/JSON(UTF-8 파일명)·복합 필터.
- **CONTENT-SKEPTIC**: RAG 답변이 실 소스 근거인지·`[N]` 클릭→SourceViewer 정합·inbox 분류 정확도·요약 hallucination.
- **ONBOARD**: incognito 신규 이메일 가입 0→4·seed ws·OnboardingBanner mount/dismiss.
- **MOBILE**: 375/768 전 라우트 layout·bottom-nav·modal overflow.
