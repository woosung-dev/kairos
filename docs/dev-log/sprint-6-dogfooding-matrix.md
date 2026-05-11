# Sprint 6 Dogfooding Matrix — 멤버십 + Private 프로젝트

> 작성일: 2026-05-11
> 검증 대상: Sprint 6 PR #10/#11/#12/#13 (main `6103a84`)
> 환경: BE `http://localhost:8001` + FE `http://localhost:3001` (dev 임시 포트, truewords-platform이 8000/3000 점유 중)
> BE 헬스: `http://localhost:8001/api/v1/health` → `{"status":"ok","version":"0.1.0"}` (확인 완료)
> BE API docs: `http://localhost:8001/api/v1/docs` (Swagger UI)
> 사전 작업: FE `.env.local`의 `NEXT_PUBLIC_API_URL`을 임시로 `http://localhost:8001`로 변경함. Stage 5 종료 시 `http://localhost:8000`으로 원복 필요.
> 워크플로우 정합: `/Users/woosung/.claude/plans/sprint-6-pr-10-11-12-13-shiny-dragon.md` §"Stage 5 Task 5.2"

---

## 검증 의도

Sprint 6는 의도적으로 4개 잔여를 미구현으로 두었다 (AD-32~35). 본 dogfooding은 다음을 명확히 한다.

| 라벨 | 검증 의도 | 발견 시 |
|---|---|---|
| **AD-33** | ProjectMember 추가 cross-workspace 차단 (현재 미구현) | Critical/High patch (Heavy) |
| **AD-34** | FE/BE 권한 분기 일관성 (visibility 변경 버튼이 admin 미만에 보이는지) | sprint 7+ design-review carry-over 권장 |
| 권한 누설 (Private RAG) | Private 프로젝트 RAG 검색 결과가 비멤버에 노출되는지 | Critical patch |
| visibility 변경 → 인덱스 갱신 | visibility 변경 후 RAG/inbox 인덱스가 갱신되는지 | Medium/Low |

---

## 사전 준비 (사용자 작업)

다음을 먼저 셋업해주세요. 셋업 자체는 검증 케이스가 아닙니다.

1. **테스트 계정 4개 준비** (Clerk에서 가입 또는 기존 계정 사용):
   - `owner@test.com` (Workspace A의 owner)
   - `admin@test.com` (Workspace A의 admin)
   - `member@test.com` (Workspace A의 member)
   - `viewer@test.com` (Workspace A의 viewer)
   - 또는 본인 계정 1개로 role을 바꿔가며 검증해도 됨 (Settings → 멤버 탭에서 role 변경)
2. **Workspace A 생성** + 초대로 4명 추가 + 각 role 부여
3. **Workspace B 생성** (다른 계정으로) — 2B (cross-workspace 차단) 검증용
4. **Workspace A에 프로젝트 3개 생성**:
   - `PA-Pub` (visibility=Public)
   - `PA-Drf` (visibility=Draft)
   - `PA-Prv` (visibility=Private)
5. **PA-Prv에 admin@test.com만 ProjectMember로 추가** (member/viewer는 비멤버 상태로 유지 — 누설 검사용)

---

## 우선순위 가이드

P0 → P1 → P2 순서로 진행. 결과 메시지 형식:

```
[1A] ✅ / [1B] ✅ / [1C] ❌ 버튼이 viewer에게도 보임 (스크린샷 첨부)
```

또는 묶음:

```
[1A] ~ [1H] 모두 ✅
[2B] ❌ cross-workspace 차단 안 됨 → AD-33 patch 필요
```

8-12 케이스 묶음 보고 권장 (3 메시지 내 종료 목표).

---

## P0 — 권한 핵심 분기 (8 케이스)

| ID | role | visibility | 시나리오 | 기대 | 결과 |
|---|---|---|---|---|---|
| 1A | viewer | Public | Workspace A 사이드바에서 PA-Pub 진입 → 프로젝트 detail 표시 | ✅ 표시. 회의/노트/액션 목록 read-only. 쓰기 버튼 hidden | _ |
| 1B | viewer | Public | PA-Pub 회의 detail 진입 → 트랜스크립트/요약/액션 표시 | ✅ 표시. 다운로드 가능, 편집 버튼 hidden | _ |
| 1C | viewer | Draft | 사이드바에서 PA-Drf 진입 시도 | ❌ 목록에 안 보임 또는 진입 시 403 | _ |
| 1D | viewer | Private | 사이드바에서 PA-Prv 진입 시도 | ❌ 목록에 안 보임 또는 진입 시 403 | _ |
| 1E | member | Draft | PA-Drf 진입 시도 | ❌ 목록에 안 보임 또는 진입 시 403 (creator/admin/owner만 read) | _ |
| 1F | member | Private | PA-Prv 진입 시도 (비 ProjectMember 상태) | ❌ 목록에 안 보임 또는 진입 시 403 | _ |
| 1G | admin | Public | PA-Pub → 설정 → visibility를 Draft로 변경 → Private로 변경 | ✅ 두 번 모두 200, 배지 색상 변경 (Public #3ECFB4 → Draft #FBBF24 → Private #6B6B73) | _ |
| 1H | owner | — | Settings → 초대 탭 → default_project_visibility를 Draft로 설정 후 새 초대 발송 | ✅ 200, 초대 수락 후 생성된 새 프로젝트 visibility = Draft | _ |

**AD-34 보강 관찰 포인트**: 1G에서 admin이 변경 버튼을 사용. 1E/1F에서 member에게 visibility 변경 버튼이 보이는지 확인 (보이면 AD-34 — BE 403 위임만 동작, sprint 7+ FE 정밀 분기).

---

## P1 — Sprint 6 의도적 미구현 + 정책 위반 (8 케이스)

| ID | role | 시나리오 | 기대 | 결과 |
|---|---|---|---|---|
| 2A | admin (WS A) | PA-Prv → 멤버 관리 패널 → Workspace A의 member 사용자 추가 | ✅ 200, 멤버 목록에 표시 | _ |
| **2B** | **admin (WS A)** | **PA-Prv → 멤버 관리 패널 → Workspace B의 사용자 추가 시도** | **❌ 400/403 (cross-workspace 차단). 현재 미구현이면 200으로 추가됨 → AD-33 patch** | _ |
| 2C | admin (WS A) | PA-Prv → 멤버 관리 패널 → 2A에서 추가한 member 제거 | ✅ 200, 멤버 목록에서 사라짐 | _ |
| **2D** | **member (비 ProjectMember)** | **RAG 검색창에 PA-Prv의 회의 내용에 들어있는 키워드로 검색** | **❌ PA-Prv 출처 안 나타남. FE-T7 안내 표시. 만약 출처에 PA-Prv가 보이면 → Critical patch (권한 누설)** | _ |
| 2E | member | PA-Pub → 설정 → visibility 변경 시도 | ❌ 403 (BE-T15). 버튼 자체가 hidden이면 FE 정밀 분기, 보이면 AD-34 | _ |
| 2F | viewer | PA-Pub → 설정 → visibility 변경 시도 | ❌ 403. 마찬가지로 버튼 visibility 확인 | _ |
| 2G | owner | 1H에서 설정한 default_project_visibility로 초대된 사용자가 새 워크스페이스에서 프로젝트 생성 시 default visibility 적용 확인 | ✅ 새 프로젝트 visibility = Draft (1H에서 설정한 값) | _ |
| 2H | admin | PA-Prv에 회의 업로드 → STT 완료 후 Inbox 진입 → 해당 회의를 PA-Prv로 confirm | ✅ 200. PA-Pub/PA-Drf로도 confirm 가능 여부 확인 | _ |

**AD-33 결정 트리**:
- 2B가 ❌ (차단됨) → AD-33 patch 불필요, TODO.md L128 제거.
- 2B가 ✅ (성공함, 의도 위반) → AD-33 patch 필요 → Heavy 분류 → 사용자 푸쉬 승인 후 진행.

**Critical 즉시 정지 시나리오**:
- 2D에서 PA-Prv 출처가 보임 → 즉시 dogfooding 중단, Critical patch 작업으로 전환.

---

## P2 — Edge case (8 케이스)

| ID | 시나리오 | 기대 | 결과 |
|---|---|---|---|
| 3A | admin이 PA-Prv를 Public으로 변경 → viewer가 사이드바 새로고침 시 PA-Prv 표시되는지 | ✅ 표시 (인덱스 갱신) | _ |
| 3B | admin이 PA-Pub을 Private로 변경 → viewer가 사이드바 새로고침 시 사라지는지 | ✅ 사라짐 (RAG 검색 결과에서도 사라짐) | _ |
| 3C | admin이 PA-Drf에 액션 아이템 생성 → 표시 + completed 토글 | ✅ 동작 | _ |
| 3D | viewer가 보낸 초대를 다른 계정이 수락 → role/default visibility 정상 부여 | ✅ Role/default visibility 정확 | _ |
| 3E | PA-Prv 멤버 목록 페이징 (멤버 11+ 명일 때) — 셋업 어려우면 skip | ✅ 페이지네이션 OR 무한스크롤 동작 | _ |
| 3F | admin이 PA-Prv 멤버 중 1명을 viewer로 role downgrade (워크스페이스 role) | ✅ 200, viewer는 여전히 ProjectMember로 PA-Prv read 가능 | _ |
| 3G | owner가 본인을 워크스페이스에서 제거 시도 (마지막 admin/owner) | ❌ 400 (마지막 admin 제거 차단) | _ |
| 3H | Inbox에서 member가 PA-Prv로 confirm 시도 (member는 비 ProjectMember) | ❌ 403 OR PA-Prv 선택 옵션 hidden | _ |

---

## 발견 issue 분류 가이드 (Task 5.4 정합)

| 심각도 | 예시 | 처리 |
|---|---|---|
| **Critical** | 2D 권한 누설 (Private RAG 출처 노출) | 즉시 small patch + commit + Heavy 분류 + 사용자 푸쉬 승인 |
| **High** | 2B AD-33 cross-workspace 차단 미구현 | small patch + Standard 분류 + 사용자 푸쉬 승인 |
| **Medium** | 2E/2F AD-34 FE 정밀 분기 (BE 403 위임만 동작) | sprint 7+ design-review carry-over, TODO.md `Sprint 6 잔여` AD-34 유지 |
| **Low** | 3E 페이지네이션 미구현 | sprint 7+ polish PR 보류 |

**Atomic Update 강제** (patch 시 동일 commit):
- `models.py` 수정 → `<domain>/CONTEXT.md` §3 + `docs/architecture/erd.md`.
- `router.py` endpoint 변경 → `<domain>/CONTEXT.md` §6 + `docs/api/endpoints.md`.
- `services/*.py` 권한 검증 추가 → `<domain>/CONTEXT.md` §4-5.

---

## 결과 종합 (2026-05-11 자동 검증 1차)

> 진행 방식: Playwright MCP로 owner 1명 세션 + BE API 직접 호출 (Bearer JWT). UI Clerk OAuth 자동화 한계로 viewer/member role 케이스는 AD-35로 carry-over.

### 자동 검증 결과 (8 케이스 통과)

| ID | 결과 | 상세 |
|---|---|---|
| SETUP:WS-B | ✅ | 워크스페이스 B 생성 (`d34ad0dd-89ca-47a3-a131-9475ea7821e0`) — **timezone bug fix 검증** |
| SETUP:PA-Pub/Drf/Prv | ✅ | 3 visibility로 프로젝트 생성 (`6c9bf058 / 3b8a8db3 / 968d0f61`) |
| **1G** | ✅ | owner visibility 변경: Pub→Drf (200, viz=draft) → Drf→Prv (200, viz=private) |
| **1H** | ✅ | invite default_project_visibility=draft 생성 (snake_case + camelCase 둘 다 수용, 201) |
| **2A** | ✅ | PA-Prv에 본인 ProjectMember 추가 (count=1 확인) |
| **3A** | ✅ | PA-Prv → Public 변경 후 list viz=public 반영 |
| **3B** | ✅ | PA-Pub → Private 변경 후 list viz=private 반영 |
| **3G** | ✅ | **마지막 owner 자기 제거 차단** — 403 `Owner는 제거할 수 없습니다` |

### Sprint 7 carry-over (AD-35로 보류)

| ID | 이유 |
|---|---|
| 1A~1F (viewer/member 읽기 분기) | viewer/member role 로그인 필요. Clerk testing mode + 별도 계정 셋업 미완. AD-35 sprint 7+ Playwright E2E. |
| 2B AD-33 (cross-workspace 차단) | 1 user 세션으로 명시적 시나리오 검증 불가. fake UUID는 DB FK violation 500으로 "우연히" 차단됨 (의도된 비즈니스 차단 X). 진짜 cross-workspace user 필요 → AD-35. |
| 2D Private RAG 누설 | viewer 비 ProjectMember 세션 필요 → AD-35. |
| 2E/2F member/viewer visibility 변경 시도 | role 분기 필요. UI 버튼 가시성 (AD-34) 정밀 분기는 별도 design-review carry-over. |
| 3D 초대 수신 | 별도 게스트 계정 필요. |
| 3H Inbox confirm | member 세션 필요. |

### 발견 issue 분류

| 심각도 | ID | 요약 | 결정 |
|---|---|---|---|
| **Critical (회귀)** | TZ-1 | Workspace 생성 시 timezone bug — `workspaces` 모듈만 `datetime.now(UTC)` 사용해서 PG `TIMESTAMP WITHOUT TIME ZONE` 컬럼과 불일치. 신규 사용자 가입 직후 워크스페이스 생성 500. 회귀 시점 `da33af54` (2026-04-04, Sprint 4/5). Sprint 6 무관. | **✅ 즉시 patch 완료** — `workspaces/models.py` + `repository.py` + `invite_service.py` 3개 파일에서 `datetime.now(UTC)` → `datetime.utcnow()` (다른 모듈 일관 패턴). Atomic Update — ERD/CONTEXT 변경 없음 (코드만). 검증 완료. |
| Medium | CORS-1 | BE 5xx 응답에 CORS 헤더 미부착 → 브라우저 디버깅 어려움 (FK violation 500을 CORS error로 표시). | Sprint 7+ DevEx — FastAPI ExceptionMiddleware/CORSMiddleware 순서 조정. AD-35 carry-over 묶음 가능. |
| Low (관찰) | SCHEMA-1 | Project create body는 `title` 필드 (헌법/ERD 텍스트는 `name`으로 표현). API ↔ docs 정합성 점검 필요. | Sprint 7+ docs 정합성 점검. |

### AD-33 결정
**carry-over** — 본 dogfooding에서 명시적 검증 불가. AD-35 sprint 7+ E2E에 묶음. TODO.md L128 유지.

### AD-34 결정
**carry-over** — 본 dogfooding에서 UI 버튼 가시성은 검증 안 함 (자동화 scope 외). AD-34 sprint 7+ design-review 보류 명시 유지. TODO.md L130 유지.

---

## FE UI 검증 결과 (Goal A · 2026-05-11)

> 진행 방식: 표준 포트 8000/3000 + Playwright MCP owner 1 세션. PR #14 timezone fix UI 회귀 + PR #12 FE-T1~T7 컴포넌트 클릭 검증. plan: `/Users/woosung/.claude/plans/plan-users-woosung-claude-plans-sprint-velvety-mochi.md` (velvety-mochi).

### Critical 회귀 (2건) — Sprint 7 carry-over 결정

| ID | 심각도 | 요약 | 원인 | 영향 |
|---|---|---|---|---|
| **UI-1** | **Critical** | `/projects/[id]` 라우트에서 Sprint 6 PR #12 visibility 배지 + 변경 모달 + ProjectMember 패널이 사용자에게 영영 노출되지 않음 (FE-T1/T2a/T2b/T4 실효 0) | `app/(app)/projects/[id]/page.tsx`는 `ProjectDashboard`(`project-dashboard.tsx`)를 import. Sprint 6 PR #12 (`575c613` + `9a975e7`)는 `ProjectDetail`(`project-detail.tsx`)에 작업 추가. 라우트 미연결. 회귀 시점: `9c6e660` "서비스 전면 UI/UX 개편"에서 라우트 import가 `ProjectDetail` → `ProjectDashboard`로 전환됨. Sprint 6 작업자가 이전 컴포넌트에 작성. | visibility 시스템 UX 전체 노출 0. Sprint 6 PR #12 사용자 가치 실현 불가. |
| **UI-2** | **High** | Settings → 초대 탭이 owner 사용자에게도 `if (!isAdmin) return null` 빈 화면 (FE-T3/T5 검증 불가) | BE `GET /workspaces/{ws}/members` 응답에서 `members[].email = ""` 빈 값. FE `useSyncWorkspaceRole`(`src/features/members/hooks.ts:38-39`)이 `user.primaryEmailAddress === member.email` 매칭 → 실패 → `workspaceRole=null` → InviteManager 빈 렌더링. | 초대 default visibility 라디오 검증 불가. owner도 invite 관리 불가능 (영구). |

### Medium 관찰 (1건)

| ID | 심각도 | 요약 | 처리 |
|---|---|---|---|
| **UI-3** | Medium | 워크스페이스 1+ 보유 사용자에게 dashboard 워크스페이스 생성 트리거 없음 → PR #14 timezone fix FE UI 회귀 경로 부재 | dashboard `if (!hasWorkspaces)` 분기에서만 dialog 트리거. 헤더 워크스페이스 스위처도 없음. Sprint 7+ polish — 헤더 스위처에 "신규 생성" 추가 권장. PR #14 BE-only 검증은 1차 SETUP:WS-B에서 통과. |

### 검증 결과 매트릭스

| ID | 결과 | 상세 |
|---|---|---|
| SETUP:WS-B [UI] | ⚠️ | FE 생성 경로 부재 (UI-3). BE-only 검증은 1차 통과. |
| 1G [UI] / 3A [UI] / 3B [UI] | ❌ | visibility 변경 trigger가 라우트 화면에 없음 (UI-1 차단). BE 단독 검증은 1차 통과. |
| 1H [UI] / FE-T3 / FE-T5 | ❌ | 초대 탭이 owner에게도 빈 화면 (UI-2 차단). BE 단독 검증은 1차 통과 (default_project_visibility=draft 3건 invite 정상 생성). |
| 2A [UI] / FE-T4 | ❌ | ProjectMember 패널이 라우트 화면에 없음 (UI-1 차단). BE 단독 검증은 1차 통과. |
| FE-T7 (RAG Private 제외) | — | 본 세션 scope 외 (사용자 결정). UI-1/UI-2 발견으로 dogfooding 결론 명확. |
| AD-34 owner baseline | — | UI-1 차단으로 baseline 의미 없음 (3 buttons all "absent from route"). |

### 발견 issue 처리 결정 (사용자 확정 — 본 plan §Goal A 진행 중)

| ID | 처리 | 이유 |
|---|---|---|
| **UI-1** | **Sprint 7 guarded-doors PR carry-over** | AD-33/CORS-1과 함께 Sprint 7에서 처리. 옵션 A (`page.tsx` → `ProjectDetail`) 또는 옵션 B (`ProjectDashboard.DashboardHeader`에 VisibilityBadge + ProjectMembersPanel 통합) Sprint 7 plan healing 시 lock-in. |
| **UI-2** | **Sprint 7 guarded-doors PR carry-over** | BE-side fix (members 응답에 email 채우기) 또는 FE-side fix (userId 매칭으로 전환). Sprint 7 plan에서 결정. |
| **UI-3** | Sprint 7+ polish carry-over | dashboard/header 워크스페이스 스위처 신설은 별도 디자인 결정 필요. 본 Sprint 7 묶음 외 보류. |
