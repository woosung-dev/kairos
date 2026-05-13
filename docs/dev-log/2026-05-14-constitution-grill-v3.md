<!-- Sprint 15 Stage 0 grill-with-docs 산출 — 헌법 v3.0 patch 적대적 검증 결과 -->

# Constitution Grill v3.0 — Sprint 15 Stage 0 (2026-05-14)

> **목적**: PRD v3.0 (Personal↔Team IA 2축) + ADR-016 lock-in 후 헌법 patch 진행 전 6 영역 적대적 검증.
> **방법**: workflow.md Stage 0 `/grill-with-docs` skill.
> **결과**: I-9 강화 + I-18 신설 + I-19 신설 본문 lock-in. R-13은 Sprint 18+ ADR-017 deferral.
> **다음**: Stage 1 `/office-hours` → `/autoplan`.
> **참고**: `docs/dev-log/016-personal-team-ia.md` (ADR-016), `docs/dev-log/2026-05-14-sprint15-handoff.md` (인계 brief), `CONTEXT-MAP.md` (헌법 root).

---

## §0. Context

### 0.1 grill 개시 시점 상태

- **메인 브랜치**: PR #27 (Sprint 14 trust-stabilize) + PR #28 (PRD v3.0 + ADR-016) 머지 완료 (commit 8311620 + bd43733/09dbc5b).
- **현 브랜치**: `sprint-15/personal-workspace` (origin/main 분기).
- **사전 정리 commit**: `d7faee1` (handoff doc cherry-pick), `ff4c011` (I-17→I-18 slot 충돌 정정 9건).

### 0.2 grill 대상 (handoff §3 + 사전 발견 D-2)

- **Q1**. I-18 신설 (Promotion 복제 + tombstone) edge case
- **Q2**. I-9 강화 (Personal workspace 격리) backward compatibility
- **Q3**. R-13 (cross-ws RAG opt-in) 사전 검증
- **Q4**. Promotion + RAG 임베딩 격리
- **Q5**. Workspace switcher state management (Sprint 14 T-7 패턴 재사용)
- **Q6**. CONTEXT-MAP invariant slot 충돌 정정 (D-2 발견)

### 0.3 산출 형식 규칙 (사용자 lock-in)

각 Q마다 5섹션 strict:
1. 적대적 케이스 (counter-example listing)
2. **[확정]** Sprint 15-16 즉시 적용 (v1.5/v1.6 lock-in)
3. **[권장]** Sprint 17+ defer (별도 ADR-017/018에서 결정, 사전 제약 명시)
4. 영향 task (현 Sprint + 미래 Sprint task 등재 explicit — 누락 방지)
5. Open question (O-α/β/γ 라벨)

---

## §1. Q1 — I-18 신설 (Promotion 복제 + tombstone) edge case

### 1.1 적대적 케이스

| Case | 시나리오 | Risk |
|------|---------|------|
| 1-A | Promote 후 원본 personal 수정 시 복제본 team에 sync? | sync 시 양방향 conflict 폭증 |
| 1-B | Team admin reject 시 원본 복원 정책? | reject 정의 모호 (명시 vs 묵시) |
| 1-C | Promote 후 원본 삭제 시 tombstone-only 잔존? | hard delete 시 audit chain 단절 |
| 1-D | 동일 아이템 multi-team promote? | 임베딩 N배 cost 발산 |
| 1-E | Personal → Team A → Team B chain promote? | 원본 추적 (immediate vs full chain) |

### 1.2 [확정] Sprint 15-16

- **1-A sync 없음** (`promote = snapshot copy`). 원본 수정/삭제 후에도 team 복제본 독립 진화. AD-41 "복제 + tombstone" 정합.
- **1-B v1.6 admin auto-accept**. 명시적 reject API 없음. Team admin이 복제본 수동 삭제만 가능. 1인 founder 마찰 해소.
- **1-C 원본 soft delete만 허용** (`tombstone status = promoted_deleted`). 복제본 영향 0. hard delete 차단. 모든 4 엔티티 (Note/Meeting/Action/InboxItem) `deleted_at` 신설.
- **1-D multi-team promote 허용**. 원본 tombstone = array (`promoted_to: [{team_a_id, item_a_id}, ...]`). M5 moat 자유도 보장.
- **1-E chain promote 허용**. tombstone 컬럼 = immediate parent. 전체 chain은 별도 `promotion_audit` 테이블.

### 1.3 [권장] Sprint 17+ defer

- **ADR-018 (Sprint 17+)**: v1.7 review queue — admin reject 후 원본 자동 복원 정책 (Q1 O1-α).
- **ADR-018 (M5 v2.0)**: 원본 수정 시 team 멤버 알림 (push / digest, opt-in). Q1 O1-β.

### 1.4 영향 task

| ID | Sprint | 작업 |
|----|--------|------|
| **S16-T2** | 16 | Promotion API + 4 엔티티 soft delete + tombstone 컬럼 + multi-team / chain promote 지원 |
| **S16-T3** | 16 | 헌법 I-18 신설 + `promotion_audit` 테이블 schema |
| **S17-T-AD18A** | 17+ | ADR-018: review queue (1-B reject 정책) + 원본 변경 알림 (1-A sync notification) |
| **S?-T-DELEGATE** | TBD | `promoted_on_behalf_of` (대리 promote, team lead가 멤버 작업 승격) — Q1 O1-γ |

### 1.5 Open question

- **O1-α** (Sprint 17): admin reject 후 원본 `promoted` → `active` revert 자동? 사용자 수동?
- **O1-β** (Sprint 18+ M5): 원본 수정 시 team 멤버 알림 — opt-in 메커니즘 (push / email digest)?
- **O1-γ**: `promoted_on_behalf_of` (대리 promote) 케이스 — 권한 모델 + audit log 형식?

---

## §2. Q2 — I-9 강화 (Personal workspace 격리) backward compatibility

### 2.1 적대적 케이스

| Case | 시나리오 | Risk |
|------|---------|------|
| 2-A | Workspace.type 컬럼 vs 별도 모델 (PersonalWorkspace 분리)? | 별도 모델 시 모든 repo query 분기 폭증 |
| 2-B | 기존 ws 마이그레이션 옵션 (a/b/c)? | 옵션 b: 1명 정의 모호. 옵션 c: UX 부담 |
| 2-C | Personal ws 강제 보유 invariant (삭제/rename/중복)? | 삭제 시 사용자 personal 데이터 잃음 |
| 2-D | 마이그레이션 스크립트 idempotency? | 재실행 시 중복 personal 발산 |
| 2-E | 신규 가입 시 personal seed 시점 (webhook vs lazy)? | webhook 실패 시 personal 부재 |

### 2.2 [확정] Sprint 15

- **2-A**: `Workspace.type: ENUM('personal','team') NOT NULL DEFAULT 'team'` 컬럼 추가. Project.visibility enum 패턴 재사용. Service layer에서 type filter 분기.
- **2-B**: **옵션 a + 1회성 마이그레이션 스크립트**. 기존 ws 모두 `type='team'` 유지 + 모든 user에 personal seed (idempotent: `INSERT ... ON CONFLICT DO NOTHING`).
- **2-C**:
  - Personal 삭제 차단 (`HTTP 403 PersonalWorkspaceProtected`). 계정 cascade 삭제 시만 OK.
  - Rename 허용 (디폴트 `{사용자명}의 개인 Kairos`).
  - 중복 차단: DB UNIQUE partial index `(owner_id) WHERE type='personal'`.
- **2-D**: **2단계 배포**. (1) alembic schema migration (type 컬럼 + UNIQUE partial index). (2) 별도 data migration (personal seed, idempotent).
- **2-E**: **첫 로그인 시 lazy seed** (`auth/dependencies.py:get_current_user` 또는 별도 `personal_workspace_service`). webhook 의존 0.

### 2.3 [권장] Sprint 17+ defer

- **Personal ws 명칭 i18n koKR** (Sprint 14 T-3 Clerk koKR 패턴 재사용). Q2 O2-γ.

### 2.4 영향 task

| ID | Sprint | 작업 |
|----|--------|------|
| **S15-T1** | 15 | BE personal 자동 시드 (lazy on first login + UNIQUE partial index) |
| **S15-T1.5** | 15 | BE data migration 스크립트 (기존 user에 personal seed, idempotent) |
| **S15-T3** | 15 | Personal 권한 모델 schema + `type` 컬럼 + member 추가/삭제 차단 invariant + `PersonalWorkspaceProtected` 예외 |
| **S15-T5** | 15 | 온보딩 UX (기존 ws → team 안내 + 개인 작업 → personal 배너) |
| **S?-T-PERSONAL-I18N** | TBD | Personal ws 명칭 i18n koKR |

### 2.5 Open question

- **O2-α**: Personal ws `inbox_threshold` 기본값 — team 기본값(0.9) 재사용? 별도 default?
- **O2-β**: Founder 본인이 만든 team ws에서 personal ws로 promote 가능? — **일단 차단** (Personal은 promote 목적지 아님, AD-41).
- **O2-γ**: Personal ws 명칭 i18n (Clerk koKR locale 정합).

---

## §3. Q3 — R-13 (cross-ws RAG opt-in) 사전 검증

### 3.1 적대적 케이스

| Case | 시나리오 | Risk |
|------|---------|------|
| 3-A | Personal RAG ↔ Team RAG 완전 분리? | privacy 침해 (admin이 다른 user personal 접근) |
| 3-B | Opt-in 통합 검색 UX (v1.8)? | I-9 단일 필터 무너짐 |
| 3-C | Admin이 다른 user personal 접근? | 법적 disclosure 요구 vs privacy |
| 3-D | RAG query workspace_id expand 메커니즘? | SQL IN vs application layer merge |

### 3.2 [확정] Sprint 15-17

- **3-A default 격리 유지**. 현 I-9 패턴 그대로 (`embeddings/repository.py:68` 단일 `workspace_id = :wid`). v1.5~v1.7까지 cross-ws 옵션 0. **코드 변경 0**.
- **3-C admin/owner 권한 무관, 다른 user personal 접근 0건 강제**. 본인 owned personal만 통합 검색 대상. 법적 disclosure 요구는 RAG API 외부 (별도 admin trail).

### 3.3 [권장] Sprint 18+ defer (ADR-017 정식 결정)

R-13 본문 후보:

> **R-13 (Sprint 18+ ADR-017에서 정식 신설)**: Cross-workspace RAG은 default 차단. 통합 검색은 (a) 사용자 본인 owned personal + 본인 멤버 team으로만 expand, (b) 검색 결과 chunk metadata에 `source_workspace` 강제 포함, (c) admin/owner도 다른 user personal 접근 0건, (d) SemanticCache cross-ws disabled, (e) 권한 변경 시 사용자별 cache 강제 무효화.

- **3-B 통합 검색 UX**: 결과 segment 표시 vs 단일 ranked list (O3-α).
- **3-D SQL IN expand**: 사용자 owned ws 리스트 service layer 검증 후 repo로 전달.

### 3.4 영향 task

| ID | Sprint | 작업 |
|----|--------|------|
| (현 Sprint 15-16 task 영향 0) | — | default 격리 유지 = 기존 코드 그대로 |
| **S17-T-AD17A** | 17~18 | ADR-017 작성 — 통합 검색 UX + expand 정책 + cache invalidate |
| **S18-T-RAG-XWS** | 18 | cross-ws RAG SQL IN expand 구현 + service layer 권한 검증 |
| **S18-T-CACHE-INV** | 18 | SemanticCache cross-ws invalidate 메커니즘 (권한 변경 trigger) |
| **S?-T-ADMIN-AUDIT** | TBD | 법적 disclosure admin audit endpoint (RAG 외부) — Q3 O3-γ |

### 3.5 Open question

- **O3-α** (ADR-017): 통합 검색 결과 segment 표시 vs 단일 ranked list.
- **O3-β** (ADR-017): SemanticCache cross-ws 활성화 시 cache key ws 조합 hash.
- **O3-γ**: 법적 disclosure 요구 audit API — 별도 admin endpoint scope.
- **O3-δ**: Team owner의 그 team 내 다른 멤버 personal 접근 0 invariant — owner 권한과 직교 (3-C 정합).

---

## §4. Q4 — Promotion + RAG 임베딩 격리

### 4.1 적대적 케이스

| Case | 시나리오 | Risk |
|------|---------|------|
| 4-A | 옵션 X (임베딩 2벌 신규 생성) vs 옵션 Y (메타데이터 array)? | 옵션 Y: I-9 단일 필터 침해 |
| 4-B | Promotion 시점 임베딩 처리 흐름 (동기 vs async)? | 동기: latency 폭증. async: feedback 부재 |
| 4-C | Chunk 수준 격리 강제 패턴 (I-9 강화)? | service 검증 누락 시 cross-ws leak |
| 4-D | 임베딩 audit log + retry 정책? | API fail 시 복제본 RAG-invisible |

### 4.2 [확정] Sprint 16

- **4-A 옵션 X (임베딩 2벌 신규 생성)**. workspace_id 강제 매칭. I-9 무손상 + Q1-A snapshot copy 정합 + Q3 default 격리 정합. 비용 trade-off 수용 ($0.0004/회의, 1k 회의 = $0.40).
- **4-B 202 Accepted + BackgroundTask + status polling** (backend rules §8 기존 패턴 재사용).
  1. Promotion API → 복제본 entity 신규 + tombstone + `status='embedding_pending'`. 202 + `promotion_id` return.
  2. BackgroundTask: 복제본 기반 임베딩 재생성 → 신규 EmbeddingChunk insert with new `workspace_id`.
  3. 완료 → `status='active'`. 실패 → `status='embedding_failed'`.
  4. FE polling `/promotions/{id}/status`.
- **4-C service layer write 검증**. `PromotionService.create_promotion`에서 `EmbeddingChunk.workspace_id == target_team_workspace_id` assertion (I-17 cross-ws 패턴 재사용). 신규 `source_id` = 복제본 entity id.
- **4-D `promotion_audit` 임베딩 단계 컬럼 포함**: `embedding_status: pending|processing|completed|failed`, `embedding_completed_at`, `embedding_error_message`. Idempotency: 복제본 entity id 기준 UNIQUE.

### 4.3 [권장] Sprint 17+ defer

- **임베딩 retry queue + exponential backoff** (Q4 4-D 권장). 별도 ADR 또는 S17 task.

### 4.4 영향 task

| ID | Sprint | 작업 |
|----|--------|------|
| **S16-T2** | 16 | Promotion API + BackgroundTask + status polling + 임베딩 2벌 생성 (옵션 X) |
| **S16-T2.5** | 16 | `promotion_audit` 테이블 schema (Q1 1-E + Q4 4-D) — embedding_status 포함 |
| **S16-T3** | 16 | 헌법 I-9 강화 (4-C inline patch) + I-18 신설 (Q1) |
| **S17-T-EMBED-RETRY** | 17+ | 임베딩 실패 retry queue + exponential backoff |
| **S?-T-EMBED-MIG** | TBD | 기존 RAG repo의 신규 EmbeddingChunk insert 시점 service assertion 추가 (코드 grep 후 도출) |

### 4.5 Open question

- **O4-α**: 임베딩 재생성 시 chunking 재실행 (`512 token 청크 + 50 overlap`) — **재실행 권장** (원본 chunking outdated 가능).
- **O4-β**: Multi-team promote (Q1 1-D) 시 N벌 임베딩 cost 누적 — abuse 시점 ADR.
- **O4-γ**: SemanticCache key에 workspace_id 포함 강제 확인 — 코드 grep follow-up.

---

## §5. Q5 — Workspace switcher state management

### 5.1 적대적 케이스

| Case | 시나리오 | Risk |
|------|---------|------|
| 5-A | Personal+Team list fetch + switcher 표시 + active default? | type 구분 없으면 사용자 혼란 |
| 5-B | switcher click invalidate 범위 (전역 vs scoped)? | 전역 clear: latency 폭증 |
| 5-C | URL `?ws=` query 동기화 충돌? | back/forward 시 store stale |
| 5-D | SSR / RSC active workspace 결정? | Zustand store 서버 접근 불가 |
| 5-E | 기존 16개 사용 site 마이그레이션 cost? | 일괄 변경 시 typecheck 깨짐 |

### 5.2 [확정] Sprint 15

- **5-A**: `useWorkspaces` hook 결과에 `type` 필드 포함. switcher UI에 Personal 배지 + Team 그룹 시각 분리 (Notion 패턴). 정렬 = personal first → team (최근 사용순). active default = personal (신규) / 마지막 사용 (기존).
- **5-B scoped invalidate + query key factory 강제**. 각 도메인 `features/[domain]/api.ts`에 factory 추가, 첫 arg = `workspaceId` 강제. switcher click → `queryClient.removeQueries({ predicate: q => q.queryKey[1] === prevWorkspaceId })`. 로그아웃 시 `queryClient.clear()` 유지 (T-7 fix 정합).
- **5-C URL = source of truth, store = mirror**. Page 진입 시 URL `?ws=` 읽음 → store sync. 권한 fail (403) → personal로 redirect + toast. back/forward → useEffect on `searchParams`.
- **5-D Server fetch는 URL `?ws=` 또는 user's personal ws**. proxy.ts protected route 진입 시 `?ws=` 없으면 server-side DB lookup → personal ws id로 redirect. Server Component는 searchParams 기반 fetch. Zustand 사용 0.
- **5-E 점진적 migration**. S15-T2에서 신규 패턴 lock-in + 신규 site만 강제. 기존 16 site는 현 패턴 유지 (T-7 fix 그대로 동작). Sprint 17+ cleanup task로 등재.

### 5.3 [권장] Sprint 17+ defer

- **기존 16 site refactor** (URL-as-source-of-truth 패턴 일괄 강제).
- **권한 stale bookmark / share link 정책** (5-C 권장) — 별도 ADR.
- **Server-side workspace context** (Async Local Storage / RSC context) 도입 검토 (5-D 권장).

### 5.4 영향 task

| ID | Sprint | 작업 |
|----|--------|------|
| **S15-T2** | 15 | FE switcher UI (Notion 패턴) + Personal/Team 배지 + scoped invalidate + URL `?ws=` sync + proxy.ts redirect |
| **S15-T2.5** | 15 | Query key factory 정리 (신규 패턴 lock-in, 기존 16 site는 현 유지) |
| **S15-T7** | 15 | proxy.ts personal redirect DB lookup 비용 OpenTelemetry 메트릭 |
| **S17-T-WS-NORMALIZE** | 17+ | 기존 16 site refactor (URL-as-source-of-truth 패턴 일괄 강제) |
| **S17-T-WS-SHARELINK** | 17+ | 권한 stale bookmark / share link 정책 별도 ADR (5-C 권장) |
| **S17-T-RSC-WS-CTX** | 17+ | Server-side workspace context (Async Local Storage / RSC context) 도입 검토 (5-D 권장) |

### 5.5 Open question

- **O5-α**: switcher UI 정렬 — personal first vs 최근 사용 first (DESIGN.md Stage 2 patch).
- **O5-β**: 모바일 switcher UI — 햄버거 list vs FAB (Sprint 14 T-10 패턴 참고, Stage 3 design-shotgun).
- **O5-γ**: active ws 변경 직후 inflight 요청 (이전 ws 데이터) 처리 — abort signal vs 결과 ignore.

---

## §6. Q6 — CONTEXT-MAP invariant slot 충돌 정정 (D-2 발견)

### 6.1 적대적 케이스

| Case | 시나리오 | Risk |
|------|---------|------|
| 6-A | 정정 commit (ff4c011) 사후 검증 | Promotion 의미 I-17 잔존? |
| 6-B | I-18 본문 lock-in scope (분리 vs 통합)? | 본문 길어짐 / 직교 invariant 폭증 |
| 6-C | I-9 강화 + I-19 신설 scope (Sprint 15)? | invariant 본문 vs 코드 atomicity |
| 6-D | R-13 슬롯 reservation? | CONTEXT-MAP에 R-X 섹션 부재 |
| 6-E | 헌법 patch PR 분리 vs 통합? | review 부담 vs 코드 atomicity |

### 6.2 [확정] Sprint 15-16

- **6-A 정정 commit `ff4c011` 검증 완료**. grep `*.py *.ts *.tsx *.md` clean. Promotion 의미 I-17 잔존 0건. 기존 I-17 의미(cross-ws ProjectMember) 표기 5건 (CONTEXT-MAP/TODO:79/qa-report 2건/erd) 의도된 유지.
- **6-B I-18 단일 invariant + I-9 강화 (4-C)는 I-9 본문 inline patch**. I-18 본문 (Q1 1-A~1-E + Q4 4-C 통합):

  > `I-18` **Promotion 불변식**: 모든 promote는 (a) 원본 보존 + soft delete만 허용, (b) workspace_id 변경 = 신규 entity 복제, (c) 원본 tombstone에 `promoted_to` 기록 + 복제본 tombstone에 `promoted_from` 기록, (d) `promotion_audit` 테이블에 chain audit log 강제 + EmbeddingChunk 단계 포함, (e) 이동(move) / sync 금지, (f) cross-workspace 데이터 이전은 audit log 없으면 503. — `backend/src/promotions/service.py` (Sprint 16 신설)

- **6-C I-9 patch + I-19 신설 Sprint 15 (S15-T3)**.

  I-9 patch (4-C inline):

  > `I-9` **멀티테넌시 격리**: 모든 Repository는 `workspace_id` 필터 강제. 신규 EmbeddingChunk insert 시 `workspace_id`는 신규 entity owner workspace와 매칭 (service layer assertion). — `<domain>/repository.py`, `backend/src/embeddings/service.py:create_chunk`

  I-19 신설 (Q2):

  > `I-19` **Workspace type invariant**: 모든 Workspace는 `type: 'personal' | 'team'`. Personal은 (a) owner 1명 강제 (DB UNIQUE partial index on `(owner_id) WHERE type='personal'`), (b) 멤버 추가/초대 차단 (service + WorkspaceMember insert 검증 → `PersonalWorkspaceProtected(403)`), (c) 삭제 차단 (계정 cascade 외), (d) 모든 user 자동 보유 (lazy seed on first login). — `backend/src/workspaces/service.py`, alembic `add_workspace_type.py`

- **6-D R-13 슬롯 reservation 안 함**. CONTEXT-MAP에 Rules (R-X) 섹션 부재 확인. R-13은 PRD/handoff/ADR-016에서 placeholder label로만 사용.
- **6-E 2 PR 분리**. Sprint 15 S15-T3 PR (I-9 patch + I-19) + Sprint 16 S16-T3 PR (I-18). 헌법 invariant + 코드 atomicity 보장.

### 6.3 [권장] Sprint 18+ defer

- **R-13 정식 slot 결정** (ADR-017 시점): 옵션 a (R-X 섹션 신설 + R-13 점유) vs 옵션 b (I-X slot로 흡수, e.g. I-20).

### 6.4 영향 task

| ID | Sprint | 작업 |
|----|--------|------|
| **ff4c011 검증** | 15 (완료) | 9건 I-17→I-18 정정 commit grep clean 검증 |
| **S15-T3 patch scope** | 15 | I-9 본문 patch (4-C EmbeddingChunk 강제) + I-19 신설 (Workspace type) atomic |
| **S16-T3 patch scope** | 16 | I-18 신설 (Promotion 불변식) + `promotion_audit` schema atomic |
| **S18-T-AD17-SLOT** | 18+ | R-13 정식 slot 결정 (R-X 섹션 신설 vs I-X 흡수) — ADR-017 시점 |

### 6.5 Open question

- **O6-α**: I-19 본문에 Personal ws 명칭 디폴트 포함? — **invariant 본문 외**. 디폴트 명칭은 정책 (service + DESIGN.md Stage 2).
- **O6-β**: `promotion_audit` schema retention 정책 (영구 vs N년 archive) — **Sprint 16 영구 default. retention은 Sprint 17+ admin trail (Q3 O3-γ)과 함께**.

---

## §7. 사전 발견 (Pre-grill discoveries)

핸드오프 prompt 가정과 실제 repo 상태 mismatch 3건. grill 진입 전 사용자 confirm 후 처리.

### 7.1 D-1. handoff doc main에 부재 (해소 — d7faee1)

- **사실**: commit `0bb19ae` (263줄)이 `docs/prd-v3-ai-memory-layer` 브랜치에만 존재. PR #28 squash merge로 main에 누락.
- **처리**: `git cherry-pick 0bb19ae` on sprint-15/personal-workspace → commit `d7faee1`.
- **검증**: `ls docs/dev-log/2026-05-14-sprint15-handoff.md` 존재.

### 7.2 D-2. CONTEXT-MAP I-17 slot 충돌 (해소 — ff4c011)

- **사실**: `CONTEXT-MAP.md:201` I-17 = Sprint 7 BE-T13 cross-workspace ProjectMember 추가 차단 (`backend/src/projects/service.py:add_member`). Promotion 불변식 아님.
- **mismatch**: ADR-016 AD-41 + handoff §1.4 + TODO S16-T3 모두 "I-17 신설 (Promotion)" 표기.
- **처리**: 9건 일괄 I-17 → I-18 정정 atomic commit (`ff4c011`).
  - ADR-016: §4 헌법 갱신 + Sprint 16 task table + Follow-ups F2 (3건)
  - handoff: 결정 lock-in §1.4 + Stage 0 다이어그램 + Q1 제목 + S16-T3 table + 다음 read 순서 (5건)
  - TODO.md: S16-T3 (1건)
- **검증**: grep `I-17` 결과 잔존 5건 모두 기존 의미 (cross-ws ProjectMember). Promotion 의미 잔존 0건.

### 7.3 D-3. CONTEXT-MAP 위치 — repo root, docs/ 아님 (deferred)

- **사실**: `/CONTEXT-MAP.md` (repo root). handoff prompt + 일부 doc reference에 `docs/CONTEXT-MAP.md` 잘못 표기.
- **처리**: handoff doc line 201 정정 완료 (ff4c011 포함). 다른 표기 (CLAUDE.md / 기타) 일괄 정정은 deferred — Sprint 15 cleanup commit 시점에 별도 task.
- **영향 task**: `S15-T-D3-CLEANUP` — CLAUDE.md + docs 전체 grep `docs/CONTEXT-MAP.md` 일괄 정정.

---

## §8. Future Sprint task backlog (누락 방지)

본 grill에서 defer 결정된 task의 explicit listing. Sprint 15 종료 commit 시 `docs/TODO.md` Sprint 17+ 후보 섹션에 반영.

### 8.1 Sprint 17 candidates

| ID | 영역 | 출처 |
|----|------|------|
| **S17-T-AD18A** | ADR-018 작성: Promotion review queue + 원본 변경 알림 (Q1 1-B, 1-A) | Q1 O1-α, O1-β |
| **S17-T-AD17A** | ADR-017 작성: cross-ws RAG opt-in UX + expand 정책 + cache invalidate (Q3) | Q3 lock-in |
| **S17-T-EMBED-RETRY** | 임베딩 실패 retry queue + exponential backoff (Q4 4-D) | Q4 권장 |
| **S17-T-WS-NORMALIZE** | 기존 16 frontend site URL-as-source-of-truth 패턴 일괄 refactor (Q5 5-E) | Q5 권장 |
| **S17-T-WS-SHARELINK** | 권한 stale bookmark / share link 정책 별도 ADR (Q5 5-C) | Q5 권장 |
| **S17-T-RSC-WS-CTX** | Server-side workspace context (Async Local Storage / RSC context) 도입 검토 (Q5 5-D) | Q5 권장 |

### 8.2 Sprint 18 candidates

| ID | 영역 | 출처 |
|----|------|------|
| **S18-T-RAG-XWS** | cross-ws RAG SQL IN expand 구현 + service layer 권한 검증 (Q3 3-D) | Q3 권장 |
| **S18-T-CACHE-INV** | SemanticCache cross-ws invalidate 메커니즘 (권한 변경 trigger) | Q3 lock-in (d)(e) |
| **S18-T-AD17-SLOT** | R-13 정식 slot 결정 (R-X 섹션 신설 vs I-X 흡수) — ADR-017 시점 | Q6 6-D 권장 |

### 8.3 Sprint 22+ / TBD candidates

| ID | 영역 | 출처 |
|----|------|------|
| **S22-T-AD18B** | ADR-018: Promotion 추천 AI (M5 moat 핵심) + confidence threshold + 사용자 검토 게이트 | handoff §1.4 + ADR-016 F5 |
| **S?-T-DELEGATE** | `promoted_on_behalf_of` (대리 promote, team lead가 멤버 작업 승격) | Q1 O1-γ |
| **S?-T-ADMIN-AUDIT** | 법적 disclosure admin audit endpoint (RAG 외부, retention 정책 통합) | Q3 O3-γ, Q6 O6-β |
| **S?-T-PERSONAL-I18N** | Personal ws 명칭 i18n koKR | Q2 O2-γ |
| **S?-T-EMBED-MIG** | 기존 RAG repo의 신규 EmbeddingChunk insert 시점 service assertion 추가 (코드 grep 후 도출) | Q4 권장 |
| **S15-T-D3-CLEANUP** | CLAUDE.md + docs `docs/CONTEXT-MAP.md` 표기 일괄 정정 (root 경로) | D-3 deferred |

---

## §9. 헌법 patch 본문 후보 (Sprint 15 S15-T3 + Sprint 16 S16-T3)

### 9.1 Sprint 15 S15-T3 PR scope

**파일**: `/CONTEXT-MAP.md` (root).

**I-9 patch (line 193)** — 4-C inline 추가:

```markdown
| I-9 | **멀티테넌시 격리**: 모든 Repository는 `workspace_id` 필터 강제. 신규 EmbeddingChunk insert 시 `workspace_id`는 신규 entity owner workspace와 매칭 (service layer assertion). | `<domain>/repository.py` `.where(... .workspace_id == workspace_id)`, `backend/src/embeddings/service.py:create_chunk` |
```

**I-19 신설 (line 202 추가, I-17 다음)** — Q2 lock-in:

```markdown
| I-19 | **Workspace type invariant**: 모든 Workspace는 `type: 'personal' \| 'team'`. Personal은 (a) owner 1명 강제 (DB UNIQUE partial index on `(owner_id) WHERE type='personal'`), (b) 멤버 추가/초대 차단 (service + WorkspaceMember insert 검증 → `PersonalWorkspaceProtected(403)`), (c) 삭제 차단 (계정 cascade 외), (d) 모든 user 자동 보유 (lazy seed on first login). | `backend/src/workspaces/service.py`, alembic `add_workspace_type.py` |
```

**Alembic migration** (`backend/alembic/versions/<hash>_add_workspace_type.py`):

```python
# Workspace.type 컬럼 추가 + UNIQUE partial index
def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("type", sa.String(), nullable=False, server_default="team"),
    )
    op.create_index(
        "uq_workspaces_owner_personal",
        "workspaces",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text("type = 'personal'"),
    )

def downgrade() -> None:
    op.drop_index("uq_workspaces_owner_personal", "workspaces")
    op.drop_column("workspaces", "type")
```

**Data migration script** (S15-T1.5, 별도 파일 or alembic data migration):

```python
# 모든 user에 personal workspace 1개씩 시드 (idempotent)
async def seed_personal_workspaces():
    users = await session.execute(select(User))
    for user in users.scalars():
        existing = await session.execute(
            select(Workspace).where(
                Workspace.owner_id == user.id,
                Workspace.type == "personal",
            )
        )
        if existing.scalar_one_or_none():
            continue  # idempotent skip
        ws = Workspace(
            name=f"{user.name}의 개인 Kairos",
            owner_id=user.id,
            type="personal",
        )
        session.add(ws)
        session.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner"))
    await session.commit()
```

### 9.2 Sprint 16 S16-T3 PR scope

**파일**: `/CONTEXT-MAP.md`, `backend/alembic/versions/<hash>_add_promotion_tombstone.py`.

**I-18 신설 (line 203 추가, I-19 다음)** — Q1 + Q4 lock-in:

```markdown
| I-18 | **Promotion 불변식**: 모든 promote는 (a) 원본 보존 + soft delete만 허용, (b) workspace_id 변경 = 신규 entity 복제, (c) 원본 tombstone에 `promoted_to` 기록 + 복제본 tombstone에 `promoted_from` 기록, (d) `promotion_audit` 테이블에 chain audit log 강제 + EmbeddingChunk 단계 포함, (e) 이동(move) / sync 금지, (f) cross-workspace 데이터 이전은 audit log 없으면 503. | `backend/src/promotions/service.py`, `backend/src/promotions/models.py:PromotionAudit` |
```

**`promotion_audit` table schema**:

```sql
CREATE TABLE promotion_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_workspace_id UUID NOT NULL REFERENCES workspaces(id),
    source_entity_type VARCHAR NOT NULL,  -- 'note' | 'meeting' | 'action' | 'inbox_item'
    source_entity_id UUID NOT NULL,
    target_workspace_id UUID NOT NULL REFERENCES workspaces(id),
    target_entity_id UUID NOT NULL,
    promoted_by_user_id UUID NOT NULL REFERENCES users(id),
    promoted_at TIMESTAMP NOT NULL DEFAULT now(),
    promotion_chain JSONB,  -- full chain (personal → team_a → team_b)
    embedding_status VARCHAR NOT NULL DEFAULT 'pending',  -- pending | processing | completed | failed
    embedding_completed_at TIMESTAMP,
    embedding_error_message TEXT,
    UNIQUE (target_entity_id)  -- idempotent on retry
);
CREATE INDEX idx_promotion_audit_source ON promotion_audit (source_workspace_id, source_entity_id);
CREATE INDEX idx_promotion_audit_target ON promotion_audit (target_workspace_id);
```

**4 엔티티 (Note/Meeting/Action/InboxItem) tombstone 컬럼 추가**:

```python
# 각 모델에 공통 적용
deleted_at: datetime | None = Field(default=None)  # soft delete
promoted_to: list[dict] | None = Field(default=None, sa_column=Column(JSONB))
promoted_from: dict | None = Field(default=None, sa_column=Column(JSONB))
status: str = Field(default="active")  # active | promoted | promoted_deleted | embedding_pending
```

---

## §10. Stage 1 진입 입력 요약

다음 Stage 1 `/office-hours` → `/autoplan` 진입 시 입력 정합:

### 10.1 Stage 1 입력

- **PRD v3.0 thesis**: AI memory layer + Personal↔Team graph (M5 moat)
- **Lock-in 결정**: AD-40~46 (Option D Personal workspace + Promotion flow) — 변경 0
- **헌법 patch 본문**: §9.1 + §9.2 (Sprint 15 + 16에 atomic 적용 예정)
- **Future Sprint backlog**: §8 (Sprint 17+/18+/22+ task explicit listing — Stage 1 forcing question 시 demand reality 검증 대상)
- **Open question**: O1-α~γ, O2-α~γ, O3-α~δ, O4-α~γ, O5-α~γ, O6-α~β (총 17건) — Stage 1 office-hours 6 forcing question + auto-review로 우선순위 결정

### 10.2 Stage 1 forcing question 후보 (v3.0 thesis 기반)

- **Demand reality**: AI memory layer 비전 외부 demand 검증 (PERSONA-002/003 인터뷰 50명 A/B).
- **Status quo**: 현 사용자 (founder 1명) Personal workspace 없이 진행 가능 여부 — pivot urgency 검증.
- **Desperate specificity**: Personal vs Team 명확한 use case 1개 (e.g. "회의 직후 personal에 raw 노트 → 정제 후 team으로 promote").
- **Narrowest wedge**: Sprint 15 7개 task 중 wedge 1개 (S15-T1 personal seed + S15-T2 switcher만이면 v1.5 ship 가능?).
- **Observation**: 1인 founder dogfooding에서 personal workspace 마찰 측정 (Sprint 15 dogfooding matrix).
- **Future-fit**: M5 moat (Personal↔Team graph) 형성에 v1.6 Promotion (Sprint 16)이 필수 vs 선택?

### 10.3 Stage 1 산출 예정 파일

- `docs/dev-log/2026-05-14-office-hours-v3.md` (Stage 1 산출)
- `docs/TODO.md` Sprint 17+ candidates 섹션 갱신 (§8 backlog 반영)

---

## §11. Stage 0 종료 기준 (handoff §verification)

- [x] 1. `docs/dev-log/2026-05-14-constitution-grill-v3.md` 생성 — 6 Q 각각 결정 + open question + 미래 task 등재
- [x] 2. ADR-016 + handoff doc에서 I-17 표기 → I-18 정정 완료 (commit `ff4c011`)
- [x] 3. CONTEXT-MAP I-18 신설 trigger 등재 (실제 신설은 Sprint 16 S16-T3 PR)
- [x] 4. Stage 1 `/office-hours` 진입 입력 = Stage 0 grill 결과 명시 (§10)
- [x] 5. `git log sprint-15/personal-workspace` 에 (a) cherry-pick handoff `d7faee1` + (b) I-17→I-18 정정 `ff4c011` + (c) Stage 0 산출 doc commit 3개 commit
