# Decisions log — Evaluator 판정 vs 메인 판정

| ID | Evaluator | 메인 최종 | 사유 |
|---|---|---|---|
| G3-020 | (live) | PASS | Ctrl+K 0 은 셀렉터 오류(팔레트에 role=dialog 없음). 스크린샷 U-cmdk-ctrlK 로 열림 확인. 후보 철회 |
| C-005 | (live) | WITHDRAWN | 5adcc865 = W-5 시드 '📋 회의록'. 환각 id 아님 |
| E2-X01 | E2 CONFIRMED P3 | CONFIRMED **P2** | invite/[code]/page.tsx:176 비로그인 CTA 가 '로그인하고 참여' 하나뿐 → 계정 없는 초대자는 반드시 sign-in→회원가입 전환을 거치고 auth-form.tsx:201-205 가 callbackURL 을 버린다. 첫 외부 초대자의 기본 경로라 P2 |
| C-001 | E2 CONFIRMED P2 (정정: ORDER BY 부재 = 삽입 순서) | CONFIRMED P2 | 정정 수용. 착지 ws 는 보장된 순서가 아님 |
| C-006 | E2 CONFIRMED P3 (정정: 노트는 재시도 없음) | CONFIRMED P3 | 정정 수용 |
| C-009 | E2 CONFIRMED P3 (정정: XFF 없으면 socket 주소) | CONFIRMED P3 | 정정 수용. 프로덕션 Cloudflare XFF append 동작은 [가정] |
| C-010 | E2 부분 CONFIRMED P3 (/search 는 Cmd-K 에 붙음) | CONFIRMED P3 (/new 만) | 정정 수용 |
| C-013 | E2 CONFIRMED P3 | CONFIRMED P3 | CSP 는 #194 에서 Report-Only 로 추가 → 프로덕션 미배포 방증 (OPS-2 와 교차) |
| C-028 | E2 CONFIRMED P3 ("45ms = 동시 요청 추정") | CONFIRMED P3 | 메인 재현은 순차 urllib 호출 2회였다(202 즉시 반환이라 간격이 짧음). 순차 반복도 중복 생성 |
| C-018 | E1 CONFIRMED **P0** (live 제안 P1) | CONFIRMED P0 | E1 이 POST 벡터 추가 확인: 숨겨진 회의를 public 프로젝트에 링크 → 전 멤버 열람. 회의 id 는 C-015 sourceId·C-016 meetingId 로 이미 노출 → 체인 성립. 메인이 projects/service.py:310-337 에서 tenant 검증만 있음을 재확인 |
| C-002 | E1 CONFIRMED **P1** | CONFIRMED P1 | FE addMeetingProject 는 PUT(features/projects/api.ts:87-97), BE 는 POST 만(projects/router.py:193) + 호출부 0 → UI 링크 경로 없음. 메인 재확인 |
| C-014/C-015 | E1 CONFIRMED P0 | CONFIRMED P0 (codex 대기) | — |
| C-016/C-017 | E1 CONFIRMED P1 | CONFIRMED P1 (codex 대기) | C-017 추가: 빈 PATCH 로 메타데이터 읽기, status 임의 문자열 저장 |
| C-020 | E1 CONFIRMED P1 [확인 필요] | CONFIRMED P1 [확인 필요] | 제품 결정 필요: 팀 WS 메모를 팀 공유로 볼지. 문서·UI·AI suggested_visibility 는 모두 personal |
| C-003/C-004/C-019/C-022 | E1 CONFIRMED P2 | CONFIRMED P2 | C-003 추가: archived/completed 도 후보 |
| C-008/C-021 | E1 CONFIRMED P3 | CONFIRMED P3 | 상향 누수 없음 확인 |
| E1-N1 | E1 새 발견 P2 | CONFIRMED P2 | 메인 재확인: notes/pipeline_service.py:45-70 embed 가 시작 시점에만 note 존재 확인 → OpenAI 호출 중 삭제되면 청크 삽입. E1 실측 3/3 |
| 부수효과 | E1 이 프로젝트 DELETE 로 semantic_caches 전체 삭제(15:02:44 UTC) | 영향 없음 | 같은 시각 E2 는 캐시 시험 안 함. 로컬 DB 에 초기 QA 의 'QA-TMP note' 고아 청크 3건 잔존(로컬 전용) |
| D-001/D-002 (OPS-1) | E3 MISLEADING impact high | CONFIRMED — 운영 P1(잠재 데이터 유실) | 메인 재확인: scripts/r2_cleanup.py:64-97 LastModified<cutoff 면 DB 참조 없이 삭제, 기본 prefix uploads/(:123-126). TODO.md:109(BL-OCI-5) 안내대로 delete=true 실행 시 30일 넘은 회의 원본 전부 삭제. 현재 실행 이력 0 이라 발생한 피해는 없음 |
| D-038 | E3 STALE impact high | CONFIRMED | Clerk +7일(2026-08-24) 정리 34일 지연. 실행 여부 [확인 필요] |
| OPS-2 | E3 CONFIRMED | CONFIRMED | 프로덕션 BE·FE 모두 #194 이전. BE 405 vs 로컬 401, FE CSP-Report-Only 헤더 부재 (C-013 과 교차) |
| OPS-3 | E3 CONFIRMED | → C-020 에 병합 | 문서 8곳이 personal 서술, 3곳은 workspace 서술 (문서끼리도 모순) |
| D-004/D-005 | E3 MISLEADING (코드만, RAG 호출은 auto-mode 가 차단) | MISLEADING 수용 | 메인 라이브 G1-069/G1-078 에서 '200 + SSE error 이벤트' 형태를 이미 관측 → E3 코드 판정과 일치 |
| 범위 밖 | Nightly Heavy E2E 2026-08-17 이후 40회 전부 실패(마지막 성공 08-01) | 수용 | 메인이 최근 5회 실패 + 원인 BETTER_AUTH_SECRET 누락 로그 확인 |

## codex 교차검증 (P0/P1 7건, codex exec -s read-only, 코드 inline 제공)

| ID | codex | E1 | 메인 최종 | 판정 근거 |
|---|---|---|---|---|
| C-014 | AGREE P0 | P0 | **P0** | 일치 |
| C-015 | INSUFFICIENT P0 (InboxService 미제공) | P0 | **P0** | 메인이 inbox/service.py:59-76 확인 — requester 없이 repo 호출, 필터 없음. E1 라이브: viewer 가 원본 요약 169자 동일 수신 |
| C-018 | AGREE P0 (public 링크 경로는 unproven) | P0 | **P0** | E1 라이브로 POST 경로 입증(숨겨진 회의 → public 프로젝트 링크 201 → member·viewer GET 200). 코드 근거: 회의 가시성 = 링크 0개 통과 또는 접근 가능한 링크 1개 이상이면 통과 |
| C-002 | **DISAGREE P2** (GET /inbox 기본값은 처리 항목도 반환) | P1 | **P1** | codex 는 FE 를 못 봤다: smart-inbox.tsx:47-49 가 isProcessed:false 로만 조회 → UI 에서 사라짐. 링크 UI 없음(addMeetingProject PUT vs BE POST, 호출부 0). 핵심 흐름 차단이라 P1 유지 |
| C-016 | AGREE **P0** | P1 | **P0** | 본 정검의 P0 정의(권한 밖 데이터 노출)에 해당 — private 회의에서 추출된 액션 제목이 viewer 에게 노출. C-015 와 같은 등급으로 맞춤 |
| C-017 | AGREE **P0** | P1 | **P1** | 쓰기 우회는 맞지만 대상 프로젝트 UUID 를 알아야 한다(E1 근거). Gate 0 차단 항목으로는 P0 와 동일 취급 |
| C-020 | AGREE **P0** | P1 [확인 필요] | **P1 [확인 필요]** | 제품 의도 미정. 개인 메모 의도면 P0 로 상향, 팀 공유 의도면 P3(문구). 결정 전까지 Gate 0 차단 |

## 사용자 결정 (2026-09-27) + 구현 판단

| # | 결정 | 구현 | 비고 |
|---|---|---|---|
| U-1 | 보고서는 P0 수정 PR 과 **함께** 푸쉬 (레포 PUBLIC) | 보고서·수정·회귀 테스트를 한 브랜치 `qa/2026-09-26-launch-readiness` 로 묶음 | 수정 없이 결함 목록만 공개되는 창을 없앤다 |
| U-2 | C-020 = **(a) 작성자 전용** (팀 WS 포함) | recall·GET·promote 원본·RAG memory 청크·RAG 캐시 재검증이 `memory_items.user_id = 요청자` 로 판정. admin/owner 우회 없음 (I-24) | 등급 P1 [확인 필요] → **P0 확정** |
| U-3 | 0-16 = 운영자 수동 재설정 runbook 으로 충분 | `docs/operations/runbooks/manual-password-reset.md` + `scripts/auth/reset-password.mjs` | 메일 발송은 Gate 1 (1-3) 그대로 |
| U-4 | **프로젝트 작성자는 role 이 member 여도 자기 프로젝트 visibility 변경 가능** | PATCH 의 visibility 변경 = admin/owner **또는** `project.created_by == 요청자` (P-11). private 전환 시 **작성자 본인이 전환하면** ProjectMember 로 보장 (잠김 방지 · admin 전환 시 자동 추가 안 함, E1-10) | 0-3 원안(admin 만)을 이 결정으로 대체 |
| U-5 | Phase 2 범위 = Gate 0 (`phase2-test-list.md` §0~§5, §6 제외) | — | — |

### 구현 중 메인 판단 (사용자 결정이 아닌 것)

| # | 판단 | 근거 | 상태 |
|---|---|---|---|
| M-1 | promote 로 만든 **사본**은 팀 공유 (`memory_items.is_shared=true`) | (a) 를 그대로 적용하면 "팀으로 올리기" 가 올린 사람에게만 보이는 무의미한 동작이 된다. 원본은 작성자 전용 유지 | ✅ 2026-09-27 사용자 확정: **유지** (Gate 0 인계 인터뷰 Q4) |
| M-2 | 기존 promote 사본 backfill — `memory_events(event_type='promote')` 의 `new_memory_id` 가 가리키는 사본 중 **원본 작성자가 직접 올린 것만** `is_shared=true` (E2-05 반영) | 마이그레이션 `a9c4e2f7b1d0`. 수정 전에는 남의 메모도 올릴 수 있었으므로(E2-02) 그 사본까지 공유로 확정하면 I-24 를 과거 데이터로 우회한다. 이벤트가 없거나 원본이 사라진 사본은 작성자 전용으로 남는다 | `test_launch_readiness_data_migrations.py` (직전 리비전에 행을 심고 head 로 올려 행 단위로 확인 · downgrade 왕복) |
| M-3 | 값이 **실제로 바뀔 때만** visibility/status 권한을 검사 | 편집 다이얼로그가 변경하지 않은 필드도 함께 보낸다. 같은 값 재전송을 403 으로 막으면 제목 수정조차 실패한다 | 테스트 `test_non_creator_member_cannot_change_visibility` · `test_member_cannot_archive_via_patch` (재전송 분기) |
| M-4 | action·inbox **promote** 에도 가시성 게이트 | 숨겨진 원본을 다른 WS 로 복사해 우회하는 경로 차단. codex/E1 보고 범위 밖이지만 같은 규칙 | — |
| M-5 | RAG 캐시: admin 은 소스 삭제 청크(`ec.id IS NULL`)를 위반으로 보지 않고, memory 규칙은 admin 에게도 적용 | 기존 N4 정책(`test_cache_hit_deleted_sources_for_admin`) 보존 + I-24 는 admin 우회가 없다 | — |
| M-6 | 0-17 의 `clerk_id` DROP 은 **보류** | 모델 주석상 레거시 행 식별 유일 단서. 프로덕션에 `clerk_id IS NOT NULL AND auth_user_id IS NULL` 행 수 확인 전 DROP 은 2단계 배포 원칙(migrations.md §6) 위반 | BL-LR-11 로 등재, `[확인 필요]` |
| M-7 | 공유 사본(`is_shared`)의 **재promote 는 원본 작성자만** — 다른 멤버가 다시 올리면 403 | 결정 (a) "메모는 작성자 전용" 의 보수적 해석. 허용하면 X 가 팀 A 에만 공유한 내용이 Y 를 거쳐 팀 B 로 퍼진다 (E2-02). 사본 소유자(`user_id`)는 promote 한 사람이라 사본 소유권으로는 막을 수 없어 `source.user_id` 를 본다 | ✅ 2026-09-27 사용자 확정: **유지** (Q5). 팀→팀 promote 정책 전반은 Gate 1 BL 로 (`REFACTORING-BACKLOG.md` BL-LR-17) |

## Gate 0 수정 검증 — codex 교차검증 (P0 SQL, 2026-09-27)

codex 는 행 형태 16종 × 역할 4종 표에서 **회의·메모·노트 규칙이 모두 기대와 일치**한다고 판정했고, 아래 5건 때문에 DISAGREE 를 냈다. 메인이 코드로 확인했다.

| # | codex 지적 | 메인 판정 | 근거 |
|---|---|---|---|
| X-1 | memory 청크의 `project_id` 가 안 보이는 private 프로젝트면 작성자에게도 숨겨진다 | REJECTED (도달 불가) | memory 청크는 `memory/pipeline_service.py:59-67 save_chunk` 에서 project_id 를 넘기지 않아 항상 NULL. 방향도 과잉 차단(누수 아님) |
| X-2 | 추출 액션이 자기 `project_id` 규칙 때문에 회의보다 좁게 보일 수 있다 → I-23 "결과가 같다" 와 불일치 | 수용 — **문구 정정** | 액션은 A-8(자기 프로젝트) AND A-9(원본 회의). 의도된 동작이라 코드는 유지하고 I-23 을 "원본보다 넓게 보이지 않는다" 로 고침 (CONTEXT-MAP) |
| X-3 | 프로젝트 범위 RAG 가 회의 청크를 `chunk.project_id` 로 거른다 | 수용 — 기지 한계 | BL-LR-10 에 이미 등재. 누락이지 누수가 아니다 |
| X-4 | 원본 회의 행이 없는 회의 청크는 링크 0개로 보여 통과한다 | REJECTED (현재 도달 불가) → Gate 1 메모 | 회의 삭제 API 가 없다 (BL-UX-4). WS 삭제는 청크까지 삭제. 회의 삭제(체크리스트 1-7) 구현 시 청크 동시 삭제가 필수 |
| X-5 | 출처 id 가 빈 캐시는 admin/owner 가 재검증 없이 히트 | REJECTED (도달 불가 · 기준선 동작) | `rag/service.py:156-168` 는 검색 결과 0건이면 캐시 저장 전에 반환한다. 빈 sources 캐시는 앱이 만들지 않는다. main 과 같은 동작 |

## Gate 0 수정 검증 — Evaluator 3종 판정 처리 (2026-09-27)

Evaluator 는 fresh context 로 주장·증거만 받았다 (E-BE1 가시성 · E-BE2 memory·마이그레이션 · E-FE). 메인이 각 결함을 코드로 다시 확인한 뒤 처리했다.

| # | 등급 | 지적 | 처리 | 근거 |
|---|---|---|---|---|
| E1-01 | P2 | 회의 export 가 프로젝트 게이트 액션을 노출 | **수정** | `find_by_meeting(requester)` · `test_meeting_export_hides_actions_filed_under_hidden_project` |
| E1-02 | P2 | 회의 promote 가 promoter 가 못 보는 액션까지 복제 (사본 `project_id=None` → 대상 WS 전원) | **수정** | `clone_action_items_for_promote` + `apply_fk_project_visibility` · `test_meeting_promote_does_not_clone_actions_promoter_cannot_see` |
| E1-03 · E2-04 | P3 | 캐시 재검사 `:req_role` NULL 이면 fail-open (`NOT IN` + NULL) — 두 Evaluator 가 독립으로 같은 지적 | **수정** | `COALESCE(:req_role, '')` · `test_cache_revalidation_treats_null_role_as_non_admin` |
| E1-05 | P3 | 액션 create/PATCH 가 숨은 회의·프로젝트 id 를 받는다 (존재 오라클 + export 에 끼워 넣기) | **수정** | `_verify_target_visibility` · `test_action_create_and_patch_into_hidden_meeting_or_project_is_404` |
| E1-10 | P3 | admin 이 private 전환해도 작성자 자동 추가 → orphan ProjectMember | **수정** (작성자 본인 전환 때만) | `test_private_switch_adds_creator_only_when_creator_switches` |
| E1-06 | P2 | private 프로젝트 삭제 → 그 프로젝트에만 연결된 회의 전체 공개 | **이연** `[확인 필요]` | 제품 규칙 결정 → BL-LR-12 (권장: 유일 링크면 409) |
| E1-04 · 08 · 09 · 11 | P3 | 잠재 결함 (현재 도달 경로 없음) | 이연 | BL-LR-13 |
| E1-07 | P3 | 숨은 프로젝트의 멤버 목록 200 | 이연 (= C-019, Gate 1) | BL-LR-2 |
| E2-01 · 03 | P2 · P3 | memory promote 대상 WS 검증이 viewer 를 통과 | **수정** | `validate_promote_target` 공용 헬퍼로 교체 (I-25) |
| E2-02 | P3 | 남의 `is_shared` 사본을 다시 promote (작성자 아님) — 정책 질문 | **수정** (M-7) | 403 `MemoryPromoteForbiddenError` · `test_non_author_cannot_repromote_shared_copy` |
| E2-05 | P3 | backfill 이 남이 올린 사본까지 공유로 확정 | **수정** | M-2 갱신 |
| E2-07 | P3 | promote 가 `is_shared=True` 를 세우는지 검사하는 테스트가 없다 | **수정** | `test_memo_promote_marks_copy_shared_and_blocks_target_viewer` |
| E2-06 · 08 | P3 | 대용량 락 · 메모 AI 오류 원문 저장(노출 0) | 이연 | BL-LR-15 |
| E-1 | P2 | callbackURL sanitizer 가 dot-segment 입력을 `//evil` 로 정규화 (BA 서버 검증만 막고 있었다) | **수정** | 정규화 뒤 `/^\/(?![/\\])/` 재검사 · 테스트 4종 추가 |
| E-2 · E-4 | P2 | 회의↔프로젝트 확인 대화상자가 반대 방향을 지킨다 | **수정** | 확인 = ① 비공개 링크뿐인 회의에 공개 프로젝트 연결 ② 마지막 링크 해제 (회의 가시성 = ANY 규칙) |
| E-3 | P3 | viewer 로 강등된 작성자에게 편집 UI | **수정** | `isCreator && role !== "viewer"` |
| E-5 | P3 | Next 16.3 `next dev` 가 AGENTS.md 블록을 고쳐 쓴다 | **수정** | 16.3 블록 그대로 커밋 (`hasCurrentAgentRules` = true) |
| E-6 · E-8 | P3 | 호출자 0 헬퍼 · recall 200자 상한 미가드 | **수정** | `truncateToCodePoints` 삭제 · `RECALL_QUERY_MAX` |
| E-7 · E-9 | P3 | 422 영문 필드명 · WS 전환 role 깜빡임 | 이연 | BL-LR-14 |


## Phase 2 라이브 재테스트에서 새로 찾은 결함 (2026-09-27)

| # | 등급 | 지적 | 처리 | 근거 |
|---|---|---|---|---|
| G3-018 | P3 | 한글 조합 중 Enter(조합 확정용)에 요청이 나간다 — 조합 이벤트를 흉내 낸 keydown(`isComposing=true`)에서 rag/ask 1회 발생(duringComposition=1). 실제 IME 에서는 확정 Enter 와 전송 Enter 가 겹쳐 중복·조기 전송이 된다 `[가정]`. 같은 가드 부재가 `/search` · ⌘K · WS 생성 입력 · 프로젝트 combobox 4곳 | **수정** | `e.nativeEvent.isComposing` 가드 4곳 + `rag-input.test.tsx` · `cmd-k.test.tsx` (가드 제거 mutation 시 둘 다 FAIL). 재빌드 후 Playwright 재검증 PASS. 규칙은 `apps/web/CONTEXT.md` F-13 |
| G2-062 (UI) | — | 완료 토글 새로고침 후 유지 판정 false | **REJECTED (테스트 선택자)** | 같은 제목 액션 2건(93ca2c1b · e4be11d3) 이라 다른 행을 읽었다. BE PATCH 200 + DB status=done 확인 후 두 건 원복 |
| G3-020 | — | Esc 1회로 ⌘K 가 안 닫힘 | **REJECTED (테스트 아티팩트)** | 첫 방문 온보딩 Popover 가 첫 Esc 를 받는다. 툴팁을 본 상태에서는 Esc 1회로 닫힘 |

## 결과 문서 검증 — Evaluator 2라운드 (2026-09-27)

`phase2-results.md` · 체크리스트 완료 표시 · BL-LR 상태를 fresh-context Evaluator 가 증거 파일·코드와 대조했다.

- **1라운드 지적 10건 → 전부 수정**. 주요 항목:
  - T-25 는 추론만 적혀 있었다 → 실제로 실행했다.
  - T-05/T-07 UI, viewer·member RAG, T-18c UI 가 빠져 있었다 → 보강해서 실행했다. 작성자 대조군 memorySrc=1 도 확인했다.
  - "nightly e2e 는 secret 등록만 하면 된다"는 전제가 틀렸다. `nightly-e2e.yml` 이 Better Auth 이전 구성이다 → 0-18 과 BL-LR-15 를 정정했다.
  - lifecycle 14일은 근거가 없었다. eslint 건수를 고쳤다. 0-1 에 e2e spec 이 없다는 점을 BL-LR-14 에 적었다.
  - FE mutation 증거를 추가했다.
- **2라운드**: 1라운드 10건은 전부 RESOLVED 다. 수정하면서 새로 생긴 경미한 오류 4건도 고쳤다: T-38 분류, 임시 WS 수, 스크린샷 수, BL-LR-15 등급.
