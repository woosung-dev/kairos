<!-- 팀 spine 멀티계정 anti-hollow-green e2e 회귀 스위트 — Generator 시나리오 스펙(구현 grain, codex 1차 반영) -->

# 팀 spine 멀티계정 e2e 회귀 — Generator 시나리오 스펙

> 상위 승인 플랜: `~/.claude/plans/ultracode-swirling-zebra.md`. 본 문서는 **구현 grain**(spec별 정확 oracle·mutation·seed)이며 Implementer/Evaluator의 authoritative 입력. **codex 1차(계획) adversarial 반영 완료**(§8). 모든 anchor·SSE 스키마·branch·cache·시드 경로는 코드 grounded.

## 0. 확정된 외부 사실 (코드 grounded — hollow-green 회피 핵심)

- **계정/타깃**: LOCAL Clerk dev(`pk_test`) `QA_LOCAL_OWNER_EMAIL=d@e.com`/`QA_LOCAL_MEMBER_EMAIL=a@e.com`(2계정), BE `:8000` **단일 프로세스**(uvicorn 1 worker — setRole 즉시성·`invalidate_member_cache` in-process 동기 의존), FE `:3003`. `E2E_API_URL=http://localhost:8000` 오버라이드 필수.
- **BE 기동**: `uv run --directory backend uvicorn src.main:app --host 127.0.0.1 --port 8000`(`--reload` 금지).
- **RBAC 캐시**(`auth/rbac.py:28-63,90-98`): `_MEMBER_CACHE`는 RoleChecker 첫 호출 전까지 **비어있음**. 무효화 mutation(T6/T8)을 관측하려면 **먼저 cache warm**(B가 RBAC 보호 endpoint 1회 호출 → 캐시 적재) 후 owner가 remove/role-change → B 재호출 → 차단/허용 검증. warm 없으면 캐시 miss로 DB 직조회 → mutation **불가시**(hollow-green).
- **visibility 우회**(`projects/repository.py:102-114`, `embeddings/repository.py:166-183`): owner/admin은 **워크스페이스 role**로 우회(creator를 ProjectMember 자동등록 **안 함** — `projects/service.py`). 즉 member(role=member·非ProjectMember)는 private 제외, member→admin 승격 시 role 우회로 포함.
- **RAG SSE 스키마**(`rag/service.py`): `thinking{status}`·`search_results{chunks:[{id,text,source,sourceType,score,...}]}`·`answer{token}`·`done{cached,sourceCount}`·`error`. 결정적 oracle = **`search_results` chunk `id` 집합**(answer 텍스트·sourceCount 아님).
- **시맨틱 캐시 함정**(`embeddings/repository.py:331-391`): 캐시 키 = ws+(project)+question(**role 무관**). hit 시 admin은 visibility 재검증 **bypass**(`:376-378`) → member가 캐시한 public-only 결과를 admin이 그대로 받음 → **T8 false/hollow**. ⇒ T5/T8 sseAsk는 **호출마다 unique nonce**로 캐시 miss 강제(≥0.93 유사도 회피) + chunk id oracle.
- **promote 분기**(`notes/service.py:318`): `if needs_embed_regenerate:` → `_bg_regenerate_embed_with_audit`(:537-545, **:541 session_factory** mutation 대상). `else:` → `_bg_promote_embed_note`(이미 임베딩된 노트). **노트 생성 직후 즉시 promote = source chunk 0 = regenerate 분기**(QA-0617-A 실 repro).
- **임베딩 시드**: `POST .../projects {title,visibility}`(create 시 visibility 지정) → `POST .../notes {projectId,plainText/content,title}` → BG embed → `GET .../notes/{id}/embedding-status {status,chunkCount}` 폴링.
- **owner 보호**(`invite_service.py:243-244,271-272`): owner role 멤버 PATCH/DELETE → `CannotModifyOwnerError`. **초대 유효성**(`:285-292`): inactive/expired/max_uses → invalid.
- **RAG citation 결함**(prompt `common/prompts.py:105` `📎 제목(날짜)` vs FE `markdown-message.tsx:22` `/\[(\d+)\]/`; sources는 `[소스 N]` 라벨 `service.py:319`) → 인라인 citation→SourceViewer 프로덕션 사망. **SourceViewer 유일 트리거 = 인라인 `[N]` 배지 클릭**(`rag-chat.tsx:55-69`; `RagSources`는 display-only).

## 1. 제품 변경 (최소)

**P-FIX-1 — RAG citation 포맷 정렬**(사용자 승인): `RAG_SYSTEM_PROMPT` 규칙3을 `📎 …` → **"답변에 사용한 각 소스를 `[소스 N]`의 번호로 `[1]`, `[2]` 형식 인용"**으로 교체(I-4 중앙 프롬프트). 회귀 가드 = BE 단위 테스트(`RAG_SYSTEM_PROMPT`에 `[1]`/번호 인용 지시 단언) + T15 e2e. Atomic: `backend/src/rag/CONTEXT.md`(citation 포맷, 있으면).

> 그 외 BE/제품 로직은 **현 main이 정답** — 회귀 가드만 추가.

## 2. 멀티계정 인프라 (Phase A, 먼저)

### `frontend/e2e/team.setup.ts`(신규, `{browser}`) — 멱등 시드
1. owner/member 각 `browser.newContext()` 로그인(`input[name="identifier"]`).
2. owner `GET /workspaces` → `type==="team"`+고정명 `"E2E Team Workspace"` discover-or-create.
3. owner `POST .../invites {role:"member",maxUses:null,expiresInDays:30}`→201.
4. member `POST /invites/{code}/accept`: 200/201=가입·**409=이미 멤버(성공)**·404/410=throw.
5. owner baseline 리셋: `GET .../members` email 매칭 `memberRecordId` → role≠member면 `PATCH {role:"member"}`.
6. **RAG 픽스처(멱등 discover-or-create by 고정 title, chunkCount>0면 skip)**: owner가 (a) **public** `"[E2E] RAG public"` note plainText에 `CYAN42` + 식별 문장, (b) **private** `"[E2E] RAG private"` note plainText에 `MAGENTA99` + 식별 문장, (c) **draft** `"[E2E] draft"`(visibility=draft, T3/T14용·임베딩 불요). 각 note embedding-status `completed`+chunkCount≥1 폴링(≤40s). publicChunkId·privateChunkId 추출 보관.
7. **seed 가드(false-green killer)**: 저장 전 team ws `GET .../members`가 정확히 owner+member 2행(emails 일치·role owner/member·B 중복 없음) 단언. 미달 throw.
8. 양쪽 `localStorage["kairos-workspace"]={state:{activeWorkspaceId:teamWsId},version:0}` 주입.

### `frontend/e2e/fixtures/team.ts`(신규) — `base.extend<TeamFixtures>`
`ownerContext/memberContext`·`ownerPage/memberPage`(goto `/dashboard`)·`teamWsId`·`memberRecordId`·`ownerPersonalWsId`·`ragFixtures{publicProjectId,privateProjectId,draftProjectId,publicChunkId,privateChunkId}`·`getToken(page)`(매 호출 fresh)·`api(page,method,path,body)`(Bearer+JSON)·`setRole(role)`(owner PATCH만, sleep·재발급 없음)·**`ensureMemberBaseline()`**(B가 멤버 아니면 invite+accept 재수립 후 role=member — membership-mutating spec 간 self-restore)·**`sseAsk(page,{question,projectId,timeRange})`**(question에 **unique nonce 자동 부착** → 캐시 miss; rag/ask SSE 수집 → `{searchResultIds:Set<string>, answer:string, sourceCount:number}`). `warmRbac(page)`(B가 `GET .../projects` 1회 → RBAC 캐시 적재). TS strict·`any` 금지(`ClerkWindow` shim).

### `frontend/playwright.config.ts`(수정, gated)
`E2E_RUN_TEAM==="true"`일 때만 `team-setup`+`team`(testMatch `e2e/tests/team/*.spec.ts`, **`fullyParallel:false`**, `dependencies:["team-setup"]`, top-level storageState 없음, `--disable-web-security`). 실행은 **`--project=team --workers=1`**(전역 fullyParallel:true와 격리). 기존 setup/chromium/public-only·`user.json` 불변.

## 3. 시나리오 표 (codex 반영 — oracle·mutation 구현 grain)

> 공통: 실 2-토큰·실 RoleChecker 관통(mock 금지). 부정 단언(absence/`toHaveCount(0)`/chunk id 부재) 필수. **membership/role mutating spec**(T2·T6·T7·T8·T11·T17)은 `describe.serial`+`beforeEach ensureMemberBaseline()`/`afterEach` 복원 — order-independent.

| # | Pri | oracle | break-to-verify (제품 mutation, file:line) |
|---|---|---|---|
| **T1** | P0 | member·viewer(setRole) `POST .../invites`→**403**; owner·admin→**201** body `code`·`inviteUrl` | `invite_router.py:37` `require_admin`→`require_viewer` ⇒ member 201 |
| **T2** | P0 | owner `DELETE .../members/{bId}`(B 제거)→owner `POST invite{role:"member"}`→B accept→**200/201** body `role=="member"`·`workspaceId==teamWsId`; 직후 B `GET /workspaces/{teamWsId}`→200(B 멤버 복원) | `accept_invite` role 강제 `"admin"` ⇒ role=="admin" |
| **T3** | P0 | member `GET .../projects`= public id만; member(비작성자) `GET /projects/{draftId}`→**404**·`{privateId}`→**404**; 목록에 draftId·privateId **부재** | `projects/repository.py:102-114` `or_(...)`→`return stmt` |
| **T4** | P0 | member `GET /workspaces/{ownerPersonalWsId}/projects`→**403**; member `GET·PATCH·DELETE /workspaces/{teamWsId}/projects/{foreignId}`(타 ws project)→**404**(admin 승격해도 404) | `projects/repository.py:28-30` `Project.workspace_id==workspace_id` 술어 제거 |
| **T5** | P0 | member `sseAsk({question:"MAGENTA99 비밀", projectId:null})`: `searchResultIds`에 **privateChunkId 부재**·answer에 `MAGENTA99` 부재; 대조 `sseAsk({question:"CYAN42"})` publicChunkId **포함** | `embeddings/repository.py:166-183` `_visibility_filter_sql` AND(...) 제거 ⇒ member 결과에 privateChunkId |
| **T6** | P0 | `warmRbac(B)` 먼저 → owner `DELETE .../members/{bId}`→204 → **같은 테스트**서 B `GET .../projects`→**403**(60s 대기 X); B `GET /workspaces`에 teamWsId 부재 (이후 ensureMemberBaseline 복원) | `invite_service.py:277-280` remove의 `invalidate_member_cache` 삭제 |
| **T7** | P1 | member `PATCH·DELETE .../members/{id}`→**403**; B=admin: role-change `PATCH .../members/{ownerId}`→**403**(require_owner) + `DELETE .../members/{ownerId}`→**403/400**(CannotModifyOwnerError) — admin-delete-일반멤버 positive는 3계정 부재로 deferred(§8 gap) | `member_router.py:35` `require_owner`→`require_member` ⇒ member role 변경 성공 |
| **T8** | P1 | `warmRbac(B)` → owner B→admin → B `GET /projects/{draftId}·{privateId}`→**200**; B `sseAsk({question:"MAGENTA99 X<nonce>"})` `searchResultIds`에 privateChunkId **포함**; 이어 owner B→member 강등 → B 동일 `sseAsk(new nonce)` privateChunkId **부재**(즉시 재격리) | `invite_service.py:249-253` update의 `invalidate_member_cache` 제거 ⇒ stale role(승격·강등 양방향 깨짐) |
| **T9** | P1 | owner 노트(plainText에 토큰, **생성 직후 임베딩 대기 없이**) 팀 promote→**202**(regenerate 분기); `GET .../notes/{newId}/embedding-status` 폴링 `completed`+`chunkCount>=1`; 팀 `sseAsk`가 토큰 chunk 검색 | `notes/service.py:541` `session_factory=session_factory` 제거 ⇒ `failed`·chunkCount 0 |
| **T10** | P1 | owner `POST /workspaces/{ownerPersonalWsId}/invites`→**403**; 메시지에 리터럴 `을(를)` 부재 | `invite_service.py:59-61` `type=='personal'` 가드 제거 |
| **T11** | P2 | owner `DELETE .../members/{bId}`→owner `POST invite`→B가 같은 code `Promise.all` 동시 2 accept: status ⊆ {200,201,409}, **500 부재**; 최종 `GET .../members` B 1행(복원) | `repository.py:98-112` ON CONFLICT→plain `add`+flush ⇒ 한쪽 500 |
| **T12** | P2 | plain_text 빈 노트 promote→**400**(NotePromoteNotEmbeddedError) | `notes/service.py:279-280` `if not source.plain_text` 가드 제거 |
| **T13** | P1 UI | B(team+personal ≥2 ws) `getByTestId("workspace-switcher")` 클릭→`getByTestId("workspace-switcher-item-{otherId}")` 클릭→`localStorage.activeWorkspaceId` 변경·active 표시 갱신; console.error **0** | WorkspaceSwitcher `handleSwitch` onClick no-op stub |
| **T14** | P2 UI | B=member `/projects`: `getByTestId("project-card-{publicId}")` 보임; `{draftId}`·`{privateId}` `getByTestId` **`toHaveCount(0)`**; console.error 0 | T3과 동일 BE break |
| **T15** | P1 UI | owner `/search` 질문(공개 seed 유도)→실 SSE 완료→`getByTestId("rag-sources")` "소스 N건" present(seed 소스 표시); 인라인 `getByTestId("citation-badge-1")` 클릭→`getByTestId("rag-source-viewer")` 열림+소스 제목; console.error 0 | `rag/service.py` `search_results` sources 방출 제거 ⇒ msg.sources 빈 → 패널 부재 + 배지 클릭 `sources[0]` undefined → viewer 안 열림(결정적) |
| **T16** | P2 UI | owner `/settings?tab=audit` `getByTestId("settings-audit-tab")` 보임; member `toHaveCount(0)`(content 숨김 안내); console.error 0 | audit 탭 role-gate 제거 ⇒ member 노출 |
| **T17** | P2 | owner가 **owner 자신** member row `PATCH {role:"member"}`→**4xx**(CannotModifyOwnerError)·`DELETE`→**4xx** | `invite_service.py:243-244`(또는 271-272) `if member.role=="owner": raise` 제거 ⇒ owner 강등/제거 성공 |
| **T18** | P2 | owner `POST invite` 후 `DELETE/deactivate invite` → B(또는 재) accept→**4xx**(비활성 초대) | `invite_service._validate_invite:287` `if not invite.is_active` 가드 제거 ⇒ 비활성 초대 accept 성공 |

### file:line anchor
visibility `projects/repository.py:102-114`·`:28-30` · RAG vis `embeddings/repository.py:166-183` · cache `embeddings/repository.py:331-391` · RBAC `auth/rbac.py:16-21`·`:28-63` · 무효화 `invite_service.py:249-253`·`:277-280`·`:59-61` · owner보호 `:243-244`·`:271-272` · 초대유효 `:285-292` · 초대 RBAC `invite_router.py:37`·`:84-98` · 멤버 RBAC `member_router.py:35`·`:51` · promote `notes/service.py:318`(분기)·`:541`(session_factory)·`:279-280`(guard) · 동시 `workspaces/repository.py:98-112` · RAG SSE/source `rag/service.py:301-331` · prompt `common/prompts.py:100-115`.

## 4. data-testid 원자 추가

`WorkspaceSwitcher.tsx`(`workspace-switcher`·`workspace-switcher-item-${ws.id}`) · `member-list.tsx`(`member-row-${id}`·`member-role-badge-${id}`·`member-actions-${id}`·`member-remove-${id}`·`member-role-change-${id}-${role}`) · `invite-manager.tsx`(`invite-create-button`·`invite-row-${id}`·`invite-copy-${id}`·`invite-deactivate-${id}`·`invite-deactivate-confirm`) · `visibility-badge.tsx`(`visibility-badge-${visibility}`) · `project-card.tsx`(`project-card-${id}`·`project-card-title-${id}`) · `citation-badge.tsx`(`citation-badge-${number}`) · `rag-sources.tsx`(`rag-sources`) · `source-viewer.tsx`(`rag-source-viewer`) · settings audit 탭(`settings-audit-tab`). kebab-case+동적 id 접미사.

## 5. 삭제 (hollow-green 4종)

`rag-citation.spec.ts`·`invite-accept-happy-path.spec.ts`(→T2 실 시드)·`settings-audit.spec.ts`(→T16)·`workspace-switch.spec.ts`(→T13). `nightly-e2e.yml` rag-citation 참조 제거. `invite-page-regression.spec.ts` 유지.

## 6. mutation gate (Phase C) + 검증

각 spec done = `(green-baseline, red-on-mutation, green-on-revert)` triple. mutation=제품 코드만. Evaluator(fresh) 병렬 + `/codex` 최종(diff adversarial).
```bash
E2E_RUN_TEAM=true E2E_API_URL=http://localhost:8000 \
QA_LOCAL_OWNER_EMAIL=d@e.com QA_LOCAL_OWNER_PASSWORD=… QA_LOCAL_MEMBER_EMAIL=a@e.com QA_LOCAL_MEMBER_PASSWORD=… \
pnpm --dir frontend exec playwright test --project=team --workers=1
pnpm --dir frontend e2e ; uv run --directory backend pytest -q
```

## 7. gotchas
1 wrong-ws/seed → members==2 정확 단언. 2 single-process BE. 3 60s JWT → 매 요청 getToken. 4 accept 409=성공. 5 stale `.auth/`. 6 노이즈 필터(Clerk CSP·음성 4xx/5xx). 7 RAG 시드 멱등. 8 **RBAC cache warm 선행**(T6/T8). 9 **시맨틱 캐시 nonce 우회**(T5/T8). 10 membership-mutating self-restore.

## 9. 구현 노트 (as-built — 비자명 결정)

빌드 중 발견·해결한 핵심(미래 유지보수용):
1. **멤버 식별 = userId**(email 아님): a@e.com 은 lazy-seed 라 `members[].email` 빈 문자열(QA-0617-F 현실) → `GET /users/me` 의 `id`(=`WorkspaceMember.userId`)로 매칭.
2. **active ws 강제 = `ownerUserId`(clerkId) 동반 주입**: `store.ensureOwner(clerkId)`(panel-layout)가 persist 소유자 불일치 시 `activeWorkspaceId=null` 리셋 → 첫 ws self-heal. 시드가 `{state:{activeWorkspaceId, ownerUserId:clerkId}}` 주입해야 team ws 유지(BL-S27c-12).
3. **RAG 캐시 우회 = `timeRange:"1m"`**: 시맨틱 캐시는 question 임베딩 기반(role 무관) + admin hit 시 visibility 재검증 bypass → poisoning. `time_range` 지정 시 BE 가 캐시 skip(`rag/service.py:67-73`) → 매 호출 fresh vector search(visibility 필터 실관통). nonce 부착은 유사도 ≥0.93 유지로 무효 + retrieval 저하 → 폐기.
4. **SSE 파싱 `\r\n`**: sse-starlette 는 `\r\n` 라인 → `\n\n` split 불가. 라인 기반 flush 파서. (잘못된 파서는 chunks=0 → private-absence 단언이 trivially pass = hollow. public 대조군이 포착.)
5. **Clerk hydrate 대기**: storageState 로 연 페이지는 `window.Clerk.session` 비동기 → `getToken` 이 `waitForFunction` 으로 대기.
6. **CORS `:3003`**: 로컬 BE `cors_origins` 기본 `:3000` → `:3003` preflight 400(console.error 노이즈). `backend/.env` `CORS_ORIGINS=...,:3003` 추가(로컬 게이트 prereq).
7. **시드 dedup**: `DELETE /notes` 는 임베딩 chunk orphan → 토큰 노트 정확히 1개 보장(list→delete extras→create 1).
8. **T15 제출 = Enter**: 전송 버튼이 피드백 FAB(z-30)와 겹쳐 pointer intercept → `rag-input` `press("Enter")`.
9. **console.error 판정**: 브라우저 generic "Failed to load resource" 는 URL 미포함 → response 리스너로 URL 기반 노이즈(Clerk accounts.dev·preflight) 필터, 앱 BE 4xx/5xx 만 기록.

## 8. codex 1차(계획) adversarial 반영

**P1 수정 완료**: T6/T8 cache pre-warm(`warmRbac`); T9 create-즉시-promote로 regenerate 분기 적중(:541); T2/T11 remove-후-accept(B 이미 멤버 충돌 해소)+self-restore; T5/T8 nonce 캐시-우회+chunk id oracle(sourceCount 폐기, 캐시 role-blind poisoning 차단); T15 mutation=`search_results` 방출 제거(결정적, 프롬프트-[N] 제거 비결정 폐기). **P2 추가**: T17(owner 보호)·T18(초대 유효성); T4에 PATCH/DELETE cross-tenant; T8에 강등 재격리; seed가 정확 emails/roles 단언. **deferred gap(3계정 부재)**: T7 admin-delete-일반멤버 positive·viewer 전 cell 매트릭스 — `docs/TODO.md` 등재. **확정 사실**: project create는 creator를 ProjectMember 자동등록 안 함 → owner는 role 우회로 private 조회(T5/T8 전제 정합).
