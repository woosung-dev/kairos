# 팀 세컨드 브레인 구현 상세

> Tiago Forte의 세컨드 브레인(Building a Second Brain)을 **팀 단위로, AI가 자동화**하여 적용한다.
> "머리는 아이디어를 만드는 곳이지, 저장하는 곳이 아니다" — 이것을 조직 전체로 확장.
>
> **이전 문서:** `para-methodology.md` (ADR-004에 의해 대체)

---

## 1. CODE 프레임워크 — 팀 세컨드 브레인의 핵심 사이클

| 단계 | 개인 세컨드 브레인 (원본) | Kairos (팀 확장) |
|------|------------------------|-----------------|
| **Capture** | 내가 메모, 하이라이트, 스크랩 | 회의 녹음, 노트 작성, 자료 업로드. 마찰 최소화. |
| **Organize** | 내 PARA에 분류 | 프로젝트에 AI 자동 연결 + 태그 자동 부여. 사용자는 선택적 조정. |
| **Distill** | Progressive Summarization (수동) | **AI Distillation (자동)** — Kairos의 핵심 차별점 |
| **Express** | 글쓰기, 발표 | RAG 검색, 프로액티브 인사이트, 보고서 생성 |

### AI Distillation — 4단계 자동 핵심 추출

L0~L4 정의 + 책임 도메인 매핑은 [`CONTEXT-MAP.md` §1](../../CONTEXT-MAP.md) single source. 본 문서는 사용자 가치 관점에서만 다룬다 — 개인 세컨드 브레인에서 가장 어렵고 귀찮은 Distill(핵심 추출)을 AI가 자동화하는 것이 Kairos 핵심 차별점.

---

## 2. 프로젝트 중심 구조 — PARA를 대체

### PARA를 제거하는 이유

1. PARA는 **개인** 생산성 도구. "이게 Area야 Resource야?" 팀원 5명이 5개 다른 답을 함
2. "프로젝트"는 모든 팀이 이미 사용하는 자연스러운 단위
3. 태그로 자유 분류 가능 (AI 자동 태그 + 수동)
4. Archive = 프로젝트 상태 "Archived" (별도 카테고리 불필요)

### 프로젝트 구조

```
프로젝트
├── 상태: Active / Completed / Archived
├── 공개: Public (기본) / Draft / Private
├── 콘텐츠: 회의, 노트, 자료 (통합, 시간순)
├── 태그: #보안 #인프라 #디자인 (AI 자동 + 수동)
├── 멤버: 프로젝트 참여자 (Join 모델)
└── 인사이트: AI 자동 종합 (L3)
```

### 사이드바 네비게이션

```
내 프로젝트
├── CMS 고도화 (Active) 🟢
├── 홈페이지 리뉴얼 (Active) 🟢
├── 보안 인프라 개선 (Active) 🟢
└── + 프로젝트 참여/생성

Inbox (3)

탐색
├── 전체 프로젝트 (Public)
└── 태그별 탐색
```

---

## 3. 개인 + 팀 지식 베이스 (승격 모델)

### 2-Layer 구조

```
Layer 1: 개인 지식 베이스
  → 자유롭게 아무거나 넣을 수 있음
  → 개인 메모, 브레인스토밍, 미완성 자료
  → 본인의 RAG에서만 검색됨

Layer 2: 팀 지식 베이스 (프로젝트)
  → 정제된 지식만 (승격된 콘텐츠)
  → 팀 프로젝트의 회의, 확정된 결정사항
  → 팀 RAG에서 검색됨
```

### 승격 흐름

```
개인 영역에서 콘텐츠 생성
  → AI: "이 내용이 CMS 고도화 프로젝트와 관련 있습니다. 팀에 공유할까요?"
  → [공유] → 팀 프로젝트에 링크 (원본은 개인에 남음)
  → [나만 보기] → 개인 영역에만 유지
```

### 자동 승격 조건

- 팀 프로젝트 내 회의 → 자동으로 팀 지식 (별도 승격 불필요)
- 개인 노트/자료 → AI 제안 + 사용자 확인 시 승격
- confidence 높은 자동 연결 → 사용자 조정 가능

---

## 4. Inbox — 콘텐츠의 1차 진입점

- 모든 생성 콘텐츠는 Inbox에 먼저 적재
- AI가 **프로젝트 연결 + 태그**를 자동 추천
- 기존 PARA와 다른 점: **분류 확정이 필수가 아닌 선택**
  - AI confidence가 높으면 자동 확정 (사용자는 잘못된 것만 수정/되돌리기)
  - confidence가 낮으면 사용자 확인 요청
- AI 추천 정보: `ai_suggested_project_id`, `ai_suggested_tags`, `ai_confidence`

### Inbox 처리 흐름 (ADR-006 §7 기준)

```
콘텐츠 생성 (회의 업로드, 노트 작성 등)
  → Inbox 적재
  → AI가 프로젝트 연결 + 태그 추천
  → 2그룹 분리:
     ├── confidence ≥ 0.9: ✅ AI 자동 확정 (수정/되돌리기 가능)
     └── confidence < 0.9: ⚠️ 사용자 확인 요청
  → 임계값은 사용자 조절 가능 (기본 90%)
```

---

## 5. 프로젝트 공개 범위

### Spotify 모델 — 기본 공개, 비공개는 예외 **[Sprint 6 구현 완료 — 2026-05-11 PR #12]**

| 상태 | 설명 | 누가 보는가 |
|------|------|------------|
| **Public** (기본값) | 워크스페이스 전체에 공개 | 모든 워크스페이스 멤버 |
| **Draft** | 작업 중 표시 (AD-24) | 작성자(creator) + admin/owner |
| **Private** | 프로젝트 멤버만 접근 (Sprint 6 L-6 ProjectMember 신설) | 명시 매핑된 ProjectMember + admin/owner |

> **권한 분기 위치**: `apps/backend/src/projects/repository.py:_apply_visibility_filter` (BE-T8). admin/owner는 모든 visibility 우회. RAG 검색에서도 동일 분기 적용 — Private 프로젝트는 비멤버 응답에서 자동 제외 (ADR-014 옵션 A, RagPipelineService).
>
> **시각화**: `apps/web/src/features/projects/components/visibility-badge.tsx` — lucide Globe(Public 청록 #3ECFB4) / FileEdit(Draft warning #FBBF24) / Lock(Private muted #6B6B73). 변경은 admin 이상만 (BE-T15).

### Archive 시 자동 공개 + 인사이트 추출

```
프로젝트 Completed → Archived 전환 시:
  → "이 프로젝트의 인사이트를 팀 전체에 공개할까요?" 확인
  → AI가 핵심 인사이트 자동 추출 (L3)
  → Public으로 전환
  → 다음 프로젝트에서 RAG로 검색 가능
```

> **Note (Sprint 6, ADR-014):** `Draft` — 작성자(creator)와 admin/owner만 조회 가능 (작업 중 상태). `Private` — ProjectMember만 조회 가능하며, RAG 검색에서 자동 제외되어 비멤버 응답에 포함되지 않음. 이 두 가지 visibility 모드로 개인↔팀 경계 구분이 완성됨.

---

## 6. 지식 신선도 관리 (Slite 참고)

모든 콘텐츠에 생성일 기준 경과 시간을 추적:

| 신선도 | 기간 | RAG에서 표시 |
|--------|------|-------------|
| 🟢 최근 | 1개월 이내 | (표시 없음) |
| 🟡 보통 | 1~3개월 | "3개월 전 회의 기반" |
| 🔴 오래됨 | 3개월+ | "오래된 소스입니다. 유효성 확인 필요" |

6개월 미갱신 콘텐츠: "이 정보가 아직 유효한지 확인해주세요" 알림.

---

## 7. 복리 지식 사이클 (Compound Knowledge)

이것이 Kairos의 핵심 가치 흐름이다:

```
프로젝트 진행 중
  → 회의, 노트, 자료가 계속 쌓임 (Capture)
  → AI가 자동으로 정리하고 인사이트 추출 (Organize + Distill)
  → RAG로 언제든 질문 가능 (Express)

프로젝트 완료
  → Archive + AI 인사이트 자동 추출
  → 조직 지식 베이스에 축적

새 프로젝트 시작
  → "비슷한 프로젝트 했던 적 있어?" → 과거 인사이트 자동 제시
  → "이 기술 스택 쓸 때 주의할 점?" → 과거 교훈 표면
  → 같은 실수를 반복하지 않는다

  ↓ 이 사이클이 반복될수록 조직이 똑똑해진다 ↓
```

---

## 8. 결정 사항 (Sprint 27a, ADR-023)

| 항목 | 결정 | 후속 BL |
|------|------|---------|
| 개인↔팀 경계 (승격) | I-18 복제 + tombstone (4 도메인 ItemPromotionAudit), 사용자 명시 액션 | — |
| 개인↔팀 경계 (퇴사) | WorkspaceMember 삭제 시 creator_id reference 유지, FE fallback "삭제된 사용자" | BL-S27-1 is_active soft delete |
| RAG 검색 범위 UX | 기본 = 워크스페이스 전체. Cmd+K 프로젝트 범위 드롭다운 (Sprint 3 구현) | BL-S27-2 신선도 라벨 |
| 회의 소속 | Workspace 직속, MeetingProjectLink N:M 옵션 (AI 자동 + 사용자 선택) | — |
| CEO/관리자 접근 | admin/owner = visibility bypass (현 코드). 운영 가시성 위해 audit log 후속 | BL-S27-3 AdminAccessAudit |
| 지식 생명주기 | audio R2 30일 TTL (구현). 텍스트 무기한. Project archive = AI 인사이트 자동 추출 | BL-S27-2 신선도 라벨 + 6개월 stale 알림 |

상세 trade-off + 회수 옵션: `docs/adr/023-second-brain-context-boundaries.md`.
