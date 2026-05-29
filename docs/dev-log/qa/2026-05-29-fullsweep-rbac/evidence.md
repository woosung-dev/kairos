# Kairos 전체 정검 — 라이브 증거 로그 (2026-05-29)

환경: 로컬 FE :3000 + 로컬 BE :8000 → 운영 Neon DB. Clerk dev 인스턴스(pk_test).
계정: Account A = `d@e.com` (clerkId `user_3E7dOsm2xeXjo8En3HSokRBPSvM`, 비-founder), 활성 워크스페이스 = "사용자의 개인 Kairos" (personal, ws `e968c95f-4bbe-4f12-9468-2741c047e142`).
공통 console warning(무시): "Clerk has been loaded with development keys" — dev 인스턴스 정상.

## Phase 1 — 페이지 sweep 결과

### /dashboard — PASS
- 렌더: h1 "무엇이든 질문하세요", 검색 버튼(⌘K), 추천 질문 4버튼, 빠른 접근 4타일(/new·/notes·/inbox·/projects), 사이드바(홈·Inbox[badge 2]·Memory[NEW]·빠른 메모·+추가·설정).
- console.error: 0 (warning 1 = Clerk dev keys).
- screenshot: 01-dashboard.png
- 상호작용: ⌘K 검색 버튼 → 커맨드 팔레트 정상 오픈(검색/이동/생성 그룹) → Esc 닫힘. PASS.

### /inbox — PASS (단, 미완성 기능 1건)
- 렌더: h1 "Inbox", "확인 필요 2건", 항목 2개(회의 type, AI 추천 70%/80%, 태그, ✅확정/✏️다른프로젝트/🗑무시 + "워크스페이스 이동" 버튼). 사이드바 Inbox 링크 active.
- console.error: 0.
- screenshot: 02-inbox.png
- **BUG-INBOX-1 (P2)**: "✏️ 다른 프로젝트" 클릭 → 패널에 "프로젝트 선택 기능은 준비 중입니다." 표시. 버튼은 동작하나 수동 프로젝트 선택 promote 기능이 **미구현 stub**. (현 워크스페이스에 프로젝트 0개이긴 함 — throwaway 프로젝트 보유 워크스페이스에서 재확인 예정.)
- 미검증(파괴/AI): ✅확정(promote), 🗑무시(dismiss), 워크스페이스 이동 → throwaway 단계에서 자작 항목으로 검증 예정.

### /new — PASS
- 렌더: h1 "콘텐츠 추가", 콘텐츠 타입 3카드(회의 녹음/노트 작성/자료 업로드), 회의 녹음 서브탭 3개(오디오 업로드/직접 녹음/텍스트로 입력).
- 오디오 업로드: 회의 제목 + 파일선택(MP3/WAV/M4A/MP4/WebM) + "업로드 시작"[disabled] (입력 전 비활성 정상).
- 텍스트 입력: 제목 + 내용(최소 50자) + char counter "0자(50자 더 필요)" + "AI 분석 시작"[disabled] (50자 미만 비활성 정상). 탭 전환 PASS.
- console.error: 0. screenshot: 03-new.png
- **AI 분석 시작 실행**: 제목/내용 입력 후 클릭 → 미팅 생성 + `/meetings/89de9991-79d8-475c-a77f-a9a415e59102` 리다이렉트. PASS (실제 파이프라인 트리거).

### /meetings/[id] — PASS (processing 상태)
- 렌더: h1 미팅 제목, "AI 분석 중" 배지, 내보내기/워크스페이스 이동 버튼, 날짜, "처리가 완료되면 자동으로 업데이트됩니다"(폴링).
- console.error: 0. screenshot: 04-meeting-detail-processing.png
- 후속: ready 상태(요약+액션아이템) + inbox 항목 생성 재확인 예정.

### /notes — PASS
- 렌더: h1 "빠른 메모", "+ 새 메모" 버튼, 기존 노트 1건("[AUDIT] agent-1 test note" → /notes/2347ab81...), 워크스페이스 이동 버튼.
- console.error: 0. screenshot: 05-notes.png

### /notes/[id] — PASS
- 렌더: 뒤로 가기 링크(→/notes), 편집/팀으로 올리기/내보내기 버튼, h1 제목, Tiptap 에디터 본문.
- 상호작용: "편집" → "저장 후 닫기"로 전환 + 제목 textbox 편집가능 + 본문 에디터 편집가능. 뒤로 가기 → /notes 복귀. PASS.
- console.error: 0. screenshot: 06-note-detail.png

### /projects — PASS (단, 권한 게이팅 hydration race 1건)
- 렌더: h1 "프로젝트", 빈 상태(projects-empty-state) "프로젝트가 없습니다".
- console.error: 0. screenshot: 07-projects.png(race 상태=버튼 없음), 07b-projects-after-rolesync.png(동기화 후=버튼 있음)
- **BUG-PROJ-ROLE-RACE (P2)**: /projects 로 hard-load/새로고침 직후 `workspaceRole`(store.ts 메모리 전용, persist 제외)이 null → `canWrite=hasRole("member")` false → "새 프로젝트" 생성 버튼 + empty-state action 이 **잠시 숨겨짐**. useMembers(role sync) resolve 후 버튼 노출. 기능은 정상이나 새로고침 시마다 "권한 없는 듯한" 첫 페인트 발생(느린 네트워크일수록 길어짐). 근본: store.ts partialize 가 workspaceRole 제외 + useSyncWorkspaceRole(members.find clerkId===user.id) 지연. file: src/features/workspaces/store.ts:48-52 + src/features/members/hooks.ts:33-41 + src/app/(app)/projects/page.tsx:16,38,79.
- 멤버 API 정상: GET /workspaces/{id}/members → {id,userId,clerkId,email,displayName,role} 반환, clerkId 매칭 정상, role=owner. (단 email="" displayName="사용자" — JWT claims 에 email 미포함 잔재.)
- 계정 A 워크스페이스 2개: personal(e968c95f) + **team "QA Cycle C Team"(7f9f446d)** — RBAC 테스트에 team 재사용 가능.

### /search (RAG) — PASS (전체 E2E 검증)
- 렌더: h1 "지식 검색", 스코프(전체/현재 프로젝트/선택한 소스), 기간·유형 필터, 입력 + 전송[disabled when empty], "Private 프로젝트는 명시적 멤버에게만 표시됩니다" 안내.
- **실제 RAG 질의**: "전체 정검 스프린트에서 결정된 범위는?" → 정확한 답변(화면 레벨 검증 + RBAC 2계정 테스트) + "출처: 📎 QA 전체정검…" 인용. 소스 펼치기 → 4건(내 미팅 회의·텍스트 / AUDIT 노트 / 2개 기존 회의) 표시. **/new→Gemini distill→OpenAI embed→RAG retrieval 전체 체인 PASS.**
- console.error: 0. screenshot: 08-search.png, 08b-search-rag-result.png
- 사이드바 race 재확인: hard-load 직후 빠른메모/+추가 숨김 → role sync 후 노출(BUG-PROJ-ROLE-RACE 사이드바도 영향).

### /memory (Recall) — PASS (capture+recall E2E)
- 렌더: h1 "메모 검색", auto-focus 검색박스, 빈 힌트, "새 메모 추가" FAB.
- **CaptureSheet**: FAB → 다이얼로그 "메모 추가"(textarea + 음성녹음 + 취소 + 저장[disabled]). 메모 입력 → 저장 → toast "메모를 저장했어요. AI 정리 중…".
- **Recall**: "RBAC 캐시 무효화" 검색 → ~30초 내 article 반환(AI distill 제목 "Kairos RBAC 캐시 이슈 검증" + "의미 매칭" 배지 + 요약 + "팀으로 올리기"). **capture→distill→embed→semantic recall E2E PASS.** (BUG-MEMORY-WS-FILTER 는 latent — 기능 정상.)
- console.error: 0. screenshot: 09-memory.png, 09b-memory-recall.png

### /settings (4탭) — PASS (+ personal invite FE 갭)
- 멤버: h1 "설정", "owner · 멤버 1", 멤버 목록(사용자, OWNER 배지). 4탭 모두 노출(owner). screenshot: 10-settings.png
- 초대: "초대 링크 생성" 버튼 + 다이얼로그(역할/visibility/만료). **personal ws 에서 생성 시 POST → 403(I-19 정상 차단)**. 단 FE 가 personal 에서도 초대 UI 노출 → BUG-PERSONAL-INVITE-UX.
- 일반: AI 임계값 4프리셋(70/80/90/95%). 80% 클릭 → PATCH /settings 200(owner mutation 정상). screenshot: 10b-settings-general.png
- Audit: "Promote Audit 로그" + 유형필터 + 빈상태. admin+ gated. screenshot: 10c-settings-audit.png

### /admin/recall-metrics — PASS (founder gate)
- 비-founder(d@e.com) → "접근 권한 없음 · founder 전용". screenshot: 11-admin-recall-metrics-denied.png. 0 errors.

### /actions — PASS — /inbox 로 리다이렉트. 0 errors.

### /pricing, /sign-in, /sign-up, / (logged-out) — 미검증(로그아웃 필요)
- 인증 상태로 /pricing·/sign-in·/sign-up 접근 시 /dashboard 리다이렉트(landing 정상). 로그아웃 없이 확인 불가 → 사용자 계정 확보 후 진행.

## Phase 2B — 워크스페이스/RBAC 라이브 검증

계정 A = d@e.com (owner). 팀 워크스페이스 "QA Cycle C Team"(7f9f446d) 재사용. **2번째 계정은 사용자 제공 대기**(MCP 단일 브라우저 + 멀티세션 UI 부재 + A 비번 미보유).

### 🔴 BUG-WS-SWITCH-BROKEN (P1/팀 P0) — 워크스페이스 전환 완전 불능
- 스위처에서 "QA Cycle C Team" 클릭(2회) + 키보드 선택 모두 → active 불변(헤더·localStorage·프로젝트 전부 personal 유지).
- 근본원인 코드 확정: dropdown-menu = Base UI(`@base-ui/react/menu`, onClick 발화). WorkspaceSwitcher.tsx:129 = Radix `onSelect` → 미발화 → handleSwitch 미호출. header.tsx:158-159 주석이 같은 함정 명시(아바타 메뉴는 onClick 으로 고쳤으나 스위처 누락). 전체 코드 onSelect= 사용처 이 1곳뿐.
- 워크어라운드: localStorage activeWorkspaceId 직접 주입 + reload → 팀 ws 진입 성공(헤더 "QA Cycle C Team" 확인). 이후 RBAC 검증은 이 워크어라운드로 진행.

### RBAC 6갭 라이브 결과
1. **visibility 필터 (owner-side) — PASS**: 팀 ws 에서 public/draft/private 프로젝트 생성(201) → owner 가 6개 전부 + 정확한 배지(공개/작업 중/비공개) 확인. owner 우회 정상. screenshot: 13b-projects-team-grid.png. (member/viewer 시점은 2번째 계정 대기.)
2. **lazy seed 멱등성 — PASS(부분)**: 계정 A 는 personal+team 각 1 owner 멤버, 중복 0. 신규 user 첫 로그인 멱등성은 2번째 계정 대기.
3. **cross-ws (I-17) — 부분**: API 레벨 IDOR 로 대체 검증(아래 #6). 프로젝트 멤버 추가 cross-ws 는 2번째 user_id 필요.
4. **role 변경 전파 (cache-stale) — 정적 확정, 라이브 대기**: BUG-RBAC-CACHE-STALE. invalidate_member_cache 미호출 → 60s stale. 라이브 repro 는 2번째 계정 필요(owner 가 B 강등 → B 60s 잔존 접근).
5. **invite — PASS**: 팀 ws invite 생성 201(code ig1bDB7bsuno, member, maxUses 5, 7일 만료). personal ws invite POST → 403(I-19). 이미 멤버가 accept → 409 + "이미 워크스페이스 멤버입니다"(graceful). screenshot: 12-invite-accept.png
6. **cross-ws IDOR — PASS**: A 토큰으로 비-멤버 워크스페이스(random uuid) GET members/projects/detail → 전부 403. 멤버십 게이트 견고.

### /projects/[id] — PASS
- h1 "QA-Public-Proj", 진행 중, "Visibility: 공개"(변경 버튼), edit, 설명, 태그, 프로젝트 빈상태(회의 녹음/노트 작성 링크). screenshot: 14-project-detail.png. 0 errors.

### 미팅 ready 직접 관찰 (evaluator gap 해소) — PASS
- /meetings/89de9991 재방문 → 상태 "완료"(was "AI 분석 중"). 요약/트랜스크립트/액션 탭.
- 요약: 정확한 Gemini 요약(입력 내용 정합, hallucination 없음). 핵심 결정사항 3건 + 주제 3건 추출. 참석자 1명, 텍스트 소스. (screenshot 04b 시도했으나 font-load 타임아웃 — 스냅샷이 증거.)

## Phase 2B 후반 — 2계정 cross-account 라이브 (계정 B = a@e.com / member)

- 로그아웃(A) → "/" landing(logged-out) 렌더 PASS(0 errors). /sign-in Clerk 폼(이메일/비번/Apple/Google/회원가입 링크/Development mode) PASS.
- B 로그인(a@e.com/ae) → /dashboard. **/sign-in 로그인 플로우 PASS.** B clerkId user_3E7dKbZ3IcTKe7I1q08YQlw92PS.
- **gap #2 lazy seed PASS(라이브)**: B 첫 로그인 → personal ws 정확히 1개(owner) 생성, 중복 0.
- invite ig1bDB7bsuno 수락 → B = 팀 "QA Cycle C Team" **member** (POST accept 정상, /dashboard 리다이렉트 + 활성 ws=team 자동 전환).
- **gap #1 visibility 필터 PASS(라이브, member 시점)**: member B 가 팀 /projects 에서 **public 4개만** 노출(QA-Public + seed 3). **QA-Draft·QA-Private 미노출 + 직접 ID 접근 시 둘 다 404.** → 화면+API 양쪽 확인(16-member-view-projects.png).
- **BUG-DRAFT-DOC-CONTRADICTION 실동작 판정**: member 가 A 의 draft 미접근(404) = **코드(draft=creator-only)가 실제 동작**. 헌법(draft=ProjectMember)이 틀린 문서임을 라이브로 확정.
- member /settings 게이팅 PASS: 탭 = 멤버/초대/일반 (**Audit 숨김** = admin+ 정상). 초대 탭은 노출되나 내용 "초대 링크 관리는 관리자(Admin) 이상 권한에서만 가능합니다" + 생성버튼 없음 + 403 없음(Sprint 23 enabled-override). 멤버 목록 2명(OWNER+MEMBER, 둘 다 displayName "사용자" — seed email/name P3).
- gap #4 cache-stale: 3 evaluator 만장일치 정적 confirmed(invalidate_member_cache 호출처 0). 라이브 repro 는 A↔B 60s 내 전환 필요로 단일 브라우저 불안정 — evaluator 도 "정적 확정 적절" 동의. 정적 확정으로 종결.
