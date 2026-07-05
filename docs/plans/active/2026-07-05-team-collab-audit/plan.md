# Kairos 팀 협업 전수 점검 & 기능 완성 스프린트

## Context

Kairos 는 "팀의 세컨드 브레인" (Capture→Organize→Distill→Express, personal-first PLG)이다. 이번 스프린트의 목적: **여러 인원이 같이 사용하는 팀 워크플로우(워크스페이스 생성→초대→수락→그룹 공동 사용)가 전부 실제로 동작함을 검증하고, 그 과정에서 발견된 기능 갭·디자인 결함·성능 병목을 코드 레벨에서 해결**한다. 배포 작업은 범위 제외. 현재 스펙 밖 아이디어는 Stage 2 제안으로만 기록.

조사 결과(Explore 3 + Plan 2 에이전트, 코드 실측 완료): 팀 협업 백엔드/프론트는 이미 성숙 — RBAC 4역할(`backend/src/auth/rbac.py`), 초대 링크 즉시수락 플로우, visibility 3단계(public/draft/private), 팀 e2e 회귀 T1~T18(`frontend/e2e/tests/team/`) 존재. 갭은 미완성이 아니라 **의도적 미배선 + 문서 드리프트 + 성능 백로그**.

**사용자 결정 (확정)**:
1. 초대 승인 단계 — 현행 즉시수락 유지, approval 은 Stage 2 제안으로만
2. 워크스페이스 삭제 — **이번에 구현**
3. 성능 — **6건 전부** 수행

열린 PR 0개, main clean (5aaa99b). 계정: owner=d@e.com, member=a@e.com (Clerk dev). DB=Neon 외부 공유.

---

## Phase 0 — 환경 기동 & 베이스라인 (기반)

1. 작업 브랜치 생성 (예: `sprint/team-collab-audit`)
2. BE: `uv run --directory backend uvicorn src.main:app --host 127.0.0.1 --port 8000` — **`--reload` 금지** (RBAC/JWT in-process 캐시). 코드 수정 후엔 명시적 재시작.
3. FE: `pnpm --dir frontend dev -p 3003` (수동 도그푸딩 브라우저는 :3000 고정 습관 있음 — 이번엔 :3003 로 통일)
4. `backend/.env` CORS_ORIGINS 에 `http://localhost:3003` 포함 확인
5. d@e.com / a@e.com 로그인 가능 여부 + 잔재 QA 데이터 상태 확인 (삭제 금지 — team.setup 이 멱등 시드)

**성공 기준**: /health 200, FE 렌더, 두 계정 로그인 OK.

## Phase 1 — 자동화 회귀 베이스라인 (코드 변경 전)

1. BE: `uv run --directory backend pytest tests/workspaces tests/auth tests/projects -q` → 이후 전체 (CI 와 동일 ignore 옵션)
2. FE 단위: `pnpm --dir frontend test`
3. 팀 e2e: `E2E_RUN_TEAM=true E2E_API_URL=http://localhost:8000 QA_LOCAL_OWNER_EMAIL=d@e.com QA_LOCAL_OWNER_PASSWORD=… QA_LOCAL_MEMBER_EMAIL=a@e.com QA_LOCAL_MEMBER_PASSWORD=… pnpm --dir frontend exec playwright test --project=team-setup --project=team --workers=1`

**성공 기준**: 전부 green (베이스라인 확보 후에만 코드 변경). 실패는 Phase 6 fix 큐로.

## Phase 2 — 수동 멀티유저 dogfooding (Playwright MCP, owner/member 2-컨텍스트)

e2e 가 못 잡는 것만 수동 검증 (storageState `frontend/e2e/.auth/owner.json`/`member.json` 재사용):

1. 풀 워크프로세스: owner ws 생성 → 초대 링크 생성(역할/만료 UI) → member `/invite/{code}` 진입 → 수락 → member 화면 즉시 반영 여부, 전환 UX
2. 동시 편집 체감: owner 콘텐츠 생성 → member 반영 지연 / 역방향
3. visibility 전환 실시간성: public→private 전환 시 member 화면에서 사라짐 + 열려 있던 상세의 403 화면 품질
4. role 강등 실시간성: member→viewer 시 편집 UI 숨김, 캐시 60s 구간 관찰(기록만)
5. 로딩/에러/빈 상태: 만료 초대 문구, 멤버 0명, RAG 스트리밍 UI
6. 반응형: 360px 에서 설정 4탭·`/invite/[code]`(모바일 메신저 공유 가능성 높음)
7. RAG 팀 컨텍스트: member 가 owner 의 public 콘텐츠 질문 → 인용 UX (private 미인용은 T5 커버)
8. 주요 페이지 첫 로드 시간 기록

버그는 즉시 수정하지 않고 Phase 6 큐에 적재 (흐름 중단 방지). QA 생성 데이터는 `QA-2607-` 접두사.

## Phase 3 — 기능 갭 구현

### 3a. 정리 (PR-1, 무위험)
- **dead code 제거**: `backend/src/workspaces/service.py:121-161` `add_member(email)` — 라우터 미배선 확정. 관련 단위 테스트 동반 삭제. (초대 링크가 유일 canonical 가입 경로 + memory `feedback_simplicity_first_dormant_code` 부합)
- **문서 드리프트 정정**: `backend/src/workspaces/CONTEXT.md` §6·W-3 — 역할변경 "admin+" → "owner-only" (코드 `member_router.py:35` require_owner·ADR-025·FE 3자 일치)
- gap log: 초대 approval 단계 부재 = 의도적 스펙, Stage 2 후보 기록

### 3b. `default_project_visibility` 연결 (PR-2, 유일 스키마 변경)
현재: `WorkspaceInvite.default_project_visibility` 저장만 되고 미적용 (`invite_service.py:71`), FE `create-project-dialog.tsx` 에 visibility 필드 없음 → 신규 프로젝트 전부 "public".
1. alembic: `workspace_members.default_project_visibility` nullable 컬럼 추가 (additive, 롤백 안전)
2. `invite_service.accept_invite`(159-218): invite → member 로 복사 1줄
3. `projects/service.py` create(~64행): 호출자 visibility 미지정 시 member seed 적용
4. 테스트: accept 후 seed 검증 + create 시 적용 각 1케이스
5. `workspaces/CONTEXT.md` W-5 를 실제 메커니즘으로 갱신 (Atomic Update)

### 3c. 워크스페이스 삭제 구현 (PR-3, 사용자 결정) ⚠️ 파괴적
- **BE**: `DELETE /api/v1/workspaces/{workspace_id}` — `require_owner` + `type=='personal'` 차단(lazy seed 무결성, I-19) + cross-tenant 404
- **cascade**: DB 에 ondelete CASCADE 없음 → 앱 레벨 단일 트랜잭션. 삭제 순서(구현 시 alembic 모델에서 FK 의존 그래프 재검증): embeddings 2테이블 → feedback(workspace nullable — SET NULL vs 삭제 실사) / inbox / actions / notes / meetings / memory / audit(ItemPromotionAudit 포함 여부 실사) → project_members → projects → workspace_invites → workspace_members → workspace
- R2 객체는 orphan 으로 두고 기존 `r2-cleanup.yml` 위임 (트랜잭션에 외부 IO 금지)
- 삭제 후 전 멤버 `invalidate_member_cache()` 호출
- **FE**: 설정 > 일반 탭에 위험 구역(danger zone) — 워크스페이스 이름 재입력 확인 다이얼로그(DESIGN.md 준수), 삭제 성공 시 personal ws 로 전환 + `kairos-workspace` localStorage 정리. 신규 UI 에 data-testid (e2e selector atomic update 규칙)
- **테스트**: pytest — owner only(403 매트릭스), personal 차단, cascade 후 잔재 0 검증, cross-tenant 404, 동시 삭제 race. 신규 API → schemathesis contract + Playwright smoke (검증 증거 표준)
- **문서**: ADR-025 역할표와 코드 정합 회복 — `workspaces/CONTEXT.md` §6 에 DELETE 추가

## Phase 4 — 성능 6건 + 측정 하네스 (PR-4)

측정 먼저, 수정 다음, 재측정으로 마감. 하네스: 동시 SSE 부하 스크립트(기존 `backend/scripts/sprint24_wave2_perf_spike.py` 패턴 재사용) + `engine.pool.checkedout()` 로깅 + RAG stage 타이밍 로그(embed/search/LLM 구간, ~10줄).

| # | 항목 | 파일 | 접근 | 측정 |
|---|---|---|---|---|
| ① | RAG SSE 스트리밍 전 commit — **동시사용 최대 병목** (스트리밍 ~10s 내내 커넥션 점유, pool 15 → 동시 15명이면 전면 블로킹) | `backend/src/rag/service.py` (~177행 스트리밍 진입 전 commit) | ~5줄, graceful degrade 분기(183행) rollback 경로 확인 | 동시 SSE 10~20개: 스트리밍 중 pool 점유 ≈ 0 |
| ② | 멤버 목록 N+1 (`list_members` 멤버마다 find_by_id — `header.tsx` 전 페이지 호출) | `workspaces/invite_service.py:222-236` + `repository.py` | User JOIN 또는 IN 배치 1쿼리, 반환 shape 유지 | 쿼리 수 1+N→1~2, 응답시간 |
| ③ | AI client 모듈 싱글턴 (요청마다 AsyncOpenAI+genai.Client 생성) | `embeddings/service.py`, `services/ai_processing.py`, `services/transcription.py`, `memory/service.py` | 모듈 lazy 싱글턴, 테스트 monkeypatch 진입점 유지 | /rag/ask first-token 20회 전/후 |
| ④ | refetchOnWindowFocus 전역 false (탭 전환마다 7개 쿼리 재발화 × 인원수) | `frontend/src/lib/query-client.tsx` | 전역 false, meeting polling 은 refetchInterval 별도라 무영향. 설정 페이지 members/invites 만 opt-in 검토 | refocus 시 요청 수 7+→0 |
| ⑤ | pool 상향 — ① 적용 후 재측정으로만 결정 | `common/database.py:23-24` (pool 5+10) | **Neon max_connections 한도 먼저 확인** (필요 시 insane-search/WebSearch) | pool timeout 발생 여부 |
| ⑥ | R2 client 재사용 (메서드마다 client 재생성 + 라우터에서 인스턴스화) | `common/r2.py`, `upload/router.py:102` | AsyncExitStack 보유 패턴 + lifespan shutdown close | presign 응답시간 전/후 |

**백로그 정리 동반** (측정 근거 첨부): PERF-5(sse-starlette 2.x 자동 cancel — stale), PERF-9(inbox N+1 반증 — 실 N+1은 멤버 목록으로 재등재), tiptap dynamic(라우트 청크 분리 확인 후 종결), BL-NEW-BE-PERF-PARALLEL-API(waterfall 실측 1회로 종결) → `docs/REFACTORING-BACKLOG.md` 갱신.

## Phase 5 — 디자인 fix (PR-5)

코드 리딩으로 이미 확인된 결함 + 스크린샷 검증(360/768/1280px × 라이트/다크). ui-ux-pro-max·design-review 스킬 + DESIGN.md 기준:

1. **에러 상태 미처리**: `member-list.tsx`(useMembers 실패 시 침묵), `invite-manager.tsx`(useInvites 동일) — 에러 UI 추가
2. **초대 페이지 네트워크 에러 오표시**: `app/invite/[code]/page.tsx` — 네트워크 실패가 "초대를 사용할 수 없습니다"로 보임 (팀 온보딩 깔때기 직결). 에러/무효 분기 분리 + 재시도
3. **a11y**: icon-only 버튼 aria-label 3건 (member-list 157행, invite-manager 289·301행)
4. **색 토큰 드리프트**: `text-red-400`/`text-green-400` 하드코딩 (member-list 194, invite-manager 296·304, invite page 133·143) → semantic 토큰, 라이트 모드 대비 확인
5. **폰트 토큰 우회**: settings/page.tsx·member-list 인라인 폰트 스택 → `var(--font-display)`/`var(--font-mono)`
6. **role raw 노출**: invite-manager 287행 `{invite.role}` 소문자 + invite 페이지 "{role} 역할로 참여" → 라벨 매핑
7. **소소한 것**: settings 멤버 수 뱃지 로딩 중 `0` 깜빡임, WorkspaceSwitcher 생성 실패 인라인 에러 유무 확인, 360px 4탭 overflow 실측
8. invite-manager 역할 선택 DropdownMenu → radio 의미론 (명세 "Two-Stack Radio" 주석과 불일치) — diff 작으면 수정, 크면 Stage 2

## Phase 6 — fix 루프 & 마감

- Phase 1~5 발견 버그: 재현 테스트 먼저(red) → 최소 수정 → green → 도메인 국소 회귀 → 큐 적재. 전부 처리 후 **전체 회귀 1회** (pytest 전체 → 팀 e2e T1~T18 → 변경 영향 수동 spot-check)
- codex 스킬로 최종 diff cross-review (프로젝트 관례)
- Stage 2 제안 문서화 + 백로그 갱신

## PR 구성 (semantic 분할, 커밋/푸쉬는 각각 사용자 승인 후)

| PR | 내용 | Atomic Update 문서 |
|---|---|---|
| PR-1 | dead code 제거 + CONTEXT.md 드리프트 정정 + gap log | workspaces/CONTEXT.md |
| PR-2 | default_project_visibility 연결 (alembic+BE+테스트) | workspaces/CONTEXT.md W-5 |
| PR-3 | 워크스페이스 삭제 (BE cascade+FE danger zone+테스트) | workspaces/CONTEXT.md §6 + ADR-025 정합 |
| PR-4 | 성능 6건 + 측정 하네스 + 백로그 stale 정리 | REFACTORING-BACKLOG.md |
| PR-5 | 디자인 fix 묶음 | DESIGN.md 참조 (필요 시) |
| PR-6 | QA 발견 버그 fix (5건 초과 시 도메인별 분할) | 각 canonical doc |

## 검증 (검증 증거 표준 준수)

- BE: pytest 전체 green + alembic upgrade dry-run output (PR-2·3)
- FE: 각 UI 변경 스크린샷 + console.error 0건
- 신규 API (ws 삭제): schemathesis contract + Playwright smoke
- 성능: 각 항목 전/후 수치 표
- 최종: T1~T18 green + 수동 8 시나리오 전부 pass 또는 Stage 2 티켓화

## 리스크

| 리스크 | 완화 |
|---|---|
| Neon 공유 DB 오염 / ws 삭제 cascade 실수 | QA 접두사 ws 만 삭제 테스트, cascade 는 pytest TestContainers 에서 먼저 검증 후 로컬 수동 1회. 단일 트랜잭션 + 실패 시 전체 롤백 |
| `--reload` 실수 | 기동 명령 고정, 수정 후 명시 재시작 |
| d@e.com/a@e.com 계정 문제 | Phase 0 사전 점검. 실패 시 수동 dogfooding 먼저, 계정 복구 병행 |
| AI 키 실호출 비용 | 풀 e2e 는 베이스라인+최종 2회만, 중간은 --grep 부분 실행 |
| pool 상향 역효과 | Neon max_connections 한도 확인 후에만, ① 재측정 우선 |

## Stage 2 제안 (구현하지 않고 기록만)

1. **초대 승인(approval) 단계** — pending 멤버 상태 + owner/admin 승인 큐 (사용자 결정으로 이연)
2. personal→team 승격 마이그레이션 (현재 의도적 lock-in, PLG 전환 퍼널)
3. RBAC 분산 캐시 invalidation (Redis pub/sub — 멀티 인스턴스 role 강등 60s 지연 해소)
4. 초대 이메일 발송 (현재 링크 복사만)
5. Promotion review queue (v1.7 로드맵) + FE 프로젝트 생성 다이얼로그 visibility 셀렉터
6. WorkspaceMember soft delete(BL-S27-1) + AdminAccessAudit(BL-S27-3) + Member.last_active_at(BL-065)
7. hybrid search 병렬화(세션 2개 분리 필요), cursor pagination 5도메인, RAG p95<5s 본격 대응(Sentry perf 연계)
8. 팀 e2e CI 통합 (nightly-e2e.yml + QA secret), T-UI-1 모바일 햄버거 nav

## 요청 도구 활용 매핑

- **Workflow(ultracode)**: Phase 2 시나리오 병렬 검증, Phase 6 버그 adversarial verify
- **context7**: sse-starlette/aioboto3/React Query/Next.js 16 API 확인 시
- **vercel-react-best-practices**: Phase 4-④·5 FE 변경 시 적용
- **ui-ux-pro-max / design-review**: Phase 5
- **codex**: Phase 6 최종 cross-review
- **insane-search / deep-research**: Neon 한도 등 외부 조사 필요 시

## 핵심 파일

- `backend/src/workspaces/{router,service,invite_service,repository,member_router}.py` + `CONTEXT.md`
- `backend/src/rag/service.py`, `backend/src/common/{database,r2}.py`, `backend/src/embeddings/service.py`, `backend/src/services/ai_processing.py`
- `frontend/src/lib/query-client.tsx`, `frontend/src/features/members/components/{member-list,invite-manager}.tsx`, `frontend/src/app/invite/[code]/page.tsx`, `frontend/src/app/(app)/settings/page.tsx`, `frontend/src/features/workspaces/components/WorkspaceSwitcher.tsx`
- `frontend/e2e/tests/team/t1~t18-*.spec.ts`, `frontend/e2e/team.setup.ts`
