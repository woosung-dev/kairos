<!-- actions 도메인 — 액션 아이템 추출/추적 (nullable 부모) -->

# actions CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- ActionItem CRUD (생성/조회/수정)
- 회의에서 자동 추출된 액션 저장 (meetings 파이프라인이 호출, `project_id` 미설정 가능)
- 사용자 수동 액션 생성 + 상태 변경
- 담당자 / 마감일 / 우선순위 관리

## 2. 비책임

- 액션 추출 알고리즘 (`services/ai_processing` — meetings 파이프라인이 사용)
- 알림 발송 (Phase B / 추후)

---

## 3. 엔티티 (소유)

- **ActionItem**
  - `workspace_id` (required — 멀티테넌시)
  - `meeting_id`: **nullable** (수동 생성 시 null)
  - `project_id`: **nullable** (orphan 허용, 후속 분류 대상 — §7 D-10)
  - `assignee_id`: **nullable** (미할당 액션 가능)
  - `due_date`: `date | None` — **timezone 없음** (`datetime.date` 타입). FE에서 사용자 로컬 해석
  - `title`, `description`
  - `priority`: `high` / `medium` / `low` (기본 `medium`)
  - `status`: `todo` / `in_progress` / `done` / `cancelled` (기본 `todo`)

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 |
|---|---|---|
| in | `meetings/pipeline` | Repository — 추출된 액션 저장 |
| out | `projects/repository` | Repository (read-only) — 부모 프로젝트 검증 (project_id 있을 때만) |
| out | `workspaces/repository` | Repository (read-only) — 담당자(WorkspaceMember) 검증 |

---

## 5. 핵심 불변식

| # | 불변식 |
|---|---|
| A-1 | **`workspace_id` 필수**, 그 외 부모 FK는 모두 nullable. `project_id=null` orphan은 허용 (사용자 분류 대상 — D-10) |
| A-2 | **status 전이는 자유** (todo ↔ in_progress ↔ done ↔ cancelled) |
| A-3 | **assignee는 워크스페이스 멤버만** (외부 사용자 할당 금지). null 허용 |
| A-4 | **AI 추출 액션도 사용자 수정 가능** — 출처(`meeting_id`)는 보존 |
| A-5 | **`due_date`는 `date` 타입 (timezone 없음)**. FE에서 사용자 로컬로 해석 — 시각 표시 시 timezone 추론 금지 |

---

## 6. 엔드포인트

> `/api/v1/workspaces/{workspace_id}/action-items` prefix (리소스 이름은 케밥 케이스).

```
GET    /                목록 (필터: project / assignee / status)
POST   /                생성 (201)
PATCH  /{id}            수정 (status / assignee / due_date / project_id 등)
```

---

## 7. 엣지 케이스

- 회의 삭제 → 자동 추출된 액션의 `meeting_id` null 처리 (액션 자체는 보존)
- 프로젝트 삭제 → 자동 archive 또는 cascade (Phase B 결정). 액션은 `project_id=null` orphan 처리 (§7 D-10)
- 마감 지난 액션 → 자동 알림 (Phase B / 추후)
- 같은 회의에서 중복 추출 → 텍스트 유사도 dedupe 부재 (CONTEXT-MAP §7 D-7)
