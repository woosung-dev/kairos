<!-- Sprint 15 인계 — 다음 세션 진입 brief (Stage 0~6 풀워크플로우) -->

# Sprint 15 Kickoff Handoff (2026-05-14)

> **목적**: 본 세션이 컨텍스트 압박으로 다음 세션에 인계 필요. 다음 세션 AI가 이 문서 + 메모리 + PR description만으로 옵션 8(Stage 0~6 풀워크플로우) Sprint 15에 즉시 진입할 수 있도록.
>
> **다음 세션 첫 액션**: 본 문서 + `project_sprint15_kickoff_handoff` 메모리 read → Stage 0 `/grill-with-docs` 진입.

---

## 1. 현재 상태 스냅샷

### 머지 대기 PR

| PR | 브랜치 | 내용 | 상태 |
|----|--------|------|------|
| **#27** | `sprint-14/trust-stabilize` | Sprint 14 trust-stabilize (P0 4 + P1 7) | 머지 대기 (사용자가 머지할 예정) |
| **#28** | `docs/prd-v3-ai-memory-layer` | PRD v3.0 + ADR-016 + 본 handoff 문서 | 머지 대기 (PR #27 후) |

### Sprint 14 종료 (commit `787ffb9`)

- P0 4건 + P1 7건 fix 완료 (T-1~T-11)
- Backend 110 PASS / FE typecheck PASS / 신규 테스트 18개
- 잔여: 사용자 Clerk Production 키 발급 (별도 트랙 E)

### PRD v3.0 lock-in (commit `bd43733` + `09dbc5b`)

- 비전: "팀의 세컨드 브레인" → **"AI memory layer for people who think out loud"**
- Moat 4 → 5 (M5 신설: Personal↔Team graph)
- Input 1 → 6+ (회의 / 음성 메모 / 메신저 / 이메일 / 웹 / 손글씨 등)
- IA 1축 → 2축 (Input v1~v5 × Visibility v1.5~v2.0)
- ADR-016 Personal↔Team IA + Promotion Flow (AD-40~46 자의 결정)

### 핵심 결정 lock-in (변경 금지)

| # | 결정 | 위치 |
|---|------|------|
| 1 | Option D (Personal workspace + Promotion flow) | ADR-016 AD-40 |
| 2 | Promotion = 복제 + tombstone (이동 X) | ADR-016 AD-41, 헌법 I-18 예정 (I-17 slot은 Sprint 7 BE-T13 cross-ws ProjectMember 차단으로 점유) |
| 3 | visibility enum 4번째 추가 X | ADR-016 AD-42 |
| 4 | Personal workspace 항상 1명, 팀 초대 불가 | ADR-016 AD-43 |
| 5 | Qdrant 미전환 (트리거 5조건 명시) | PRD §부록 B |
| 6 | 신규 ADR 예정: 017(R-13 cross-ws RAG) / 018(Promotion 추천 AI M5) / 019(Qdrant) | PRD §부록 C |

---

## 2. 옵션 8 풀워크플로우 — Sprint 15 진입 계획

`.ai/templates/workflow.md` Stage 0~6 완전 실행.

```
Stage 0  /grill-with-docs                          [START HERE]
   ↓     헌법 I-9 강화 / I-18 신설 (Promotion) / R-13 예정 적대적 검증
   ↓     산출: docs/dev-log/2026-05-14-constitution-grill-v3.md
   ↓     예상 0.5-1일

Stage 1  /office-hours → /autoplan
   ↓     v3.0 thesis 6 forcing question + auto-review (CEO/Design/Eng)
   ↓     산출: docs/dev-log/2026-05-14-office-hours-v3.md
   ↓     예상 0.5-1일

Stage 2  /design-consultation (mini)
   ↓     DESIGN.md에 Personal vs Team workspace 색상/배지 정책 patch
   ↓     예상 0.5일

Stage 3  design-shotgun + brainstorming + writing-plans + /codex
   ↓     5 화면 brainstorming (3-5 variant 각)
   ↓     3 핵심 화면 shotgun (switcher / promotion 모달 / tombstone)
   ↓     docs/dev-log/sprint-15-plan.md
   ↓     /codex 적대적 plan 검토
   ↓     예상 1.5-2일

Stage 4  TDD + systematic-debugging + Playwright + improve-codebase-architecture
   ↓     Sprint 14 패턴 (brief → plan before code → TDD → impl → atomic doc → 자동 commit)
   ↓     S15-T1~T7 + S16-T1~T6 task 진행
   ↓     예상 sprint 자체 1-2주

Stage 5  Standard 검증+배포
   ↓     변경 위험도 Standard (IA + 새 컴포넌트)
   ↓     E2E + 회귀 + Playwright dogfooding
   ↓     예상 0.5-1일

Stage 6  /retro → /learn
         Sprint 15 retrospective + 학습 .ai/project/lessons.md 등재
         예상 0.5일
```

**총 준비 워크플로우 (Stage 0~3)**: 3.5-5일
**구현 (Stage 4)**: 1-2주
**마무리 (Stage 5~6)**: 1-1.5일

---

## 3. Stage 0 grill 1차 대상 (즉시 진입 가능)

### Q1. I-18 신설 (Promotion 복제 + tombstone) edge case

- Promote 후 작성자가 원본 수정하면? (복제본 영향 0인가 / sync 정책 / 무관)
- Team admin이 reject하면 원본 복원? tombstone에 reject 기록?
- Promote 후 원본 삭제 시 tombstone만 잔존?
- 동일 아이템을 2개 team에 동시 promote 가능한가?
- Personal → Team A → Team B (chain promotion) 허용?

### Q2. I-9 강화 (Personal workspace 격리) backward compatibility

- 현재 사용자의 워크스페이스는 어떻게 처리?
  - 옵션 a: 기존 = Team으로 유지 + 신규 Personal 자동 시드
  - 옵션 b: 1명 워크스페이스는 자동 Personal 전환
  - 옵션 c: 사용자 선택 마이그레이션 마법사

### Q3. R-13 예정 (cross-ws RAG opt-in) 사전 검증

- Personal RAG → Personal data만 / Team RAG → Team data만 default
- "Personal + Team 통합 검색" opt-in 시 권한 모델:
  - admin도 다른 사용자 personal 접근 불가
  - 사용자 자기 personal + 본인 멤버 team만 통합

### Q4. Promotion + RAG 임베딩 격리

- 복제 시 임베딩 2벌 생성 vs 임베딩 메타데이터에 workspace_id 추가
- RAG 검색 시 workspace_id 필터로 자동 격리

### Q5. Workspace switcher state management

- 활성 workspace = Zustand persist `activeWorkspaceId`
- Sprint 14 T-7 에서 stale wid 가드 + `queryClient.clear()` 패턴 추가됨
- Personal workspace 진입 시 workspace 목록에 항상 포함되도록 보장

---

## 4. ADR-016 task 매핑 (Sprint 15 + 16)

### Sprint 15 (v1.5 Personal workspace)

| Task | 설명 | 의존 |
|------|------|------|
| S15-T1 | BE: 신규 가입 시 Personal workspace 자동 시드 | — |
| S15-T2 | FE: Workspace switcher UI 우상단 | T1 |
| S15-T3 | BE: Personal workspace 권한 모델 — 항상 1명, 팀 초대 불가 schema 제약 | T1 |
| S15-T4 | DOC: ADR-016 작성 (✅ 완료, commit `09dbc5b`) | — |
| S15-T5 | UX: 온보딩 — personal만 노출, "팀 합류" 액션 시 team 안내 | T1, T2 |
| S15-T6 | BIZ: tagline 5개 외부 A/B 테스트 (사용자 의지에 따라) | (병렬) |
| S15-T7 | OBS: RAG p50/p95 + 벡터 수 카운터 (Qdrant 트리거 #3 자동 감지) | — |

### Sprint 16 (v1.6 Promotion + v2 음성 메모)

| Task | 설명 | 의존 |
|------|------|------|
| S16-T1 | FE: "Promote to Team..." 액션 모달 | Sprint 15 완료 |
| S16-T2 | BE: Promotion API — 복제 + 임베딩 신규 생성 + tombstone | S16-T1 |
| S16-T3 | DOC: 헌법 I-18 신설 + ADR-016 referenced | S16-T2 |
| S16-T4 | FE: `/new`에 "음성 메모" 탭 추가 | — |
| S16-T5 | BE: Voice note 모델 + STT + Gemini 요약 + 태그 | S16-T4 |
| S16-T6 | UX: Personal에서 음성 메모 첫 진입 시나리오 | S16-T4, T5 |

---

## 5. 사용자 정책 + Lessons Learned (본 세션)

### 사용자 정책 변경

- **자동 커밋 OK** — Sprint 14 중 변경됨. PR 게이트만 사용자 승인.
- **메모리 [feedback_no_auto_commit.md]는 본 정책에 의해 superseded** (다음 세션에서 인지 + 통합 시 갱신)

### Lessons Learned (over-correction 3회)

> 본 세션에서 사용자가 3번 연속 같은 종류 over-correction 지적. 다음 세션에서 반복 금지.

1. **Sprint 14 패턴 = Sprint 15 패턴**이라는 잘못된 anchor
   - Sprint 14는 trust-stabilize fix(의사결정 부담 작음). Sprint 15는 v3.0 위 1차 구현(의사결정 부담 큼).
   - 같은 워크플로우로 진입하면 안 됨.

2. **PRD v3.0 변화 규모를 과소평가**
   - v2.0 → v3.0은 부분 patch가 아니라 thesis pivot.
   - ADR-016 self-confirm 직후라 외부 검증 0건. office-hours + grill-with-docs 필수.

3. **mattpock 해석 실패**
   - `mattpock` = `.ai/templates/workflow.md` Stage 0 **`/grill-with-docs`** (사용자 own slang)
   - 추측 기반 답변 금지 → workflow.md 직접 참조 우선.

### 일반 lesson

- 사용자 워크플로우 질문 시 가장 먼저 `.ai/templates/workflow.md` 직접 read.
- 사용자 의견 두 번 깎이면 자기 reasoning 의심 (over-skip 패턴).
- 옵션 매트릭스 작성 시 **단기 + 장기 + YC** 세 column 동시 평가.

---

## 6. 다음 세션 첫 message 템플릿

새 세션 open 후 사용자가 채팅에 그대로 붙여넣으면 즉시 Sprint 15 풀워크플로우 진입.

```
Sprint 15 진입.

다음 read 순서로 컨텍스트 파악 후 옵션 8 풀워크플로우 Stage 0부터 진행해줘:

1. docs/dev-log/2026-05-14-sprint15-handoff.md  (본 인계 문서)
2. docs/requirements/prd.md v3.0 §3.6 IA 2축 로드맵
3. docs/dev-log/016-personal-team-ia.md  (ADR-016, AD-40~46)
4. CONTEXT-MAP.md  (repo root, 헌법 I-9 강화 / I-18 신설 Promotion / R-13 예정)
5. docs/TODO.md Sprint 15-16 후보 (S15-T1~T7, S16-T1~T6)

Stage 0 /grill-with-docs 부터 시작. 5개 grill 대상 (handoff §3)을 적대적으로 검증해서
docs/dev-log/2026-05-14-constitution-grill-v3.md 산출.

자동 커밋 OK. PR만 사용자 승인. brief → plan → impl 8단계 패턴 (Sprint 14 검증된 방식).

over-correction 경계: Stage 0/brainstorming/shotgun 깎지 말 것 (handoff §5 lessons).
```

---

## 7. 참조 인덱스 (다음 세션 자료)

### PR (영구 기록)

- PR #27 Sprint 14 trust-stabilize — 11 fix + verification doc
- PR #28 PRD v3.0 + ADR-016 + 본 handoff

### 문서

- `docs/requirements/prd.md` v3.0 (681 lines)
- `docs/dev-log/016-personal-team-ia.md` ADR-016 (255 lines)
- `docs/CONTEXT-MAP.md` 헌법
- `docs/TODO.md` Sprint 15-16 후보
- `.ai/templates/workflow.md` Stage 0~6 정의

### 메모리

- `project_sprint15_kickoff_handoff.md` (본 인계의 메모리 버전)
- `project_sprint14_status.md` Sprint 14 완료 + 자의 결정 AD-36~39
- `project_multi_agent_qa.md` Sprint 14 입력 (Sentinel/Curious/Casual)

### Skill 참조 (Stage 별)

- Stage 0: `grill-with-docs` (project skill)
- Stage 1: `office-hours` / `autoplan` (user skill)
- Stage 2: `design-consultation` (user skill)
- Stage 3: `design-shotgun` / `superpowers:brainstorming` / `superpowers:writing-plans` / `codex` (mixed)
- Stage 4: `superpowers:test-driven-development` / `superpowers:systematic-debugging` / `playwright MCP`
- Stage 5: `qa` / `design-review` / `review`
- Stage 6: `retro` / `learn`

---

## 8. Stage 0 grill 시작 명령

다음 세션에서 Stage 0 진입 시:

```
Skill 도구로 grill-with-docs 호출 (project skill)
   ↓
대상: CONTEXT-MAP.md + ADR-016 + PRD v3.0 §3.6
   ↓
5개 grill 영역 (handoff §3 Q1~Q5) 적대적 검증
   ↓
edge case 발굴 → 산출 docs/dev-log/2026-05-14-constitution-grill-v3.md
   ↓
필요 시 CONTEXT-MAP patch + ADR-016 amendment commit
   ↓
Stage 1 /office-hours 진입
```
