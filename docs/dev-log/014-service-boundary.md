# ADR-014: Service-to-Service 경계 정책 결정 (D-2/D-3 + Sprint 6 권한 검증 위치)

> **날짜:** 2026-05-11
> **상태:** Accepted
> **작성자:** Claude Opus 4.7 (1M context) + 사용자 (Sprint 6 진입 직전)
> **관련:** ADR-009 §"후속" F8 + §"비용/리스크" + §"4. 부채 D-2/D-3 처리 보류 결정 (AD-15)" / ADR-010 §"검증 시그널" M1 / ADR-011 §"외부 인터뷰" PERSONA-002~003 / CONTEXT-MAP §4.2 + §7 D-2 D-3 / `.ai/stacks/fastapi/backend.md` §3
> **출처:** Sprint 6 plan vivid-clarke (`/Users/woosung/.claude/plans/sprint-6-vivid-clarke.md`) §3 (옵션 A 채택 + 코드량 측정 ~120-180줄 + AD-19~22 라벨)
> **워크플로우:** `.ai/templates/workflow.md` Stage 3 Step 4 (writing-plans + Generator-Evaluator + /codex 중위험+) — Sprint 6 plan에서 분기된 정책 ADR

---

## 배경

Phase A (Stage 0 헌법 retrofit, cea0be9 → PR #8 머지) + Phase B (Stage 1 메타 retrofit, c4cdae1 → PR #9 머지) 완료 후 Sprint 6 (멤버십 + Private 프로젝트, ADR-009 F1) 진입 직전. 헌법 CONTEXT-MAP §7 부채 D-2 (notes/service.py → embeddings.service 직접 의존) + D-3 (rag/service.py → embeddings.{models, repository, service} 직접 의존) 처리 결정이 Sprint 6 D-1 visibility (Project Public/Draft/Private) 권한 검증 위치 결정과 직결.

ADR-009 §"D-2/D-3 처리 보류 결정" (AD-15)에서 두 부채 처리를 Sprint 6 진입 직전 별도 ADR로 분리하기로 결정. ADR-009 §"비용/리스크": "Sprint 6 진입 직전 D-2/D-3 처리 ADR을 먼저 작성하는 것이 더 안전할 수 있음 — 본 결정은 retrofit 스코프 폭주 방지 vs Sprint 6 스코프 증가 트레이드오프." 사용자 결정으로 본 ADR-014 신설 (ADR-009 F8 항목 = 본 ADR-014).

본 ADR은 Sprint 6 plan vivid-clarke §3에서 brainstorming + 코드량 측정 후 도출한 **옵션 A (orchestrator 도입)** 결정을 ADR Nygard 포맷으로 lock-in한다. 코드 변경은 동반하지 않음 (정책 ADR). 실제 부채 해소는 Sprint 6 PR (BE-T9~T14 + T-CONST-1)에서 처리.

### 자의 결정 라벨 (본 산출에서 추가)

ADR-009 AD-1~18 소진 후 AD-19부터 시작. Sprint 6 plan vivid-clarke §5와 정합.

- **AD-19**: 옵션 A (orchestrator 도입) 권장 — B/C 대비. 자의 = "Sprint 6 스코프 +3 task vs D-2/D-3 영구 부채" 트레이드오프에서 전자 선택. 사용자 brainstorming + 코드량 측정 후 lock-in.
- **AD-20**: D-2/D-3 부채 해소를 Sprint 6 **같은 PR**에서 처리 (별도 PR 분리 X). 자의 = 권한 검증 task와 강결합되어 분리 시 임시 패턴 잔존 위험. 분리 옵션도 정당하나 본 ADR은 통합 권장.
- **AD-21**: 헌법 §4.2 갱신 = "embeddings 예외 허용" 명시 (옵션 a). embeddings 도메인을 `services/`로 디렉토리 이동 (옵션 b)는 ~30 파일 import 갱신 → Sprint 6 스코프 폭주, 보류 (§"후속" F8.4 Sprint 7+ 검토).
- **AD-22**: orchestrator 진입 메서드 명명 = meetings(`process_meeting`) 패턴 따라 notes는 `process_note_*`, rag는 `process_ask` 또는 `ask` 그대로 통일.

---

## 결정

### 1. 부채 본질 재정의

헌법 §4.2 정책: "service-to-service 직접 호출 금지, orchestrator(`<domain>/pipeline_service.py` 또는 `services/`) 경유 필수. Repository는 read-only 한정 OK." 코드 현실: `embeddings.service`가 notes/rag/meetings 3개 도메인에서 호출되는 **사실상 cross-domain shared service**.

| 도메인 | 호출 위치 | 헌법 §4.2 정합 |
|---|---|---|
| **meetings** | `pipeline_service.py:193,200-202` (`embedding_service.embed_meeting()` + `invalidate_cache()`) | ✅ orchestrator 경유 |
| **notes** | `notes/service.py:7,112,124-132` (`EmbeddingService` import + `embedding_service.repo.delete_by_source()` + `embed_note()` + `invalidate_cache()`) | ❌ service 직접 호출 (D-2) |
| **rag** | `rag/service.py:9-11,39,43-45,74-87` (3개 import + `generate_embeddings` + repository 직접 호출 다수) | ❌ service 직접 호출 (D-3) |

**정책-코드 갭의 본질**: "embeddings를 일반 도메인 모듈로 분류한 것 자체가 부정확." 실제로는 `services/transcription.py` + `services/ai_processing.py`와 동급의 **cross-cutting 인프라성 컴포넌트**. 단 디렉토리 위치(`backend/src/embeddings/`)는 도메인 패턴(router/service/repository/models)을 모두 갖춰 도메인으로 분류된 상태. 본 ADR은 **분류는 보존하되 호출 규칙만 명시화** (AD-21).

### 2. 권한 검증 위치 옵션 비교

Sprint 6 D-1 visibility (Public/Draft/Private) 추가 시 Router decorator (workspace 멤버십 + role)만으로는 불충분 — `project_id`별 visibility를 service 호출 직전에 확인해야 함. 검증 위치 결정이 D-2/D-3 처리와 직접 결합.

| 옵션 | 권한 검증 위치 | D-2/D-3 부채 | Sprint 6 +코드 | 헌법 §4.2 영향 | 향후 부채 |
|---|---|---|---|---|---|
| **A (선택)** | orchestrator(`*/pipeline_service.py`) 진입 메서드. dependencies.py에서 WorkspaceMember + Project(visibility) 주입 | **해소** (notes·rag·meetings 모두 동일 패턴) | **~120-180줄** (notes 50-70 + rag 40-60 + deps/router 수정 ~50). 전체 Sprint 6 ~15% | "embeddings.service 호출 = orchestrator 내부에서만 허용" 행 추가, D-2/D-3 부채 §7에서 제거. 헌법 결정 #1 보강 | **없음** (정합) |
| B | `auth/rbac.py`에 `require_project_visibility(project_id)` 추가. service.py에서 embedding_service 직접 호출 유지 | **보존** (영구 부채화 위험) | ~30-50줄 | §4.2 D-2/D-3 영구 부채 등재 또는 "예외 허용" 추가 | **고위험** — rag.service.ask() 안 권한 누락 가능. service-to-service 호출 패턴이 Sprint 7+ Wedge 신규 도메인에 전염 |
| C | `rag.service.ask()`/`notes.service.create_note()` 안에서 `project_repo.find_by_id` 호출 후 visibility 검증 | **보존 + 회색지대 확대** | +0 | §4.2 권한 검증 위치 미정의 → 헌법 약화 | **최고위험** — 기존 패턴(Router decorator만 권한 검증) 깨짐. Service에 권한 + 비즈니스 로직 혼재. ADR-009 F8 의미 약화 |

### 3. 옵션 A 선택 근거 4가지

1. **meetings 패턴 그대로 복제** — `meetings/pipeline_service.py:33-222` (222줄)가 이미 6 Repository + 3 Service(transcription/ai_processing/embedding) 주입 + 단일 진입 메서드 + 마지막 1회 commit 패턴 확립. notes/rag도 동일 골격 → 신규 설계 부담 0. 학습 곡선·코드 리뷰 부담 최소.

2. **헌법 + 백엔드 규칙 100% 정합** — `.ai/stacks/fastapi/backend.md` §3 "크로스 레포지토리 트랜잭션 = 동일 session을 여러 repo에 주입 + 조율 Service에서 1회 commit" 정신 + 헌법 I-1 "AsyncSession은 Repository만 보유" + I-2 "마지막 1회 commit" 모두 정합.

3. **권한 검증 강건성** — orchestrator 진입(예: `RagPipelineService.ask(question, project_id, member: WorkspaceMember)`)에서 Project visibility + member role 검증 후 service 호출. **SSE 스트리밍 시작 전에 검증 완료** → 권한 누락이 사용자에게 노출되지 않음. 옵션 B(decorator)는 service 내부 호출이 검증을 우회할 가능성 있음.

4. **D-2/D-3 영구 해소** — Sprint 7+ Wedge 신규 도메인이 자동 채택할 패턴. 부채 영구 차단. 헌법 §4.2가 "service-to-service 금지"를 강제하므로 신규 도메인은 처음부터 orchestrator 패턴 사용.

### 4. 헌법 §4.2 갱신 방향 (Sprint 6 T-CONST-1에서 처리)

**CONTEXT-MAP §4.2 표 추가 (신규 행)**:

| 케이스 | 허용 | 강제 위치 |
|---|---|---|
| `embeddings.service` 호출 | ✅ orchestrator(`*/pipeline_service.py` 또는 `services/`) 내부에서만 | code review |

**§4.2 ⚠️ 행 제거**: 현 표의 D-2/D-3 두 행 (notes→embeddings.service, rag→embeddings.{models,repository,service}) 삭제 — orchestrator 도입으로 위반 사라짐.

**§4.2 Mermaid 다이어그램 갱신**: 현 Mermaid의 두 점선 화살표(`notes -.현재 부채.-> embeddings`, `rag -.현재 부채.-> embeddings`)를 실선으로 변경 + 코멘트 갱신(`notes -.orchestrator only.-> embeddings`, `rag -.orchestrator only.-> embeddings`) 또는 `notes/rag → embeddings`를 `meetings -. orchestrator only .-> inbox/embeddings` 패턴과 동일 형식으로 통일. T-CONST-1 task 정의에 Mermaid 갱신 포함.

**§7 부채 표**: D-2/D-3 행에 ✅ "ADR-014로 해소, Sprint 6 BE-T9~T14에서 구현" 표기 후 다음 retrofit에서 완전 제거.

**§4.2 헌법 결정 #1 보강**: 기존 결정에 한 줄 추가 — "embeddings·ai_processing·transcription은 cross-domain shared service로 분류. 직접 호출은 orchestrator 경계(`*/pipeline_service.py` 또는 `services/`) 내부에서만 허용."

### 5. D-2/D-3 부채 해소 결정

본 Sprint 6 PR에 통합 (별도 PR 분리 X — AD-20). 권한 검증 task와 강결합되어 분리 시 임시 패턴이 머무를 위험. Sprint 6 plan vivid-clarke §4.4 (BE-T9~T14)에 task로 lock-in:

- BE-T9: `notes/pipeline_service.py` 신설
- BE-T10: `notes/dependencies.py` 갱신
- BE-T11: `notes/router.py` endpoint 분기
- BE-T12: `rag/pipeline_service.py` 신설
- BE-T13: `rag/dependencies.py` 갱신
- BE-T14: `rag/router.py` endpoint 분기

### 6. ADR-009 / ADR-010 / ADR-011 cross-link

| 산출 | 책임 영역 | 본 ADR-014 정합 |
|---|---|---|
| **ADR-009** | Stage 1 총괄·F8 부채 처리 | F8 = 본 ADR로 lock-in. AD-15 (D-2/D-3 보류) 해제. |
| **ADR-010** | Future-Fit Thesis. M1 = RAG 품질 시그널 | 권한 누락이 RAG 품질 시그널을 오염하지 않도록 orchestrator 진입 검증 필수. 본 ADR §"검증 기준" 6번. |
| **ADR-011** | Persona 정의. PERSONA-002/003 협업 검증 시그널 S6 | visibility 분기 동작 시나리오가 Sprint 6 V-T2 (Playwright E2E)에 포함 — 페르소나 협업 가설 검증 가능. 본 ADR §"검증 기준" 7번. |

---

## 결과

### 1. Sprint 6 plan vivid-clarke 영향 (이미 §3·§4.4·§4.8에 반영)

| Task | 신규/조정 |
|---|---|
| BE-T9 `notes/pipeline_service.py` 신설 | 본 ADR로 lock-in — NoteRepository + EmbeddingService + ProjectRepository 주입. 진입 메서드 `create_note_with_membership`/`delete_note_with_cleanup`/`embed_note_async`. |
| BE-T10 `notes/dependencies.py` 갱신 | pipeline_service 조립 추가, 동일 session 공유 |
| BE-T11 `notes/router.py` endpoint 분기 | BackgroundTasks 호출을 service → pipeline_service로 |
| BE-T12 `rag/pipeline_service.py` 신설 | EmbeddingRepository + EmbeddingService + AIProcessingService + ProjectRepository 주입. 진입 메서드 `ask`가 visibility + member 검증 후 RagService.ask 위임 (AsyncGenerator wrapping). |
| BE-T13 `rag/dependencies.py` 갱신 | pipeline_service 조립 + project_repo 주입 |
| BE-T14 `rag/router.py` endpoint 분기 | `/ask` endpoint를 service → pipeline_service로 |
| **T-CONST-1** | CONTEXT-MAP §4.2 표 (embeddings 예외 행 추가, D-2/D-3 행 제거) + §7 D-2/D-3 부채 항목 갱신 |

스코프 증가 = +6 BE task + 1 헌법 갱신 task. Sprint 6 전체 ~15% (코드량 ~120-180줄, meetings 패턴 복제이므로 신규 설계 부담 0).

### 2. 헌법 갱신 (Sprint 6 머지 후 T-CONST-1로 처리)

- `CONTEXT-MAP.md` §4.2 표 1행 추가 + D-2/D-3 ⚠️ 행 제거
- `CONTEXT-MAP.md` §7 D-2/D-3 부채 항목에 ✅ "ADR-014로 해소" 표기
- `CONTEXT-MAP.md` §4.2 "헌법 결정 #1" 보강 1문장

### 3. ADR-009 cross-link 갱신 (Sprint 6 머지 후 T-CONST-2로 처리)

- ADR-009 §"후속" F8 항목에 본 ADR-014 cross-link 추가 + closeout 표기

### 4. Sprint 6 검증 시나리오에 포함 (V-T2/V-T5)

- V-T2 시나리오 5: Private project의 RAG 검색 결과가 비멤버 응답에서 0건 (orchestrator 권한 검증 정합)
- V-T5: Private project의 embedding chunk가 비멤버 RAG 응답에 포함되지 않음 (SSE source 검증)

---

## 비용 / 리스크

### 권장 옵션 A 위험 (3개)

- **R-1 (Sprint 6 스코프 +6 task)**: 본 ADR 도입으로 Sprint 6 BE task가 6개 추가. 완화: meetings 패턴 복제이므로 신규 설계 부담 0, 코드량 약 120-180줄, 추정 1-2일 작업. /codex challenge 모드 (Sprint 6 plan §6.2)로 사각지대 catch.
- **R-2 (rag/pipeline_service.py가 SSE 스트리밍 wrapping 신설)**: RagService.ask()의 `AsyncGenerator[dict, None]`을 pipeline_service가 권한 검증 후 그대로 yield 위임. 미세하게 wrapper 1단 추가. 완화: AsyncGenerator 위임은 Python 표준 패턴(`async for x in inner: yield x`), 리스크 낮음.
- **R-3 (EmbeddingService 호출자 3개 도메인 명시화)**: meetings/notes/rag → 향후 EmbeddingService 시그니처 변경 시 3곳 동기 수정. 완화: 인터페이스 안정 — `embed_*`, `invalidate_cache`, `generate_embeddings` 3개 메서드. 시그니처 변경은 별도 ADR 트리거.

### 미선택 옵션 위험

**옵션 B (rbac decorator만)**: D-2/D-3 영구 부채화. service.py 안에 visibility 검증이 없으므로 향후 Private Project 누출 보안 사고 가능. ADR-009 F8 "service-to-service 경계 정책 결정"이 사실상 미결정으로 회귀. Sprint 7+ Wedge 신규 도메인이 동일 패턴(부채) 답습.

**옵션 C (service 내부 검증)**: 권한 검증 패턴이 Router decorator + Service 내부 검증으로 이원화 → Sprint 7+ 신규 도메인이 어느 패턴 따라야 할지 불명확. 헌법 §4.2 약화 + 코드 리뷰 부담 증가.

### 본 ADR 자체 위험

- **R-4 (헌법 §4.2 "embeddings 예외" 명시가 추후 약점)**: cross-domain shared service가 임의로 늘어날 가능성. 완화: §"후속" F8.4에 Sprint 7+ embeddings를 `services/`로 디렉토리 이동 검토 ADR-015 등재.
- **R-5 (본 ADR 결정이 ADR-010/011 cross-link을 가정)**: ADR-010 supersedes 시 §6 cross-link 매핑 표가 즉시 갱신 필요. 완화: §"후속" F8.5에 ADR 정합성 점검 항목 등재.

---

## 검증 기준

### 1. Sprint 6 plan §6.1 결함 검출 책임 경계

본 ADR이 정책 결정으로 책임지는 항목 vs Sprint 6 plan에 위임하는 항목 명시 분리:

| # | 결함 포인트 | 본 ADR 책임 | Sprint 6 plan 위임 |
|---|---|---|---|
| 1 | I-9 멀티테넌시 격리 | — | V-T2 시나리오 3 (cross-workspace 격리) |
| 2 | I-13 API prefix | — | BE-T1~T16 (router endpoint prefix 보존) |
| 3 | Migration 안전성 | — | V-T3 (alembic round-trip), AD-25 (server_default) |
| 4 | 권한 회색지대 | ✅ 옵션 A 강건성 §3.3 근거 + 옵션 B/C 비권장 §2 표 | — |
| 5 | Draft 정의 모호 | — | AD-24 (Sprint 6 plan §5) |
| 6 | FE/BE 권한 불일치 | — | FE-T6 + BE-T15 (ROLE_CONFIG ↔ require_admin 매트릭스 정합) |
| 7 | Test 커버리지 (visibility 3 × role 4 = 12+ 케이스) | — | V-T1, §6.2 /codex 36 케이스 매트릭스 |
| 8 | ProjectMember 격리 | — | V-T2 시나리오 1, BE-T6/T8 (cross-workspace member 차단) |
| 9 | SSE 권한 시점 | ✅ §"검증 기준" 6번 + §3.3 근거 3 (SSE 시작 *전* 검증) | — |
| 10 | 마지막 1회 commit | ✅ §"검증 기준" 5번 + 헌법 I-2 cross-link | — |

**책임 분담**: 본 ADR = 4/9/10 (정책 결정 + 강건성 시그널). Sprint 6 plan = 1/2/3/5/6/7/8 (구현 검증 시그널).

### 2. 검증 checkbox + 측정 명령

각 항목은 머지 후 측정 가능. PASS 임계는 모든 명령이 0 exit code 또는 명시된 기대값 일치.

- [ ] **C-1 본 ADR §"결과" 표 ↔ Sprint 6 plan §4.4 일치**: `grep -E "BE-T(9|10|11|12|13|14)" /Users/woosung/.claude/plans/sprint-6-vivid-clarke.md` 결과 6행 ∩ `grep -E "BE-T(9|10|11|12|13|14)" docs/dev-log/014-service-boundary.md` 결과 6행. task ID + 진입 메서드 + 주입 dependency 모두 동일.
- [ ] **C-2 헌법 §4.2 갱신 적용**: `grep -n "embeddings.service" CONTEXT-MAP.md | grep -c "orchestrator"` ≥ 1 AND `grep -nE "(notes|rag).*embeddings.*⚠️|⚠️.*(notes|rag).*embeddings" CONTEXT-MAP.md` = 0 (D-2/D-3 ⚠️ 행 제거 확인). Mermaid의 `notes -.현재 부채` / `rag -.현재 부채` 두 점선 제거(`grep -c "현재 부채" CONTEXT-MAP.md` = 0).
- [ ] **C-3 §7 D-2/D-3 closeout 표기**: `grep -nE "D-(2|3).*ADR-014" CONTEXT-MAP.md` 결과 2행 ∩ `grep "ADR-014로 해소" CONTEXT-MAP.md` 결과 ≥ 1.
- [ ] **C-4 ADR-009 §"후속" F8 closeout cross-link**: `grep -A1 "F8" docs/dev-log/009-stage1-retrofit.md | grep "ADR-014"` 결과 ≥ 1 AND closeout 표기 (취소선 또는 명시).
- [ ] **C-5 notes/rag pipeline_service.py meetings 패턴 정합**: `grep -E "AsyncSession" backend/src/notes/pipeline_service.py backend/src/rag/pipeline_service.py` 결과 0 (헌법 I-1 정합 — Service에 AsyncSession import 금지). `cd backend && uv run pytest tests/notes/ tests/rag/ -v` 결과 PASS. commit 회수 검증 = `grep -c "await.*commit()" backend/src/notes/pipeline_service.py backend/src/rag/pipeline_service.py` 각 파일 ≤ 2 (성공 1 + 실패 1, 헌법 I-2 정합).
- [ ] **C-6 rag/pipeline_service.py SSE 시작 전 권한 검증**: `grep -B20 "AsyncGenerator\|yield" backend/src/rag/pipeline_service.py | grep -E "visibility|require_|member" | head -1` 결과 ≥ 1 (yield 전에 visibility/member 검증 코드 존재). ADR-010 M1 RAG 품질 시그널 측정 시 권한 누락 source 오염 검증 = V-T5 PASS.
- [ ] **C-7 Sprint 6 V-T2 시나리오 5 + V-T5가 ADR-011 S6 검증 입력**: `cd e2e && npx playwright test sprint-6-visibility.spec.ts -g "시나리오 5"` PASS AND `grep -E "V-T(2|5).*PERSONA|S6" /Users/woosung/.claude/plans/sprint-6-vivid-clarke.md` 결과 ≥ 1.

---

## 후속

> 책임자: 사용자 (1인 풀스택 founder). 시점·측정 지표 명시.

| # | 항목 | 시점 | 측정 지표 | 결과물 |
|---|---|---|---|---|
| F8.1 | Sprint 6 BE-T9~T14 + T-CONST-1 구현 | Sprint 6 PR (본 ADR 머지 직후) | meetings 패턴 정합 + 권한 검증 일원화 + V-T2 시나리오 5 PASS | Sprint 6 PR diff |
| F8.2 | meetings/pipeline_service.py 권한 검증 추가 | Sprint 6 BE-T9~T14와 동시 | meetings도 process_meeting 진입에서 visibility + member 검증 (현재 router decorator만) | 동일 PR |
| F8.3 | 헌법 §4.2 + §7 갱신 PR | Sprint 6 머지 직후 (T-CONST-1·T-CONST-2 통합 가능) | 본 ADR §"결과" §2·§3 정합 | docs PR |
| F8.4 | embeddings를 `services/`로 이동 검토 (옵션 b) | Sprint 7+ 또는 무기한 보류 | cross-domain shared service의 디렉토리 위치 일관성 (transcription/ai_processing와 동급) | 신규 ADR-015 (예정) |
| F8.5 | D-9 (meetings commit 5회) 별도 처리 | Sprint 7+ | meetings/pipeline_service.py:71/86/90/215/222 commit 회수 단일화 또는 헌법에 "진행 보고용 commit 허용" 명시 | 별도 ADR 또는 D-9 직접 패치 |
| F8.6 | ADR 정합성 정기 점검 | Sprint 7+ retrospective | ADR-009/010/011/014 cross-link 표 supersedes 발생 시 즉시 갱신 | 별도 retrofit PR |

---

## 메모: 본 ADR의 위치

ADR-014는 **Sprint 6 진입 직전 service-to-service 경계 정책 ADR**이다. ADR-009 F8 lock-in + 헌법 §4.2 갱신 트리거 + Sprint 6 plan vivid-clarke §3 골격 lock-in의 3가지 책임을 동시 수행.

코드 변경은 동반하지 않는 **정책 ADR**. 실제 부채 해소(D-2/D-3)는 Sprint 6 PR (BE-T9~T14)에서 처리. 헌법 갱신 (§4.2 + §7)은 Sprint 6 머지 직후 T-CONST-1·T-CONST-2로 별도 처리.

본 ADR 머지 후 Sprint 6 plan vivid-clarke §10 2번(T-ADR-014 본문 작성) 완료 → 3번(EVAL-CONST 1라운드) 진입. 9+/10 PASS 후 사용자 검토 게이트 → 4번 → §10 5번(T-DESIGN-1 `/design-shotgun`) 시작.

Phase A → Phase B → Sprint 6 진입 흐름:
- Phase A (Stage 0 헌법 retrofit, cea0be9 → PR #8 머지)
- Phase B (Stage 1 메타 retrofit, c4cdae1 → PR #9 머지)
- T-F10 closeout (PR #10 머지, 05fee4b)
- **T-ADR-014 (본 ADR, 진행 중)** — Sprint 6 진입 직전 정책 결정
- Sprint 6 PR (BE-T1~T19 + FE-T1~T7 + T-CONST-1 + V-T1~T5) — 본 ADR 결정 적용
