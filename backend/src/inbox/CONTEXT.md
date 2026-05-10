<!-- inbox 도메인 — 콘텐츠 1차 진입점 + AI 자동 분류 추천 + 사용자 조정 -->

# inbox CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- 모든 콘텐츠(회의/노트/자료)의 **1차 진입점** 적재
- AI가 추천한 프로젝트 연결 + 태그 저장 (`ai_suggested_*`)
- `workspaces.inbox_threshold` 기반 자동 확정 / 사용자 확인 분기
- 사용자의 분류(classify, N:M) 또는 무시(dismiss) 처리

## 2. 비책임

- 콘텐츠 원본 저장 (Meeting/Note/Source 도메인 별도)
- AI 추천 생성 (`services/ai_processing` — meetings 파이프라인이 호출)
- 임베딩

---

## 3. 엔티티 (소유)

- **InboxItem**
  - `title`, `summary` (UI 노출용 메타)
  - `source_type`: `meeting` / `note` / `attachment`
  - `source_id`: 원본 콘텐츠 ID
  - `ai_suggested_project_id` (단수), `ai_suggested_project_title`
  - `ai_suggested_tags` (JSONB)
  - `ai_confidence` (0.0~1.0)
  - `is_processed` (사용자 처리 완료 플래그)

> **비대칭 주의**: AI 추천은 **단수** (`ai_suggested_project_id`), 사용자 분류는 **N:M** (`classify` 엔드포인트의 `project_ids: list[UUID]`).

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 |
|---|---|---|
| out | `projects/repository` | Repository (read-only — 후보 프로젝트 조회) |
| out | `workspaces/repository` | Repository (read-only — `inbox_threshold` 조회) |
| in | `meetings/pipeline_service` | service 위임 (적재 시) |
| in | `notes/service` | service 위임 (적재 시) |
| in | `upload/service` | service 위임 (적재 시) |

---

## 5. 핵심 흐름

### 5.1 적재 (다른 도메인 → Inbox)
```
콘텐츠 생성 (회의 처리 완료 / 노트 작성 / 파일 업로드)
  → InboxService.create_from_<source>()
  → AI 추천 (project_id + tags + confidence) 저장
  → confidence 분기 (워크스페이스의 `inbox_threshold` 사용):
     ├─ confidence ≥ threshold: is_processed=true 자동 확정 (사용자 수정/되돌리기 가능)
     └─ confidence <  threshold: is_processed=false (사용자 확인 대기)
```

### 5.2 사용자 처리
```
GET    /inbox                  → 미처리(is_processed=false) 우선 정렬
POST   /inbox/{id}/classify    → 사용자가 project_ids: list[UUID] + tags 확정 (N:M)
POST   /inbox/{id}/dismiss     → 사용자가 무시 (is_processed=true, projects 비움)
```

---

## 6. 핵심 불변식

| # | 불변식 |
|---|---|
| IB-1 | **자동 확정 시에도 `ai_suggested_*` 필드 보존** (사용자가 되돌릴 수 있음) |
| IB-2 | **confidence 임계값은 워크스페이스별 `workspaces.inbox_threshold`** (기본 0.9, PATCH 가능) — 헌법 I-10 |
| IB-3 | **dismiss는 삭제 아님** — 감사/되돌리기 위해 보존 |
| IB-4 | **source_type + source_id 유일성** — 같은 콘텐츠 중복 적재 금지 |
| IB-5 | **classify는 idempotent + N:M** — 같은 InboxItem을 여러 번 classify해도 마지막 입력의 project_ids/tags가 최종 |

---

## 7. 엔드포인트

> 모두 `/api/v1/workspaces/{workspace_id}/inbox` prefix.

```
GET    /                    목록 (미처리 우선)
POST   /{id}/classify       확정/수정 (project_ids: list, tags: list)
POST   /{id}/dismiss        무시
```

---

## 8. 엣지 케이스

- AI 추천이 없는 경우 (confidence=0) → 사용자 확인 항상 필요
- 추천된 프로젝트가 삭제됨 → `ai_suggested_project_id` null 처리, 재추천 또는 사용자 선택
- 사용자가 새 프로젝트 생성하며 분류 → projects 도메인 호출 후 Inbox 확정
