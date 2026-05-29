# Kairos 전체 정검 — 버그/이슈 목록 (2026-05-29)

우선순위: P0(차단/보안) > P1(핵심 기능/권한) > P2(UX·정합성) > P3(개선).
출처: [정적]=Phase 2A 정적 감사, [라이브]=MCP Playwright 화면 검증.

---

## P0 / P1 (headline)

### BUG-WS-SWITCH-BROKEN (P1, 팀 사용엔 P0) [라이브 — 근본원인 코드 확정]
**워크스페이스 전환이 UI 에서 완전히 동작하지 않음.** 스위처 드롭다운에서 다른 워크스페이스를 클릭/키보드 선택해도 active workspace 가 바뀌지 않음(헤더 라벨·localStorage·프로젝트 목록 전부 불변, 2회 클릭 + 키보드 모두 재현).
- **근본원인**: dropdown-menu 가 Base UI(`@base-ui/react/menu`)로 마이그레이션됨 → `Menu.Item` 은 **`onClick`** 으로 액션 발화. 그러나 `WorkspaceSwitcher.tsx:129` 는 여전히 Radix API 인 **`onSelect={() => handleSwitch(ws.id)}`** 사용 → Base UI 가 무시(React 가 DOM text-selection 이벤트로 attach, 클릭 시 미발화) → `handleSwitch` 영원히 미호출.
- **결정적 증거**: `header.tsx:158-159` 에 개발자 본인이 남긴 주석 — "base-ui Menu.Item 은 onClick 사용 — onSelect (Radix API) 는 미동작". 아바타 메뉴(설정/로그아웃)는 `onClick` 으로 고쳤으나 WorkspaceSwitcher 는 누락. codebase 전체에서 `onSelect=` 는 이 1곳뿐(grep 확인).
- **영향**: personal + team 워크스페이스를 가진 사용자가 **UI 로 팀 워크스페이스에 진입 불가**. 팀 협업/RBAC 핵심 플로우 차단. ("새 워크스페이스"는 onClick 이라 동작 → 생성은 됨, 전환만 불능.)
- **evaluator 합의**: 3/3 만장일치 confirmed (codex 가 `@base-ui v1.3.0 MenuItem.d.ts` 에 onSelect prop 부재·onClick/closeOnClick 만 존재 직접 확인).
- **fix (범위 확대 — evaluator 정정)**: ① `WorkspaceSwitcher.tsx:129` `onSelect` → `onClick` (1단어). ② **회귀가드 hollow-green 해소**: `workspace-switch.spec.ts` 는 이미 activeWorkspaceId 변화 assert 를 보유하나 `auth.setup.ts` 가 ws 1개만 시드 → non-active 옵션 0 → `test.skip` 으로 무력화돼 이 버그가 출시까지 생존. setup 에 **2번째 워크스페이스 시드 + skip 게이트 제거** 필수(이게 진짜 fix 범위).

## P1

### BUG-RBAC-CACHE-STALE (P1) [정적, 라이브 검증 예정]
role 변경/멤버 제거 시 `rbac.py:60-62 invalidate_member_cache` 헬퍼가 정의·권고 주석까지 있으나 `invite_service.py:240(update_member_role)`·`:262(remove_member)` 어디서도 호출 안 함. `_MEMBER_CACHE` TTL 60s(rbac.py:27-28) → admin 이 멤버를 강등/제거해도 해당 멤버는 **최대 60초간 이전 권한 유지**(visibility 우회/쓰기 가능). deny-default + workspace 1차 게이트로 완전 우회는 아니나 권한 강등 즉시성 위배. → Phase 2B gap #4 로 라이브 검증.
- fix: invite_service update_member_role/remove_member commit 직후 `invalidate_member_cache(workspace_id, member.user_id)` 2줄 추가.

### BUG-DRAFT-DOC-CONTRADICTION (P1 거버넌스, 보안 영향 없음) [정적 + 라이브 확정]
draft visibility 정의 모순: `CONTEXT-MAP.md:64`(헌법, draft=ProjectMember) ↔ `projects/CONTEXT.md:60 P-5`(draft=creator+admin/owner) ↔ 코드 `projects/repository.py:105-108`(draft=creator-only+admin/owner 우회).
- **라이브 확정**: member B 가 owner A 의 draft 프로젝트 미접근(목록 미노출 + 직접 ID 404) → **코드(creator-only)가 실제 동작**. 헌법이 틀린 outlier.
- **evaluator 정정**: 초기 "정반대" 표현은 **과장**(심각도 disputed). 코드는 projects/CONTEXT.md + RAG 필터까지 내부 일관하고 헌법 1곳만 stale. 보안 즉시노출 위험 없음(코드가 더 보수적). → P1 은 source-of-truth 거버넌스 관점 유지, **헌법 §5 line 64 를 "draft=creator 전용+admin/owner 우회"로 atomic update 정정**.

---

## P2

### BUG-PROJ-ROLE-RACE (P2) [라이브]
/projects 등 write-gated 페이지로 hard-load/새로고침 직후 `workspaceRole`(메모리 전용, persist 제외)이 null → "새 프로젝트" 생성 버튼 + empty-state action 이 role sync(useMembers) 완료 전까지 숨겨짐. 기능 정상이나 새로고침마다 "권한 없는 듯한" 첫 페인트. file: `store.ts:48-52` partialize + `members/hooks.ts:33-41` + `projects/page.tsx:16,38,79`.
- fix 후보: workspaceRole 도 persist 하거나, role 로딩 중엔 skeleton/낙관적 표시.

### BUG-INBOX-PROMOTE-STUB (P2) [라이브]
Inbox 항목 "✏️ 다른 프로젝트" 클릭 → "프로젝트 선택 기능은 준비 중입니다." 패널. 버튼은 동작하나 수동 프로젝트 선택 promote 미구현 stub. (현 워크스페이스 프로젝트 0 — 프로젝트 보유 시 재확인 예정.)

### BUG-MEMORY-WS-FILTER (P2) [정적]
`memory/repository.py:55-95,139` MemoryItem mutation 5종(update_distilled/embedding/status/transcript, clear_r2_audio_key)이 `workspace_id` WHERE 없이 PK 단독 필터 + `memory/models.py` MemoryItem 에 composite FK 전무(타 도메인과 불일치). 현재 service 가 항상 사전 검증 → 실 IDOR 아니나 다층 방어 2계층 공백(latent IDOR).

### BUG-WS-MEMBER-UNIQUE (P2) [정적, evaluator escalation]
`workspace_members` 의 `(workspace_id, user_id)` UNIQUE 제약 부재(`idx_workspace_members_ws_user` = unique=False). lazy seed 의 NOT EXISTS 가드에 DB 백스톱이 없어 신규 user 첫 로그인 시 dashboard 5+ endpoint 동시 fanout → 이론상 중복 owner-member row 가능. (라이브 단일계정 seed 는 중복 0 확인했으나 동시성 미재현.) → DB UNIQUE 제약 추가 권장.

### BUG-ADR024-STATUS (P2) [정적]
`docs/adr/024` Status="Accepted"(supersedes 022)이나 main 코드는 ADR-022(webhook SKIP) 상태와 정합(sync handler 부재). 결정-실행 갭이 Status 표기에 없음. → "Accepted(decision)/Deferred(execution, PR#106 closed)"로 정정.

---

## P3

### BUG-ROLE-ENUM-VALIDATION (P3) [정적]
`invite_service.py:46,228` invite.role/new_role 에 ROLE_LEVEL enum 검증 부재 → 임의 문자열 허용(현재 fail-safe=deny). RoleChecker.__init__ 패턴 일관성 위해 검증 추가 권고.

### BUG-ORPHAN-PROJECTMEMBER (P3) [정적]
WorkspaceMember 제거 시 해당 user 의 ProjectMember row 미정리 → 재초대 시 과거 private 멤버십 부활(workspace 1차 게이트로 접근은 차단, 데이터 위생 문제).

### 잔여 데이터 위생 (P3) [라이브]
멤버 record email="" / displayName="사용자" — lazy seed 시 JWT claims 에 email 미포함(ADR-022 webhook SKIP 잔재). 멤버 목록 UI 가독성 저하.
