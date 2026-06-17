<!-- 다음 세션용 프롬프트 — 멀티 에이전트 QA 전수 검증 (팀/멀티계정, ultracode) -->

# 신규 세션 프롬프트 — 멀티 에이전트 QA 전수 검증

> 아래 블록을 새 세션에 그대로 붙여넣으세요. ultracode 모드 전제.

---

ultracode 모드로 진행한다. **목표: 지금까지 계획·구현된 Kairos의 모든 기능이 "팀 단위(멀티 유저)"로 실제 작동하는지 라이브 전수 검증하고, 결함을 우리 워크플로우대로 고친다.** 단순 코드 리뷰가 아니라 **여러 페르소나 에이전트가 각자 실제로 써보고 테스트**하는 Multi-Agent QA다. Generator(페르소나 검사) → Evaluator(opus+codex 교차검증) 패턴을 끝까지 적용한다.

## 0. Context Sync (먼저 순서대로 읽기)
1. `CONTEXT-MAP.md`(헌법) → `AGENTS.md` → `DESIGN.md` → `.ai/templates/workflow.md`(Plan→Code→Test + 위험도 Lite/Standard/Heavy)
2. `docs/requirements/prd.md`(검증 대상 기능 전체 — CODE: Capture/Organize/Distill/Express/Promote + 2축 로드맵)
3. memory: `project_sprint29_done`(직전 리팩토링·라이브 스모크 함정) · `project_multi_agent_qa`(Sentinel/Curious/Casual 선례) · `project_sprint28_fullsweep_qa_done`(18라우트+2계정 선례) · `feedback_asyncpg_greenlet_precheck`
4. `docs/REFACTORING-BACKLOG.md` + `docs/dev-log/qa/2026-06-01-deep-review/report.md`(잔여 52건·기존 findings)
5. **git 상태 먼저 확인**: PR #124(코드 R1/R3/R4)·#125(로드맵) 머지 여부 → 머지됐으면 `main`, 아니면 `sprint-29/refactor-p1-2026-06` 기준으로 검증(머지 안 된 코드 fix가 누락되지 않게).

## 1. 라이브 스택 + 멀티계정 셋업
- BE: `uv run --directory backend uvicorn src.main:app --host 127.0.0.1 --port 8000`(백그라운드) / FE: `pnpm --dir frontend dev`(:3000, **포트 3000 고정**) / Neon. health 200 + :3000 응답 폴링 후 진행. dep 변경 있었으면 dev 서버 **재시작**.
- **테스트 계정**: `frontend/.env.local`의 `QA_LOCAL_*` 전수 확인(`rg QA_LOCAL .env.local`). 현재 최소 OWNER(d@e.com)+MEMBER(a@e.com) 2계정. **각 계정을 role(owner/admin/member/viewer)에 매핑**하고, full RBAC/5-페르소나 커버에 계정이 부족하면 **"추가 Clerk dev 계정 발급 필요"를 사용자 액션으로 플래그**(빈번한 질문 대신 TODO에 기록).
- 인증: Playwright `e2e/auth.setup.ts` storageState(`E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000 E2E_USER_EMAIL/PASSWORD=QA_LOCAL_*`). **계정별 storageState** 생성. CI 결제 차단 시 로컬 대체검증.

## 2. 멀티 에이전트 페르소나 패널 (Generator — Workflow 병렬)
각 페르소나는 **라이브(Playwright MCP/스크린샷)로 독립 검사** + 발견을 구조화 산출(라우트/계정/role/심각도 P0~P3/스크린샷):
- **신규유저(new)**: 가입→온보딩 0→4단계, 첫 진입, empty states, 첫 워크스페이스 lazy seed.
- **일반사용자(casual)**: 핵심 happy path — 회의 업로드→요약/액션/날짜정규화, 노트 작성, inbox 분류, RAG 질문(마크다운+citation), 음성메모.
- **관심사용자(power)**: 깊은 기능 — promotion(개인→팀 복제), project visibility(public/draft/private), RAG 필터/source, export(MD/JSON), 워크스페이스 전환.
- **QA(엣지·보안)**: **cross-tenant 격리(I-9)** · **RBAC 매트릭스(owner/admin/member/viewer 권한·가시성 경계)** · 입력 검증·에러 경로·중복/동시성·실패 후 retry.
- **디자인(design)**: DESIGN.md 정합 · 라이트/다크 토큰 대비(WCAG AA) · features emoji 0(Sprint 29 후 회귀 확인) · 반응형 · **console.error 0** · AI slop.

## 3. 팀/멀티계정 핵심 시나리오 (사용자 최우선 요구)
**여러 .env 계정을 하나씩 로그인**해 팀 흐름을 실제로 관통한다:
- 계정 A(owner) 초대 발급 → 계정 B(member) 수락 → **role별 가시성/액션 차이** 확인.
- 계정 A의 draft/private 프로젝트를 계정 B가 **접근 불가(403/404)** 확인 = cross-tenant/visibility 격리.
- promotion(개인 워크스페이스 → 팀) 복제 + audit + 권한.
- 각 계정에서 핵심 기능(capture/RAG/inbox/notes/memory)이 **계정별로 정상 작동**하는지 1:1 체크.

## 4. 기능 커버리지 매트릭스
PRD 전 기능 × (계정/role) → **PASS / FAIL / N/A** 표. CODE 5단계 + 도메인(meetings·notes·inbox·memory·projects·rag·workspaces·onboarding·feedback) 누락 없이.

## 5. Evaluator (검증 — false-positive 제거)
페르소나 findings를 **독립 evaluator(opus + codex) 교차**로 adversarial 재현. **Sprint 29 함정 필수 반영**: ① 사용자 데이터(프로젝트명 emoji 등)를 UI 결함으로 오인 금지 ② Clerk SDK 외부 `clerk.accounts.dev` 400 등 외부 노이즈 필터 ③ 라이브로 재현 안 되면 finding 폐기. 확정 findings만 triage(P0~P3).

## 6. Test → Fix → Ship (workflow.md 준수)
- 위험도 분류(Lite/Standard/Heavy). P0/P1 fix는 **TDD + 실DB 회귀 테스트**(Sprint 29 패턴, asyncpg greenlet 충돌은 pre-check/ON CONFLICT). 
- 검증 증거 표준: FE 스크린샷+`console.error` 0 / BE `pytest`+alembic dry-run. Heavy는 `/codex`+agy 교차.
- **Git Safety**: 커밋·푸쉬·머지·배포는 각각 사용자 승인 후. fix는 클러스터별 commit 단일 PR. 최종 `/codex review`.

## 7. 산출물
QA 리포트(커버리지 매트릭스 + 확정 findings P0~P3 + 스크린샷) → fix PR → 종결 BL 등재 → 메모리 closeout. 검증 안 끝난 항목·추가 계정 필요는 `docs/TODO.md`.

## 함정 체크(Sprint 29 학습)
:3000 고정 · dep 변경 시 dev 재시작 · storageState 재인증 · 사용자데이터/외부노이즈 false-positive 필터 · feature-scoped 정적체크 한계(라이브 필수) · 전체 pytest 간헐 테스트격리 flake(재실행 확인).

---
