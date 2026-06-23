<!-- 2026-06-19 Kairos 전체 제품+팀 7-페르소나 멀티 에이전트 라이브 QA 리포트 (Generator→LiveDriver→분리 Evaluator(codex+agy)→Implementer fix-loop) -->

# 2026-06-19 Kairos 전체 제품 + 팀 멀티 에이전트 라이브 QA 리포트

> main `2d1ea43` 기준. 7-페르소나 Generator → Live Driver(2계정·실 AI) → **분리 Evaluator(opus gate + codex + agy 적대 반증)** → **Implementer fix-until-done 루프(codex+agy RESOLVED까지)**. 사용자 요청으로 검증/평가를 Generator와 분리하고 codex+agy 교차검증 + 수정 루프를 워크플로우에 추가.

## 0. 한 줄 결과

7 후보 결함 중 **4건 확정**(2 P0 IDOR + 2 P2, codex+agy 둘 다 동의) → **fix-until-done 루프**(codex 3회 NO-GO→완전화 포함)로 전부 RESOLVED, **2건 반증**(false-positive 필터), **1건 partial**(agy 이견 → 백로그). **최종 codex GO(9) + agy GO(10)**. 검증: pytest 566→**608** / e2e T1~T18 **green** / tsc clean / vitest 63 / FE console.error 0 / CAND-A·B·D·E 라이브 재검증.

## 1. 방법론 — 강화된 워크플로우 (이번 세션 추가분)

```
Generator(7 페르소나, 병렬, 코드 근거 체크리스트)
  → Live Driver(메인 루프, 직렬, 2계정 probe + Playwright MCP, 실 AI)
  → 분리 Evaluator(fresh, per finding 병렬): opus 6문항 gate + codex exec 반증 + agy 반증
       └ CONFIRMED = opus(real & !fp & in-scope) AND codex confirm AND agy confirm
  → Implementer(별도, 직렬, TDD): RED 회귀 테스트(버그지점 mock 금지) → fix → GREEN → atomic commit
       └ codex exec review + agy review → 둘 다 RESOLVED 까지 루프(≤3회) → 아니면 revert+백로그
```

- **분리 = load-bearing**: Generator/Evaluator/Implementer 각각 fresh context (self-grading·버그지점 mock 금지, QA-0617-A 교훈).
- **codex+agy 둘 다**(사용자 D2): per-finding 적대 반증 + 최종 게이트. `codex exec -s read-only` / `agy -p`.
- 의사결정 분기 전체 기록: `decisions-log.md`.

## 2. Baseline (Phase 0) — 무손상 기준선

- BE :8000 단일 프로세스(`--reload` 없음) 재시작, main `2d1ea43` (2026-06-18 citation fix 포함).
- `pytest -q` → **566 passed, 1 skipped**.
- team e2e `--project=team` (T1~T18) → **27 passed** (spine green).
- `codex exec` / `agy -p` 비대화형 동작 확인.

## 3. 커버리지 (갭 우선 — spine 회귀 가드 전제로 깊이 이동)

Generator 82 후보 항목(P0=3/P1=26/P2=40/P3=13, `generator-checklist.json`). cross-persona 수렴: citation→SourceViewer(~10×), SemanticCache, viewer write-block, promote LIVE, SENTINEL IDOR.

| 영역 | 측정 방식 | 결과 |
|---|---|---|
| 보안 IDOR/격리(SENTINEL) | 2계정 probe spec(실토큰) | note/meeting IDOR + orphan ProjectMember 발견(P0×2) |
| AI 품질·citation(CONTENT-SKEPTIC) | MCP 라이브 RAG ask + citation 클릭 | RAG 그라운딩 양호, citation [N]→SourceViewer 동작(snippet+highlight), 단 404 storm 발견 |
| promote/export/pagination(POWER/CURIOUS) | probe spec | export(UTF-8)·viewer write-block·pagination = PASS; promote 멱등성 = partial |
| UI/UX·console(CASUAL/MOBILE) | MCP 라우트 sweep + 반응형 | dashboard/inbox/notes/projects/memory console.error 0; /search FAB 겹침 발견 |

console.error 0 확인 라우트: /dashboard /inbox /notes /projects /memory.

## 4. 확정 결함 (CONFIRMED — opus + codex + agy 3자 동의)

| ID | P | 결함 | 라이브 증거 | codex | agy |
|---|---|---|---|---|---|
| CAND-A | **P0** | note/meeting GET·export 가 project visibility 미검증 → 비멤버에게 private/draft 콘텐츠(+회의 transcript) 누수 | 비멤버 member GET+export note → 200+nonce; 대조 project 상세 404 | ✅ P0 | ✅ P0 |
| CAND-B | **P0** | ws 멤버 제거가 ProjectMember 미정리 → 재초대 시 orphan 으로 private 접근 부활 | remove→reinvite 후 private project 200 + RAG MAGENTA 누수 | ✅ | ✅ |
| CAND-D | P2 | feedback FAB 가 RAG 전송 버튼 pointer intercept(마우스 클릭 불가, Enter만) | elementFromPoint(send)=FAB, click timeout | ✅ | ✅ |
| CAND-E | P2 | citation source 상세 fetch 404 시 retry/refetch storm(console 1→45+) + wrong-id 의심 | 1클릭에 console 에러 45+ 폭증 | ✅ | ✅ |

## 5. 반증/이견 (분리 Evaluator 가 걸러낸 false-positive — 검증/평가 분리의 가치)

| ID | 판정 | 근거 |
|---|---|---|
| CAND-C | **PARTIAL** (백로그) | opus+codex: promote 멱등성 가드 부재 = 실제. **agy 이견**: copy-on-trigger 복제는 의도된 설계(전 도메인 일관). → 사용자 결정 필요, 백로그 BL-QA0619-C. |
| CAND-F | **REJECTED** | opus+codex: **meeting DELETE 경로 자체가 없음** → "삭제로 인한 orphan chunk" 전제 불성립. cited id 는 chunk.id 의심(→ CAND-E 로 흡수). |
| CAND-G | **REJECTED** | /actions→/inbox 리다이렉트는 **의도됨**(Sprint 27d BUG-S27d-2). Performance.measure 에러는 react-server-dom-turbopack **dev 런타임 artifact**(프로덕션 아님). |

## 6. 수정 결과 (4 confirmed RESOLVED)

> ⚠️ Implementer **워크플로우는 codex/agy 리뷰 CLI 무출력 stall(180s 워치독)로 ~2.9h 후 중단** → CAND-A/B/D 커밋 후 CAND-E 직전 멈춤. **메인 루프가 인수**: 커밋된 fix 검증(테스트·라우터 배선·pyright delta 0) + CAND-E 직접 완료 + 라이브 재검증. (learnings: 외부 리뷰 CLI 는 배경 bash 로, 워크플로우 agent stall 회피.)

| ID | P | fix commit(s) | 회귀 테스트 | 라이브 재검증 |
|---|---|---|---|---|
| CAND-A | P0 | `27d3124` | `test_note_meeting_visibility_idor.py` (RED: requester gate 부재 → 200 leak) | probe: 비멤버 note GET+export → 404 기대 (e2e 재실행) |
| CAND-B | P0 | `1229fc1`+`855904c` | `test_member_removal_revokes_project_access.py` + `_residue_completeness.py` | probe: remove→reinvite → 404 + RAG no-MAGENTA (e2e 재실행) |
| CAND-D | P2 | `78c6528` | `search-fab-overlap.spec.ts` | **VERIFIED**: elementFromPoint(send)=rag-submit, overlap=false, click OK |
| CAND-E | P2 | `3b86929` | `test_format_sources_sourceid.py` (RED: sourceId key 부재) | **VERIFIED**: citation→`/meetings/062b2307`=200(전엔 chunkId→404), console 0 errors(전엔 45+), full transcript 로드 |

- 모든 fix backward-compatible (requester None / sourceId None 폴백). pyright delta **0**(기존 SQLModel typing 노이즈, 변경 라인 밖).

### 6.1 fix-until-done 루프 — codex NO-GO → 완전화 → 재검증 (사용자 요청 핵심)

1차 fix 후 **최종 codex 리뷰가 NO-GO(conf 8)** 판정 — 2개 미완 발견(검증/평가 분리의 가치):
- **CAND-A 미완(P0)**: detail/export 만 게이트했고 **list/status/write 경로는 그대로 누수**. 특히 `GET /notes?projectId=<private>` 가 `list_notes` → `_to_dict`(content+plainText)로 private 노트 **본문 전체 누수**. + meeting list/status, note status/update/delete/promote 미게이트.
- **CAND-E 미완**: cache-hit 경로가 sourceId 없는 구 캐시 sources 를 그대로 serve → 여전히 chunkId 404.

→ **완전화 패스**(commit `64dd6e5`+`c85c3e5`+`557d08e`): notes/meetings **list 에 project-visibility SQL 필터**(`_note_visibility_filter`/`_meeting_visibility_filter`, embeddings `_visibility_filter_sql` 패턴 재사용) + status/update/delete/promote `_verify_*_visibility` 게이트 + cache-hit sourceId-부재 → cache MISS 처리. **+17 real-seam 회귀 테스트**(mutation-gate RED 확인). pytest **582→604 passed**.

**2차 codex NO-GO**(conf 8): 회의 M2M cross-link 엣지(meeting 이 public-A + private-B 동시 링크 시 `?projectId=private-B`로 B 링크 존재성 누수 + detail 이 모든 linked project 메타 노출). → **M2M 게이트**(commit `bb67a15`, `_is_project_accessible` — projectId 필터 시 그 프로젝트 접근권 검사 + detail linked-projects 필터). +4 real-seam 테스트. pytest **604→608 passed**.

**최종 verdict — codex GO(conf 9, M2M closed, codex 가 직접 테스트 실행 확인) + agy GO(conf 10, residual leak none)**. ※ agy 1차 NO-GO 는 내가 truncated diff(`sed 1,200p`)를 줘서 `get_meeting_status`의 게이트 호출이 잘려보인 **false-positive** — full diff 재검증 시 GO(get_meeting_status:304 가 `_verify_meeting_visibility` 호출 확인). **교훈: 리뷰어에게 truncated diff 금지.**

## 7. 회귀 무손상 (Phase 5)

- 전체 pytest (완전화 후): **604 passed, 1 skipped** (baseline 566 + 38 신규 회귀/보안 테스트). 독립 재실행 확인.
- frontend tsc: **clean** / vitest: **63 passed**.
- team e2e T1~T18 (수정 후): **34 passed (10m)** — spine green + probe 재검증.
- **probe 재검증(라이브, CAND-A/B 보안 확정)**: SENTINEL-01 note get/export → **404, leaks_nonce=false**(전 200/leak); SENTINEL-03 residue → **404, magenta=false**(전 200/leak); viewer write-block/export/pagination = PASS. (CAND-C promote 멱등성만 dup=true = 백로그 partial.)
- FE console.error 0: dashboard/inbox/notes/projects/memory **0**; /search citation 클릭 후 **0**(CAND-E fix, 전 45+).
- **CAND-D/E 라이브 검증**: 전송 버튼 클릭 가능(elementFromPoint=rag-submit); citation→`/meetings/062b2307`=**200**(전 chunkId 404), full transcript 로드.
- **최종 codex+agy GO/NO-GO**: **codex GO(conf 9) + agy GO(conf 10)** — 둘 다 GO (사용자 D2 "전부 codex+agy" 충족). pytest **608 passed** 독립 확인.

## 8. 백로그 / 후속

- BL-QA0619-C: promote 멱등성 가드(설계 결정 필요 — agy 는 의도된 설계로 봄).
- (반증된 CAND-F/G 는 결함 아님 — 기록만.)

## 부록

- 의사결정 기록: `decisions-log.md`
- Generator 체크리스트: `generator-checklist.json`
- probe 측정 로그: `probe-results.log`
- 스크린샷: `screenshots/`
