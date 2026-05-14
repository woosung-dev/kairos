<!-- Sprint 15 Stage 3 Q4 — codex 적대적 plan 검토 결과 -->

# Sprint 15 Plan Codex Adversarial Review (2026-05-14)

> **목적**: Stage 3 Q4 산출. sprint-15-plan.md + Stage 1 design doc + Q2 brainstorm doc을 codex CLI (gpt-5.1 frontier) 적대적 검토.
> **모델**: codex-cli 0.130.0 + medium reasoning + web_search 활성. 토큰 81920 input / 5257 output / 1067 reasoning.
> **결과**: **VERDICT = FIX iter 1**. 20개 issue 사전 수정 후 R1 진입 권장.

---

## §1. Codex 검토 결과 (verbatim)

검토 기준: 제공된 3개 문서 (Stage 1 design doc + Q2 brainstorm + sprint-15-plan.md) + 공식 API 문서 (OpenAI Whisper / pricing, Gemini 2.5 Flash, MDN MediaRecorder). 레포 파일은 읽지 않음.

### AXIS A — Hidden complexity (12 issues)

**1. MediaRecorder Safari/iOS**
- Problem: R4의 `new MediaRecorder(stream, { mimeType: "audio/webm" })`는 Safari/iOS에서 바로 깨질 수 있다.
- Why it bites: 첫 외부 PERSONA가 iPhone Safari로 들어오면 녹음 버튼이 실패하고 텍스트 폴백만 남는다. 음성 Recall wedge 검증이 텍스트 메모 검증으로 변질된다.
- Fix: `frontend/src/features/memory/hooks.ts`에 `MediaRecorder.isTypeSupported()` 기반 MIME negotiation 추가. 우선순위 `audio/webm;codecs=opus`, `audio/mp4`, `audio/aac`, fallback no-options. 실패 시 `capture_mode=text_only` metric 기록.

**2. Whisper file format / ffmpeg**
- Problem: Whisper webm 직접 수용을 "1차 시도, 실패 시 ffmpeg fallback"으로 처리하는 건 production path가 아니다.
- Why it bites: 첫날 샘플이 Chrome webm이면 통과하고, iOS mp4/aac에서 실패하거나 반대로 Cloud Run ffmpeg 미설치로 fallback이 죽는다. 503으로 UX가 끝난다.
- Fix: `backend/src/memory/service.py`에 `normalize_audio(input_bytes, content_type) -> wav_bytes`를 먼저 구현. `backend/Dockerfile`에 `ffmpeg` 설치를 R1 필수로 넣어라. API call은 `client.audio.transcriptions.create(model="whisper-1", file=wav_file)` 한 가지 포맷으로 고정.

**3. R1 latency 2s vs sync distill 모순**
- Problem: R1 acceptance `POST /memory returns 202 + distilled_json ≤2s p95`는 Whisper + Gemini 동기 호출과 모순이다.
- Why it bites: 5분 음성 업로드, transcription, R2 upload, Gemini distill을 한 request에서 끝내면 2초 p95는 불가능하다. 202를 쓰면서 body에 최종 distill을 요구하는 것도 의미가 충돌한다.
- Fix: `backend/src/memory/router.py`는 즉시 `202 {memory_id, status:"processing"}`만 반환. `backend/src/memory/service.py`는 `BackgroundTasks`로 `transcribe -> distill -> embed` 실행. FE는 `GET /api/v1/workspaces/{workspace_id}/memory/{memory_id}` polling.

**4. Gemini 2.5 Flash EOL 2026-06-17** ⚠️
- Problem: Gemini 2.5 Flash는 2026-06-17 discontinuation 예정인데 Sprint 15가 2026-05-14 시작이다.
- Why it bites: 14일 테스트가 끝나자마자 모델 EOL 리스크가 Sprint 16 의사결정을 오염시킨다. "Gemini `gemini-2.5-flash` 고정" 제약과 충돌한다.
- Fix: `docs/TODO.md`에 `P0: Gemini 2.5 Flash EOL 대응 ADR` 추가. 단기 코드는 `backend/src/core/config.py`에 모델 상수 유지하되, Day 0 spike에 "현재 모델 호출 가능 기간 / quota / deprecation warning" 체크를 포함.

**5. EmbeddingChunk signature change blast radius**
- Problem: `EmbeddingChunk.create_chunk`에 `source_workspace_id`를 추가하는 변경은 blast radius가 과소평가됐다.
- Why it bites: notes, meetings, inbox, upload, pipeline, test factory 중 하나라도 누락하면 런타임 TypeError 또는 잘못된 workspace embedding이 생긴다.
- Fix: `backend/src/embeddings/service.py`에 breaking signature 변경 금지. 대신 `create_chunk_for_source(source: EmbeddableSource)` wrapper를 추가하거나 기존 signature에 keyword-only optional을 두고 deprecation test를 작성. `rg "create_chunk\(" backend/src backend/tests` 결과를 R3 체크리스트 산출물로 문서화.

**6. capture 후 embedding 생성 경로 부재** ⚠️
- Problem: capture 후 embedding 생성 경로가 없다.
- Why it bites: R3 vector search는 `embedding_chunks`를 JOIN하지만 R1은 `status="embedding_pending"`만 저장한다. 결국 vector 결과는 항상 0이고 keyword fallback만 검증된다.
- Fix: `backend/src/memory/service.py` capture 성공 후 `BackgroundTasks.add_task(embedding_service.create_chunk, source_type="memory", source_id=item.id, workspace_id=item.workspace_id, content=distilled_text)` 추가. 실패 시 `memory_items.status='embedding_failed'`와 retry 대상 저장.

**7. pgvector SQL CAST 문제**
- Problem: pgvector SQL `CAST(:qvec AS vector)`에 Python list string을 넣는 방식은 깨질 가능성이 높다.
- Why it bites: asyncpg/SQLAlchemy가 vector literal을 기대한 형식으로 보내지 않으면 recall endpoint가 500을 낸다.
- Fix: `backend/src/memory/repository.py`에 `pgvector.sqlalchemy.Vector` 타입 또는 안전한 literal formatter를 중앙화. SQL 예: `ORDER BY ec.embedding <=> :query_embedding`을 typed bind로 처리.

**8. 기존 user backfill 누락**
- Problem: Personal workspace migration이 기존 사용자 backfill을 안 한다.
- Why it bites: 기존 사용자는 로그인 전까지 personal workspace가 없고, admin metric / FE active workspace / promote source workspace가 빈 상태로 깨진다. 외부 테스트 계정과 founder 계정 상태가 달라진다.
- Fix: alembic migration에 backfill SQL 추가:
```sql
INSERT INTO workspaces (id, owner_id, name, type, created_at)
SELECT gen_random_uuid(), u.id, COALESCE(u.display_name, '사용자') || '의 개인 Kairos', 'personal', now()
FROM users u
WHERE NOT EXISTS (
  SELECT 1 FROM workspaces w WHERE w.owner_id = u.id AND w.type = 'personal'
);
```

**9. first-login race condition**
- Problem: concurrent first-login race 처리에서 `IntegrityError` 후 `session.rollback()`이 user 생성까지 되돌릴 수 있다.
- Why it bites: 동시 요청 하나가 personal ws 충돌을 맞으면 user row 저장도 rollback되어 인증은 성공했는데 DB user가 없는 상태가 된다.
- Fix: `backend/src/auth/dependencies.py`에서 `INSERT ... ON CONFLICT DO NOTHING` 또는 nested transaction 사용. Personal seed는 raw SQL로 idempotent하게 분리:
```sql
INSERT INTO workspaces (id, owner_id, name, type)
VALUES (:id, :owner_id, :name, 'personal')
ON CONFLICT ON CONSTRAINT uq_workspaces_owner_personal DO NOTHING;
```

**10. R2 30일 TTL cleanup cron 위치 없음**
- Problem: R2 30일 TTL cleanup cron 실행 위치가 없다.
- Why it bites: Cloud Run은 stateless다. "cron job 1개"는 구현체가 아니고, R2 audio가 계속 쌓이며 개인정보 삭제 약속도 깨진다.
- Fix: GCP Cloud Scheduler → authenticated Cloud Run endpoint `POST /api/v1/admin/memory/r2-cleanup` 추가. 대상 파일은 `memory_items.r2_audio_key WHERE created_at < now() - interval '30 days'`.

**11. ProjectMember invariant R5 누락**
- Problem: ProjectMember invariant가 R5에 실제로 없다.
- Why it bites: workspace member-add만 막아도 project membership API가 personal workspace project에 멤버를 붙일 수 있으면 I-19가 우회된다.
- Fix: `backend/src/projects/service.py`의 `add_member` / invite / project visibility 변경 경로에 `workspace.type == "personal"` 가드 추가. 테스트는 `backend/tests/projects/test_personal_project_invariants.py`.

**12. fixtures 부재**
- Problem: 테스트 계획이 존재하지 않는 fixtures에 의존한다.
- Why it bites: `auth_user`, `memory_client`, `test_workspace`, `seed_memories`, Clerk JWT mock이 없으면 TDD가 첫날 fixture 공사로 전환된다.
- Fix: R1 전에 `backend/tests/conftest.py`에 `auth_user`, `bearer_header`, `override_get_current_user`, `personal_ws`, `team_ws` fixture를 먼저 만드는 T-1 태스크 추가.

### AXIS B — PERSONA outreach realism (7 issues)

**1. 5 PERSONA / 7일 cold outreach 비현실적**
- Problem: 5 PERSONA / 7일은 cold outreach로는 비현실적이다.
- Why: 인디해커즈/X/HN에서 5명 demo + 7일 commitment를 받는 건 "관심 클릭"이 아니라 높은 마찰의 user research다. 응답 5명이 아니라 완료 5명이 필요하다.
- Fix: R8 목표를 `outreach 80명 -> booked 8명 -> completed demo 5명 -> day-7 retained 3명` funnel로 바꿔라. `docs/dev-log/sprint-15-r8-outreach.md`에 channel별 sent/open/reply/book/show/retained 컬럼 추가.

**2. Day 3 gate too late**
- Problem: Day 3 `0/5이면 확장`은 너무 늦다.
- Why: 14일 일정에서 Day 3까지 기다리면 booking 가능한 캘린더가 Day 5 이후로 밀린다. 7일 testing window가 Day 12까지 못 끝난다.
- Fix: Day 0에 cold 50건 발송. Day 1 0 booked면 즉시 warm intro / 유료 리서치 / founder network DM로 확장. Day 3은 "0 응답"이 아니라 "3 demos booked 미만" gate로 바꿔라.

**3. Minimum criteria 정의 문제**
- Problem: Day 7 `≤1명 응답 시 Minimum으로 자동 조정`은 success criteria가 아니라 실패 기준 완화다.
- Why: 외부 demand 검증이 목표인데 founder-only fallback이 통과로 취급된다. PRD pivot이 다시 founder mental model로 고정된다.
- Fix: Minimum을 "Sprint 16 build freeze + outreach sprint 강제"로 정의. `founder + 1`은 product validation으로 인정하지 말고 operational fallback으로만 기록.

**4. Outreach subject 약함**
- Problem: 메시지 subject가 약하다.
- Why: "AI memory layer 5분 인터뷰 + 1주 testing"은 창업자 입장에서 받을 가치가 안 보인다. AI 툴 홍보 DM로 보인다.
- Fix: opening을 problem-first로 바꿔라. 예:
```text
혹시 창업 아이디어/결정 메모를 Notion, Apple Notes, DM에 흩어놓고 나중에 못 찾는 편인가요?
7일짜리 작은 prototype을 테스트 중입니다. 30분만 화면공유로 써보고, 마음에 안 들면 바로 끊어도 됩니다.
조건: 최근 7일 안에 실제로 다시 찾고 싶었던 메모/생각이 있어야 합니다.
```

**5. HN-Show / Reddit 부적합 (Korean founder)**
- Problem: HN Show / Reddit r/SaaS는 Korean founder의 7일 테스트 모집 채널로 부적합하다.
- Why: 글로벌 audience는 영어 데모, timezone, trust, signup friction이 크다. Korean founder의 한국어 제품/문서/Clerk flow와 맞지 않는다.
- Fix: 1차 채널을 warm Korean builder network로 고정. HN/Reddit은 "landing interest" 용도만. R8에는 `warm_intro`, `indie_kr`, `x_dm_kr`, `paid_research`를 별도 채널로 분리.

**6. dropout 모델 없음**
- Problem: dropout 모델이 없다.
- Why: 30분 demo에 동의한 사람 중 상당수는 7일 동안 capture 0회로 끝난다. 계획은 demo agreement를 retained testing으로 착각한다.
- Fix: R8 acceptance를 `day-2 activation`으로 쪼개라. 기준: demo 후 48시간 내 PERSONA당 capture ≥3, recall ≥1. 미달자는 dropout으로 처리하고 replacement pool 5명을 계속 모집.

**7. unprompted signal 5표본 측정 불가**
- Problem: "unprompted 없으면 불편"은 5명 표본에서 측정 불가능에 가깝다.
- Why: 인터뷰 진행자가 기다린다고 unprompted signal이 생기지 않는다. 반대로 founder demo 직후의 표현은 courtesy bias다.
- Fix: 질문을 행동 기반으로 바꿔라. `지난 7일 중 Kairos가 없었으면 어느 메모를 어디서 찾았을지`, `이걸 계속 쓰기 위해 지금 $10 결제할지`, `다음 주에도 5개 이상 capture할지`를 interview form에 고정.

### AXIS C — Cost / Latency validation (7 issues)

**1. Whisper 비용 10× 틀림** ⚠️
- Problem: 계획은 `$0.06/min × 5min × 50 = $15`라고 쓰지만 현재 OpenAI transcription pricing은 `gpt-4o-transcribe $0.006/min`, `gpt-4o-mini-transcribe $0.003/min`로 표시된다. 50건 × 5분이면 $1.50 또는 $0.75다. `whisper-1` 가격/모델 선택은 현재 pricing 표와 불일치한다.
- Fix: Day 0 spike 문서에 실제 모델명을 고정: `whisper-1` 유지인지 `gpt-4o-mini-transcribe` 전환인지 결정. `docs/dev-log/sprint-15-cost-spike.md`에 `model, minutes, billed_cost, p50, p95, failure_rate` 기록.

**2. Gemini distill "ignored" 틀림**
- Problem: Gemini distill "ignored"는 틀렸다. 작아도 측정해야 한다.
- Why: Gemini 2.5 Flash는 output/thinking token이 비용을 만든다. JSON schema 실패 재시도까지 넣으면 호출 수가 150이 아니라 200~300이 된다.
- Fix: `backend/src/memory/service.py`에서 `response.usage_metadata`를 저장하는 `memory_ai_calls` 테이블 추가. Day 0 invalidation threshold: distill p95 > 3s, parse failure > 10%, retry rate > 10%, cost per capture > $0.02면 R1 sync distill 금지.

**3. OpenAI embedding latency 무시**
- Problem: OpenAI embedding "ignored"는 latency 관점에서 틀렸다.
- Why: 비용은 작아도 recall query마다 embedding call이 들어가면 p95 2초를 잡아먹는다. 검색 자체보다 remote embedding이 병목이다.
- Fix: query embedding cache 추가:
```sql
CREATE TABLE memory_query_embedding_cache (
  workspace_id uuid NOT NULL,
  normalized_query text NOT NULL,
  embedding vector(1536) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, normalized_query)
);
```

**4. R1 latency p95 ≤2s wrong metric**
- Problem: R1 latency p95 ≤2s는 wrong metric이다.
- Why: capture endpoint는 업로드 크기, Whisper, Gemini, R2, DB commit을 포함한다. 2초 안에 끝내려면 기능을 가짜로 만들거나 실패율을 숨기게 된다.
- Fix: metrics를 분리: `POST /memory enqueue p95 ≤500ms`, `transcription job p95 ≤45s for 5min audio`, `distill p95 ≤3s`, `embedding p95 ≤1s`, `recall p95 ≤2s`.

**5. Day 0 spike scope 정의 없음**
- Problem: Day 0 10-sample spike가 무엇을 측정할지 정의가 없다.
- Why: "10 sample call"만 하면 happy-path 10개로 통과 선언한다. production 실패는 iOS MIME, 0초 녹음, 긴 음성, 한국어 발화, 조용한 오디오, Gemini JSON 파싱에서 나온다.
- Fix: Day 0 spike 샘플을 고정:
  - Chrome webm 10s / 60s / 5min
  - Safari iOS mp4/aac 10s / 60s
  - 한국어 filler 많은 음성 60s
  - 무음/저음질 10s
  - 텍스트 500자 / 3000자 / 10000자
  - 실패 케이스 25MiB 초과
- Invalidate thresholds: transcription failure > 5%, end-to-end job p95 > 60s, Gemini JSON invalid > 10%, total cost per active tester per week > $2, recall p95 > 2s at 100 seeded chunks.

**6. pgvector p95 + Neon cold start**
- Problem: pgvector p95 "small N이면 당연히 빠름"은 Neon cold start / connection / embedding call을 빼먹은 계산이다.
- Why: DB vector query 30ms여도 serverless connection + OpenAI embedding + app cold start가 2초를 넘긴다.
- Fix: `backend/tests/perf/test_memory_recall_latency.py`에 seeded 100 chunks 기준 실제 HTTP p95 측정 추가. query stages를 `embed_ms`, `db_ms`, `fallback_ms`, `total_ms`로 로깅.

**7. R7 in-memory latency tracker Cloud Run 무효**
- Problem: R7 in-memory latency tracker는 Cloud Run에서 의미 없다.
- Why: instance scale-out/restart 시 counter가 리셋되고, founder admin page가 거짓 p95를 보여준다.
- Fix: DB metrics table 사용:
```sql
CREATE TABLE memory_events (
  id uuid PRIMARY KEY,
  workspace_id uuid NOT NULL,
  user_id uuid NOT NULL,
  event_type text NOT NULL,
  latency_ms integer,
  created_at timestamptz NOT NULL DEFAULT now()
);
```
R7 `/metrics`는 이 테이블에서 percentile 계산.

---

## §2. VERDICT

**FIX iter 1 (20 issues 사전 수정 권장)**:

```
A1, A2, A3, A4, A6, A8, A9, A10, A11, A12
B1, B2, B3, B6
C1, C2, C3, C4, C5, C7
```

A5/A7/B4/B5/B7/C6는 정보 제공 — plan 수정 권장이지만 R1 진입 차단 정도는 아님.

---

## §3. Synthesis Recommendation (Claude 입장)

**Recommendation**: Plan FIX iter 1 진입 — codex 지적 중 R1 진입 직전 차단 항목 7개 + R2 진입 차단 항목 3개 만 우선 fix, 나머지는 R8 outreach realism은 Day 0 outreach 시작 전 fix.

근거 (비교):
- **R1 진입 차단 (즉시 fix)**: A3 (2s p95 wrong metric — sync distill 불가) / A6 (embedding 경로 부재) / A12 (fixtures 부재) / C4 (latency metric 분리) / C5 (Day 0 spike scope) — 이 7개 없으면 R1 TDD가 첫날부터 막힘.
- **R2/R5 진입 차단 (T0/R2 fix)**: A8 (기존 user backfill) / A9 (race condition) / A10 (R2 cron 위치) — alembic migration + service 코드와 atomic.
- **R8 outreach 차단 (Day 0 직전 fix)**: B1 (funnel definition) / B2 (Day 3 too late) / B3 (Minimum criteria) — outreach 시작 시점에 정합.
- **잔여 fix R7/R6 시점에 처리**: A1 (MediaRecorder Safari) / A2 (ffmpeg) / A4 (Gemini EOL ADR) / A11 (ProjectMember) / C1 (Whisper 비용 실측) / C2 (Gemini usage table) / C3 (embedding cache) / C7 (Cloud Run metrics table).

---

## §4. Stage 4 진입 결정 gate

| 옵션 | 의미 | 추천 여부 |
|------|------|----------|
| GO as-is | sprint-15-plan.md 그대로 R1 진입 | ❌ 위험 |
| **FIX iter 1** | 본 doc의 20 issue 중 우선 7개 (R1 진입 차단) + 3개 (R2/R5 atomic) + 3개 (R8 outreach) = 13개 plan patch 1회 → R1 진입 | ✅ 추천 |
| Pivot | wedge 자체 재고 | ❌ 본 검토는 wedge가 아닌 구현 detail 지적 |

**다음 단계**: plan patch FIX iter 1 작성 후 R1 진입.
