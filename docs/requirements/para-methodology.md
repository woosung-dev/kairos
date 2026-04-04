# ~~PARA 방법론 구현 상세~~ (Deprecated)

> **⚠️ 이 문서는 ADR-004에 의해 대체되었습니다.**
> 현재 Kairos는 PARA 대신 **프로젝트 + 태그** 구조를 사용합니다.
> 최신 문서: [`second-brain.md`](second-brain.md) | 결정 근거: [`ADR-004`](../dev-log/004-second-brain-pivot.md)
>
> 아래 내용은 **기록 보존 목적**으로만 유지됩니다.

---

# PARA 방법론 구현 상세

> Tiago Forte의 PARA 방법론을 기반으로, **실행도(Actionability)**를 기준으로 정보를 분류한다.
> 단순한 주제별 폴더가 아니라, 정보의 "지금 당장 행동이 필요한 정도"에 따라 분류하는 시스템.

---

## 1. PARA 4계층 — 실행도 기반 분류

| 카테고리 | 정의 | 기준 | 실제 예시 |
|----------|------|------|-----------|
| **Projects** | 끝이 있고 목표가 명확한 업무 | 마감일 O, 구체적 결과물 O | "CMS 고도화 개발", "홈페이지 리뉴얼" |
| **Areas** | 지속적으로 책임져야 하는 영역 | 마감일 X, 지속적 기준 유지 | "보안 관리", "팀 온보딩" |
| **Resources** | 개인/조직의 관심사 및 참고 자료 | 당장 실행 불필요, 나중에 참고 | "기술 아티클", "벤치마킹 자료" |
| **Archives** | 완료/중단된 항목 | 비활성화, 검색 가능하게 보존 | 완료 프로젝트, 종료된 영역 |

### 분류 판단 기준 (AI 추천 로직)

```
마감일이 있고 구체적 결과물이 명확한가?
  → Yes: Project
  → No: 지속적으로 책임져야 하는 영역인가?
    → Yes: Area
    → No: 나중에 참고할 가치가 있는가?
      → Yes: Resource
      → No: Archive
```

---

## 2. Inbox — 모든 콘텐츠의 1차 진입점

- 회의록, 메모, 파일, 링크 등 **모든 생성 콘텐츠는 Inbox에 먼저 적재**
- AI가 PARA 분류를 추천하되, **최종 결정은 사용자가 확정**
- `is_processed=false` 상태로 적재 → 사용자 확정 시 `true`로 전환
- AI 추천 정보: `ai_suggested_para_type`, `ai_suggested_para_id`, `ai_confidence`

### Inbox 처리 흐름

```
콘텐츠 생성 (회의 업로드, 메모 작성 등)
  → Inbox 자동 적재 (is_processed=false)
  → AI가 PARA 분류 추천 (confidence score 포함)
  → 사용자가 Inbox에서 확인
  → PARA 분류 확정 (N:M 연결)
  → is_processed=true
```

---

## 3. N:M 관계형 연결 — 폴더 방식 탈피

### 핵심 설계 철학

- 전통적 **폴더 방식**: 하나의 회의록은 하나의 폴더에만 속함 → 정보 고립
- Kairos **관계형 방식**: 하나의 회의록이 **Project A + Area B**에 동시에 속할 수 있음

### 구현

```sql
-- content_para_links (N:M 중간 테이블)
CREATE TABLE content_para_links (
    id UUID PRIMARY KEY,
    content_id UUID NOT NULL,
    content_type VARCHAR(20) NOT NULL,  -- meeting | note | attachment
    para_item_id UUID NOT NULL REFERENCES para_items(id),
    linked_at TIMESTAMP DEFAULT NOW()
);
```

### 예시

하나의 회의에서 3개 주제를 논의한 경우:

| 회의 | 연결된 PARA | 타입 |
|------|-------------|------|
| "3월 킥오프 미팅" | CMS 고도화 개발 | Project |
| "3월 킥오프 미팅" | 보안 관리 | Area |
| "3월 킥오프 미팅" | AWS 전환 참고자료 | Resource |

→ Notion의 관계형 데이터베이스 방식 벤치마킹

---

## 4. Archive → Resource 재활용 사이클

### 상태 전환 규칙

```
Projects ↔ Areas ↔ Resources ↔ Archives
(단방향 X, 자유로운 상태 전환)
```

### Archive 전환 시 재활용 흐름

1. Project 완료 → "Archive로 이동" 선택
2. 시스템이 확인 모달 표시: **"내부 메모/회의록을 Resource로 보존하시겠습니까?"**
3. 사용자가 "예" 선택 → 내부 콘텐츠가 Resource로 전환
4. Archive된 데이터도 **RAG 검색 소스에 포함** (과거 성공 사례, 의사결정 맥락 복원)

### 핵심 가치

> **프로젝트가 끝나도 지식은 죽지 않는다.**
> Archive의 과거 성공 데이터가 새 프로젝트의 RAG 소스로 활용된다.

---

## 5. Weekly Review 워크플로우

Tiago Forte의 Weekly Review를 시스템으로 구현:

1. **Inbox 비우기** — 미분류 항목 확인, PARA 분류 확정
2. **Projects 점검** — 진행 중인 프로젝트의 액션 아이템 상태 확인
3. **Areas 점검** — 지속 관리 영역에 주의가 필요한 항목 확인
4. **다음 주 태스크** — 우선순위 정리, 기한 임박 액션 아이템 확인

### UI

- 좌측 사이드바 하단에 "Weekly Review" 바로가기
- `/weekly-review` 전용 가이드 뷰 제공
