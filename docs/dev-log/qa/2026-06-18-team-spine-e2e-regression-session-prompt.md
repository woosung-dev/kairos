<!-- 다음 세션용 프롬프트 — 팀 spine 라이브 검증을 멀티계정 e2e 회귀로 고정 (ultracode, Generator/Evaluator + anti-hollow-green) -->

# 신규 세션 프롬프트 — 팀 spine e2e 회귀 스위트 구축

> 아래 `---` 사이 블록을 새 세션에 그대로 붙여넣으세요. ultracode 모드 전제. 이 프롬프트는 2026-06-17 멀티 에이전트 팀 QA(main `3b3241c` 머지 완료)의 후속이며, **검증 자료는 `docs/dev-log/qa/2026-06-17-multi-agent-qa/report.md` + 본 문서 §부록(테스트 타깃 표)** 에 grounded 되어 있습니다.

---

ultracode 모드로 진행한다. **목표: 2026-06-17 팀 QA에서 라이브로 1회 검증한 "팀/멀티테넌시 spine"을 멀티계정 Playwright e2e 회귀 스위트로 영구 고정한다.** 단순히 테스트를 추가하는 게 아니라, **각 테스트가 실제로 RED 될 수 있음(invariant를 제품 코드에서 깨면 빨개짐)을 별도 Evaluator 에이전트가 mutation으로 증명**하는 anti-hollow-green 스위트를 만든다. Generator(테스트 설계) → Implementer(작성, TDD) → **별도 Evaluator(opus mutation gate + codex 교차)** 를 끝까지 분리 적용한다.

## 왜 이 작업인가 (배경)
- 2026-06-17 팀 QA에서 cross-tenant 격리(I-9)·visibility 3종·RAG private 누수 0·RBAC 4-cell·revocation·promote 검색성을 owner(`d@e.com`)+member(`a@e.com`) 2계정으로 라이브 검증했고 **전부 PASS**. 하지만 그건 **1회성 수동 검증**이라 다음 변경에서 조용히 깨질 수 있다 → 영구 가드 필요.
- **핵심 함정(이번 QA의 교훈)**: 기존 BE 테스트는 **RBAC 의존성을 mock으로 override** 한다(`backend/tests/workspaces/test_invite_api.py` 가 `require_admin` 등을 전부 mock → "member→403"이 실제로 검증 안 됨). visibility/RAG 테스트도 `requester_role=`를 손으로 넘겨 실 `RoleChecker`+Clerk JWT 경로를 우회한다. 그리고 QA-0617-A(P1)는 **버그 지점 `embed_note_async`를 noop mock한 테스트가 버그를 가려서** 놓쳤다. **이 스위트는 두 개의 실 토큰으로 실 RBAC 체인을 관통해야 하고, 모든 스펙은 mutation으로 RED 가능성을 증명해야 한다.**
- 로드맵(discovery-first, PR #125)과 정합: prospect에게 동작하는 팀 제품을 자신 있게 보여주려면 핵심 팀 흐름이 회귀하지 않아야 한다.

## 0. Context Sync (순서대로)
1. `CONTEXT-MAP.md` §6 불변식 — **I-9**(cross-tenant 404, admin 우회 불가) · **I-13**(API ws prefix) · **I-17**(cross-ws ProjectMember write 403) · **I-19**(personal no-invite) · §5 visibility(public/draft/private, draft=creator-only+admin/owner 우회, private=ProjectMember+admin/owner 우회+RAG 자동 제외).
2. `AGENTS.md` → `.ai/templates/workflow.md`(위험도) → `.ai/common/global.md` §2(doc routing) → `.ai/integrations/with-superpowers.md` + `with-gstack.md`(스킬 라우팅).
3. `docs/dev-log/qa/2026-06-17-multi-agent-qa/report.md`(커버리지 매트릭스 — 자동화 대상) + 본 문서 §부록(T1~T14 테스트 타깃 표, oracle + break-to-verify).
4. memory: `project_team_qa_20260617_done`(직전 QA 결과·결함) · `feedback_e2e_selector_atomic_update`(신규 page/component = e2e selector 동시 atomic update) · `feedback_e2e_trace_snapshot_first`(e2e 실패 시 trace.zip page snapshot 먼저, `.first()` 금지·`data-testid` 권장) · `feedback_asyncpg_greenlet_precheck` · `feedback_brainstorming_must_not_skip`.
5. **git/상태 verify**: main `3b3241c` 기준. BE(:8000)에 **수정 반영 위해 재시작** 필요(이전 세션 BE는 fix 전 코드). FE(:3000/3003).

## 1. 위험도 = HEAVY → 게이트 순서 강제
인증/멀티계정 auth refactor → `.ai/templates/workflow.md` 상 **Heavy**(인증 트리거). 게이트: `verification-before-completion → /codex + agy 교차 → /review → /qa Exhaustive → /ship → Monitor`. **API 시그니처 변경 시 schemathesis contract + Playwright E2E 둘 다 통과(한쪽만이면 PR 차단)**. 증거표준: FE 스크린샷+console.error 0 / BE pytest+alembic dry-run + **mutation-gate triple 표를 PR body에**. doc routing: 격리/불변식 건드리면 `CONTEXT-MAP.md` canonical doc 동반(Atomic Update). 플랜 = `docs/plans/active/<slug>.md`.

## 2. 에이전트 아키텍처 (Generator / Implementer / 별도 Evaluator — anti-hollow-green 핵심)
| 역할 | 스킬 | 동시성 | 산출 |
|---|---|---|---|
| **Generator (설계)** | `brainstorming` → `writing-plans` + **`/codex`(계획)** | 직렬 | 시나리오 = {invariant, 정확 oracle, **break-to-verify mutation**} 목록 (mutation을 설계 시점에 미리 정의 = Step 5를 기계적으로) |
| **Implementer (작성)** | `test-driven-development` + `subagent-driven-development` (config 공유로 **직렬 권장**, 독립 spec만 worktree 병렬) | 직렬→부분 병렬 | 멀티계정 auth setup(먼저) + `.spec.ts` 파일 + 필요한 `data-testid` atomic 추가. 태스크 간 `requesting-code-review` 게이트 |
| **Evaluator (검증 — 구현과 다른 fresh 에이전트)** | `dispatching-parallel-agents` + `verification-before-completion` + **`/codex`(최종)** | 병렬 | spec별 **green→red→green triple** + codex adversarial diff review. 둘 다 통과해야 ship |

**Generator/Evaluator 분리 = load-bearing 규칙**: Evaluator는 spec이 어떻게 작성됐는지 모르는 fresh context. 입력 = spec 파일 + invariant + mutation 레시피만. self-grading 금지.

## 3. 하드 선행 작업 (멀티계정 인프라 — 먼저, 직렬, 코드리뷰 게이트)
현재 `frontend/e2e/auth.setup.ts`는 **단일 계정**(하나의 `e2e/.auth/user.json`, `E2E_USER_*`만 사용). `.env.local`의 `E2E_OWNER_*`/`E2E_VIEWER_*`/`QA_LOCAL_*`는 **선언만 되고 코드에서 미참조(dead)**. 모든 격리 spec이 member 세션에 의존하므로 이걸 **가장 먼저** 만든다(깨진 auth fixture는 모든 격리 spec을 false-green으로 만든다 → 최고 레버리지 게이트).
1. **이중 storageState**: `auth.setup.ts`를 role 파라미터화(또는 `owner.setup.ts`/`member.setup.ts` 분리) → `e2e/.auth/owner.json` + `e2e/.auth/member.json`. `QA_LOCAL_OWNER_*`(d@e.com)/`QA_LOCAL_MEMBER_*`(a@e.com) 소비. `localStorage["kairos-workspace"]` 주입 유지.
2. **two-context 픽스처**: 한 테스트에서 owner/member 두 `browser.newContext({storageState})` + 공용 `getToken(page)` 헬퍼(복붙된 `window.Clerk.session.getToken()` 통합, 토큰 ~60s 만료 주의).
3. **결정적 팀 시드**: owner가 실 endpoint로 초대 발급 → member 수락(수동 `E2E_INVITE_CODE` punt 제거) → member가 알려진 role로 ws 멤버임을 보장. settings-audit의 구조적 미커버 분기 해소.
4. **stable selector atomic 추가**(`feedback_e2e_selector_atomic_update`): 현재 팀 컴포넌트 대부분 `data-testid` 없음 — workspace-switcher 메뉴 아이템, member-list 행+role 배지, invite-manager 생성/복사/비활성 버튼+행, visibility-badge, project-card 에 `data-testid` 추가. `invite-accept-happy-path.spec.ts:67`이 이미 잘못 가정한 `data-testid="workspace-switcher"` 도 실제로 추가.
5. **un-skip / 재게이트**: `rag-citation.spec.ts:43`의 **영구 `test.skip`** 과 `invite-accept-happy-path.spec.ts`의 env+code 이중 skip(hollow-green)을 시드 기반 실 흐름으로 교체. 새 env 플래그 `E2E_RUN_TEAM=true`(기존 `E2E_RUN_INVITE`/`E2E_RUN_HEAVY` 패턴) + CI는 `vars.E2E_ENABLED` 뒤.
6. **CI 와이어링**: 새 팀 spec이 `E2E_OWNER_*`/`E2E_VIEWER_*` secret을 `e2e` job env에 등록(`test.yml`는 현재 `E2E_USER_*`만). 로컬 게이트 = `pnpm e2e tests/<spec>` (CI는 결제 차단, memory `project_sprint28_fullsweep_qa_done`).

## 4. 테스트 타깃 (§부록 표 T1~T14를 Implementer에 직접 전달)
- **Pure-API(빠르고 견고, 먼저)**: T1~T12. `Authorization: Bearer <clerk jwt>` → `:8000`, 실 `RoleChecker` 관통(기존 mock 테스트와의 갭). `twoAccountFixture`({ownerToken, memberToken, wid, personalWid} + `setRole(role)` 헬퍼).
- **UI-driven(data-testid 필요)**: T13(ws-switch, BUG-WS-SWITCH 가드) · T14(member 프로젝트 목록 public만 렌더).
- **엣지 회귀 명시 고정**: T11(동시 accept 409, QA-0617-D) · T12(0-chunk promote 분기, QA-0617-A) — 둘 다 이번 세션 발견, 별도 named spec.

## 5. anti-hollow-green 프로토콜 (비협상 핵심)
모든 spec이 "done" 되려면:
```
1. green-baseline:  pnpm e2e tests/X.spec.ts (clean code) → PASS
2. red-on-mutation: invariant를 **제품 코드에서** 깸(ws_id WHERE 제거 / RBAC dep 주석 / private 필터 제거 — §부록 file:line) → spec MUST FAIL
3. green-on-revert:  git checkout 제품 파일 → 다시 PASS
→ (green,red,green) triple 기록. RED 없는 spec은 hollow → 거부, Step 4로 반려.
```
mutation은 **제품 코드만**(테스트 아님 — 테스트만 고쳐서 빨개지는 건 정확히 막으려는 hollow-green). Step 0(Generator)에서 mutation을 미리 설계해 Step 5를 기계적으로.

## 6. /codex 2회 호출 (요구)
① **계획**(Step 1): scenario→oracle 완전성 점검(presence만 보고 absence 누락 등). ② **최종**(Step 5b): spec+config+auth diff adversarial 리뷰(absence 누락, `toHaveCount(0)` 누락, mutation 무관하게 통과하는 spec, owner/member storageState 교차오염).

## 7. 함정 체크
- mock으로 invariant 우회 금지(실 2-토큰 RBAC 관통) · `embed_note_async`류 "버그 지점 mock" 금지.
- `data-testid` 우선, `.first()`/i18n 텍스트 정규식 금지(`feedback_e2e_trace_snapshot_first`). 신규 testid는 spec과 **같은 PR atomic**.
- 토큰 60s 만료(즉시 fetch) · Clerk `accounts.dev` 외부 노이즈 필터 · 의도적 음성 API 프로브의 4xx/5xx console 로그는 앱 결함 아님.
- CI 결제 차단 → 로컬 mutation 게이트가 standing 대체 · 포트 :3000/3003 고정 · BE 재시작(fix 반영).
- 기존 hollow-green spec(rag-citation 영구 skip, invite 이중 skip, settings-audit role-blind, workspace-switch single-ws)을 **고치거나 대체**(방치 금지).

## 8. 수용 기준 (done 정의)
- 멀티계정 auth setup(owner.json+member.json) + two-context 픽스처 + 시드 동작.
- T1~T12 pure-API + T13~T14 UI spec 작성, **각 spec의 (green,red,green) triple 기록 PR body 포함**.
- 전체 `pnpm e2e` 로컬 green + BE pytest 무회귀 + console.error 0(UI) + `/codex` 최종 PASS + `/review`.
- CONTEXT-MAP/endpoints 등 canonical doc Atomic Update. Git Safety(커밋·푸쉬·머지 각 승인).

## 9. 산출물
e2e 스위트(specs + auth setup + 픽스처 + data-testid) · mutation-gate triple 표 · 플랜 doc · PR(Heavy 게이트 통과) · 메모리 closeout.

---

## 부록 A — 테스트 타깃 표 (T1~T14, oracle + break-to-verify)

> 계정: owner `d@e.com`(BE `caf5c27b…`) + member `a@e.com`(BE `15676bf0…`). owner가 B의 role을 member↔admin↔viewer 변경해 4-role 커버. 라이브 검증된 동작 기준(draft: member 비작성자→404, owner/admin 우회→200).

| # | Pri | Mode | 시나리오 | oracle (정확 단언) | break-to-verify (RED) |
|---|---|---|---|---|---|
| **T1** | P0 | API | 초대 발급 RBAC | `POST /workspaces/{wid}/invites`: member→**403**, viewer→**403**, owner/admin→**201**(body inviteUrl,code) | `invite_router.py:37` `require_admin`→`require_viewer` ⇒ member 201 |
| **T2** | P0 | API | 초대 수락 | `POST /invites/{code}/accept`(B)→**200/201**, body `role=="member"`, `workspaceId==wid`; 이후 B `GET /workspaces/{wid}`→200 | `accept_invite` role 강제 `"admin"` ⇒ role mismatch |
| **T3** | P0 | API | visibility 필터 | member `GET /workspaces/{wid}/projects`→public만(draft·private 부재); `GET /projects/{draftId}`(member 비작성자)→**404**; `{privateId}`→**404** | `repository.py:_apply_visibility_filter` `or_(...)`→`return stmt` ⇒ member가 draft/private 봄 |
| **T4** | P0 | API | cross-tenant I-9 | member `GET /workspaces/{ownerPersonalWid}/projects`→**403**; `GET /workspaces/{wid}/projects/{foreignId}`(타 ws id)→**404**(admin도 우회 불가) | `repository.find_by_id` 의 `workspace_id==` 술어 제거 ⇒ 타 ws id 해석됨 |
| **T5** | P0 | API | RAG private 누수 | owner가 private 프로젝트에 "MAGENTA비밀" chunk + public "CYAN" 시드; member `POST /rag/ask`(project_id=null) SSE: answer에 "MAGENTA" 없음, citation에 privateChunk source_id 없음, `done.sourceCount`=public만 | `embeddings` vector_search visibility WHERE 제거(`test_vector_search_visibility.py` seam) ⇒ MAGENTA 노출 |
| **T6** | P0 | API | revocation(캐시 무효화) | owner `DELETE /members/{bId}` 후 같은 테스트 내 B `GET /workspaces/{wid}/projects`→**403**(60s 대기 없이); ws가 B `GET /workspaces` 목록서 사라짐 | `invite_service.remove_member`의 `invalidate_member_cache` 호출 삭제 ⇒ 60s까지 접근 유지(BUG-RBAC-CACHE-STALE) |
| **T7** | P1 | API | RBAC mutate 경계 | `PATCH /members/{id}`(member)→**403**; `DELETE`(member)→**403**; B=admin: `DELETE`→**204** but `PATCH`(role 변경)→**403**(require_owner) | `member_router.py:35` `require_owner`→`require_member` ⇒ member role 변경 성공 |
| **T8** | P1 | API | admin bypass 대칭 | owner가 B→admin `PATCH` 후 B `GET /projects/{draftId}`·`{privateId}`→**200**; B RAG answer가 "MAGENTA" 포함; 같은 테스트서 즉시 반영 | `update_member_role`의 `invalidate_member_cache` 제거 ⇒ stale role로 private 404 |
| **T9** | P1 | API | note(chunk有) promote→팀 RAG 검색 (QA-0617-A fixed) | owner 개인 노트 임베딩 완료 후 팀 promote→**202**; `GET /notes/{newId}/embedding-status` 폴링 `completed`+`chunkCount>=1`; 팀 RAG가 노트 내용 반환 | `notes/service.py:537-542` `session_factory=session_factory` 제거 ⇒ status "failed", chunkCount 0 |
| **T10** | P1 | API | I-19 personal 초대 금지 | owner `POST /workspaces/{personalWid}/invites`→**403**(PersonalWorkspaceProtected); 메시지에 리터럴 `을(를)` 없음(QA-0617-E 가드) | `invite_service.create_invite`의 `type=='personal'` 가드 제거 ⇒ 201 |
| **T11** | P2엣지 | API | 동시 invite-accept (QA-0617-D) | B가 같은 code 동시 2건 accept: 결과 {201,409}, **절대 500 아님**, 최종 membership=1 | `repository.add_member`를 plain `session.add`+flush로 되돌림(ON CONFLICT 제거) ⇒ 한쪽 500 |
| **T12** | P2엣지 | API | 0-chunk note promote 분기 | plain_text 없는 노트 promote→**400**(NotePromoteNotEmbeddedError); plain_text 있고 chunk 0→**202**+최종 completed(regenerate) | `service.promote`의 `if not source.plain_text` 가드 제거 ⇒ 빈 노트 202 후 silent fail |
| **T13** | P1 | UI | ws 전환(BUG-WS-SWITCH 가드) | B(≥2 ws) `getByTestId("workspace-switcher")` 클릭→2번째 ws 선택; active-ws 표시/URL 변경; 전환 중 console.error **0** | switcher `onClick` no-op stub ⇒ ws 불변 |
| **T14** | P2 | UI | member 프로젝트 목록 public만 | B=member `/projects`: public 카드 보임, draft·private 제목 DOM 부재; console.error 0 | T3과 동일 BE break ⇒ draft/private 카드 렌더 |

### file:line 앵커 (break-to-verify)
- visibility filter: `backend/src/projects/repository.py:72-114`(`_apply_visibility_filter`) · I-9 anchor `:23-32`(`find_by_id`)
- RAG visibility: `backend/src/rag/pipeline_service.py:35-95` + `embeddings` vector_search(seam `backend/tests/embeddings/test_vector_search_visibility.py`)
- RBAC: `backend/src/auth/rbac.py:99-112`(ROLE_LEVEL); 캐시 무효화 `backend/src/workspaces/invite_service.py:251-253,277-280`
- 초대 RBAC: `backend/src/workspaces/invite_router.py:37`(require_admin), accept `:84`(public)
- 멤버 RBAC: `backend/src/workspaces/member_router.py:35`(require_owner role-change), `:51`(require_admin remove)
- promote fix: `backend/src/notes/service.py:537-542`; 400-guard `:279-280`
- 동시 accept: `backend/src/workspaces/repository.py:88-103`(ON CONFLICT)

## 부록 B — 현재 인프라 사실 (Implementer 참고)
- specs: `frontend/e2e/tests/*.spec.ts`; config `frontend/playwright.config.ts`(fullyParallel, chromium `--disable-web-security`, webServer :3003); auth `frontend/e2e/auth.setup.ts`(단일 `user.json`).
- 가까운 선례: `qa-sentinel-p1-token.spec.ts`(토큰 직접 API), `workspace-switch.spec.ts`(2-ws 시드 + onClick), `settings-audit.spec.ts`(role 분기 — 단일 계정이라 한쪽 항상 skip = 구조적 미커버), `invite-accept-happy-path.spec.ts`(E2E_RUN_INVITE 게이트 + manual code punt).
- fragile selector: workspace-switcher 메뉴(text-based), member-list(testid 0), invite-manager(testid 0, 한글 텍스트 버튼), visibility-badge(aria-label만), project-card(href/text), citation-badge(`aria-label="출처 N"`).
- 로컬 게이트: `pnpm e2e tests/<spec>` (dev :3003 자동 기동, `.env.local` 자격). 팀 spec은 `E2E_RUN_TEAM=true` 신설 권장.

---
