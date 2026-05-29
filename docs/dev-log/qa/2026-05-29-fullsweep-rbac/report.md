# Kairos 전체 정검 보고서 — 화면 레벨 QA + 워크스페이스/권한 심층 검증

- 일자: 2026-05-29 · 환경: 로컬 FE :3000 + 로컬 BE :8000 → 운영 Neon DB · Clerk dev(pk_test)
- 계정 A: `d@e.com` (owner, 비-founder) · 팀 ws "QA Cycle C Team"(7f9f446d) 재사용
- 방법: MCP Playwright 화면 레벨(메인 에이전트 순차 구동) + 정적 감사 Workflow(opus 3-lens) + API 레벨 검증
- 산출물: 본 report.md · bugs.md · evidence.md · screenshots/(01~14) · evidence 입력은 Phase 3 evaluator 패널로 감사

---

## 1. 종합 판정 (Ship-readiness)

**핵심 기능 파이프라인(AI/RAG/Memory)은 견고하나, 워크스페이스 전환 P1 버그로 팀/RBAC 플로우가 UI 차단됨. 외부 dogfooding 전 P1 3건 수정 권장.**

- AI 파이프라인 E2E (회의 텍스트→Gemini 요약→OpenAI 임베딩→RAG 검색→인용) **전부 PASS** — 미팅 "완료" 상태 + 정확한 요약·핵심결정 직접 관찰.
- Memory capture→distill→embed→semantic recall E2E **PASS**.
- 18개 라우트: 인증 12개 + 미인증 landing/sign-in 까지 sweep, 전부 0 console.error.
- **워크스페이스 전환 완전 불능(P1, 팀 사용 P0)** — UI 스위처로 팀 진입 불가(invite 수락만 우회 경로). e2e 회귀가드도 hollow-green 으로 무력화돼 출시까지 생존.
- RBAC **2계정 라이브 검증**: member 가 public 만 보고 draft/private 차단(404), Audit 탭 숨김 등 권한 분기 정상 동작. 설계 방향 = **direction-correct-with-fixes (7.5/10)**, evaluator 종합 QA 신뢰도 **7.3/10**. GO 전 P1 3건(WS-SWITCH·CACHE-STALE·헌법 draft 정의) 수정 권고.

## 2. 페이지 sweep 결과 (18 라우트)

| 라우트 | 결과 | 비고 |
|---|---|---|
| /dashboard | ✅ PASS | ⌘K 팔레트, 추천질문 4, 빠른접근 4타일 |
| /inbox | ✅ PASS | AI 분류 항목 + 액션버튼. ⚠️"다른 프로젝트" 미구현 stub |
| /actions | ✅ PASS | → /inbox 리다이렉트 |
| /new | ✅ PASS | 3 콘텐츠타입 + 오디오/녹음/텍스트 탭, 검증 disabled 정상 |
| /meetings/[id] | ✅ PASS | AI 분석중→**완료** 직접 관찰: 요약+핵심결정 3+주제 (정확, hallucination 없음) |
| /notes | ✅ PASS | 목록 + 새 메모 |
| /notes/[id] | ✅ PASS | 편집 토글, 저장, 팀으로 올리기, 뒤로 |
| /projects | ✅ PASS | 그리드/빈상태. ⚠️hard-load 시 생성버튼 role-race |
| /projects/[id] | ✅ PASS | 제목/상태/visibility/edit/태그/빈상태 |
| /search (RAG) | ✅ PASS | 실제 질의→정답+4소스 인용 (E2E) |
| /memory (Recall) | ✅ PASS | capture→distill→semantic recall (E2E) |
| /settings (멤버) | ✅ PASS | 4탭 노출(owner) |
| /settings (초대) | ✅ PASS | team 생성 OK / personal 403. ⚠️personal FE 노출 |
| /settings (일반) | ✅ PASS | 임계값 PATCH 200 |
| /settings (Audit) | ✅ PASS | admin+ gated |
| /invite/[code] | ✅ PASS | 수락 페이지 + 이미멤버 409 graceful |
| /admin/recall-metrics | ✅ PASS | 비-founder 차단 |
| 워크스페이스 전환 | 🔴 FAIL | **BUG-WS-SWITCH-BROKEN (P1)** — invite 수락은 active ws 전환됨(우회 경로) |
| / (logged-out landing) | ✅ PASS | 마케팅 풀페이지, nav/hero/CODE 파이프라인/footer, 0 errors |
| /sign-in | ✅ PASS | Clerk 폼 + 로그인 플로우(B 로그인 성공) |
| /sign-up | ◐ 링크 확인 | landing/sign-in 의 회원가입 링크 → Clerk hosted. 폼 직접 sweep 생략 |
| /pricing (logged-out) | ◐ 링크 확인 | landing nav "요금" 링크 존재. (인증 시 /dashboard 리다이렉트) |

## 3. RBAC 6갭 라이브 검증

| # | 갭 | 결과 | 근거 |
|---|---|---|---|
| 1 | visibility 필터 | ✅ **PASS (라이브, 2계정)** | member B 가 public 4개만 노출, **draft·private 미노출 + 직접 ID 404**. owner 는 전부. |
| 2 | lazy seed 멱등성 | ✅ **PASS (라이브)** | B 첫 로그인 → personal ws 정확히 1개 owner. (DB UNIQUE 부재 동시성은 BUG-WS-MEMBER-UNIQUE P2) |
| 3 | cross-ws member add(I-17) | ◐ API 대체 | #6 으로 커버, 프로젝트 멤버추가는 추가 setup 필요 |
| 4 | role 변경 전파 | 🔴 정적 확정 (3 evaluator 만장일치) | **BUG-RBAC-CACHE-STALE** (60s). 라이브 repro 불안정 → 정적 종결 |
| 5 | invite max_uses/만료/personal | ✅ PASS | team 201, personal 403(I-19), 이미멤버 409, member-view 게이팅 메시지 |
| 6 | cross-ws IDOR | ✅ PASS | 비멤버 ws GET → 전부 403, cross-visibility 직접접근 404 |

2계정(A=owner d@e.com / B=member a@e.com) 라이브로 gap #1·#2·#5·#6 확정. #4 만 정적(evaluator 동의). member /settings 게이팅(Audit 숨김·초대 content-gated) 화면 확인.

## 4. 설계 방향 검증 (정적 감사 3-lens, opus)

**verdict = direction-correct-with-fixes · 7.5/10.** 핵심 방향(workspace 4역할 1차 게이트 + project 3-visibility 2차 분기 + cross-tenant 404 + composite FK I-9)은 1인 founder→소규모 팀에 적합하고 일관적. 결함은 전부 보안 구멍 아닌 정합성/즉시성/계약 문제이며 fail-safe 방향. GO 전 수정 항목: (1) cache 무효화 누락(P1), (2) draft 정의 헌법-코드 모순(P1), (3) ADR-024 status-코드 갭(P2). 추가: workspace_members (workspace_id,user_id) UNIQUE 부재 → lazy seed 동시성 중복 가능(P2).

## 5. 버그 요약 (상세 bugs.md)

| ID | P | 출처 | 한줄 |
|---|---|---|---|
| BUG-WS-SWITCH-BROKEN | P1 | 라이브 | 워크스페이스 전환 불능 — onSelect(Radix) vs Base UI onClick. fix 1단어 |
| BUG-RBAC-CACHE-STALE | P1 | 정적 | role 강등/제거 후 60s stale 권한 — invalidate_member_cache 미호출 |
| BUG-DRAFT-DOC-CONTRADICTION | P1 | 정적 | draft visibility 헌법(ProjectMember) ↔ 코드(creator-only) 정반대 |
| BUG-PROJ-ROLE-RACE | P2 | 라이브 | hard-load 시 role-gated CTA flash-hidden (workspaceRole persist 제외) |
| BUG-INBOX-PROMOTE-STUB | P2 | 라이브 | "다른 프로젝트" promote 미구현 stub |
| BUG-PERSONAL-INVITE-UX | P2 | 라이브 | personal ws 초대 UI 노출(백엔드 403 정상) |
| BUG-MEMORY-WS-FILTER | P2 | 정적 | MemoryItem mutation 5종 workspace_id WHERE 누락 + composite FK 부재 (latent) |
| BUG-WS-MEMBER-UNIQUE | P2 | 정적 | workspace_members (ws,user) UNIQUE 부재 → 동시 seed 중복 가능 |
| BUG-ADR024-STATUS | P2 | 정적 | ADR-024 Accepted 표기 ↔ 코드 ADR-022 SKIP 유지 |
| BUG-ROLE-ENUM / ORPHAN-PM / SEED-EMAIL | P3 | 정적/라이브 | enum 미검증 / orphan ProjectMember / 멤버 email 공란 |

## 6. 검증된 강점 (PASS 하이라이트)

- 전체 AI 파이프라인 E2E (회의/메모 → 요약·임베딩·RAG·recall) 실동작 + 정확한 인용.
- 멀티테넌시 격리(I-9): 비멤버 워크스페이스 API 전부 403, composite FK 다층 방어.
- I-19 personal 격리: 초대 생성/수락 백엔드 403/graceful.
- founder 게이트, 이미-멤버 409, owner 임계값 PATCH 등 권한 분기 정상.

## 7. 잔여 (사용자 입력 필요)

- 2번째 계정(email/password) → 갭 #1 member-view, #4 cache-stale 실측, #2 동시 seed.
- 로그아웃 후 미인증 4개 페이지(/, /pricing, /sign-in, /sign-up) sweep.

## 8. Phase 3 Evaluator 패널 결과 (빈컨텍스트 opus + codex + 완전성 비평 + synthesis)

- **종합 QA 신뢰도: 7.3/10.** 4축 평균 = 성공기준 6.83 / 엣지 5.83 / 문서검정 7.0 / 아키텍처 7.17.
- **헤드라인 버그 합의**: BUG-WS-SWITCH-BROKEN **3/3 만장일치 confirmed**(codex 가 `@base-ui v1.3.0 MenuItem.d.ts` 에 onSelect prop 부재·onClick 만 존재 직접 확인) · BUG-RBAC-CACHE-STALE **3/3 confirmed**(invalidate_member_cache production 호출처 grep 0) · BUG-DRAFT-DOC **존재 3/3 confirmed, 심각도 disputed**(“정반대”는 과장 — 헌법 1곳만 outlier, 코드는 projects/CONTEXT + RAG 필터까지 내부 일관).
- **evaluator 가 지적한 본 QA 사각지대 2건 (일부는 본 세션에서 해소)**:
  1. WS-switch 회귀가드 **오진단** — `workspace-switch.spec.ts` 는 이미 activeWorkspaceId 변화 assert 보유. 진짜 문제는 `auth.setup.ts` 가 ws 1개만 시드 → non-active 옵션 0 → `test.skip` 으로 무력화(hollow-green). **fix 범위 확대**: onClick 1단어 + setup 2번째 ws 시드 + skip 게이트 제거.
  2. RBAC 4갭·AI 파이프라인이 정적/owner-side/processing-only 였던 점 → **본 세션 후반에 계정 B 로 gap #1(member-view)·gap #2(lazy seed) 라이브 확정 + 미팅 ready 직접 관찰로 해소**. gap #4(cache-stale)만 정적 확정 유지(라이브 repro 불안정, evaluator 동의).
- **GO 전 권고(evaluator 합의)**: (a) WS-SWITCH onClick + e2e skip 게이트 제거, (b) RBAC 강등 즉시성 캐시 무효화 배선, (c) 헌법 draft 정의 코드 정합 정정, (d) 미팅 ready 산출물 실관찰(✅ 본 세션 완료).
