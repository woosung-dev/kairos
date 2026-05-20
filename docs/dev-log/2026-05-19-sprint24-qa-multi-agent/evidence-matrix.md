# Sprint 24 Multi-Agent QA — Evidence Matrix

> codex F7 권고 수락. 모든 SCN-/BUG-/BL-/T- ID 연결 추적.

**ID prefix**:
- `SCN-` = 시나리오 ID (Sentinel 39 + Curious + Casual + Power + Mobile)
- `BUG-` = 페르소나 발견 결함
- `BL-` = REFACTORING-BACKLOG.md 등재 항목
- `T-` = Sprint 24 plan 작업

**연결 규칙**: 1 BUG → 1 SCN + 1 BL (필요 시) + 1 T (Sprint 24 작업).

---

## 사전 등재 (페르소나 dispatch 전, 정적 분석)

| SCN | BUG | BL | T | Severity | 페르소나 | 재현 명령 | trace | screenshot | Sprint 24 task |
|---|---|---|---|---|---|---|---|---|---|
| SCN-BL-005-01 | — | **BL-005** | T-N+1 (조건부) | (info) | static | `grep -nE 'self\.repo\.session\.(execute\|exec)' backend/src/memory/service.py` | — | — | BL-005 close 검토 |
| SCN-BL-006-01 | (TBD) | **BL-006** | T-N+1 | P0 | static | `grep -rnE 'from src\.embeddings\|embeddings\.create_chunk' backend/src/memory/` | — | — | pipeline_service 위임 + I-21 helper 분리 |
| SCN-BL-006-02 | (TBD) | BL-006 | T-N+1 | P0 | static | memory/service.py:550 lazy import EmbeddingRepository | — | — | 동일 |
| SCN-BL-006-03 | (TBD) | BL-006 | T-N+1 | P0 | static | memory/service.py:780 lazy import EmbeddingRepository | — | — | 동일 |
| SCN-BL-006-04 | (TBD) | BL-006 | T-N+1 (확인) | (info) | static | memory/repository.py:33 _apply_hnsw_session_params | — | — | I-21 헌법 patch or helper 분리 |

---

## Tier 1 보안/멀티테넌시 SCN- (Day 1 Sentinel 결과 2026-05-19T13:41~13:45Z)

| SCN | BUG | BL | T | Severity | 페르소나 | 재현 | 결과 | trace | screenshot | Sprint 24 task |
|---|---|---|---|---|---|---|---|---|---|---|
| SCN-T1-01 (Cross-tenant RAG) | — | — | — | (info — PASS) | Sentinel | `pytest tests/integration/test_workspace_idor_matrix.py::TestRagIDORMatrix -v` + 정적 pipeline_service.py:45 | ✅ PASS | — | — | — |
| SCN-T1-02 (Private RAG visibility) | — | — | — | (info — PASS) | Sentinel | 정적 pipeline_service.py:49-58 draft/private 분기 | ✅ PASS | — | — | — |
| SCN-T1-03 (Prompt injection) | — | — | T-3 [확인 필요] | (info — auth gate PASS) | Sentinel | `curl -X POST /rag/ask -d '{"query":"ignore...500자A"}'` → 401 | ✅ PASS (M conf — 인증된 본문 추가 검증 필요) | — | — | 인증된 prompt injection live test 추가 |
| SCN-T1-04 (WS IDOR 13ep) | — | — | — | (info — PASS) | Sentinel | `pytest tests/integration/test_workspace_idor_matrix.py test_workspace_idor_real_db.py -v` → 24/24 PASS | ✅ PASS | — | — | — |
| SCN-T1-05 (ProjectMember 차단) | — | — | — | (info — PASS) | Sentinel | pytest TestProjectsRealDBIDOR (3건) + test_rag_pipeline_admin_cannot_bypass | ✅ PASS | — | — | — |
| SCN-T1-06 (R2 presigned IDOR) | — | **BL-신규 후보** | T-3 [확인 필요] | (info — PASS M conf) | Sentinel | upload/router.py:31 require_member + r2.py:26 file_key=uploads/{uuid4}/{filename} | ✅ PASS (workspace_id prefix 미적용 — 방어 강화 권장) | — | — | file_key=workspaces/{ws_id}/uploads/{uuid4}/{filename} 으로 변경 검토 |
| SCN-T1-07 (Clerk JWT) | — | — | — | (info — PASS) | Sentinel | `curl -H "Authorization: Bearer fake_token" /api/v1/workspaces` → 401 | ✅ PASS | — | — | — |
| SCN-T1-08 (CSRF/RateLimit/Secret) | — | **BL-신규 후보** | T-3 [확인 필요] | (info — Rate L conf) | Sentinel | CORS OPTIONS evil.example → 400 "Disallowed CORS origin". `grep -rE "sk_test_\|sk_live_\|AIza" frontend/src backend/src` + FE HTML root → 0 매치. Rate limit 미측정 | ✅ PASS (CORS/Secret), [확인 필요] Rate limit | — | — | Rate limit middleware 부재 여부 + 도입 검토 |
| SCN-T1-09 (Sentry PII) | — | — | — | [Blocked: mock] | Sentinel | sentry.client.config.ts + main.py:41-50 `_scrub_pii_hook` (transcript/email/password/audio_url + user.email/ip_address) | 🟡 PASS (mock) | — | — | DSN 발급 시 live dashboard 검증 |
| SCN-T1-10 (EmbedChunk IDOR) | — | — | — | (info — PASS) | Sentinel | `curl /api/v1/openapi.json` paths → `embed`/`chunk` 매치 0건 | ✅ PASS | — | — | — |
| SCN-T1-11 (Personal WS 초대) | — | — | — | (info — PASS) | Sentinel | invite_service.py:60-61 PersonalWorkspaceProtected | ✅ PASS | — | — | — |
| SCN-T1-12 (Role 즉시 적용) | — | — | — | (info — PASS) | Sentinel | `grep "Cache\|@cached" auth/ workspaces/` → 0 매치. require_member DB 직접 조회 | ✅ PASS | — | — | — |

---

## Composite FK regression SCN-FK-01~12 (Day 1 Sentinel Tier 2, 2026-05-19T22:57Z)

| SCN | Entity | 매핑 test | 결과 | trace | screenshot |
|---|---|---|---|---|---|
| SCN-FK-01 | MeetingProjectLink (insert) | test_meeting_project_links_workspace_match | ✅ PASS | pytest stdout | — |
| SCN-FK-02 | MeetingProjectLink (update) | (transitive) | ✅ PASS | — | — |
| SCN-FK-03 | MeetingProjectLink (query) | orphan SELECT | ✅ PASS | — | — |
| SCN-FK-04 | InboxItem (insert) | test_inbox_suggested_project_workspace_match | ✅ PASS | pytest stdout | — |
| SCN-FK-05 | InboxItem (update) | (transitive) | ✅ PASS | — | — |
| SCN-FK-06 | InboxItem (query) | orphan SELECT | ✅ PASS | — | — |
| SCN-FK-07 | ActionItem (insert) | test_action_items_project_workspace_match + meeting_workspace_match | ✅ PASS | pytest stdout | — |
| SCN-FK-08 | ActionItem (update) | (transitive) | ✅ PASS | — | — |
| SCN-FK-09 | ActionItem (query) | orphan SELECT | ✅ PASS | — | — |
| SCN-FK-10 | EmbeddingChunk (insert) | test_embedding_chunks_project_workspace_match | ✅ PASS | pytest stdout | — |
| SCN-FK-11 | EmbeddingChunk (update) | (transitive) | ✅ PASS | — | — |
| SCN-FK-12 | EmbeddingChunk (query) | orphan SELECT | ✅ PASS | — | — |

**보너스** (12 SCN 범위 밖, PASS 확인): Note, ProjectMember, SemanticCache.
**판정**: 12/12 PASS. Sprint 21 BL-050 Simple 4 composite FK 강화는 회귀 0건. T-N+2 (fixture 자동화) 잔여.

---

## Sprint 23 D1~D4 SCN-D1~D4 (Day 1 Sentinel Tier 2, 2026-05-19T23:00Z, 정적 분석)

| SCN | BUG | BL | T | Severity | 페르소나 | 재현 | 결과 | Evidence |
|---|---|---|---|---|---|---|---|---|
| SCN-D1 (WorkspaceSwitcher) | — | — | — | (info — PASS) | Sentinel | 정적 `frontend/src/features/workspaces/components/WorkspaceSwitcher.tsx` | ✅ PASS | L41-64 predicate-based invalidateQueries(workspaces.list 보존) + router.refresh() 제거 |
| SCN-D2 (Settings Compact deep-link) | — | — | — | (info — PASS) | Sentinel | 정적 `frontend/src/app/(app)/settings/page.tsx` | ✅ PASS | L7 useSearchParams import + L68/76 tabParam = searchParams.get("tab") + L131 "?tab=* deep-link" + Codex 2.5차 P1 Suspense fix |
| SCN-D3 (Inbox dismiss) | — | — | — | (info — PASS) | Sentinel | 정적 `frontend/src/features/inbox/api.ts` + `hooks.ts` | ✅ PASS | api.ts L10-14 inboxKeys: byWorkspace + list (queryKey isolation), hooks.ts L54/80 invalidateQueries(byWorkspace prefix), smart-inbox.tsx L47 isProcessed:false |
| SCN-D4 (ItemPromoteModal 5 도메인) | — | — | — | (info — PASS) | Sentinel | 정적 `frontend/src/components/shared/ItemPromoteModal.tsx` + BE 5 promote endpoint | ✅ PASS | BE: inbox/router.py:60 + memory/router.py:126 + notes/router.py:136 + actions/router.py:84 + meetings/router.py:126. FE: 5 callsite + inbox/CONTEXT.md IB-8 (헌법 I-18 promote=복제+tombstone + ItemPromotionAudit) |

---

## Curious (TTFV + 경쟁사) — Day 2 2026-05-19 23:08~23:17 KST

| SCN | BUG | Severity | 재현 | 결과 |
|---|---|---|---|---|
| SCN-CUR-FIRST-5 | (T-LAND-01 후보) | High UX | Playwright 5초 stopwatch + landing snapshot | ❌ **FAIL** (단일 viewport, 사회적 증거 0) |
| SCN-CUR-FIRST-30 | (T-LAND-02 후보) | High UX | Playwright 30초 stopwatch + scroll | ❌ **FAIL** (Features/Pricing 섹션 0) |
| SCN-CUR-FIRST-60 | — | Medium | 1분 자기보고 | 🟡 Maybe (한국어 UI 호기심) |
| SCN-CUR-TTFV-01 (Kairos) | — | (info) | epoch ms stopwatch | **255.5초** (가입 128.7s + nav 43.8s + AI 83.1s) |
| SCN-CUR-TTFV-02 (Granola) | — | (info) | macOS native 측정 불가 | n/a (landing 5초/30초 PASS) |
| SCN-CUR-TTFV-03 (Notion AI) | — | (info) | 기존 계정 가정 | n/a (landing PASS) |
| SCN-CUR-FRICTION | (T-LAND-03 후보) | Medium | observation | **6/10** (ToS/Privacy 부재 -2, Korean/English mix -1) |
| SCN-CUR-VALUE-AI | **BUG-CURIOUS-001 (P0 Critical)** | **P0 Critical** | AI 요약/액션 review | ❌ 액션 마감일 2024년 hallucinate |
| SCN-CUR-VALUE-RAG | **BUG-CURIOUS-002 (P1 High)** | **P1 High** | dashboard 추천 질문 click | ❌ Dead-click (⌘K만 동작) |
| SCN-CUR-VALUE-ONB | **BUG-CURIOUS-003 (P0 High)** | **P0 High** | 신규 가입 → dashboard 도달 | ❌ Onboarding step 1~4 미발화 (Sprint 22 OBN 회귀) |
| SCN-CUR-DECISION | — | (info) | self-report | **Kairos Maybe→No / Granola Yes** |

---

## Casual (과업 성공률 + a11y) — Day 2 2026-05-19 23:40~23:52 KST

| SCN | BUG | Severity | 재현 | 결과 |
|---|---|---|---|---|
| SCN-CAS-TASK-A (회의 업로드→AI 요약) | — | (info) | stopwatch | ✅ **PASS** 40초 |
| SCN-CAS-TASK-B (Inbox promote) | **BUG-CASUAL-002 + 003** | Medium UX | stopwatch | ❌ **FAIL** (Inbox 빈 상태 안내 vs 빠른 메모 mismatch + promote vocabulary 3종 혼란) |
| SCN-CAS-TASK-C (RAG 질문) | — | (info) | stopwatch | ✅ **PASS** 63초 |
| SCN-CAS-VOCAB (용어 해독률) | (T-VOCAB 후보) | Medium UX | observation | 🟡 **33-60%** (promote/Compact mode/Memory 혼란) |
| SCN-CAS-STUCK (막힘 지점 count) | — | (info) | observation | 🟡 **7건 / 5건 미해결** (포기) |
| SCN-CAS-A11Y-1 (axe /) | (BUG-CASUAL a11y 5건 묶음) | Serious | axe inject | 🟡 color-contrast 다수 |
| SCN-CAS-A11Y-2 (axe /dashboard) | 동일 | Serious | axe inject | 🟡 color-contrast |
| SCN-CAS-A11Y-3 (axe /inbox) | 동일 | Serious | axe inject | 🟡 color-contrast |
| SCN-CAS-A11Y-4 (axe /projects/[id]) | 동일 | Serious | axe inject | 🟡 color-contrast |
| SCN-CAS-A11Y-5 (axe /meetings/[id]) | 동일 | Serious + Moderate | axe inject | 🟡 color-contrast + heading-order |
| SCN-CAS-KBD (Tab/Skip/focus) | **BUG-CASUAL-006** | Medium a11y | keyboard nav | ❌ Skip link 부재 (WCAG 2.4.1) |
| SCN-CAS-MOBILE-NAV (BottomNav 44pt 1회) | **BUG-CASUAL-005** | Medium a11y | resize 375x667 | ❌ **5중 4개 미달** (홈 36/추가 40/Inbox 41/메모 36 px) |
| SCN-CAS-XVER-001 (BUG-CURIOUS-001 cross) | (진단 도출) | (info) | 회의 연도 명시 vs 미명시 | ✅ **연도 명시 시 정확** → fix prompt 컨텍스트 |
| SCN-CAS-XVER-002 (BUG-CURIOUS-002 cross) | — | (info) | 추천 질문 click | ✅ **100% 재현 확정** |

---

## Power (60-90분 발견성) — Day 3 2026-05-20 00:08~00:18 KST (10분)

| SCN | BUG | Severity | 결과 | Evidence |
|---|---|---|---|---|
| SCN-POW-SHORTCUT | BUG-POW-001 | P2 Medium UX | ❌ FAIL (2/10) | cmd-k.tsx:40-54 Cmd+K/Esc 만 / `g i` 시퀀스 미구현 / `?` help 모달 0 |
| SCN-POW-BULK | BUG-POW-002 | P2 Medium UX | ❌ FAIL (0/10) | Inbox/Memory/Notes multi-select 0 + BE bulk endpoint 0 |
| SCN-POW-EXPORT | BUG-POW-003 P1 + 004 P2 | P1+P2 | 🟡 PARTIAL (3/10) | Meeting/Note md+json만. NoteDetail (`/notes/[id]`) 폴더 부재 → NoteExportButton 100% 도달 불가. PDF/Notion/zip 0 |
| SCN-POW-RAG-ADV | **BUG-POW-005 P0** + 006 P1 | **P0 Critical + P1** | ❌ FAIL (3/10) | search-scope.tsx:31-37 MOCK_SELECTABLE_SOURCES 가짜 5건 + embeddings/repository.py time_range SQL 절 미사용 (dead param) |
| SCN-POW-API-DOCS | BUG-POW-007 | P2 Medium | 🟡 PARTIAL (6/10) | `/api/v1/docs` Swagger 200 + `/redoc` 200 + 47 paths OpenAPI 3.1.0. FE 진입점 0 + PAT 발급 흐름 0 |
| SCN-POW-AUDIT | **BUG-POW-008 P1** | P1 (compliance) | ❌ FAIL (1/10) | Sprint 23 D4 ItemPromotionAudit write 5 도메인 ✅ / read endpoint 0 / Settings 3 탭 audit 0 |

**Power 평균 발견성 점수**: 2.5/10 (Power 적대적). Cross-persona insight 5건 cross-link.

---

## Mobile (80% 핵심 + 20% viewport) — Day 3 2026-05-20 00:20~01:22 KST (62분)

| SCN | BUG | Severity | 결과 | Evidence |
|---|---|---|---|---|
| SCN-MOB-RECORD-01 (한 손 녹음 시작) | BL-MOB-001 + BL-MOB-003 | 🟡 PASS with caveats | 녹음+업로드 동작 ✅ / 녹음 버튼 y=759 (viewport 667 밖) 스크롤 강요 / 권한 거부 fallback 미검증 | screenshots/SCN-MOB-RECORD-01-* |
| SCN-MOB-RECORD-02 (BG 업로드 지속) | — | ✅ PASS | 탭 전환 5s + reload 모두 polling 정상 | screenshots/SCN-MOB-RECORD-02-* |
| SCN-MOB-NAV | BUG-CASUAL-005 confirmed | ❌ FAIL (100% 재현, 3 viewport 일관) | 홈 36w / 추가 40w / Inbox 41w / 메모 36w (4/5 width < 44pt, 세로 PASS) | screenshots/SCN-MOB-NAV-375x667-bottomnav.png |
| SCN-MOB-INBOX-NOTIF | **BUG-MOBILE-004 P2** | ❌ FAIL | BottomNav badge 0 + sonner toast 0 (다른 페이지에서 신규 Inbox 인지 불가) | screenshots/SCN-MOB-INBOX-NOTIF-list.png |
| SCN-MOB-3G | **BUG-MOBILE-005 P1 Performance** | ❌ FAIL (baseline 3-4s) | localhost BE API 3015-3865ms (workspaces/members/meetings/inbox 모두) → 3G 7-10s 예상 cancel 임계 | (측정표 본 보고서) |
| SCN-MOB-VIEWPORT-01/02/03 | **BUG-MOBILE-001 P0 High UX** | ❌ FAIL (3 viewport 일관) | U 프로필 버튼 (36x36) x_right=427 / viewport 밖 52/34/15px / 잘리는 ancestor `main.flex-1 overflow-hidden` | screenshots/SCN-MOB-VIEWPORT-02-393x852.png + 03-412x892.png + NAV-375x667 |

---

## Tier 2 기능 엣지 SCN-D-*  (Day 1 Sentinel Tier 2, 2026-05-19T23:10Z)

| SCN | 영역 | 시나리오 | 결과 | BL 후보 | Evidence |
|---|---|---|---|---|---|
| SCN-D-1-1 | upload | 0 byte audio 차단 | 🟡 BL 후보 | BL-T2-001 | upload/router.py:18-24 size 필드 부재 |
| SCN-D-1-2 | upload | audio MIME 화이트리스트 | 🟡 BL 후보 | BL-T2-002 | content_type=octet-stream default + whitelist 0 |
| SCN-D-1-3 | meetings | 4hr+ audio chunk 분할 | 🟡 BL 후보 | BL-T2-003 | transcription.py whisper-1 직접 호출, chunk 0건 |
| SCN-D-1-4 | meetings | 빈 transcript guard | 🟡 BL 후보 | BL-T2-004 | pipeline_service.py L214 early-return 부재 |
| SCN-D-1-5 | i18n | 한국어/이모지 처리 | ✅ PASS | — | common/prompts.py:69+L117 한국어 명시 |
| SCN-D-1-6 | meetings | AI 구조화 fallback | ✅ PASS | — | pipeline_service.py L236-303 try/except status='failed' |
| SCN-D-1-7 | inbox | autoProcessed=false 분기 | ✅ PASS | — | pipeline_service.py L120 + inbox/service.py L60-106 |
| SCN-D-2-1 | meetings | 202 polling endpoint | ✅ PASS | — | router.py L114 GET /status |
| SCN-D-2-2 | upload | 중복 파일 hash | 🟡 알려진 한계 | (CONTEXT.md L132) | meetings/CONTEXT.md "R2 hash 비교 미구현" 명시 |
| SCN-D-2-3 | meetings | BG task session 독립 | ✅ PASS | — | pipeline_service.py L38-43+L177 session_factory 패턴 |
| SCN-D-2-4 | meetings | polling timeout | ✅ PASS | — | session_factory 독립 + R7 D1 race fix |
| SCN-D-3-1 | sentry | source map (Vercel) | ✅ PASS | — | next.config.ts L8 withSentryConfig |
| SCN-D-3-2 | sentry | rate limit | ✅ PASS | — | tracesSampleRate:0.1 |
| SCN-D-3-3 | sentry | breadcrumb | ✅ PASS | — | @sentry/nextjs 자동 + instrumentation.ts onRequestError |
| SCN-D-4-1 | onboarding | lazy personal seed | ✅ PASS | — | auth/dependencies.py L79+L99+L129 |
| SCN-D-4-2 | onboarding | TTFV step progression | ✅ PASS | — | onboarding/service.py L41-47 step/totalSteps=4 |
| SCN-D-4-3 | onboarding | EmptyState 9 callsite | ✅ PASS | — | components/empty-state.tsx 9 import |
| SCN-D-4-4 | onboarding | step idempotency | ✅ PASS | — | repository.py L19-27 WHERE onboarding_step < :target |
| SCN-D-4-5 | onboarding | step 조회 API | ✅ PASS | — | OnboardingResponse schema 정의됨 |
| SCN-D-5-1 | input | max_length 일관성 | 🟡 BL 후보 | BL-T2-006 | meetings/projects/notes title 무제한 |
| SCN-D-5-2 | input | whitespace trim | ✅ PASS | — | embeddings/memory/auth/rag service strip() |
| SCN-D-5-3 | i18n | Unicode | ✅ PASS | — | D-1-5 동일 |
| SCN-D-5-4 | security | SQL injection | ✅ PASS | — | Pydantic UUID + text() 바인딩 파라미터 |
| SCN-D-5-5 | security | CSP header | 🟡 BL 후보 | BL-T2-007 | main.py middleware 0 |
| SCN-D-5-6 | security | X-Frame-Options | 🟡 BL 후보 | BL-T2-007 | 0 매치 |
| SCN-D-5-7 | security | HSTS | 🟡 BL 후보 | BL-T2-007 | 0 매치 |
| SCN-D-5-8 | security | Referrer-Policy | 🟡 BL 후보 | BL-T2-007 | 0 매치 |

---

## BUG 등재 (페르소나 발견 후 채움) — Day 2 Curious + Casual 갱신

### Day 2 Curious (3건)
| BUG ID | Severity | 영역 | 페르소나 | 재현 | Root cause 추정 | T 후보 |
|---|---|---|---|---|---|---|
| **BUG-CURIOUS-001** | **P0 Critical** | AI prompt | Curious | 회의 본문 "7월 X일" (연도 없음) → AI 액션 추출 시 마감일 2024-07-25/22/12 생성 (현재 2026년 5월) | LLM prompt에 현재 연도 컨텍스트 부재 + 시간 추론 안전망 부재. **Casual 진단**: 연도 명시 input → 2026년 정확 | T-AI-DATE (P0) |
| **BUG-CURIOUS-002** | **P1 High** | dashboard UX | Curious + Casual | 추천 질문 "최근 회의에서 결정된 사항은?" 직접 클릭 → button active 표시만 (응답 없음). ⌘K command palette 사용 시 정상. **Casual 100% 재현 확정** | onClick handler가 ⌘K 흐름과 분기 안 됨 (Sprint 23 D2 회귀 가능성) | T-CMD-K-FIX (P1) |
| **BUG-CURIOUS-003** | **P0 High** | onboarding UX | Curious | 신규 가입자 dashboard 도달 후 onboarding step 1~4 UI 발화 0 | Sprint 22 OBN-01~04 BE hook은 있으나 FE UI render 미연동 (Casual은 reuse 계정이라 검증 skip) | T-OBN-05 (P0) |

### Day 2 Casual 단독 발견 (6건)
| BUG ID | Severity | 영역 | 페르소나 | 재현 | Root cause | T 후보 |
|---|---|---|---|---|---|---|
| **BUG-CASUAL-001** | **P1 High** | FE routing | Casual | sidebar / dashboard "프로젝트" 클릭 → `/projects` 404. BE `/api/v1/projects` 존재. | FE `frontend/src/app/(app)/projects/page.tsx` 미구현 (list page) | T-PROJ-LIST (P1) |
| BUG-CASUAL-002 | Medium UX | inbox copy | Casual | Inbox empty state "노트 추가하면 자동 분류" → 빠른 메모 입력 후 Inbox 미적재 | empty state copy / actual flow mismatch | T-INBOX-COPY (P2) |
| BUG-CASUAL-003 | Medium UX | vocabulary | Casual | promote 같은 동작에 3종 카피 ("워크스페이스 이동" / "팀으로 올리기" / "보낼까요") | 단일 동사 통일 안 됨 | T-VOCAB-UNIFY (P2) |
| BUG-CASUAL-004 | Low UX | cmd-k | Casual | ⌘K AI 검색 모드 전환 시 query "?"로 리셋 | 모드 전환 시 state 보존 미구현 | T-CMD-K-STATE (P3) |
| BUG-CASUAL-005 | Medium a11y (WCAG 2.5.5) | mobile | Casual | BottomNav 5중 4개 < 44pt (홈 36 / 추가 40 / Inbox 41 / 메모 36) | mobile-first 검증 부재 | T-MOBILE-NAV (P2) |
| BUG-CASUAL-006 | Medium a11y (WCAG 2.4.1) | keyboard | Casual | Skip link 부재 → sidebar 7항목 + header 3 통과 후 main 도달 | `<a href="#main">` skip link 미구현 | T-A11Y-SKIP (P2) |

### Day 2 종합 BUG (Curious + Casual)
- P0 Critical: 1 (BUG-CURIOUS-001)
- P0 High: 1 (BUG-CURIOUS-003)
- P1 High: 2 (BUG-CURIOUS-002, BUG-CASUAL-001)
- Medium: 4 (BUG-CASUAL-002/003/005/006)
- Low: 1 (BUG-CASUAL-004)

### Day 3 Power 단독 발견 (8건)
| BUG ID | Severity | 영역 | 페르소나 | 재현 | T 후보 |
|---|---|---|---|---|---|
| **BUG-POW-005** | **P0 Critical** | RAG MOCK 누출 | Power | `/search` "선택한 소스" → 가짜 5건 ("Sprint 3 회고" 등) 노출 | T-RAG-MOCK-REMOVE (1h) |
| **BUG-POW-003** | **P1 High** | NoteDetail 부재 | Power | `/notes/[id]` 폴더 부재 → NoteExportButton 100% 도달 불가 | T-NOTE-DETAIL (3h) |
| **BUG-POW-006** | **P1 High** | RAG time_range dead | Power | FE 4 옵션 vs BE 결과 무변동 (SQL 미사용) | T-RAG-TIME-FILTER (2h) |
| **BUG-POW-008** | **P1 High (compliance)** | Audit read | Power | Sprint 23 D4 write 5도메인 / read 0 + Settings 0 | T-AUDIT-VIEW (4h) |
| BUG-POW-001 | P2 Medium | 단축키 가짜 표시 | Power | ⌘K 모달 G I/G P/G N/G S/C 표시 / 핸들러 부재 | T-CMD-K-SEQ (3h, CASUAL-004 통합) |
| BUG-POW-002 | P2 Medium | Inbox 벌크 | Power | multi-select / bulk action 0 | T-INBOX-BULK (4h) |
| BUG-POW-007 | P2 Medium | API docs FE 진입점 + PAT | Power | `/api/v1/docs` 200 / FE 0 / PAT 0 | T-API-PAT (6h) |
| BUG-POW-004 | P2 Low | bulk export | Power | workspace zip export 부재 | T-EXPORT-ZIP (4h) |

### Cross-persona insight (Power가 정리)
1. **MOCK 누출 카테고리**: BUG-POW-005 + BUG-CURIOUS-001 → "AI 거짓말" 인식
2. **FE 미구현 dead-end**: BUG-POW-003 + BUG-CASUAL-001 → Sprint 24 missing-FE-detail bundle
3. **UI 가짜 약속**: BUG-POW-001 + BUG-CASUAL-003 → 신뢰 손상
4. **⌘K 통합 fix**: BUG-POW-001 + BUG-CASUAL-004 동시 해결 (~3h)
5. **Sprint 23 D4 가짜 완료**: ItemPromotionAudit write only → Power 발견성 0

### Day 3 Mobile 단독 발견 (3 BUG + 3 BL)

| BUG ID | Severity | 영역 | 페르소나 | 재현 | T 후보 |
|---|---|---|---|---|---|
| **BUG-MOBILE-001** | **P0 High UX** | 헤더 잘림 | Mobile | 375/393/412 viewport 모두 — U 프로필 버튼 (36x36) x_right=427 / viewport 밖 52/34/15px → 로그아웃/프로필 도달 불가 | T-MOBILE-HEADER (0.5-1h) |
| **BUG-MOBILE-005** | **P1 High Performance** | BE 첫 진입 latency | Mobile | localhost BE API workspaces/members/meetings/inbox 모두 3015-3865ms / 캐시 후 190-350ms | T-BE-PERF (spike 4-6h) |
| BUG-MOBILE-004 | P2 Medium UX | 알림 부재 | Mobile | 새 회의 업로드 후 a[href="/inbox"] 자식 0개 (badge/dot/count 없음) + sonner toast 0 | T-NAV-BADGE (1h) |
| BL-MOB-001 | BL | 녹음 버튼 스크롤 강요 | Mobile | `/new` 직접 녹음 진입 시 녹음 버튼 y=759 (viewport 667 밖) — scrollHeight=929, 317px 스크롤 후 도달 | BL 등재 |
| BL-MOB-002 | BL | 추천 질문 42pt | Mobile | dashboard 추천 질문 4 버튼 h=42 (WCAG 2.5.5 미달) — BUG-CURIOUS-002 dead-click 영역 동일 | T-CMD-K-FIX 동시 |
| BL-MOB-003 | BL | 권한 거부 fallback 미검증 | Mobile | Chromium MCP 환경 자동 grant. 실 기기 거부 환경 dogfood 필요 | BL 등재 |

### Cross-verify
- **BUG-CASUAL-005**: ✅ 100% 재현 + 3 viewport 일관. 가로 padding 만 fix (T-MOBILE-NAV 0.5h 적절)
- **Sprint 22 OBN-04 BottomNav collision fix**: ✅ 겹침 없음 (5 항목 균등)

### Day 1+2+3 (Sentinel + Curious + Casual + Power + Mobile) 종합 BUG
- **P0 Critical**: 2 (CURIOUS-001 AI date hallucinate + POW-005 RAG MOCK) ⚠️
- **P0 High**: 2 (CURIOUS-003 Onboarding + **MOBILE-001 헤더 잘림**) ⚠️ +1 Mobile
- **P1 High**: 6 (CURIOUS-002 + CASUAL-001 + POW-003/006/008 + **MOBILE-005 BE perf**) ⚠️ +1 Mobile
- **P2 Medium**: 9 (CASUAL-002/003/005/006 + POW-001/002/007 + **MOBILE-004** + a11y) +1 Mobile
- **P2 Low**: 2 (CASUAL-004 + POW-004)
- **Sentinel BL** (P2~P3): 7건 (BL-T2-001~007) + 헌법 BL-006 P0
- **Mobile BL**: 3건 (BL-MOB-001/002/003)

> **Sentinel 정적분석 0 BUG → Day 2+3 dogfood 20 BUG** = multi-agent QA가 정적분석으로 잡지 못하는 결함의 가치 명확.

---

## BL 신규 등재 (Tier 2 Sentinel 발견 6 신규 + 1 알려진 한계)

| BL 임시 ID | 영역 | 영향 | Severity | T 후보 |
|---|---|---|---|---|
| BL-T2-001 | upload 0 byte 차단 | Low | Low | T-N+3 |
| BL-T2-002 | audio MIME whitelist | Medium | Medium | T-N+3 |
| BL-T2-003 | Whisper chunk 분할 (4hr+) | High | High | T-N+4 (production 필수) |
| BL-T2-004 | 빈 transcript guard | Medium | Medium | T-N+3 |
| BL-T2-005 | onboarding router test env fixture | Low | Low | T-N+5 (테스트 cleanup) |
| BL-T2-006 | input max_length 일관성 | Medium | Medium | T-N+3 |
| BL-T2-007 | CSP/X-Frame/HSTS/Referrer-Policy middleware | Medium | Medium (Clickjacking 노출) | T-N+3 |

**알려진 한계** (CONTEXT.md 명시): D-2-2 R2 hash 비교 (중복 파일 검출) — backlog 등재 별도 불필요.

---

## Sprint 24 task T-N (sprint-24-plan.md 작성 시 채움)

| T | 제목 | 의존 | BUG/BL | 시간 | 우선 |
|---|---|---|---|---|---|
| ~~T-1~~ | ~~ADR-019 Phase B Gemini 6 spot swap~~ — **closed `003908a` 2026-05-15 PR #32** | — | — | ~~3h~~ ✅ | — |
| **T-2** | Post-Swap Delta 측정 (5 시나리오) | T-1 ✅ closed | — | 2h | P0 |
| ~~Wave 1~~ | ~~BL-063 ActionItem 자동 복제 + BL-064 Note BG schedule + BL-066 dogfood verify~~ — **closed `b1c777b` 2026-05-20 PR #99** | — | BL-063/064/066 | ✅ | — |
| **T-AI-DATE** | AI 액션 마감일 hallucinate fix (prompt 현재 연도 컨텍스트) | — | BUG-CURIOUS-001 | 1.5h | **P0 Critical** |
| **T-RAG-MOCK-REMOVE** | RAG MOCK_SELECTABLE_SOURCES 제거 (search-scope.tsx:31) | — | BUG-POW-005 | 1h | **P0 Critical** |
| **T-OBN-05** | Onboarding step 1~4 FE 발화 fix | — | BUG-CURIOUS-003 | 2h | **P0 High** |
| **T-CMD-K-FIX** | Dashboard 추천 질문 dead-click fix | — | BUG-CURIOUS-002 | 1h | P1 High |
| **T-PROJ-LIST** | `/projects` FE list page 신설 (sidebar dead-end fix) | — | BUG-CASUAL-001 | 2h | **P1 High** |
| **T-NOTE-DETAIL** | NoteDetail (`/notes/[id]`) 페이지 구현 | — | BUG-POW-003 | 3h | **P1 High** |
| **T-RAG-TIME-FILTER** | RAG time_range SQL clause 추가 | — | BUG-POW-006 | 2h | P1 High |
| **T-AUDIT-VIEW** | ItemPromotionAudit read endpoint + Settings audit 탭 | — | BUG-POW-008 | 4h | P1 (compliance) |
| **T-CMD-K-SEQ** | ⌘K 시퀀스 단축키 (G I/G P 등) + `?` help (POW-001 + CASUAL-004 통합) | — | BUG-POW-001 + BUG-CASUAL-004 | 3h | P2 |
| **T-MOBILE-HEADER** | 모바일 헤더 우측 잘림 fix (header padding lg:pl-X md:pl-0) | — | BUG-MOBILE-001 | 0.5-1h | **P0 High UX** |
| **T-BE-PERF** | dashboard 첫 진입 BE API 3-4s spike (Clerk JWT verify + DB lookup 직렬 의심) | — | BUG-MOBILE-005 | 4-6h | **P1 Performance** |
| **T-NAV-BADGE** | BottomNav Inbox 미확인 항목 badge (inboxKeys.byWorkspace subscribe) | — | BUG-MOBILE-004 | 1h | P2 |
| **T-LAND-01** | Landing 5초 룰 PASS — wedge headline + RAG demo | — | (Curious gemini F2) | 4h | P1 (마케팅 sprint) |
| **T-LAND-02** | Landing 30초 룰 PASS — use case + Pricing + Privacy/ToS | — | (Curious) | 3h | P2 (마케팅) |
| **T-VOCAB-UNIFY** | promote 카피 통일 (3종 → 1종) | — | BUG-CASUAL-003 | 0.5h | P2 |
| **T-MOBILE-NAV** | BottomNav 44pt 확보 | — | BUG-CASUAL-005 | 0.5h | P2 |
| **T-A11Y-SKIP** | Skip link 추가 | — | BUG-CASUAL-006 | 0.5h | P2 |
| **T-A11Y-CC** | color-contrast 5 페이지 (axe serious 5건) | — | BUG-CASUAL-a11y | 2h | P2 |
| T-INBOX-COPY | Inbox empty state 빠른 메모 mismatch | — | BUG-CASUAL-002 | 1h | P2 |
| T-CMD-K-STATE | ⌘K 모드 전환 state 보존 | — | BUG-CASUAL-004 | 0.5h | P3 |
| **T-N+1** | BL-006 cross-domain import 해소 | T-1 closed (carry 해제) | BL-006 + SCN-BL-006-01~04 | 3h | P0 |
| **T-N+2** | composite FK regression fixture 자동화 | — | SCN-FK-01~12 | 2h | P1 |
| T-N+3 | BL-T2-001/002/004/006/007 묶음 (input + security headers) | — | BL-T2 5건 | 4h | P2 |
| **T-N+4** | BL-T2-003 Whisper 4hr+ chunk 분할 | — | BL-T2-003 | 4h | **High (production)** |
| T-N+5 | BL-T2-005 onboarding router test fixture | — | BL-T2-005 | 0.5h | P3 |

**우선 순서 (실제 Sprint 24 진입)** — Day 3 Mobile 결과 반영 FINAL:

| 단계 | 작업 | 시간 | 누적 | 비고 |
|---|---|---|---|---|
| 0 (closed) | ~~T-1 Phase B swap (003908a)~~ + ~~BL-063/064/066 Wave 1 (PR #99)~~ | — | 0h | Pre-Sprint Closure ✅ |
| 1 | T-2 Phase B Post-Swap Delta | 2h | 2h | 2026-05-28 데드라인 (swap 충족) |
| 2 | T-AI-DATE + T-RAG-MOCK-REMOVE (**P0 Critical bundle**) | 2.5h | 4.5h | 신뢰 회복 |
| 3 | T-OBN-05 + **T-MOBILE-HEADER** (P0 High UX bundle) | 2.5-3h | 7.5h | Sprint 22 회귀 + 모바일 헤더 잘림 |
| 4 | T-PROJ-LIST + T-NOTE-DETAIL (P1 High FE missing pages bundle) | 5h | 12.5h | sidebar dead-end |
| 5 | T-CMD-K-FIX (P1 High Dashboard, BL-MOB-002 동시 fix) | 1h | 13.5h | UX 신뢰 |
| 6 | T-RAG-TIME-FILTER + T-AUDIT-VIEW (P1 High compliance) | 6h | 19.5h | RAG/compliance |
| 7 | **T-BE-PERF** (P1 Performance spike, dashboard 3-4s) | 4-6h | 24.5h | 모바일 사용성 직결 |
| 8 | T-N+1 (BL-006 헌법 §4.2 위반) | 3h | 27.5h | atomic |
| 9 | T-N+4 (BL-T2-003 Whisper 4hr+ production 차단) | 4h | 31.5h | production |
| 10 | T-N+2 (composite FK fixture) | 2h | 33.5h | 회귀 안전망 |
| 11 | P2 묶음 (T-VOCAB/MOBILE-NAV/A11Y-SKIP/A11Y-CC/CMD-K-SEQ/INBOX-COPY/NAV-BADGE) | 6.5h | 40h | UX/a11y |
| (carry) | T-INBOX-BULK + T-API-PAT + T-EXPORT-ZIP + BL-T2-001/002/004/006/007 + T-LAND-01/02 | ~25h | — | Sprint 25 |

**총 Wave 2 P0+P1 = 24.5h** (T-1 3h closed 제외) / 8일 가용 (~32-64h working) = 충분. P2/P3는 Sprint 25 carry.
**Mobile 추가 부담**: T-MOBILE-HEADER 0.5-1h (P0) + T-BE-PERF 4-6h (P1 spike) = +5-7h. 일정 재정렬 시 T-BE-PERF carry 옵션도 가능.

---
