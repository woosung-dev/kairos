<!-- Sprint 14 작업 계획 — Multi-Agent QA(2026-05-13) 결과 기반 -->

# Sprint 14 — 가입 첫 5분 신뢰 회복 + RAG 안정화

> 입력: `docs/dev-log/qa/2026-05-13-multi-agent-qa/integrated-report.html`
> 기준 Sprint: 13 직후 (BL-003/004 완료, PR #21 머지)
> 작성: 2026-05-13

---

## 1. 목표 (1줄)

**가입 첫 5분의 신뢰 침식 제거 + RAG 안정화** — 외부 시각(Sentinel/Curious/Casual) 종합 결과, "도입 가능한 베타"로 진입하기 위한 신뢰 회복 Sprint.

---

## 2. 범위

### In Scope (11건)

| 분류 | 항목 | 출처 |
|------|------|------|
| P0 (Critical) | BUG-C01 RAG 5xx graceful degrade | Sentinel |
| P0 | "오늘 할 일" 사이드바 메뉴 404 즉시 숨김 | Curious + Casual |
| P0 | Clerk Production 키 + koKR localization | Curious |
| P0 | "RAG" → "AI 검색" 카피 일괄 치환 | Casual |
| P1 (High) | BUG-H03 헌법 I-16 위반 audit + alias | Sentinel |
| P1 | BUG-H02 visibility 모달 race condition | Sentinel + Casual |
| P1 | BUG-H01 dashboard stale ws + setState-in-render | Sentinel |
| P1 | BUG-H04 meeting detail `projects: []` 동기화 | Sentinel |
| P1 | 사이드바 vs 페이지 카운트 동기화 (Inbox 3 vs 12) | 3 페르소나 공통 |
| P1 (Mobile) | 모바일 햄버거 토글 무동작 → 모바일에서 숨김 | Casual |
| P1 (Mobile) | 모바일 BottomNav "빠른 메모" 진입점 추가 | Casual |

### Out of Scope (Sprint 15+ 또는 별도 트랙)

- **신규 가입자 onboarding tour** (Curious P2, Sprint 15 권고 — 빈 워크스페이스 첫 5분 가치 도달 경로 설계 필요)
- **가격/고객 로고/보안 페이지** (B2B 신뢰 신호 마케팅 트랙 — dev 단독 처리 불가)
- **vs Otter / vs Notion AI 비교표** (Marketing)
- **viewer/member RBAC + Private RAG 누설 multi-user E2E** (AD-35, Clerk testing mode 도입 후)
- **BUG-M01~M06 + L01~L02** (Sprint 15에서 polish — 본 Sprint는 신뢰 신호 + Critical/High에 집중)
- **검색 답변 인라인 [소스] 표기 정리** (P2, polish)
- **"2026-09-01 기준" 미래 날짜 [확인 필요]** — 시드 데이터인지 로직 버그인지 확인 후 결정

---

## 3. 작업 분해

### T-1 — BUG-C01 RAG 5xx graceful degrade (BE) ⚠️ P0

- **대상 파일**:
  - `backend/src/rag/service.py` — Gemini 호출 catch
  - `backend/src/rag/schemas.py` — `AskRequest.question` validation
  - `backend/src/rag/router.py` — SSE error event emit
- **변경 내용**:
  1. `AskRequest.question`: `Field(min_length=1, max_length=500)` + `field_validator`로 strip 후 ≥2자 검증
  2. `RagService.ask` 또는 `pipeline_service`에서 Gemini 예외 (`BlockedPromptError`, 빈 candidate, `google.genai.errors.*`) catch
  3. SSE error event 송출: `event: error\ndata: {"message":"질문을 처리할 수 없습니다. 다시 시도해주세요","retryAfter":3}\n\n`
  4. SemanticCache 오염 방지 — 5xx 발생 시 cache miss 처리, store 안 함
- **예상 시간**: 3시간
- **의존성**: 없음
- **테스트**:
  - `tests/test_rag_service.py` — Gemini SafetyFilter 거부 시 graceful response 단위 테스트 추가
  - whitespace-only / 10000자 입력 → 422 검증
  - max_length 정확 경계 (500/501자) 검증
- **검증**: Playwright MCP로 prompt-injection 류 입력 시 200 + 한국어 안내 + Sentry 5xx 0건

### T-2 — "오늘 할 일" 사이드바 메뉴 404 숨김 (FE) ⚠️ P0

- **대상 파일**: `frontend/src/components/layout/Sidebar.tsx` (또는 동등 파일 — grep `오늘 할 일`)
- **변경 내용**: 메뉴 항목 제거 또는 feature flag로 숨김. 기능 자체는 미구현 상태이므로 "준비 중" 페이지 신설 X.
- **예상 시간**: 30분
- **의존성**: 없음
- **테스트**: Playwright e2e — 사이드바에 "오늘 할 일" 텍스트 부재 확인
- **검증**: Curious + Casual 시나리오 재현 — 막힘 지점 #1 해소

### T-3 — Clerk Production 키 + koKR localization ⚠️ P0

- **대상 파일**:
  - `frontend/.env.local` + Vercel env (사용자 작업) — `pk_live_*` / `sk_live_*` 교체
  - `frontend/src/app/layout.tsx` 또는 `ClerkProvider` 래퍼 — `localization={koKR}` 적용
  - `frontend/src/app/(auth)/sign-in/page.tsx` + `(auth)/sign-up/page.tsx` — `appearance` props에 한국어 텍스트 override
- **변경 내용**:
  1. Production Clerk instance 생성 (사용자 작업) → publishable/secret 키 환경변수 갱신
  2. `@clerk/localizations` 패키지 설치 → `koKR` import → `<ClerkProvider localization={koKR}>` 적용
  3. 로그인 후 redirect를 `/dashboard`로 강제 (현재 랜딩 redirect 이슈 — Curious T+1초)
- **예상 시간**: 2시간 (코드 1시간 + 사용자 협업 1시간)
- **의존성**: 사용자 작업 (Clerk dashboard에서 Production 인스턴스 생성)
- **테스트**: Playwright e2e — sign-in 화면에 "Development mode" 배지 부재 + 한국어 위젯 확인
- **검증**: Curious 핵심 망설임 1번 해소 (Dev 배지 + 영어 위젯)

### T-4 — "RAG" → "AI 검색" 카피 일괄 치환 (FE + 시드) ⚠️ P0

- **대상 파일**:
  - `frontend/src/components/**` — grep `\bRAG\b` 일괄 치환 (a11y aria-label 포함)
  - `frontend/src/features/rag/**` — 컴포넌트명은 유지하되 사용자 노출 텍스트만 변경
  - `backend/src/projects/seed.py` 또는 동등 — 템플릿 프로젝트 시드 본문에서 "RAG" 제거 ("AI 검색"/"팀 지식 검색"으로)
  - `backend/src/notes/seed.py` — "RAG 성능 개선 아이디어" 노트 제목 변경
- **변경 내용**:
  1. `rg -n '\bRAG\b' frontend/src` 결과 매핑 — 사용자 노출 카피만 치환 (코드 식별자 변경 X)
  2. `backend/src/**/seed*.py` 동일 작업
  3. 가이드라인 추가: `frontend/src/features/rag/CONTEXT.md` 또는 ADR — "사용자 노출 카피에서 RAG 약어 사용 금지" 명시
- **예상 시간**: 2시간 (grep 매핑 1시간 + 일괄 치환 + 검증 1시간)
- **의존성**: T-2 와 동일 디렉터리 일부 — 직렬 작업 권고
- **테스트**: Playwright e2e — `/dashboard`, `/inbox`, `/projects/{id}` 페이지에 "RAG" 텍스트 0건 확인 (a11y aria-label 포함)
- **검증**: Casual 용어 해독률 37.5% → 50%+ 회복

### T-5 — BUG-H03 헌법 I-16 위반 audit + alias (BE) — P1

- **대상 파일**:
  - `backend/src/workspaces/schemas.py:72` — `UpdateWorkspaceSettingsRequest`
  - `backend/src/**/schemas.py` 전체 audit (grep)
- **변경 내용**:
  1. `UpdateWorkspaceSettingsRequest`에 `alias="inboxThreshold"` + `model_config = {"populate_by_name": True}`
  2. `find backend/src -name 'schemas.py' -exec grep -L 'populate_by_name' {} \;` 으로 누락 schema 일괄 식별
  3. 누락된 모든 RequestModel에 alias + populate_by_name 추가
  4. 추후 회귀 차단을 위해 `tests/test_schemas_alias.py` 신설 — 모든 Request* 클래스 introspection으로 `populate_by_name=True` 강제 검증
- **예상 시간**: 4시간 (audit 2시간 + 변경 + 테스트 2시간)
- **의존성**: 없음
- **테스트**: 신규 introspection 테스트 + 기존 테스트 회귀
- **검증**: curl PATCH `{"inboxThreshold":0.85}` → 200. schemathesis property test (V-T4) 도입은 별도 Sprint.

### T-6 — BUG-H02 visibility 모달 race condition fix (FE) — P1

- **대상 파일**:
  - `frontend/src/features/projects/hooks/useWorkspaceRole.ts`
  - `frontend/src/features/projects/components/VisibilityBadge.tsx`
  - `frontend/src/features/projects/components/project-detail.tsx:142`
  - 권한 분기 사용하는 다른 컴포넌트 audit (grep `useWorkspaceRole`)
- **변경 내용**:
  1. `useWorkspaceRole`이 `{role, isLoading, canManage}` 반환하도록 변경
  2. `VisibilityBadge` 클릭 핸들러: `onClick={() => canManage && setOpen(true)}` (closure 회피)
  3. isLoading 중에는 버튼 disabled + 스피너
  4. 다른 권한 분기 컴포넌트도 동일 패턴 적용
- **예상 시간**: 3시간
- **의존성**: 없음
- **테스트**: e2e — soft navigation 후 visibility 배지 클릭 시 모달 정상 열림
- **검증**: Sentinel BUG-H02 + Casual 모바일 dropdown 미노출 동시 해소

### T-7 — BUG-H01 dashboard stale ws + setState-in-render (FE) — P1

- **대상 파일**:
  - `frontend/src/app/(app)/dashboard/page.tsx:78-82`
  - `frontend/src/components/layout/Header.tsx` — `useMembers(wid)` 호출부
  - 로그아웃 핸들러
- **변경 내용**:
  1. `dashboard/page.tsx:78-82`의 `setActiveWorkspaceId(currentWid)` 직접 호출을 `useEffect`로 이동
  2. `Header`의 `useMembers(wid)`에 `enabled: !!wid && workspaces.includes(wid)` 가드 추가
  3. 로그아웃/워크스페이스 제거 시 `queryClient.removeQueries({ queryKey: ['workspace', oldId] })` 호출
- **예상 시간**: 2시간
- **의존성**: 없음
- **테스트**: e2e — 로그인 후 dashboard 진입 시 stale UUID 호출 0건 (Network 검증)
- **검증**: React 콘솔 setState-in-render 경고 0건

### T-8 — BUG-H04 meeting detail projects 동기화 (BE) — P1

- **대상 파일**:
  - `backend/src/meetings/service.py` — `get_detail`
  - `backend/src/meetings/repository.py` — link 조회 추가
  - `backend/src/meetings/schemas.py` — MeetingDetailResponse.projects 채우기
- **변경 내용**: `MeetingService.get_detail`에서 `MeetingProjectLink` join → `projects` 필드 채움. 또는 `projects` 필드를 응답에서 제거 (정책 결정 필요).
- **예상 시간**: 2시간
- **의존성**: 없음
- **테스트**: `tests/test_meeting_service.py` — link 후 detail에 `projects` 채워짐
- **검증**: curl `POST .../meetings/{mid}/projects` → `GET .../meetings/{mid}` `projects` 채워짐

### T-9 — 사이드바 vs 페이지 카운트 동기화 (FE) — P1

- **대상 파일**:
  - `frontend/src/components/layout/Sidebar.tsx` — Inbox/Archive badge
  - `frontend/src/features/inbox/hooks.ts` — count query
- **변경 내용**:
  1. badge 정의 lock-in: "사이드바 Inbox 카운트 = 미분류 InboxItem 수" (또는 사용자 결정)
  2. 사이드바 badge query와 페이지 query를 동일 source-of-truth로 통합
  3. 동일 query key 사용으로 React Query 캐시 일치
- **예상 시간**: 2시간
- **의존성**: 없음
- **테스트**: e2e — 사이드바 카운트 N == /inbox 페이지 미분류 N
- **검증**: Curious + Casual 막힘 해소 (Inbox 3 vs 12 모순)

### T-10 — 모바일 햄버거 토글 무동작 (모바일에서 숨김) (FE) — P1 Mobile

- **대상 파일**: `frontend/src/components/layout/Header.tsx` 또는 `MobileHeader.tsx`
- **변경 내용**: 모바일 viewport (md:hidden 또는 useMediaQuery)에서 햄버거 버튼 숨김. 모바일 1차 내비는 BottomNav로만.
- **예상 시간**: 1시간
- **의존성**: T-11 와 함께 작업 권고
- **테스트**: e2e — 375x667 viewport에서 햄버거 버튼 부재 확인
- **검증**: Casual 막힘 #7 (모바일 햄버거 누름 → 무동작) 해소

### T-11 — 모바일 BottomNav "빠른 메모" 진입점 추가 (FE) — P1 Mobile

- **대상 파일**:
  - `frontend/src/components/layout/BottomNav.tsx`
  - 빠른 메모 모달 컴포넌트 (모바일 전용 호출 패턴)
- **변경 내용**:
  1. BottomNav 5개 탭 중 "추가" 또는 "검색" 자리 재배치 — "빠른 메모" 진입점 추가
  2. 또는 "추가" 탭을 누르면 빠른 메모 모달 + 회의 추가 옵션 액션시트 (UX 결정 필요)
  3. 데스크톱 사이드바 IA와 일관 — "빠른 메모" 모바일에서도 1탭 접근
- **예상 시간**: 3시간 (UX 결정 + 구현 + 테스트)
- **의존성**: T-10 와 함께
- **테스트**: e2e — 375x667 viewport에서 BottomNav 통해 빠른 메모 모달 도달
- **검증**: Casual 막힘 #8 (모바일 빠른 메모 진입점 부재) 해소

---

## 4. 검증 기준

### 신규 테스트 추가
- T-1: rag service Gemini SafetyFilter graceful test (3건)
- T-1: AskRequest validation 단위 테스트 (3건 — whitespace / max_length / 정상)
- T-5: schemas alias introspection 테스트 (전 Request schema)
- T-6: useWorkspaceRole isLoading 단위 테스트
- T-8: MeetingService.get_detail projects 채움 테스트

### 회귀 점검 (기존 테스트 유지)
- Sprint 9 BackgroundTask session_factory
- Sprint 10 R2 프록시 업로드
- Sprint 13 BL-003/004
- AD-33 cross-workspace ProjectMember 차단

### dogfooding (Sprint 14 종료 시)
- 3 페르소나 산출물 (`docs/dev-log/qa/2026-05-13-multi-agent-qa/`) 의 P0/P1 결함이 모두 해소됐는지 Playwright MCP로 재검증
- 특히: "오늘 할 일" 메뉴 부재 / "RAG" 카피 0건 / Clerk Dev 배지 부재 / 모바일 햄버거 부재 / BottomNav 빠른 메모 진입점 존재
- BUG-C01 재현 시도: prompt-injection 류 입력 → 200 응답 + 한국어 안내 확인

### 메트릭
- Composite Health Score: 5.9 → 7.5+ 목표 (Sentinel 기술 안정성 + Curious 신뢰 신호 + Casual UX 종합)
- Curious 도입 결정: Maybe → Yes (조건부) 전환 가능성
- Casual 용어 해독률: 37.5% → 50%+

---

## 5. 위험 + 완화책

| 위험 | 발생 확률 | 영향 | 완화책 |
|------|-----------|------|--------|
| Clerk Production 인스턴스 생성 지연 (사용자 작업) | 중 | T-3 차단 | 사용자에게 사전 요청 + Sprint 14 킥오프 시 명시. T-3는 Production 키 없이도 koKR localization 부분은 진행 가능 |
| BUG-C01 fix 후 다른 LLM 예외 케이스 미처리 잔재 | 중 | RAG 신뢰 회복 부분 효과 | tests/에 알려진 prompt-injection 패턴 5-10건 입력 → 모두 graceful 검증. Sentry monitoring 강화 |
| T-5 schemas alias audit 범위 확대로 시간 초과 | 중 | Sprint 14 일정 지연 | 우선 `Request` 클래스만 audit. `Response` 는 Sprint 15+ |
| T-11 모바일 BottomNav UX 결정 지연 (디자인 의사결정) | 중 | T-11 차단 | "추가" 탭에 액션시트 제안으로 디폴트 진행, 사용자 거부 시 별도 디자인 sprint |
| "RAG" 코드 식별자와 사용자 노출 카피 혼동으로 식별자까지 변경 → 회귀 | 낮음 | 빌드 실패 | grep 매핑 단계에서 "사용자 노출"만 화이트리스트. CI에서 검증 |

---

## 6. 자의 결정 라벨

- **AD-36** Sprint 14 P0/P1 우선순위 — 본 multi-agent QA 결과 기반. P2/P3는 Sprint 15+ 보류.
- **AD-37** "Marketing 트랙 분리" — 가격 페이지 / 고객 로고 / 비교표는 dev sprint와 분리. Curious 핵심 망설임이지만 dev 단독 처리 불가.
- **AD-38** "RAG" 코드 식별자 유지 결정 — 사용자 노출 카피만 치환. 폴더/컴포넌트명은 도메인 용어로 유지 (개발자 가독성).
- **AD-39** BUG-M01~M06 + L01~L02 (Sentinel polish 결함) Sprint 15+ 보류 — 본 Sprint는 신뢰 회복 critical/high에 집중.

---

## 7. 예상 일정

| 작업 | 예상 시간 | 의존성 | 누적 |
|------|-----------|--------|------|
| T-1 RAG graceful | 3h | - | 3h |
| T-2 메뉴 404 숨김 | 0.5h | - | 3.5h |
| T-3 Clerk Prod + koKR | 2h | 사용자 | 5.5h |
| T-4 RAG 카피 치환 | 2h | T-2 (직렬) | 7.5h |
| T-5 헌법 I-16 audit | 4h | - | 11.5h |
| T-6 visibility race | 3h | - | 14.5h |
| T-7 dashboard stale ws | 2h | - | 16.5h |
| T-8 meeting projects sync | 2h | - | 18.5h |
| T-9 카운트 동기화 | 2h | - | 20.5h |
| T-10 모바일 햄버거 숨김 | 1h | T-11 함께 | 21.5h |
| T-11 BottomNav 빠른 메모 | 3h | T-10 함께 | 24.5h |
| **검증 + dogfooding** | **3h** | 전 | **27.5h** |

> **총 ~28시간 (3-4일 집중)**. 병렬 작업 가능 시 2-3일.

---

## 8. 후속 (Sprint 15+ 등재)

다음 Sprint 후보 (현 시점에서는 백로그):
- **Sprint 15 — Onboarding & Trust**: 신규 가입자 onboarding tour, 빈 워크스페이스 첫 5분 가치 도달 경로, dashboard dead button 수정, 검색 답변 인라인 [소스] 표기 정리, Sentinel polish (M01~M06, L01~L02)
- **Sprint 16 — Multi-User Verification**: AD-35 Clerk testing mode + multi-user E2E + V-T4 schemathesis property test + V-T5 RAG 권한 누설 E2E
- **Sprint 17 — Marketing Assets** (Marketing 트랙): 가격 페이지, 고객 로고, vs Otter / vs Notion AI 비교표, 보안 페이지 (SOC 2 진행 상황)

---

## 부록 — 참조 문서

- `docs/dev-log/qa/2026-05-13-multi-agent-qa/integrated-report.html` — 통합 보고서 (HTML)
- `docs/dev-log/qa/2026-05-13-multi-agent-qa/qa-report.md` — Sentinel 원본 (361줄)
- `docs/dev-log/qa/2026-05-13-multi-agent-qa/interested-user-report.md` — Curious 원본 (204줄)
- `docs/dev-log/qa/2026-05-13-multi-agent-qa/general-user-report.md` — Casual 원본 (168줄)
- `docs/CONTEXT-MAP.md` I-16 (camelCase API 헌법 불변식)
- `docs/REFACTORING-BACKLOG.md` BL-001 (meetings export 최적화 — Sprint 14 OOS)
