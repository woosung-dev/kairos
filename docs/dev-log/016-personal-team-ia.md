# ADR-016: Personal↔Team IA + Promotion Flow

> **날짜:** 2026-05-14
> **상태:** Accepted (구현 Sprint 15-16)
> **작성자:** Claude Opus 4.7 (1M context) + 사용자 (PRD v3.0 갱신 직후)
> **관련:** PRD v3.0 §0 + §2 + §3.6 + 부록 A · ADR-006 UI/UX 개편 · ADR-010 Future-Fit Thesis (M5 신설) · ADR-011 Persona · ADR-014 Service-to-Service 경계 · CONTEXT-MAP I-9 (workspace 격리)
> **워크플로우:** `.ai/templates/workflow.md` Stage 3 Step 4 — PRD v3.0 §3.6 IA 2축 로드맵에서 분기된 v1.5~v2.0 IA 결정 ADR

---

## 배경

Sprint 14(trust-stabilize, PR #27) 완료 직후 사용자가 다음 두 질문을 제기.

1. **포지셔닝**: "회의 위주 좁다. YC 관점에서 더 큰 비전 필요."
2. **개인↔팀 IA**: "팀 강조하는데 개인 영역 있나? Notion·Claude의 CLAUDE.md/local.md 패턴처럼 개인→검증→팀 승격 방식 필요한가?"

답변 분석 결과 — YC 관점, 시장 사례 7개(Notion/Slack/Figma/GitHub/Linear/Confluence/Apple Notes), 사용자 CLAUDE.md vs CLAUDE.local.md 비유 — 3축 모두 동일 결론: **개인↔팀 IA는 v1.5 핵심 기능이어야 함**.

PRD v3.0(`docs/requirements/prd.md`, PR #28)이 다음을 lock-in:
- AI memory layer 비전 (Input 다양화 + Personal↔Team 양축)
- §3.6 IA 2축 로드맵 (v1~v5 input × v1.5~v2.0 visibility)
- Moat M5 신설 (Personal↔Team graph)

본 ADR은 PRD v3.0 §3.6의 **Y축 v1.5~v2.0 결정**을 Nygard 포맷으로 lock-in한다. 코드 변경은 동반하지 않음(정책 ADR). 실제 구현은 Sprint 15 PR(v1.5 Personal workspace), Sprint 16 PR(v1.6 Promotion + v2 음성 메모), Sprint 18 PR(v1.8 Cross-workspace RAG, 별도 ADR-017)에서.

### 자의 결정 라벨

Sprint 14 AD-39 소진 후 AD-40부터 시작.

- **AD-40**: Option D (Personal workspace + Promotion flow, Notion 패턴) 채택 — A/B/C 대비. 자의 = "workspace 단위 격리(헌법 I-9)와 일관성 + 사용자 mental model 명확성" 트레이드오프에서 단순함 + 보안 선택.
- **AD-41**: Promotion = **복제 + tombstone** (이동 아님). 자의 = 감사 추적 + 원본 변경 시 팀 자산 영향 차단 + 롤백 가능성. 복제 비용(스토리지 2x)은 텍스트 + 1536d 임베딩 기준 무시 가능.
- **AD-42**: visibility enum 4번째(`personal`) 추가하지 **않음** — workspace 단위 분리로 충분. 자의 = enum 폭증 회피 + 권한 코드 분기 단순화. Project.visibility는 그대로 public/draft/private 3개.
- **AD-43**: Personal workspace는 항상 **1명, 팀 초대 불가** (BE schema 제약으로 강제). 자의 = 사용자 실수로 팀 노출 방지 + privacy 보장 단순화.
- **AD-44**: Promotion review queue (v1.7)는 Sprint 17에서 결정 — 1차는 admin auto-accept 가능 (특히 1인 founder가 본인 personal → 본인이 admin인 team으로 promote 시 마찰 없음).
- **AD-45**: Cross-workspace RAG(v1.8)는 본 ADR scope 외, 별도 ADR-017로 분기. 헌법 R-13 신설 예정.
- **AD-46**: Promotion 추천 AI(v2.0, M5 moat 핵심)는 본 ADR scope 외, 별도 ADR-018로 분기.

---

## 결정

### 1. IA 모델 — Workspace 단위 분리 (Option D)

```
사용자 ─┬─ Personal workspace ("{사용자명}의 개인 Kairos")
        │   - 항상 1명, 팀 초대 불가 (AD-43)
        │   - visibility = public 기본 (workspace 내부에선 의미 없음)
        │   - 모든 input 채널(v1~v5) 수용
        │
        └─ Team workspaces (0~N개)
            - 기존 워크스페이스 모델 그대로
            - RBAC owner/admin/member/viewer
            - visibility public/draft/private (Sprint 6 ADR-014 정합)
```

신규 가입 시 Personal workspace **자동 시드** (S15-T1). 팀 초대 받으면 별도 Team workspace 합류.

### 2. Promotion Flow

```
[Personal workspace]                    [Team workspace]
  Meeting / Note / ActionItem  ──promote──►  복제본 (신규 ID, 신규 임베딩)
  │                                          │
  │ tombstone: promoted_to                   │ tombstone: promoted_from
  │   {team_workspace_id,                    │   {personal_workspace_id,
  │    target_project_id,                    │    original_item_id,
  │    promoted_at,                          │    promoted_by_user_id,
  │    new_item_id}                          │    promoted_at}
  └─ 원본 유지 (RAG 검색에서 personal 범위로만 검색됨)
```

**핵심 원칙**:
- 복제(AD-41) — 원본은 personal에 영구 잔존, 복제본은 team에서 독립 진화
- 임베딩도 양쪽에 별도 저장 (workspace_id 격리, I-9 유지)
- 사용자가 personal 원본 수정해도 team 복제본에 영향 없음 (의도된 분리)
- Promotion audit log 영구 보존 (감사 추적)

### 3. 권한 모델

| 액션 | Personal | Team |
|------|---------|------|
| Personal → Team **promote** | 작성자 본인 only | 대상 team에 `member+` 권한 필요 |
| Team review queue accept/reject | N/A | team admin/owner (1차 admin auto-accept, AD-44) |
| 원본 personal 삭제 | 작성자 본인 (tombstone은 잔존) | N/A |
| 복제본 team 수정/삭제 | N/A | team `member+` (기존 권한 모델) |

### 4. 헌법 갱신 (CONTEXT-MAP)

- **I-9 (workspace 격리) 유지 + 강화**: Personal workspace도 workspace_id로 격리. RAG 검색은 항상 단일 workspace_id 필터.
- **I-17 신설**: "Promotion은 항상 복제 + tombstone, 이동 금지." Promotion으로 인한 cross-workspace 데이터 이전은 audit log 강제.
- **R-13 신설 (Sprint 18+ ADR-017)**: Cross-workspace RAG은 명시적 opt-in + 권한 재검증. 본 ADR scope 외 — Sprint 18 ADR-017에서 결정.

### 5. 마케팅 메시지 lock-in (PRD §7-Marketing 정합)

- 1차 tagline: _"당신의 두 번째 뇌, 그리고 팀의 첫 번째 기억."_
- 개발자 페르소나용: _"Kairos는 git처럼 작동합니다. 개인 영역에서 실험하고, 팀에 promote하세요."_ (CLAUDE.md/local.md 비유)
- B2B 세일즈용: _"Personal-first onboarding. 도입 마찰 0."_

---

## 옵션 비교 (채택 = D)

### Option A — Personal Workspace 자동 생성 (채택 ✅)

```
신규 가입 → Personal workspace 1개 시드
팀 초대 → Team workspace 별도 합류
Workspace switcher로 toggle
```

| Pros | Cons |
|------|------|
| 명확한 격리 (I-9 정합) | Workspace 단위라 cross-search는 별도 작업(R-13, v1.8) |
| Notion Plus 사용자 즉시 이해 | 1 사용자 = 2+ workspace 인프라 부담 |
| Privacy 강함 (실수 노출 위험 0) | "내 personal로 team 질문 답하기" 불가 (v1.8까지 대기) |

### Option B — Team workspace 안 Personal Project (탈락)

| Pros | Cons |
|------|------|
| 단일 workspace 단순 | visibility enum 4 → 헌법 갱신 폭주 |
| Cross 검색 자동 | 실수로 visibility public 변경 시 노출 위험 (AD-42 회피 이유) |

### Option C — visibility=personal 추가 (탈락)

| Pros | Cons |
|------|------|
| 가장 작은 변경 | Project 단위 — 회의 1건 promotion 불가 (전체 project 이동만) |
| 헌법 R-10 그대로 | draft vs personal 차이 사용자 혼란 |

### Option D — Personal Workspace + Promotion Flow (Option A 확장, **채택**)

Option A에 promotion 액션 + tombstone + review queue 추가. 본 ADR이 채택한 풀스택 모델.

| Pros | Cons |
|------|------|
| 사용자 비유(CLAUDE.md/local.md)와 일치 | 가장 많은 구현 (Sprint 15~17) |
| YC partner "single-player first" 격언 | RAG 인프라 양쪽 유지 필요 |
| Notion/Slack/Figma 사용자 학습 곡선 0 | |
| 마케팅 카피 강력 ("git처럼 작동") | |
| M5 moat 핵심 (PRD §3.5) | |

---

## 시퀀스 다이어그램 — Promotion 흐름 (v1.6, Sprint 16)

```
사용자          FE                BE                      DB
  │             │                  │                       │
  │ ──"Promote to Team..."───────► │                       │
  │             │                  │                       │
  │ ──target_team + project 선택──► │                       │
  │             │                  │                       │
  │             │ ─POST /promote─► │                       │
  │             │                  │ ─verify perms (AD-43)─► │
  │             │                  │ ◄────permission OK──── │
  │             │                  │                       │
  │             │                  │ ─SELECT 원본 item────► │
  │             │                  │ ─SELECT embedding────► │
  │             │                  │                       │
  │             │                  │ ─INSERT 복제 item────► │
  │             │                  │  (new_id, target_ws) │
  │             │                  │ ─INSERT embedding────► │
  │             │                  │  (target_ws 격리)     │
  │             │                  │ ─UPDATE 원본 tombstone► │
  │             │                  │  promoted_to: {...}   │
  │             │                  │ ─INSERT audit log────► │
  │             │                  │                       │
  │             │ ◄──202 + new_id──│                       │
  │ ◄──toast───│                  │                       │
  │             │                  │ ─(if admin auto-      │
  │             │                  │   accept) status=     │
  │             │                  │   accepted (AD-44)    │
  │             │                  │ ─else queued for      │
  │             │                  │   admin review        │
```

---

## 구현 task 매핑 (Sprint 15-16)

### Sprint 15 — v1.5 Personal workspace (이 ADR의 1차 ship)

| Task | 설명 | 의존 |
|------|------|------|
| S15-T1 | BE: 신규 가입 시 Personal workspace 자동 시드 | — |
| S15-T2 | FE: Workspace switcher UI 우상단 | T1 |
| S15-T3 | BE: Personal workspace 권한 모델 — 항상 1명, 팀 초대 불가 schema 제약 (AD-43) | T1 |
| S15-T4 | DOC: ADR-016 작성 (본 ADR, 완료) | — |
| S15-T5 | UX: 온보딩 — personal만 노출, "팀 합류" 액션 시 team 안내 | T1, T2 |
| S15-T6 | BIZ: PRD §7-Marketing tagline 외부 A/B 테스트 | (병렬) |
| S15-T7 | OBS: RAG p50/p95 + 벡터 수 카운터 (Qdrant 트리거 #3 자동 감지) | — |

### Sprint 16 — v1.6 Promotion + v2 음성 메모

| Task | 설명 | 의존 |
|------|------|------|
| S16-T1 | FE: "Promote to Team..." 액션 모달 (target ws + project 선택) | Sprint 15 완료 |
| S16-T2 | BE: Promotion API — 복제 + 임베딩 신규 생성 + tombstone (AD-41) | S16-T1 |
| S16-T3 | DOC: 헌법 I-17 신설 + ADR-016 referenced | S16-T2 |
| S16-T4 | FE: `/new`에 "음성 메모" 탭 (회의와 분리) | — |
| S16-T5 | BE: Voice note 모델 + STT + Gemini 요약 + 태그 | S16-T4 |
| S16-T6 | UX: Personal에서 음성 메모 첫 진입 시나리오 lock-in | S16-T4, T5 |

### Sprint 17+ (v1.7 review queue, v1.8 cross-ws RAG)

본 ADR scope 외. Sprint 17 진입 시 사용자 행동 데이터 + Sprint 16 PR 결과 기반 별도 ADR(017).

---

## 비용 / 리스크

### 비용

- Sprint 15 dev 시간 추정 1~2주 (S15-T1~T7)
- Sprint 16 dev 시간 추정 2~3주 (S16-T1~T6, promotion + 음성 메모 2축 동시)
- 인프라: 사용자당 workspace 2+ → DB row 증가. 임베딩은 lazy 인덱싱(질의 시점) 옵션 검토 (Sprint 15 후속)

### 리스크

| # | 리스크 | 발생 가능성 | 완화책 |
|---|--------|------------|--------|
| R1 | Privacy 환각 — 사용자가 Personal로 알고 적었는데 실수로 Team 노출 | 중 | UI 색상 + 상단 banner "지금 어느 workspace" 항상 명시. workspace switcher visual cue 강화. |
| R2 | 데이터 중복(복제)으로 사용자 혼란 ("같은 노트가 두 군데?") | 중 | tombstone에 원본/복제 link 명시 + UI에 "Promoted from {Personal}" 배지 표시 |
| R3 | Sprint 15 ship 지연 → v1.6~v2.0 카스케이드 지연 | 중 | S15-T1~T5만 우선 ship, T6 마케팅 + T7 모니터링은 백그라운드 |
| R4 | "단일 워크스페이스" 사용자에게 불필요한 복잡도 | 낮 | 1인 founder는 Personal만 사용해도 완전 동작. Team workspace는 옵션 |
| R5 | Cross-workspace RAG(v1.8) 권한 누설 | 높 | 본 ADR scope 외 — ADR-017 (R-13 헌법 신설)에서 처리 |
| R6 | Promotion 추천 AI(v2.0) 잘못 추천 시 신뢰 손상 | 중 | M5 moat 핵심 — ADR-018에서 confidence threshold + 사용자 검토 게이트 결정 |
| R7 | 임베딩 2배 비용 (personal + team 복제) | 낮 | OpenAI text-embedding-3-small $0.02/1M token, 회의 1건 ~$0.001. Personal+Team 복제도 무시 가능 |

---

## 후속 (Follow-ups)

- **F1 (Sprint 15 킥오프 시)**: 본 ADR + Sprint 15 plan 정합 점검. S15-T1~T7 task 분해.
- **F2 (Sprint 16 킥오프 시)**: 헌법 I-17 신설 PR + Promotion 시퀀스 detail 결정.
- **F3 (Sprint 17 킥오프 시)**: v1.7 review queue — admin auto-accept vs manual review 정책. AD-44 재검토.
- **F4 (Sprint 18 킥오프 시)**: **ADR-017 Cross-workspace RAG** 신설 — 헌법 R-13 명시 + Personal↔Team 검색 권한 분기.
- **F5 (Sprint 22+ 킥오프 시)**: **ADR-018 Promotion 추천 AI** 신설 — M5 moat 핵심 + confidence threshold + 사용자 검토 게이트.
- **F6 (외부 인터뷰 F4 후)**: PERSONA-002/003 인터뷰에서 "개인↔팀 분리 필요?" 응답 ≥60% 시 본 ADR 검증 완료. 미만 시 IA 단순화 옵션 재검토 (Option B/C).

---

## 검증 시그널

| # | 시그널 | 임계값 | 측정 시점 |
|---|--------|--------|----------|
| V1 | 신규 가입자 1주 retention | ≥40% | Sprint 15 ship 후 1개월 |
| V2 | Personal → Team promotion 발생률 | 사용자 1인당 ≥3건/월 | Sprint 16 ship 후 1개월 |
| V3 | Workspace switcher 혼란 toast/문의 비율 | ≤5% | Sprint 15 ship 후 |
| V4 | 외부 인터뷰 "개인↔팀 분리 가치 있음" 응답률 | ≥60% (5~10명) | Sprint 17+ (F4) |
| V5 | Promotion 후 team 복제본 활용도 (조회·인용) | personal 원본 대비 ≥150% | Sprint 16 ship 후 3개월 |

V1~V5 종합 PASS 시 IA Option D 채택 검증 완료. V4 미달 시 본 ADR supersede 검토.
