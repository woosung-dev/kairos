<!-- Sprint 15 Stage 3 Q2 brainstorming 산출 — 5 화면 wireframe + 5 Open Q lock-in -->

# Sprint 15 Recall-first — Brainstorm Spec (2026-05-14)

> **목적**: Sprint 15 Stage 3 Q2 산출. 5 화면 wireframe + edge case + 5 Open Q lock-in. Q3 `/writing-plans` 입력으로 `docs/dev-log/sprint-15-plan.md`에 통합 예정.
>
> **상위 source-of-truth**: `~/.gstack/projects/woosung-dev-kairos/woosung-sprint-15-personal-workspace-design-20260514-090026.md` (Stage 1 design doc, Recall-first wedge pivot).
>
> **design system**: `DESIGN.md` §Workspace Types + §Recall UI + §Promote Modal + §Feature Flag UX.
>
> **approved variants** (`/design-shotgun` Q1): A1 personal-first switcher / B3 search-first FAB / C1 promote dropdown.

---

## §1. Lock-in 결정 — 5 Open Q

| ID | 영역 | 결정 | 근거 |
|----|------|------|------|
| **O-A** | Recall source memo 표시 개수 | **Top 3** | Stage 1 design doc §1 R3 spec ("top-3") + Codex 2nd opinion ("2~3개"). B3 dense list (3 × 80px = 240px above-fold) 정합. 5개 검토는 PERSONA testing 결과 후 별도 task. |
| **O-B** | Keyword fallback rank algo | **Token overlap count** | atomic_notes ∩ query_tokens 개수 정렬. ~10 SQL line, R3 1.5h 일정 내 완료. BM25 (Postgres tsvector + GIN) 는 Sprint 17+ `S17-T-RECALL-BM25` defer. |
| **O-C** | "would miss this?" survey 수집 방식 | **인터뷰 only** (in-app modal 0) | Codex evidence pattern 원본 "unprompted" 정합. modal로 prompt 시 sycophantic bias. PERSONA 5명 × 30분 = ~3h founder time. signal quantity는 R7 metric (capture count + recall click) 보완. 7일 안 이탈자 감지는 metric으로 별도. |
| **O-D** | PERSONA outreach 채널 priority | **인디해커즈 1st → X DM 2nd → HN-Show 3rd** | Stage 1 design doc §1 R8 spec 정합. 한국 founder 관계망 high warm-conversion 우선. Day 3 0/5 응답 시 cold expansion (LinkedIn / Reddit r/SaaS / 본인 X 친구 DM). |
| **O-E** | Voice audio file retention | **R2 store + 30일 TTL** | 7일 testing window + 23일 cushion + Whisper future backfill 가능. cost ≈ $0.001/월 (75MB / 5명 × 50 capture). cron job 1개로 자동 cleanup. Sprint 17+ scale 시 ADR 검토. |

---

## §2. 5 화면 Wireframe + Edge Case

### 2.1 화면 1 — Capture flow (R1, B3 FAB trigger)

```
[/memory page → 우하단 🎙️ FAB 클릭]
┌─ Capture modal sheet ─────────────────────┐
│  ● 0:05 REC  (max 5min)        [Stop]    │
│  ──────────── or ────────────             │
│  ┌──────────────────────────────────┐   │
│  │ textarea (autosize 4 rows)        │   │
│  │ "type a thought..."               │   │
│  └──────────────────────────────────┘   │
│                            [Save]        │
└──────────────────────────────────────────┘
```

**Edge case**:
- **마이크 권한 거부** → textarea-only fallback + tooltip "마이크 권한 차단 — 텍스트만 가능"
- **파일 size >25MB** (Whisper API hard limit) → toast "5분 이내 메모로 줄여주세요" + 녹음 자동 중단
- **Whisper 503** → toast "음성 변환 재시도 중 — 텍스트는 임시 저장됨" + retry 버튼. memory_items row는 transcription pending 상태로 save (status='transcription_pending').
- **mp3 코덱 unsupported** → MediaRecorder default webm 사용. 서버는 ffmpeg로 webm → mp3/wav 변환 후 Whisper 호출.
- **녹음 0초** (즉시 Stop) → toast "녹음 너무 짧음 — 1초 이상 녹음하세요" + 저장 차단.

### 2.2 화면 2 — Distill 결과 view (R1 BE → R4 FE)

```
[Capture Save 직후 toast: "분석 중..." 1.5~2s] →
┌─ Distilled preview card ─────────────────┐
│  Aa 자동 생성된 title (Satoshi 18px)     │
│  ── atomic notes ──                       │
│  • point 1                                │
│  • point 2                                │
│  • point 3                                │
│  ── @founder · #kairos ──                 │
│                                           │
│  visibility:                              │
│  (●) 🔒 Personal   ( ) 👥 Team — AI 추천 │
│  ────                                     │
│  [Save to memory]   [Edit override]      │
└──────────────────────────────────────────┘
```

**Edge case**:
- **Gemini parse fail** → fallback `{title=first_120chars, atomic_notes=[chunked_512token, ...]}` + 노란 warning banner "AI 분석 실패 — 원본 텍스트 보존".
- **suggested_visibility = 'team'** → Team radio 자동 선택, 사용자 override 가능. Edit 버튼 클릭 시 distilled_json 직접 수정 textarea 열림.
- **distill timeout (>5s)** → spinner 유지 + 30s 후 fallback (raw text save + AI 분석 skip).

### 2.3 화면 3 — Recall query + 결과 (R3 BE + R4 FE)

```
[B3 search-first FAB layout]
┌─ Sticky search bar ─────────────────────────────────┐
│ 🔍 "어제 sprint 결정 사항"            ⌘K           │
└─────────────────────────────────────────────────────┘
🔒 Personal | 👥 Team   (client-side tab filter)

[Vector match results — Top 3 from O-A]
┌─ Result Card 1 ─────────────────────────────────────┐
│ Aa Sprint 15 wedge 결정                            │
│ "Recall-first wedge pivot lock-in. Promote는..."   │
│ 2h ago · personal · 0.87 score    [Promote ghost]   │
└─────────────────────────────────────────────────────┘
┌─ Result Card 2 ─────────────────────────────────────┐ ... │
└─────────────────────────────────────────────────────┘
┌─ Result Card 3 ─────────────────────────────────────┐ ... │
└─────────────────────────────────────────────────────┘

[Vector 0건 → Keyword fallback signal]
┌─ Result Card 1 ─────────────────────────────────────┐
│ Aa ...                                              │
│ ⚡ keyword match · 2h ago                           │
└─────────────────────────────────────────────────────┘
```

**Edge case**:
- **vector 0 + keyword 0** → empty state "검색 결과 없음. 다른 단어로 다시." + 최근 capture 3개 fallback list (위안 + discover).
- **동의어 미일치** → distill 시 Gemini prompt에 `"atomic_notes는 다양한 표현 + 동의어 포함"` 명시 (R1 prompts.py).
- **typo** → token overlap fallback (O-B)이 흡수. 대소문자/공백 normalize, 한국어 어절 단위 split.
- **검색어 너무 짧음** (1-2자) → "3자 이상 입력하세요" placeholder 옆 inline hint (즉시 검색 안 함).

### 2.4 화면 4 — 1st-time onboarding (R5 lazy seed + flag ON)

```
[NEXT_PUBLIC_RECALL_ENABLED=true 첫 진입 + 자동 personal seed]
┌─ Sidebar (NEW pill 1주일 한정) ─┐
│ Home                            │
│ Inbox                           │
│ Projects                        │
│ • Memory 🆕                     │  ← NEW pill (sidebar.tsx 1주일 expiry)
│ Settings                        │
└────────────────────────────────┘

[/memory 첫 진입 — empty state]
┌─ /memory page ──────────────────────────────────────┐
│ Memory · 2026-05-14                                  │
│                                                      │
│ 🌱 첫 메모를 저장하세요                              │
│ 우측 하단 🎙️ FAB을 눌러 시작.                       │
│                                                      │
│ ┌──────────────────────────────────────────────────┐│
│ │ 🔍 Search your memory...                  ⌘K     ││
│ └──────────────────────────────────────────────────┘│
│ 🔒 Personal | 👥 Team                                │
│                                                      │
│   (empty + dashed arrow →)                          │
│                                                      │
│                                              ╭───╮  │
│   ← 여기서 시작                              │🎙️ │  │ pulse animation
│                                              ╰───╯  │
└──────────────────────────────────────────────────────┘
```

**행동**:
- 첫 capture 완료 → arrow + pulse animation 제거 (memory_items count ≥ 1)
- 첫 recall 검색 → search bar 위 1회 confetti "🎉 첫 검색 성공"
- 그 외 guided tour 0 — Sprint 17+ 정식 onboarding 시 검토.
- Personal workspace lazy seed (R5)는 첫 login 시점 (`auth/dependencies.py:get_current_user` invariant). 사용자 인지 없음.

### 2.5 화면 5 — PERSONA testing demo flow (R8, 30분)

```
[founder가 PERSONA 5명 각각 진행 — Zoom/Discord 화면 공유]

 0:00 ─ 인트로 (3분)
        "AI memory layer 5분 보여드릴게요. 30분 인터뷰 + 7일 사용 동의?"

 3:00 ─ founder demo (5분)
        founder가 본인 dogfooding 데이터로:
         - capture 1회 (마이크 5초)
         - recall 1회 (검색어 입력 → top 3 시연)

 8:00 ─ PERSONA hands-on (10분)
        PERSONA 본인이 직접:
         - capture 3회 (마이크 2 + 텍스트 1)
         - 본인이 입력한 메모로 recall 시도
         - founder 옆에서 관찰, 도움 최소화

18:00 ─ Q&A (5분)
         - "어떤 부분이 헷갈렸나요?"
         - "기존 Notion / Apple Notes 대비?"
         - 절대 묻지 않음: "이거 좋아요?" — sycophantic bias 회피

23:00 ─ 7일 사용 약속 (5분)
         - Slack/Discord 채널 invite (founder 1:1)
         - 7일 후 30분 인터뷰 일정 fix
         - Clerk Production 계정 생성 helper
         - 7일 후 unprompted 발언 wait (O-C 인터뷰 only)

28:00 ─ Thank-you + buffer (2분)
```

**검증 metric** (R7 instrumentation + R8 interview):
- PERSONA 1명당 7일 capture count ≥ 5
- recall click-through ≥ 30%
- 7일 후 인터뷰에서 "이거 없으면 불편" unprompted 발언 = Best 3명+ / Medium 2명+ / Minimum 1명+ (Stage 1 §Success Criteria 정합)

---

## §3. Atomic doc + 코드 강제 (Stage 1 design doc §4 정합)

| commit | atomic doc | atomic 코드 |
|--------|------------|------------|
| **R3 commit** | `CONTEXT-MAP.md` I-9 4-C inline patch | `embeddings/service.py:create_chunk` assertion |
| **R5 commit** | (none — CONTEXT-MAP I-19 본문 등재는 Sprint 17+ 정식 신설 시) | alembic add_workspace_type + `auth/dependencies.py` lazy seed + UNIQUE partial index |
| **R6 commit** | `docs/dev-log/016-personal-team-ia.md` AD-41 reframe inline (R1 진입 직전 별도 commit 가능) | promote API + audit row + embedding BackgroundTask + DESIGN.md §Promote Modal CTA 검증 |

---

## §4. Q3 writing-plans 진입 입력

- 본 doc + Stage 1 design doc + `/design-shotgun approved.json` 통합.
- 출력 = `docs/dev-log/sprint-15-plan.md` (writing-plans skill 산출).
- 산출 구조 (Stage 3 plan §2.3 제안):
  1. Context (Stage 1 + Stage 0 헌법 patch 요약)
  2. Schedule (Day 1~14 stagger)
  3. R1~R8 Task spec (TDD test cases 먼저, Vertical Slice, critical files, atomic doc map)
  4. Dependencies (Clerk Prod key + Whisper/Gemini cost spike)
  5. Success Criteria 3 tiers (Stage 1 정합)
  6. Verification (Stage 4 진입 입력 = R1 first failing test)

---

## §5. Self-review checklist (brainstorming skill)

- [x] **Placeholder scan**: TBD / TODO / 미정 항목 0 — 5 Open Q 모두 결정.
- [x] **Internal consistency**: 5 화면 wireframe 모두 approved variants (A1/B3/C1) + DESIGN.md spec 정합.
- [x] **Scope check**: 단일 Sprint 15 R1~R8 plan 입력 — 적정 size.
- [x] **Ambiguity check**: edge case 처리 각 화면 명시. O-A~E lock-in.

**STATUS**: 승인 완료. Q3 writing-plans 진입 준비.
