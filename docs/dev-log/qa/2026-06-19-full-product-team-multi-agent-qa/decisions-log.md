<!-- 2026-06-19 전체 제품+팀 멀티 에이전트 QA의 의사결정 기록 (선택지 + 선택 결과) -->

# 2026-06-19 Full-Product Team Multi-Agent QA — 의사결정 기록

> 사용자 요청: "선택지가 있던 항목의 경우 어떤 선택지들이 있었고 이렇게 했다는 것을 기록으로 남겨." 본 파일 + PR 본문에 모든 분기점을 기록한다.

## 세션 진입 분기 (AskUserQuestion, 사용자 직접 선택)

| ID | 질문 | 선택지 | 선택 | 비고 |
|---|---|---|---|---|
| D1 | codex 검증 + Generator/Evaluator 분리 + fix 루프 강화 영속화 범위 | (A) 세션+템플릿 영속화 / (B) 이번 세션에만 | **B 이번 세션에만** | 재사용 문서(.ai/templates/workflow.md, 세션 프롬프트 템플릿) 미변경 |
| D2 | 분리 Evaluator 외부모델 교차검증 구성 | (A) per-finding codex + 최종 codex+agy / (B) 전부 codex만 / (C) 전부 codex+agy | **C 전부 codex+agy** | 모든 후보 결함 + 최종 GO/NO-GO 둘 다. 가장 엄격 |
| D3 | fix-until-done 루프 수정 커밋 처리 | (A) QA 브랜치 atomic 자동 커밋 / (B) 커밋 보류 일괄 | **A QA 브랜치 atomic 자동 커밋** | 푸쉬/머지는 별도 — D4로 갱신됨 |

## 세션 중 분기 (사용자 후속 지시로 자동 결정)

| ID | 분기 | 선택지 | 선택 | 근거 |
|---|---|---|---|---|
| D4 | Git Safety 진행 범위 | (A) commit만 후 push/PR 승인대기 / (B) commit→push→PR 자율 진행 | **B 자율 진행 (PR까지)** | 사용자 명시 "끝까지 진행하면서 PR까지 생성해줘". 머지는 제외(PR 생성까지만) |
| D5 | Phase 2 라이브 드라이빙 동시성 | (A) 병렬 / (B) 직렬 계정 스위칭 | **B 직렬 계정 스위칭** | 사용자 "2계정 병렬은 측정 어려움 → 스위칭 형태라도 꼼꼼하게". 정확도 > 속도 |
| D6 | 자동 진행 시 잔여 선택지 처리 | (A) 매번 질문 / (B) 추천안으로 자동 진행 | **B 추천안 자동 진행** | 사용자 "물어보지 말고". 모든 분기 본 파일에 기록 |

## 아키텍처 결정 (Senior Tech Lead 판단)

- **하이브리드 실행**: 병렬 인지작업(Generator 7페르소나, Evaluator)은 Workflow, 직렬 라이브(Live Driver)는 메인 루프. 라이브 stack은 단일 브라우저 + 단일 BE in-process RBAC 캐시 + 공유 Neon → 병렬 충돌하므로 직렬 필수 (D5와 정합).
- **분리 = load-bearing**: Generator(가설 생성) ↔ Evaluator(확정 판정) ↔ Implementer(수정) 각각 fresh context. self-grading 금지, 버그 지점 mock 금지 (QA-0617-A 교훈).
- **codex/agy 비대화형 호출 검증 완료**: `codex exec -s read-only -o <file> "..."` (smoke PONG OK) / `agy -p "..."` (--print 비대화형).

## Baseline 증거 (Phase 0)

- BE :8000 단일 프로세스 재시작 (`--reload` 없음, RBAC 캐시 단일성). `Application startup complete`. 현재 main `2d1ea43` 코드 기준 (2026-06-18 citation fix 포함 보장).
- `uv run --directory backend pytest -q` → **566 passed, 1 skipped** (107.75s).
- team e2e T1~T18 baseline → **27 passed (8.4m)** — spine 무손상 기준선 green.
- QA 브랜치: `qa/2026-06-19-full-product-team` (from main `2d1ea43`).

## D7 — Phase 2 측정 방식 (Senior Tech Lead 판단 + 사용자 D5 정합)

| 분기 | 선택지 | 선택 | 근거 |
|---|---|---|---|
| API-level 후보 측정 | (A) MCP 수동 클릭 / (B) 2계정 probe spec(team fixture 재사용) / (C) 혼합 | **C 혼합** | API/보안/데이터 = team fixture 재사용 probe spec(실토큰·실 RBAC·실 AI, 결정적 측정 = "꼼꼼한 측정"). UI/UX/반응형 = MCP 브라우저. probe spec 은 throwaway 측정용 — 회귀 테스트는 Implementer 별도 작성. |

## Phase 1 Generator 산출

- 7 페르소나 병렬 → **82 후보 항목** (P0=3, P1=26, P2=40, P3=13). `generator-checklist.json`. cross-persona 수렴: citation [N]→SourceViewer(~10×), SemanticCache 정합, viewer write-block, promote LIVE, 3 P0 SENTINEL IDOR.

## Phase 2 Live Driver — candidate-FAIL (라이브 재현)

probe harness(`probe-results.log`) + MCP 브라우저(d@e.com, ws "QA Cycle C Team"). console.error 0 확인: dashboard/inbox/notes/projects/memory.

| ID | P | 요약 | 라이브 증거 |
|---|---|---|---|
| CAND-A | P0 | note/meeting 읽기·export visibility-residue IDOR | member가 private project note GET+export → 200+nonce 누수 (대조 project 상세 404) |
| CAND-B | P0 | ws 멤버 제거 후 재초대 시 orphan ProjectMember 잔존 | 재초대 후 private project 200 + RAG MAGENTA 누수 |
| CAND-C | P2 | promote 멱등성 부재 → 중복 클론 | 2회 promote → 서로 다른 new_note_id 2건 |
| CAND-D | P2 | feedback FAB가 RAG 전송 버튼 가림(pointer intercept) | elementFromPoint(send center)=FAB, click timeout |
| CAND-E | P1 | citation 클릭 시 source 404 → console 에러 retry storm | 1클릭에 console 에러 1→45+ 폭증 |
| CAND-F | P1 | 삭제된 meeting orphan embedding chunk → citation 404 | RAG가 죽은 meeting id 1cf3af92 인용 (실제 062b2307) |
| CAND-G | P3 | /actions Performance.measure dev 에러 (低신뢰·dev artifact 추정) | dev 콘솔 TypeError, 평가자 반증 대상 |

→ 7 후보 모두 분리 Evaluator(opus gate + codex + agy)로 적대 검증 (Phase 3).

## Phase 4/5 — fix-until-done 루프 결과 (codex+agy 게이트)

| 결함 | 판정 | 처리 |
|---|---|---|
| CAND-A (P0) | CONFIRMED → 1차 fix(detail/export) → **codex NO-GO**(list/status/write 누수) → 완전화 → **codex NO-GO**(M2M cross-link) → M2M 게이트 → **GO** | RESOLVED (3 round) |
| CAND-B (P0) | CONFIRMED → fix(ProjectMember revoke + EXISTS guard) | RESOLVED |
| CAND-D (P2) | CONFIRMED → fix(fabSafe gutter), 라이브 검증 | RESOLVED |
| CAND-E (P2) | CONFIRMED → fix(sourceId + storm guard) → codex NO-GO(cache) → cache guard → GO, 라이브 검증 | RESOLVED |
| CAND-C (P2) | PARTIAL(agy 이견: 의도된 설계) | 백로그 BL-QA0619-C |
| CAND-F/G | REJECTED(meeting delete 없음 / dev artifact) | 기록만 |

**최종 게이트: codex GO(conf 9) + agy GO(conf 10).** 검증: pytest 608 / e2e T1~T18 green / tsc clean / vitest 63 / FE console.error 0.

⚠️ **learning**: 외부 리뷰어(codex/agy)에게 **truncated diff 금지** — agy 1차 NO-GO 는 `sed 1,200p`로 `get_meeting_status` 게이트 호출이 잘려보인 false-positive 였음(실제 라인 304 에 존재). full diff 재검증 시 GO.
⚠️ **learning**: codex exec review --base 는 custom prompt 불가 → `codex exec -s read-only` 로 "git diff main...HEAD 리뷰" 지시. 외부 리뷰 CLI 는 워크플로우 agent(180s 무출력 stall) 말고 **배경 bash**로 호출.
