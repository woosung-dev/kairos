<!-- 2026-06-17 멀티 에이전트 팀 단위 라이브 전수 QA 리포트 -->

# Kairos 멀티 에이전트 팀 단위 라이브 QA — 2026-06-17

> 목표: 계획·구현된 전 기능이 **팀 단위(멀티 유저)** 로 실제 작동하는지 라이브 전수 검증 + 확정 결함 수정.
> 방법: Generator(7 페르소나 에이전트, 코드 근거 체크리스트) → Live Driver(Playwright MCP, 2계정 직접 로그인, API+DB+UI 증거) → Evaluator(opus 인라인 6문항 게이트 + Codex 교차) → Implementer(별도 서브에이전트 TDD).
> 기준: main `0192260`(PR #124 머지본). fix 브랜치 `qa/2026-06-17-team-qa-fixes`.

## 1. 요약

- **라이브 스택**: FE `:3000` → BE `:8000` → 공유 Neon. AI 키(GEMINI/OPENAI/R2/CLERK) 모두 활성 → 실 AI 파이프라인 동작.
- **계정**: owner `d@e.com`(BE `caf5c27b…`) / member `a@e.com`(BE `15676bf0…`). 4 role 은 owner가 B를 member↔admin↔viewer 변경으로 전수.
- **팀/멀티유저 핵심 = 전부 PASS** (초대→수락→role별 가시성/액션, cross-tenant I-9, visibility, RAG 누수 격리, admin bypass, RBAC 캐시 즉시성, revocation, ws 전환).
- **확정 결함 3건 + P3 2건**. P1 1건은 **이번 세션 수정 + TDD 회귀 + Codex review PASS**.
- **검증**: 전체 pytest **551 passed / 1 skipped**(회귀 +1). FE 라우트 7종 console.error 0. emoji→lucide 회귀 0.

## 2. 확정 Findings

| ID | 심각도 | 영역 | 요약 | 상태 |
|---|---|---|---|---|
| **QA-0617-A** | **P1** | notes/promote | 0-chunk 노트(임베딩 완료 전/실패 노트) 승격 시 BG 재임베딩이 RuntimeError로 항상 실패 → 승격 노트가 팀 RAG/검색에서 영구 누락 (silent, 202 성공 반환) | **✅ FIXED (이 PR)** |
| **QA-0617-C** | P2 | notes/embedding-status | `count_note_chunks` 가 승격 노트의 복제 chunk를 0으로 오집계 → embedding-status `chunkCount:0` (실제 chunk 존재·RAG 검색 정상) | BL 등재 |
| **QA-0617-D** | P2 | workspaces/invite | 동시 invite-accept 2건 → 하나가 **500**(IntegrityError 미처리). UNIQUE 제약이 중복 membership은 차단(데이터 안전)하나 graceful 409/idempotent 아님 | BL 등재 |
| **QA-0617-E** | P3 | workspaces(i18n) | `PersonalWorkspaceProtected` 메시지 "초대**을(를)** 수행할 수 없습니다" — 한국어 조사 플레이스홀더 `을(를)` 노출 | BL 등재 |
| **QA-0617-F** | P3 | workspaces/members | 멤버 목록 API 가 `email` 빈 문자열 반환(표시 공백) — seed 데이터 displayName/email 미설정 잔재 | BL 등재 |

> **Evaluator 후속 (stacked PR `qa/2026-06-17-remaining-defects` → `qa/2026-06-17-team-qa-fixes`)**: Implementer(별도 서브에이전트) + 어드버서리얼 재현으로 5건 처리. **A/D/E = 진짜 결함 수정**, **C/F = 코드 버그 반증**(C=probe 타이밍 아티팩트, 실파이프라인 재현 시 count 정상 / F=lazy-seed 유저 실 데이터, 직렬화 경로 정상) — 회귀 가드 테스트만 추가. 상세 = `docs/REFACTORING-BACKLOG.md` BL-QA0617-*.

### QA-0617-A 상세 (P1, FIXED)
- **근본 원인**: `backend/src/notes/service.py` `_bg_regenerate_embed_with_audit`(needs_embed_regenerate 분기)가 `NotePipelineService(...)` 를 **`session_factory` 없이** 생성 → `embed_note_async`(`pipeline_service.py:52`)가 `self.session_factory is None` → `RuntimeError` → except → audit `"failed"`.
- **라이브 증거**: 개인 노트 생성 직후 팀 승격 → embedding-status `{status:"failed", chunkCount:0}`(4회 폴링 안정) + 팀 RAG가 해당 콘텐츠(MAGENTA) **미검색**. 대조군(임베딩 완료 후 승격)은 정상(CYAN 검색됨) → 버그는 **regenerate 분기에만 격리**(meeting/memory promote는 `session_factory()` 직접 사용 → 무영향).
- **기존 테스트가 놓친 이유**: `test_note_promote.py::test_promote_note_chunk_zero_plain_text_schedules_embed` 가 버그 지점인 `embed_note_async` 자체를 noop monkeypatch → RuntimeError 미발화 (deep-review "test가 버그를 mock" 교훈 재발).
- **수정**: 생성자에 `session_factory=session_factory` 전달(meetings 패턴 정합). 1줄.
- **회귀 테스트**: `test_promote_note_chunk_zero_regenerates_embedding_real_path` — `embed_note_async` 미mock, OpenAI seam(`EmbeddingService.generate_embeddings`)만 stub. fix 전 audit "failed"로 실패 → fix 후 "completed"+chunk≥1 통과.
- **Codex review**: PASS(no actionable bugs).

## 3. 커버리지 매트릭스 (PRD 기능 × role → PASS/FAIL/N/A)

`PASS`=라이브 확인 / `FAIL`=결함 / `N/A-def`=이번 세션 미실행(사유) / `STATIC`=코드 정적 확인.

### 팀/멀티테넌시 (최우선)
| 기능 | owner | admin | member | viewer | 근거 |
|---|---|---|---|---|---|
| 초대 발급 | PASS | PASS | **403** | **403** | API 201 / member·viewer 403 |
| 초대 수락 | — | — | PASS | PASS | 200. 동시 2건=QA-0617-D |
| visibility 필터(public/draft/private) | PASS(bypass) | PASS(bypass) | PASS(public만, draft·private 404) | PASS | API+UI |
| cross-tenant 접근(I-9) | PASS | PASS | PASS(403/404) | PASS | personal·other-team·resource mismatch 403 |
| role 변경 | PASS | **403** | **403** | **403** | owner만 |
| 멤버 제거 | PASS | PASS | **403** | **403** | admin+ |
| revocation(제거 후) | — | — | PASS(403+ws 소멸) | PASS | |
| RAG 누수 격리 | PASS(bypass) | PASS(bypass) | PASS(private 답변·citation 제외) | PASS | sourceCount 정확 |
| I-19 personal 초대 금지 | PASS(403) | — | — | — | |
| RBAC 캐시 즉시성 | PASS | PASS | — | — | promote→admin 즉시 반영 |
| 워크스페이스 전환 UI | PASS | — | PASS | — | switcher onClick |

### CODE 파이프라인
| 단계 | 기능 | 결과 | 근거 |
|---|---|---|---|
| Capture | 노트 생성 + 자동저장 | PASS | 201 + 임베딩 completed |
| Capture | 메모리 캡처(text) | PASS | 202 |
| Capture | 회의 업로드(오디오) | N/A-def | 풍부한 음성 샘플 부재(결정1) — 기계동작만 deferred |
| Organize | inbox 자동분류 UI | PASS(render) | classify/dismiss 버튼 + AI 추천 80% |
| Distill | 노트 임베딩 | PASS | chunkCount 2 |
| Express | RAG ask SSE + markdown + [N] citation | PASS | owner/admin/member |
| Express | memory recall | PASS(API) | |
| Promote | memory 승격 | PASS | 팀 RAG 검색됨 |
| Promote | note 승격(chunk 있음) | PASS | 팀 RAG 검색됨 |
| Promote | note 승격(0-chunk) | **FAIL→FIXED** | QA-0617-A |
| Promote | meeting/inbox/action 승격 | STATIC | session_factory 패턴 정상(grep). 라이브 미실행 |

### UI/디자인
| 항목 | 결과 | 근거 |
|---|---|---|
| console.error 0 (7 라우트) | PASS | sign-in/dashboard/projects/search/inbox/memory/settings |
| emoji→lucide 회귀 | PASS | features+app/(app) JSX 리터럴 emoji 0 |
| lucide 아이콘 전면 | PASS | nav/badge 모두 img(lucide) |
| `/actions` 라우트 | PASS | /inbox 의도된 리다이렉트(actions-redirect.spec) |

### N/A-deferred (사유 명시 — `docs/TODO.md` 플래그)
- 회의 오디오 파이프라인 콘텐츠 검증(transcription/화자분리/요약 품질): 풍부한 화자 샘플 부재(결정1).
- export(MD/JSON), 온보딩 0→4 가입 플로우, meeting/inbox/action promote 라이브, viewer write-block 라이브: 시간/우선순위(팀 spine 우선) — 정적/회귀 테스트로 일부 커버.

## 4. PASS 하이라이트 (회귀 없음 확인)
멀티테넌시 격리(I-9 cross-tenant 404/403 전수) · visibility 3종 분기 + admin/owner bypass 대칭(RAG 포함) · **RAG private 누수 0**(답변+citation 양쪽) · RBAC 4-cell 경계 · 캐시 무효화 즉시성 · revocation · 워크스페이스 전환(BUG-WS-SWITCH 회귀 없음) · memory/note(chunked) promote 검색성 · console.error 0 · emoji 0.

## 5. 기준선 false-positive 필터 (재보고 안 한 것)
deep-review(2026-06-01) 잔여 다수가 PR #123/#124에서 이미 fixed → 재보고 금지 적용. 라이브/코드로 재확인: projects-500→409 · invalidate_member_cache 호출 · WorkspaceMember UNIQUE · notes create/update BG 세션 · GEMINI 키 유효 · WS-SWITCH onClick. 프로젝트 제목 emoji(🚀💡📋)=온보딩 시드 **데이터**(UI 회귀 아님). Clerk `accounts.dev` CSP 경고=외부 노이즈. 의도적 음성 API 프로브의 4xx/5xx console 로그=테스트 아티팩트(앱 결함 아님).

## 6. 검증 증거
- BE: `uv run --directory backend pytest -q` → **551 passed, 1 skipped** (98s). 회귀 테스트 fix 전 fail→후 pass.
- alembic: 스키마 변경 없음 → migration 불요.
- FE: 라이브 스크린샷(screenshots/01~04) + console.error 0.
- Codex review(diff): PASS.

## 7. 산출물
- 본 리포트 + `screenshots/` (owner 대시보드, member visibility-filtered 프로젝트, memory, settings).
- fix: `backend/src/notes/service.py`(+1) + `backend/tests/notes/test_note_promote.py`(+1 test).
- BL 등재: QA-0617-C/D/E/F (`docs/REFACTORING-BACKLOG.md`).
- `docs/TODO.md`: 음성 샘플 갭 + 전용 admin/viewer dev 계정.
