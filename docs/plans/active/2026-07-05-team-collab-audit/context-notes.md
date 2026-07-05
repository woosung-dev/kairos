# 팀 협업 전수 점검 스프린트 — 컨텍스트 노트

> 작업 중 내린 결정과 근거. 계속 append. 2026-07-05 시작.

## 사용자 결정 (플랜 승인 시 확정)
1. **초대 승인 단계**: 현행 즉시수락 유지. approval 은 Stage 2 제안으로만. — 사용자가 "초대 승인" 언급했으나 현행 스펙 유지 선택.
2. **워크스페이스 삭제**: 이번에 구현 (에이전트 권고는 Stage 2 였으나 사용자가 구현 선택).
3. **성능**: 6건 전부 (코어 4 + 조건부 2 권고였으나 전체 선택).

## 조사에서 확정된 사실 (재조사 불필요)
- 역할 변경 권한: 코드 owner-only (`member_router.py:35` require_owner). CONTEXT.md §6·W-3 의 "admin+" 가 틀린 것.
- `add_member(email)` (`workspaces/service.py:121-161`): 3개 라우터 어디에서도 미호출 — dead code 확정.
- `default_project_visibility`: invite 에 저장만 (`invite_service.py:71`), accept 에서 미사용, FE create-project-dialog 에 visibility 필드 없음.
- DB 전체에 ondelete=CASCADE 없음 → ws 삭제는 앱 레벨 cascade 필수.
- 성능 백로그 실측: PERF-5(sse-starlette 2.x 자동 cancel — stale), PERF-9(inbox N+1 반증 — 실제는 2쿼리), tiptap(라우트 청크 분리로 무해), PARALLEL-API(wid persist 로 대부분 해소). **신규 발견**: RAG SSE 스트리밍 중 커넥션 점유(rag/service.py 검색 후 commit 없이 ~10s 스트리밍), 멤버 목록 N+1(invite_service.py:222-236, header.tsx 가 전 페이지 호출).
- sse-starlette>=2.0.0, pool_size=5/max_overflow=10 (database.py:23-24).

## 환경 메모
- **backend/.env 에 R2_* 키 없음** (2026-07-05 확인) — 업로드/회의 오디오 로컬 경로 제한 가능. meeting-upload e2e 는 nightly 전용이라 이번 범위 영향 제한적. R2 client 재사용(⑥) 구현은 코드 레벨로 가능하나 로컬 실측정은 불가할 수 있음 → 단위 테스트로 검증.
- CORS_ORIGINS 에 :3000/:3003 둘 다 이미 포함.
- BE 는 --reload 금지 (RBAC/JWT in-process 캐시). 코드 수정 후 명시 재시작.
- QA 데이터 접두사: `QA-2607-`. team.setup 잔재 데이터 삭제 금지 (멱등 시드).

## 구현 설계 결정

### 3b default_project_visibility 연결 — 최소 경로 확정
- `WorkspaceMember.default_project_visibility: str | None = None` 필드 추가 (nullable, alembic additive).
- `invite_service.accept_invite`: `WorkspaceMember(role=..., default_project_visibility=invite.default_project_visibility)` 복사.
- `projects/schemas.py` `CreateProjectRequest.visibility`: `"public"` 기본값 → `None` (미지정 감지 가능하게).
- `projects/router.py create_project`: `visibility=data.visibility or member.default_project_visibility or "public"` — 라우터가 이미 `member: WorkspaceMember` 주입받고 있어 서비스/리포 변경 불필요.

### 🐛 발견: private 프로젝트 creator 락아웃 (신규 버그, PR-2 에서 함께 fix)
- `projects/repository.py:_apply_visibility_filter` — private 은 ProjectMember 만 (creator 분기 없음, 필터·get_project 둘 다).
- `projects/service.py create_project` 는 creator 를 ProjectMember 로 추가하지 않음.
- → member 가 visibility=private 로 프로젝트 생성 시 즉시 자기 프로젝트 404. 현재는 FE 에 create 시 visibility 필드가 없어 잠재 상태지만, 3b seed 연결 시(초대가 private seed 면) 상시 노출됨.
- fix: create 시 visibility=private 면 creator 를 ProjectMember 로 같은 트랜잭션에 자동 추가.

### 3c cascade 대상 테이블 (workspace_id FK 전수)
embedding_chunks, semantic_caches / feedbacks(nullable — 정책 결정 필요) / meetings, inbox_items, notes, action_items / memory_items, memory_ai_calls, memory_events, memory_query_embedding_cache(ws composite pk) / promotion_audit(source+target 양쪽) / meeting_project_links, project_members, projects / workspace_invites, workspace_members → workspaces. 콘텐츠 간 FK (meeting_project_links→meetings/projects 등) 실사 후 순서 확정.

### 3a 확인
- `add_member` 관련 테스트는 전부 projects 도메인(ProjectMember)용 — workspaces dead code 는 테스트 잔재 없이 제거 가능.

## Phase 4 성능 — 구현 상세 결정
- **① SSE commit**: `rag/service.py` 스트리밍 진입 직전 `embedding_repo.commit()` — red-green 검증 완료 (`tests/rag/test_sse_connection_release.py`: fix 제거 시 checkedout=1 로 fail, 적용 시 0). 기존 `test_gemini_successful_answer_saves_cache` 의 commit 단언 1→2회로 갱신 (의도된 동작 변화).
- **③ AI 싱글턴**: 생성자 identity 를 캐시 키로 사용 — 테스트가 `patch("...genai")`/`patch("...AsyncOpenAI")` 하면 ctor 가 달라져 자동으로 mock client 생성, 해제 시 실 client 복원. 기존 테스트 무수정 통과.
- **⑥ R2**: lifespan close 를 core/lifespan 에 넣었다가 arch 게이트(core→common allowlist, BUG-S28-ARCH-4) fail → main.py 레벨 `_app_lifespan` 래퍼로 이동해 게이트 준수.
- **⑤ pool**: 기본값 유지 + env 설정화만 (DB_POOL_SIZE/DB_MAX_OVERFLOW). ① 이 주 고갈 원인을 제거했고 Neon 한도 미확인 상태 상향은 역효과 위험.
- rag.timing 로그 추가 (embed/search/llm/total ms) — BL-S27e-1 판단 근거용.

## Phase 2 dogfooding 결과 (자동화 보조 스윕, 스크린샷 20장)
- S1 풀 플로우 PASS: ws 생성→초대 UI 생성→비로그인/로그인 초대 페이지→수락→member 목록 즉시 반영→danger zone UI 삭제(204). 스크린샷: scratchpad/dogfood/.
- S3 PASS: private 전환 시 member 목록 제거 + 열린 상세는 /projects 로 조용히 리다이렉트 (존재 은닉 정합).
- S4 PASS: viewer 강등 시 사이드바 빠른 메모/+추가 제거 확인.
- S5 PASS: 무효 초대 화면 정상. S6 PASS: 360px 4탭/danger zone/멤버 목록 라이트·다크 모두 정상 (bottom-nav 존재 — T-UI-1 은 랜딩 한정 재확인).
- console.error: 앱 발 0건. Clerk dev `/v1/environment` PATCH 400 만 반복 (외부 노이즈, 프로브로 확정).
- 로드 시간(dev): dashboard 4.4s / settings 4.9s / projects 2.7s / notes 3.4s.
- **발견→수정**: 초대 role Select 트리거 raw "member" 노출 → 라벨 매핑. DangerZone "을(를)" 리터럴 → 문구 재구성 (QA-0617-E FE 확장).
- **발견→수정**: team.setup 이 매 실행 초대 신규 발급 → 활성 초대 90개 누적. 재사용 로직 추가 + 89개 일괄 비활성화 (일회용 t97 스펙, 실행 후 삭제).
- Neon 이 간헐적으로 느림 (idle 후 첫 쿼리 수 초) — 스윕 재시도 원인이었음. Clerk dev 로그인도 한때 redirect loop (반복 로그인 rate limit 추정) → storageState 재사용(--no-deps)으로 우회.

## codex cross-review 처리 (P1 3 / P2 4)
- **P1-1 cascade 순서/누락 → 부분 수용**: 구체 주장(notes.embedding_chunk_id)은 사실과 다름(notes 에 해당 FK 없음, memory_items 는 이미 chunks 앞에서 삭제). 그러나 취지 수용 — metadata 기반 완전성 테스트 추가 → **즉시 `item_promotion_audit` 누락 적발** → cascade 에 추가 + 시드/단언 보강. 향후 새 도메인이 workspace FK 추가 시 CI 에서 잡힘.
- **P1-2 rollback 미보장 → 반박**: session 은 request-scoped(`get_async_session` async with) — 예외 시 세션 close 로 미커밋 트랜잭션 자동 롤백, commit 은 전체 성공 후 1회뿐이라 부분 삭제 잔존 불가. 명시 rollback 은 불가능 시나리오 방어라 미추가.
- **P1-5 visibility 값 미검증 → 반박**: 유일한 유입 경로인 `CreateInviteRequest.default_project_visibility` 가 `pattern=^(public|draft|private)$` 로 검증. 라우터 폴백 체인은 유효값만 도달.
- **P2-7 focus refetch off 의 권한 표면 stale → 수용**: useMembers/useInvites/useWorkspaces 3개만 `refetchOnWindowFocus: true` opt-in.
- **P2-4 싱글턴 → 부분 반박**: AsyncOpenAI/genai.Client 생성자는 sync — 단일 이벤트 루프에서 check-then-set 사이 await 없어 race 불가 (R2 는 async 라 lock 있음). get_settings 도 lru_cache 라 런타임 키 회전 자체가 불가. env 변경 테스트가 생기면 캐시 클리어 헬퍼 필요 — 현재 해당 테스트 없음.
- **P2-3 RAG 실패 경로 → 기존 정책 확인**: cache 저장 실패 try/except(비치명), onboarding graceful — done 이벤트 차단 없음.
- **P2-6 DangerZone fallback → 소수용**: 삭제 ws 는 명시 필터, personal 은 lazy seed 로 항상 존재, workspaces 목록은 스위처가 항상 로드. 잔여 리스크는 이론적 — 미조치.

## 작업 로그
- 2026-07-05: 브랜치 생성, 플랜 산출물 3종 생성. Phase 0 완료(BE/FE 기동, ready db ok). Phase 1: 핵심 pytest 125 pass, FE vitest 71 pass, BE 전체 622 pass, 팀 e2e 27/27 pass (8.2m).
- 2026-07-05: Phase 3 완료 — 3a dead code 제거+CONTEXT 정정 / 3b visibility 시드 연결(alembic 5933c7261107 적용, creator 락아웃 fix 포함, 테스트 4) / 3c ws 삭제(cascade 20문, 테스트 4 + T19 e2e 3). Phase 4 완료 — 성능 6건 + 측정. Phase 5 완료 — 디자인 fix (에러 상태 2, aria 3, 토큰 드리프트, invite 네트워크 에러 분리, role 라벨, Select 의미론, 뱃지 깜빡임). Phase 2 스윕 6/6. FE build PASS.
