<!-- ADR-010 thesis 검증 입력 — Otter/Granola/Reflect/Mem/Tana 5개 경쟁자 분석 + Kairos 차별점 -->

# Kairos Competitive Analysis — Otter / Granola / Reflect / Mem / Tana

> **출처:** `docs/dev-log/adr/010-future-fit-thesis.md` (ADR-010 §"비용/리스크" 인용 — "Mem/Reflect/Tana 등 소형 경쟁자는 competitive-analysis.md에서 별도 다룸")
> **상위:** `docs/dev-log/adr/009-stage1-retrofit.md` (ADR-009 §2 Q2 status quo 보강)
> **헌법:** `CONTEXT-MAP.md` §1·§3 CODE 가치 흐름·§6 핵심 불변식
> **페르소나 cross-link:** `docs/requirements/personas.md` (Wedge 우선순위 매트릭스)
> **최종 수정:** 2026-05-11
> **상태:** 1차 (사실 출처 미보강 — 모두 `[확인 필요]` 라벨, 각 사 공식 문서 WebFetch 후속 권장)

---

## 0. 1차 작성 컨텍스트 + 출처 정책

본 문서는 ADR-010 thesis(future-fit moat M1~M4) 검증 + ADR-009 Q2 status quo 보강을 위한 5개 경쟁자 비교. **본인 직접 사용 경험 + 각 사 공식 문서/요금제 검증 미진행** 시점에서 작성 — 따라서:

### 자의 결정 라벨 (본 산출에서 추가)

- **AD-16**: 5개 서비스 기능·가격·타겟·차별점 모든 항목에 `[확인 필요]` 라벨 일괄 부여. 출처는 training data 기반 일반 인식이며 정확성 미확신. 각 사 공식 문서(웹사이트·요금제 페이지) WebFetch 보강 후속 작업 권장. 본인 직접 사용 경험으로 채울 수 있는 항목은 후속 패치 시 라벨 해제.
- **AD-17**: Granola를 ADR-010 위협 시나리오 3개(T3) + 본 분석 5개 양쪽에 두는 결정. 자의 — Granola는 (a) 단일 wedge 경쟁자(W1 회의 요약·액션 추출)이자 (b) 통합 도구로 확장 가능성 있는 시나리오 양쪽에 해당. 두 컨텍스트 분리 가능하지만 cross-link 명시로 정합 유지.

### 출처 정책

각 서비스의 기능·가격·타겟 사실은 출처 명시 필수 — 본인 사용 경험이면 `[본인 경험 — YYYY-MM-DD]`, 각 사 공식이면 `[공식 — URL]`, training data 기반이면 `[확인 필요 — training data 기반, 정확성 미확신]`. 본 1차는 모두 마지막 라벨.

ADR-010 thesis 검증 시 본 분석이 인용되려면 Sprint 6+ 후 본인 직접 사용 경험으로 ≥3개 서비스 라벨 해제 필요.

- **AD-18**: "≥3개" 임계값은 자의 — 5개 중 절반 이상(60% 정합, ADR-009 §5 측정 모집단 정합과 같은 단위 60%)이 직접 경험·공식 출처로 라벨 해제되어야 본 분석이 thesis 검증 입력으로 인용 가능. 임의 수치 — Sprint 6+ 실측 후 조정 가능.

> **표 셀 라벨 정책 (AD-16 정합 통일)**: 본 문서 §2.1~§2.4의 모든 표 셀은 일괄 `[확인 필요]` 라벨 적용 — Kairos 행 + "확인 필요" 인라인 표기 셀 외 모든 사실 항목 동일. 표마다 셀 인라인 라벨 중복 부착은 가독성 저하로 생략. 셀이 후속 보강(B1/B2)으로 라벨 해제될 때 `[본인 경험 — YYYY-MM-DD]` 또는 `[공식 — URL]` 라벨 셀별 명시.

---

## 1. 5개 경쟁자 개요

| # | 서비스 | 1줄 요약 `[확인 필요]` | 출시 | 주 사용자 |
|---|---|---|---|---|
| C1 | **Otter.ai** | 실시간 회의 STT + 화자 분리 + AI 요약. Slack/Zoom/Teams 통합. | 2016 | 영어권 비즈니스/대학 회의 사용자 |
| C2 | **Granola** | macOS native 회의 요약 (시스템 오디오 캡처). Notion/Obsidian export. | 2024 | macOS startup founder / 1:1 회의 많은 IC |
| C3 | **Reflect** | 노트 + AI 검색 + 백링크 그래프. iOS/Mac/Web. | 2021 | PKM (개인 지식 관리) 사용자 |
| C4 | **Mem** | AI 자동 분류 노트 + RAG Q&A. 백링크 자동 생성. | 2020 | 개인 지식 관리 / 작가 / researcher |
| C5 | **Tana** | 노트 + 데이터베이스 + 슈퍼태그 + AI Q&A. 노드 기반. | 2022 (베타) | PKM (Roam Research 후속) + 팀 협업 |

---

## 2. 차원별 비교 표 `[전부 확인 필요]`

### 2.1 기능 범위 (헌법 §3 CODE 가치 흐름 매핑)

| 서비스 | Capture | Organize | Distill L1 (요약) | Distill L2 (액션/결정) | Distill L3 (프로젝트) | Distill L4 (조직) | Express (RAG) |
|---|---|---|---|---|---|---|---|
| Kairos | ✅ 회의·노트·자료 | ✅ AI 자동 분류 (I-10) | ✅ 회의 요약 | ✅ 액션·결정 | ⚠️ 부분 (Phase 4 ADR-007) | ❌ 미구현 | ✅ 6-Layer + SSE |
| **C1 Otter** | ✅ 회의 (라이브 STT) | ⚠️ 폴더 수동 | ✅ 회의 요약 | ⚠️ 부분 (액션만) | ❌ | ❌ | ⚠️ Otter Chat (단일 회의 범위) |
| **C2 Granola** | ✅ 회의 (macOS 시스템 오디오) | ❌ (Notion export 의존) | ✅ 회의 요약 | ⚠️ 부분 | ❌ | ❌ | ❌ |
| **C3 Reflect** | ✅ 노트 | ⚠️ 백링크 수동 + AI 보조 | ⚠️ 부분 | ❌ | ❌ | ❌ | ✅ AI 검색 (단일 사용자 노트) |
| **C4 Mem** | ✅ 노트 | ✅ AI 자동 분류 | ✅ 노트 요약 | ❌ | ❌ | ❌ | ✅ RAG Q&A (단일 사용자) |
| **C5 Tana** | ✅ 노트·DB | ✅ 슈퍼태그 | ⚠️ 부분 | ⚠️ 부분 (DB 통한 액션) | ❌ | ❌ | ✅ AI Q&A (워크스페이스 범위) |

> 본 표의 ✅/⚠️/❌ 판정은 [확인 필요] — 본인 사용 경험 또는 각 사 공식 문서로 검증 후 라벨 해제.

### 2.2 가격 `[전부 확인 필요]`

| 서비스 | Free | Pro 개인 | Team/Business | 비고 |
|---|---|---|---|---|
| Kairos | (TBD — Sprint 6+ 후 결정) | (TBD) | (TBD) | 1인 풀스택 founder 솔로 SaaS, 가격 모델 미정 |
| **C1 Otter** | 월 600분 / 회의 3개 30분 | ~$17/월 (1200분, 90분/건) | ~$30/월 (Business, 6000분) | Enterprise custom |
| **C2 Granola** | 무료 베타 (2024 기준) | (유료 transition 미상) | (미상) | 출시 초기 |
| **C3 Reflect** | (확인 필요) | ~$10/월 | (팀 플랜 미상) | |
| **C4 Mem** | Free | Mem X ~$10/월 (AI 기능) | (확인 필요) | |
| **C5 Tana** | Free | Pro ~$10/월 | Plus ~$24/월 | |

### 2.3 타겟 사용자 `[전부 확인 필요]`

| 서비스 | 1차 타겟 | 2차 타겟 | Kairos 페르소나 매칭 (personas.md) |
|---|---|---|---|
| Kairos | 5-10명 팀 (PRD §2) | 다중 프로젝트 PM/PO | PERSONA-001 self-confirmed + PERSONA-002/003 `[가설]` |
| **C1 Otter** | 비즈니스 회의 (영어권) | 대학 강의 녹음 | PERSONA-002 (W1 1순위) 부분 매칭 |
| **C2 Granola** | macOS startup founder | 1:1 회의 많은 IC | PERSONA-002 1:1 부분 / PERSONA-003 클라이언트 회의 |
| **C3 Reflect** | 개인 지식 관리 | iOS/Mac 사용자 PKM | PERSONA-001 부분 (개인 노트 RAG) |
| **C4 Mem** | 개인 작가/researcher | knowledge worker 개인 | PERSONA-001 부분 (단일 사용자 범위) |
| **C5 Tana** | 노드 기반 PKM (Roam 후속) | 팀 협업 베타 | PERSONA-003 부분 (다중 프로젝트 DB) |

### 2.4 차별점 (ADR-010 thesis moat M1~M4 정렬)

| 서비스 | 차별점 1줄 `[확인 필요]` | Kairos M1 (계층 RAG) | Kairos M2 (자동 Inbox) | Kairos M3 (CODE 통합) | Kairos M4 (L4 미구현) |
|---|---|---|---|---|---|
| Kairos | 워크스페이스 단위 시간 누적 L4 (예정) + 자동화된 Inbox + 계층 RAG (ADR-010 thesis) | M1 自社 | M2 自社 | M3 自社 | M4 自社 |
| **C1 Otter** | 실시간 라이브 STT + 화자 분리 강함 | ⚠️ Otter Chat 단일 회의 범위, 계층 청킹 X | ❌ 폴더 수동 | ❌ STT+요약 단일 wedge | ❌ |
| **C2 Granola** | macOS 시스템 오디오 자동 캡처 (마찰 최소) | ❌ RAG 없음 | ❌ Notion export 의존 | ⚠️ Capture+Distill만 (Express 없음) | ❌ |
| **C3 Reflect** | 백링크 그래프 + iOS native | ⚠️ AI 검색 있으나 단일 사용자·계층 청킹 X | ❌ 수동 백링크 | ⚠️ Capture+Express (Distill L2 X) | ❌ |
| **C4 Mem** | AI 자동 분류 + 백링크 자동 | ⚠️ RAG Q&A 단일 사용자 범위 | ✅ AI 자동 분류 (Kairos M2와 직접 경쟁) | ⚠️ Capture+Organize+Express (Distill L2 X) | ❌ |
| **C5 Tana** | 슈퍼태그 + 데이터베이스 + 워크스페이스 협업 | ⚠️ AI Q&A 워크스페이스 범위 (계층 청킹 X) | ⚠️ 슈퍼태그 (수동·반자동) | ✅ Capture+Organize+Distill L2 부분+Express (Kairos와 가장 근접) | ❌ |

> **M2 (자동 Inbox) Mem 경쟁 주의**: ADR-010 §"M2"에서 "ChatGPT/Notion AI는 수동 분류 중심" 단언했으나, **Mem이 AI 자동 분류로 동일 영역**. ADR-010 M2 약점("메커니즘 모방 가능, 진짜 차별은 누적 품질")이 직접 적용 — Mem과 Kairos M2 비교에서 inbox_threshold 0.9(I-10) + 사용자 행동 시그널 S4 80%(ADR-009)가 차별 anchor.
>
> **M3 (CODE 통합) Tana 경쟁 주의**: Tana가 워크스페이스 + 슈퍼태그 + AI Q&A로 Kairos M3 통합 경험과 가장 근접. ADR-010 §"M3" 약점("일관성 자체가 약점, 모방 시 전환비용 낮음")이 가장 직접 위험. M3 강도 평가 "中" 정합.

---

## 3. ADR-010 위협 시나리오와 본 분석 관계

ADR-010 §"위협 시나리오 3개"는 **통합 도구**(ChatGPT memory+Projects / Notion AI / Granola) 위협. 본 분석 5개는 **단일 wedge 영역 경쟁자**(W1~W4). 두 컨텍스트 관계:

| 분류 | 서비스 | 위협 깊이 |
|---|---|---|
| **통합 도구 위협 (ADR-010 T1~T3)** | ChatGPT (T1), Notion AI (T2), Granola (T3) | thesis 흡수 risk — moat M1~M4 직접 위협 |
| **단일 wedge 경쟁 (본 분석 C1~C5)** | Otter (W1), Granola (W1, AD-17 cross-link), Reflect (W4), Mem (W3+M2), Tana (M3+W3) | wedge 선정 시 경쟁 우선순위 — ADR-009 F6 wedge 선정 ADR 입력 |
| **양쪽 등장** | Granola | AD-17 — 단일 wedge 경쟁 + 통합 도구 확장 시나리오 양쪽 |

ChatGPT memory + Notion AI는 본 분석에 별도 등장 X — 위협 시나리오 컨텍스트(통합 도구 흡수)에 한정. competitive analysis는 wedge 선정 입력으로 동작.

---

## 4. Kairos 차별점 요약 (ADR-010 thesis 정합)

본 분석을 통해 ADR-010 M1~M4 강도가 5개 경쟁자에 대해 어떻게 작동하는지 정리:

### 4.1 단기 (Sprint 6~Sprint 10 추정, L4 미구현 동안)

- **M1 (계층 RAG)**: 5개 경쟁자 중 Tana만 워크스페이스 범위 AI Q&A — 계층 청킹·6-Layer·1536d 임베딩·Semantic Cache 깊이는 Kairos 우위. 단 ADR-010 M1 강도 "中" — 청킹 전략 공개 기술이므로 단독으로는 약함.
- **M2 (자동 Inbox)**: Mem과 직접 경쟁. inbox_threshold 0.9 + 사용자 행동 시그널 S4 80%로 anchor. 차별 입증은 Sprint 6+ usage analytics 후.
- **M3 (CODE 통합)**: Tana가 가장 근접. Capture+Organize+Distill L2+Express 일관성이 Kairos 우위이나 모방 risk 높음.

### 4.2 장기 (Sprint 7+ 외부 인터뷰 후, L4 구현 시점 — ADR-007 Phase 4)

- **M4 (L4 조직 인사이트)**: 5개 경쟁자 중 **누구도 L4 영역에 진입 X** (모두 단일 사용자 또는 단일 워크스페이스 단기 범위). ADR-010 M4 "강(잠재)" 강도가 본 분석에서 가장 강력하게 뒷받침됨. **단 미구현 timeline risk가 thesis 약점** — Sprint 7+ L4 구현 ADR(F7) 진입 전까지는 약점 유지. timeline risk 대응 옵션은 **ADR-010 §4 O1/O2/O3** (Sprint 7 L4 우선화 vs Sprint 6 후 L4 vs L3 점진 → L4) — Sprint 6 완료 후 **ADR-009 F7 L4 우선화 검토 ADR**에서 옵션 선택.

### 4.3 ADR-009 wedge 선정 입력 (F6)

페르소나-Wedge 매트릭스(personas.md §4) + 본 경쟁자 분석 → ADR-009 F6 wedge 선정 ADR 입력:

- **W1 (회의 요약·액션) — Otter + Granola 직접 경쟁**: PERSONA-002 1순위. 단기 차별 깊이 = 계층 RAG로 회의 결과 즉시 RAG 통합 (Otter Chat은 단일 회의 범위). Granola는 macOS 한정 + Express 없음.
- **W2 (Inbox 자동 분류) — Mem 직접 경쟁**: PERSONA-001 2순위. inbox_threshold + 사용자 행동 시그널 차별 anchor.
- **W3 (프로젝트 RAG Q&A) — Mem + Tana 경쟁**: PERSONA-001/003 1순위 + **PERSONA-002 2순위 부분 수혜** (personas.md §4 매트릭스 — 3명 모두 W3 1-2순위). 워크스페이스 단위 격리(I-9) + 계층 청킹이 단일 사용자 범위 경쟁자 대비 우위.
- **W4 (노트 검색) — Reflect 경쟁**: PERSONA 우선순위 낮음 (1차). W3와 부분 중복.

---

## 5. 후속 보강 계획

| # | 작업 | 시점 | 결과물 |
|---|---|---|---|
| B1 | 본인 직접 사용 경험 보강 — Otter/Granola/Mem 중 ≥1개 1주 사용 후 §2 라벨 해제 | Sprint 6 진입 전 (선택) | 본 문서 patch + `[본인 경험 — YYYY-MM-DD]` 라벨 |
| B2 | 각 사 공식 문서 WebFetch — 5개 서비스 가격·기능 라벨 해제 | Sprint 6 진입 전 (필수) | 본 문서 patch + `[공식 — URL]` 라벨 |
| B3 | ADR-009 F6 wedge 선정 ADR 입력 — 본 §4.3 wedge별 차별 anchor 사용 | Sprint 6 완료 + F4 외부 인터뷰 결과 후 | `docs/dev-log/adr/012-wedge-selection.md` (예정) |
| B4 | ADR-010 thesis 갱신 — 본 §4.1~4.2 분석으로 moat 강도 재평가 (M1/M2/M3 中 유지 vs 강 상향?) | Sprint 7+ 외부 인터뷰 + L4 구현 진입 시점 | ADR-010 supersedes 또는 갱신 PR |
| B5 | competitive analysis 정기 갱신 사이클 — **매 Sprint 종료(경량 갱신)** + **분기 1회(풀 리뷰)** 분리. Sprint 주기는 ADR-009 F1~F10 기준 currently 미명시 — Sprint 6 킥오프 시 주기 lock-in 후 본 항목 정합 갱신. | 매 Sprint 종료 + 분기 1회 | 본 문서 patch |

---

## 6. Self-Check (작성 정합 점검)

- [x] 5개 서비스(Otter/Granola/Reflect/Mem/Tana) 모두 §1 개요 + §2.1~2.4 4개 차원 비교 작성.
- [x] 모든 사실 항목에 `[확인 필요]` 라벨 (AD-16 정합).
- [x] AD-17 Granola 양쪽 등장 cross-link 명시 (§3 표).
- [x] ADR-010 위협 시나리오 3개(T1~T3)와 본 분석 5개 관계 명시 (§3).
- [x] ADR-010 moat M1~M4 강도가 5개 경쟁자에 대해 어떻게 작동하는지 §4에 정리.
- [x] M2 Mem 경쟁 + M3 Tana 경쟁 주의 명시 (ADR-010 §M2/M3 약점과 정합).
- [x] personas.md Wedge 매트릭스 cross-link (§4.3 W1~W4 단기 차별 anchor).
- [x] ADR-009 F6 wedge 선정 ADR 입력 명시 (§4.3).
- [x] 후속 보강 5개 (B1~B5) 시점·결과물 명시.
- [x] CONTEXT-MAP §3 CODE 가치 흐름 매핑 (§2.1 표 헤더).
- [x] §6 도메인 정식 용어 사용 (Workspace, InboxItem, 별칭 없음).
