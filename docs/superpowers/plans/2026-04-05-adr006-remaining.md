# ADR-006 잔여 (임계값 설정 + 내보내기) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ADR-006 UI/UX 개편의 미완료 2개 항목을 마무리하여 11/11 완료로 닫는다.

**Architecture:** Workspace 모델에 `inbox_threshold` 컬럼 추가 + 파이프라인에서 동적 참조. 내보내기는 각 서비스에 export 메서드 추가 + 라우터에 GET export 엔드포인트.

**Tech Stack:** FastAPI + SQLModel + Alembic (BE), Next.js 16 + React Query + Tailwind (FE)

---

## File Map

### 새로 생성
| 파일 | 역할 |
|------|------|
| `backend/alembic/versions/*_add_inbox_threshold.py` | 마이그레이션 |
| `backend/tests/workspaces/test_settings_api.py` | 임계값 설정 API 테스트 |
| `backend/tests/meetings/test_export.py` | 회의 내보내기 테스트 |
| `backend/tests/notes/test_export.py` | 노트 내보내기 테스트 |
| `frontend/src/features/workspaces/hooks.ts` | 워크스페이스 설정 mutation 훅 |
| `frontend/src/features/meetings/components/export-button.tsx` | 회의 내보내기 버튼 |
| `frontend/src/features/notes/components/export-button.tsx` | 노트 내보내기 버튼 |

### 수정
| 파일 | 변경 |
|------|------|
| `backend/src/workspaces/models.py` | `inbox_threshold` 컬럼 추가 |
| `backend/src/workspaces/schemas.py` | 설정 요청/응답 스키마 |
| `backend/src/workspaces/repository.py` | `update_threshold()` |
| `backend/src/workspaces/service.py` | `update_settings()`, `get_workspace()` 응답에 threshold 포함 |
| `backend/src/workspaces/router.py` | `PATCH /workspaces/{id}/settings` |
| `backend/src/meetings/pipeline_service.py:155,160,174` | 하드코딩 0.9 → workspace.inbox_threshold |
| `backend/src/meetings/router.py` | `GET /meetings/{id}/export` |
| `backend/src/meetings/service.py` | `export_meeting()` |
| `backend/src/notes/router.py` | `GET /notes/{id}/export` |
| `backend/src/notes/service.py` | `export_note()` |
| `frontend/src/app/(app)/settings/page.tsx` | 일반 탭에 임계값 프리셋 UI |
| `frontend/src/features/workspaces/api.ts` | `updateWorkspaceSettings()` |
| `frontend/src/features/meetings/api.ts` | `exportMeeting()` |
| `frontend/src/features/notes/api.ts` | `exportNote()` |
| `frontend/src/features/meetings/components/meeting-detail.tsx` | 헤더에 ExportButton 추가 |

---

## Task 1: Workspace inbox_threshold 컬럼 + 마이그레이션

**Files:**
- Modify: `backend/src/workspaces/models.py`
- Create: `backend/alembic/versions/*_add_inbox_threshold.py`

- [ ] **Step 1: Workspace 모델에 inbox_threshold 추가**

```python
# backend/src/workspaces/models.py — Workspace 클래스에 추가
class Workspace(SQLModel, table=True):
    __tablename__ = "workspaces"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    owner_id: uuid.UUID = Field(foreign_key="users.id")
    inbox_threshold: float = Field(default=0.9)  # AI 자동 확정 임계값 (0.5~1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

- [ ] **Step 2: Alembic 마이그레이션 생성**

Run: `cd backend && .venv/bin/python -m alembic revision --autogenerate -m "add_inbox_threshold"`

- [ ] **Step 3: 마이그레이션 파일 정리**

자동 생성된 마이그레이션에서 기존 인덱스 삭제 감지를 제거하고, inbox_threshold 컬럼 추가만 남긴다.

```python
def upgrade() -> None:
    op.add_column('workspaces', sa.Column('inbox_threshold', sa.Float(), nullable=False, server_default='0.9'))

def downgrade() -> None:
    op.drop_column('workspaces', 'inbox_threshold')
```

- [ ] **Step 4: 마이그레이션 적용**

Run: `cd backend && .venv/bin/python -m alembic upgrade head`

- [ ] **Step 5: 커밋**

```bash
git add backend/src/workspaces/models.py backend/alembic/versions/*_add_inbox_threshold.py
git commit -m "feat: Workspace inbox_threshold 컬럼 추가"
```

---

## Task 2: 임계값 설정 BE API

**Files:**
- Modify: `backend/src/workspaces/schemas.py`
- Modify: `backend/src/workspaces/repository.py`
- Modify: `backend/src/workspaces/service.py`
- Modify: `backend/src/workspaces/router.py`
- Create: `backend/tests/workspaces/test_settings_api.py`

- [ ] **Step 1: 스키마 추가**

```python
# backend/src/workspaces/schemas.py — 추가

class UpdateWorkspaceSettingsRequest(BaseModel):
    inbox_threshold: float = Field(ge=0.5, le=1.0)
```

- [ ] **Step 2: Repository에 update_threshold 추가**

```python
# backend/src/workspaces/repository.py — 추가

async def update_threshold(
    self, workspace_id: uuid.UUID, threshold: float
) -> None:
    await self.session.execute(
        update(Workspace)
        .where(Workspace.id == workspace_id)
        .values(inbox_threshold=threshold, updated_at=datetime.now(UTC))
    )
```

- [ ] **Step 3: Service에 update_settings 추가**

```python
# backend/src/workspaces/service.py — 추가

async def update_settings(
    self, workspace_id: uuid.UUID, inbox_threshold: float
) -> dict:
    workspace = await self.repo.find_by_id(workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError()
    await self.repo.update_threshold(workspace_id, inbox_threshold)
    await self.repo.commit()
    return {"inboxThreshold": inbox_threshold}
```

- [ ] **Step 4: get_workspace 응답에 inboxThreshold 포함**

`service.py`의 `get_workspace()` 반환 dict에 `"inboxThreshold": workspace.inbox_threshold` 추가.

- [ ] **Step 5: Router에 PATCH /settings 엔드포인트 추가**

```python
# backend/src/workspaces/router.py — 추가

@router.patch("/{workspace_id}/settings")
async def update_workspace_settings(
    workspace_id: uuid.UUID,
    data: UpdateWorkspaceSettingsRequest,
    member: WorkspaceMember = Depends(require_owner),
    service: WorkspaceService = Depends(get_workspace_service),
):
    return await service.update_settings(workspace_id, data.inbox_threshold)
```

- [ ] **Step 6: 테스트 작성**

```python
# backend/tests/workspaces/test_settings_api.py

@pytest.mark.asyncio
async def test_update_threshold(client, mock_service):
    mock_service.update_settings.return_value = {"inboxThreshold": 0.8}
    res = await client.patch(
        f"/api/v1/workspaces/{WID}/settings",
        json={"inbox_threshold": 0.8},
    )
    assert res.status_code == 200
    assert res.json()["inboxThreshold"] == 0.8

@pytest.mark.asyncio
async def test_update_threshold_invalid(client, mock_service):
    res = await client.patch(
        f"/api/v1/workspaces/{WID}/settings",
        json={"inbox_threshold": 0.3},  # 0.5 미만 → 422
    )
    assert res.status_code == 422
```

- [ ] **Step 7: 테스트 실행 + 커밋**

Run: `.venv/bin/python -m pytest tests/workspaces/test_settings_api.py -v`

```bash
git add backend/src/workspaces/ backend/tests/workspaces/test_settings_api.py
git commit -m "feat: Inbox 임계값 설정 API (PATCH /workspaces/{id}/settings)"
```

---

## Task 3: 파이프라인 하드코딩 제거

**Files:**
- Modify: `backend/src/meetings/pipeline_service.py:155,160,174`
- Modify: `backend/src/meetings/dependencies.py`

- [ ] **Step 1: PipelineService에 workspace_repo 주입 확인**

이미 `self.meeting_repo`가 있고, meeting에서 `workspace_id`를 알 수 있다. workspace를 조회하려면 WorkspaceRepository가 필요하지만, 이미 meeting에서 workspace_id를 알고 있으므로 직접 조회한다.

pipeline_service.py의 `__init__`에 이미 다른 repo들이 주입되어 있다. WorkspaceRepository를 추가로 주입하는 대신, 파이프라인 시작 시 workspace를 한 번 조회하는 방식을 사용한다.

pipeline_service.py의 `__init__`에 `workspace_repo: WorkspaceRepository` 파라미터 추가:

```python
from src.workspaces.repository import WorkspaceRepository

class MeetingPipelineService:
    def __init__(
        self,
        meeting_repo: MeetingRepository,
        project_repo: ProjectRepository,
        action_repo: ActionItemRepository,
        inbox_repo: InboxRepository,
        workspace_repo: WorkspaceRepository,  # 추가
        r2_service: R2Service,
        transcription_service: TranscriptionService,
        ai_service: AIProcessingService,
        embedding_service: EmbeddingService,
    ) -> None:
        # ... 기존 + 추가
        self.workspace_repo = workspace_repo
```

- [ ] **Step 2: dependencies.py에 workspace_repo 주입**

```python
# backend/src/meetings/dependencies.py — get_pipeline_service 수정

from src.workspaces.repository import WorkspaceRepository

async def get_pipeline_service(
    session: AsyncSession = Depends(get_async_session),
) -> MeetingPipelineService:
    return MeetingPipelineService(
        meeting_repo=MeetingRepository(session),
        project_repo=ProjectRepository(session),
        action_repo=ActionItemRepository(session),
        inbox_repo=InboxRepository(session),
        workspace_repo=WorkspaceRepository(session),  # 추가
        r2_service=R2Service(),
        transcription_service=TranscriptionService(),
        ai_service=AIProcessingService(),
        embedding_service=EmbeddingService(EmbeddingRepository(session)),
    )
```

- [ ] **Step 3: 파이프라인에서 workspace.inbox_threshold 사용**

`process_meeting()` 메서드 내에서, meeting 조회 직후 workspace를 조회하여 threshold를 얻는다:

```python
# pipeline_service.py — process_meeting() 내부, meeting 조회 후

workspace = await self.workspace_repo.find_by_id(meeting.workspace_id)
threshold = workspace.inbox_threshold if workspace else 0.9
```

그리고 155행, 160행, 174행의 `0.9`를 `threshold`로 교체:

```python
# 155행
is_processed=confidence >= threshold,

# 160행
if confidence >= threshold and existing_project_id_str:

# 174행
if confidence >= threshold and existing_project_id_str:
```

- [ ] **Step 4: 기존 테스트 실행 확인**

Run: `.venv/bin/python -m pytest tests/meetings/test_pipeline.py -v`

- [ ] **Step 5: 커밋**

```bash
git add backend/src/meetings/pipeline_service.py backend/src/meetings/dependencies.py
git commit -m "refactor: 파이프라인 임계값 하드코딩 제거 → workspace.inbox_threshold 참조"
```

---

## Task 4: 임계값 설정 FE UI

**Files:**
- Create: `frontend/src/features/workspaces/hooks.ts`
- Modify: `frontend/src/features/workspaces/api.ts`
- Modify: `frontend/src/app/(app)/settings/page.tsx`

- [ ] **Step 1: 워크스페이스 API에 settings 함수 추가**

```typescript
// frontend/src/features/workspaces/api.ts — 추가

export async function updateWorkspaceSettings(
  token: string,
  wid: string,
  data: { inbox_threshold: number }
): Promise<{ inboxThreshold: number }> {
  return apiClient(`/workspaces/${wid}/settings`, {
    token,
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
```

- [ ] **Step 2: 워크스페이스 hooks 생성**

```typescript
// frontend/src/features/workspaces/hooks.ts
"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { updateWorkspaceSettings } from "./api";

export function useUpdateWorkspaceSettings(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { inbox_threshold: number }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return updateWorkspaceSettings(token, wid!, data);
    },
    onSuccess: (result) => {
      toast.success(`임계값이 ${Math.round(result.inboxThreshold * 100)}%로 변경되었습니다`);
      if (wid) {
        queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "설정 변경에 실패했습니다");
    },
  });
}
```

- [ ] **Step 3: /settings 일반 탭에 프리셋 버튼 UI 추가**

`app/(app)/settings/page.tsx`의 "일반" TabsContent에 `ThresholdSettings` 컴포넌트를 추가. 프리셋 버튼 4개 (0.7, 0.8, 0.9, 0.95), 현재 워크스페이스의 threshold 값을 표시, 클릭 시 mutation 호출.

워크스페이스 상세 조회(`GET /workspaces/{id}`)에서 `inboxThreshold`를 받아와 현재 선택된 값 표시.

- [ ] **Step 4: tsc --noEmit 확인**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/features/workspaces/api.ts frontend/src/features/workspaces/hooks.ts frontend/src/app/\(app\)/settings/page.tsx
git commit -m "feat: Inbox 임계값 설정 FE — 프리셋 버튼 UI"
```

---

## Task 5: 회의 내보내기 BE

**Files:**
- Modify: `backend/src/meetings/service.py`
- Modify: `backend/src/meetings/router.py`
- Create: `backend/tests/meetings/test_export.py`

- [ ] **Step 1: MeetingService에 export_meeting 추가**

```python
# backend/src/meetings/service.py — 추가

async def export_meeting(
    self, meeting_id: uuid.UUID, fmt: str
) -> tuple[str, str, str]:
    """회의 내보내기. (content, filename, media_type) 반환."""
    meeting = await self.repo.find_by_id(meeting_id)
    if meeting is None:
        raise MeetingNotFoundError()

    segments = await self.repo.get_segments(meeting_id)
    summary = await self.repo.get_summary(meeting_id)
    # 액션 아이템은 별도 repo가 필요하므로 일단 요약+트랜스크립트만

    if fmt == "md":
        content = self._to_markdown(meeting, summary, segments)
        return content, f"{meeting.title}.md", "text/markdown; charset=utf-8"
    else:
        data = self.get_meeting_detail.__wrapped__(self, meeting_id)
        # JSON은 기존 상세 응답 재활용
        detail = await self.get_meeting_detail(meeting_id)
        import json
        content = json.dumps(detail, ensure_ascii=False, indent=2)
        return content, f"{meeting.title}.json", "application/json; charset=utf-8"

@staticmethod
def _to_markdown(meeting, summary, segments) -> str:
    lines = [f"# {meeting.title}"]
    if meeting.recorded_at:
        lines.append(f"> {meeting.recorded_at.strftime('%Y-%m-%d')}")
    lines.append("")

    if summary:
        lines.append("## 요약")
        lines.append(summary.summary)
        lines.append("")

        if summary.key_decisions:
            lines.append("## 핵심 결정사항")
            for d in summary.key_decisions:
                lines.append(f"- {d}")
            lines.append("")

    if segments:
        lines.append("## 트랜스크립트")
        for seg in segments:
            mins = int(seg.start_sec // 60)
            secs = int(seg.start_sec % 60)
            lines.append(f"**{seg.speaker}** ({mins:02d}:{secs:02d}): {seg.text}")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 2: Router에 export 엔드포인트 추가**

```python
# backend/src/meetings/router.py — 추가

from fastapi.responses import Response

@router.get("/{meeting_id}/export")
async def export_meeting(
    workspace_id: uuid.UUID,
    meeting_id: uuid.UUID,
    format: str = Query(default="md", regex="^(md|json)$"),
    member: WorkspaceMember = Depends(require_viewer),
    service: MeetingService = Depends(get_meeting_service),
):
    content, filename, media_type = await service.export_meeting(meeting_id, format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 3: 테스트 작성 + 실행**

```python
# backend/tests/meetings/test_export.py

@pytest.mark.asyncio
async def test_export_meeting_md(client, mock_service):
    mock_service.export_meeting.return_value = (
        "# 테스트 회의\n\n## 요약\n테스트",
        "테스트 회의.md",
        "text/markdown; charset=utf-8",
    )
    res = await client.get(
        f"/api/v1/workspaces/{WID}/meetings/{MID}/export?format=md",
    )
    assert res.status_code == 200
    assert "테스트 회의" in res.text
```

Run: `.venv/bin/python -m pytest tests/meetings/test_export.py -v`

- [ ] **Step 4: 커밋**

```bash
git add backend/src/meetings/service.py backend/src/meetings/router.py backend/tests/meetings/test_export.py
git commit -m "feat: 회의 내보내기 API (GET /meetings/{id}/export?format=md|json)"
```

---

## Task 6: 노트 내보내기 BE

**Files:**
- Modify: `backend/src/notes/service.py`
- Modify: `backend/src/notes/router.py`
- Create: `backend/tests/notes/test_export.py`

- [ ] **Step 1: NoteService에 export_note 추가**

```python
# backend/src/notes/service.py — 추가
import json

async def export_note(
    self, note_id: uuid.UUID, fmt: str
) -> tuple[str, str, str]:
    """노트 내보내기. (content, filename, media_type) 반환."""
    note = await self.repo.find_by_id(note_id)
    if note is None:
        raise NoteNotFoundError()

    title = note.title or "Untitled"

    if fmt == "md":
        content = f"# {title}\n\n{note.plain_text}"
        return content, f"{title}.md", "text/markdown; charset=utf-8"
    else:
        data = {
            "id": str(note.id),
            "title": title,
            "content": note.content,
            "plainText": note.plain_text,
            "createdAt": note.created_at.isoformat(),
            "updatedAt": note.updated_at.isoformat(),
        }
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return content, f"{title}.json", "application/json; charset=utf-8"
```

- [ ] **Step 2: Router에 export 엔드포인트 추가**

```python
# backend/src/notes/router.py — 추가

from fastapi.responses import Response

@router.get("/{note_id}/export")
async def export_note(
    workspace_id: uuid.UUID,
    note_id: uuid.UUID,
    format: str = Query(default="md", regex="^(md|json)$"),
    member: WorkspaceMember = Depends(require_viewer),
    service: NoteService = Depends(get_note_service),
):
    content, filename, media_type = await service.export_note(note_id, format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 3: 테스트 작성 + 실행**

Run: `.venv/bin/python -m pytest tests/notes/test_export.py -v`

- [ ] **Step 4: 커밋**

```bash
git add backend/src/notes/service.py backend/src/notes/router.py backend/tests/notes/test_export.py
git commit -m "feat: 노트 내보내기 API (GET /notes/{id}/export?format=md|json)"
```

---

## Task 7: 내보내기 FE (ExportButton + API)

**Files:**
- Modify: `frontend/src/features/meetings/api.ts`
- Modify: `frontend/src/features/notes/api.ts`
- Create: `frontend/src/features/meetings/components/export-button.tsx`
- Create: `frontend/src/features/notes/components/export-button.tsx`
- Modify: `frontend/src/features/meetings/components/meeting-detail.tsx`

- [ ] **Step 1: meetings/api.ts에 exportMeeting 추가**

```typescript
// frontend/src/features/meetings/api.ts — 추가

export async function exportMeeting(
  token: string,
  wid: string,
  id: string,
  format: "md" | "json"
): Promise<Blob> {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(
    `${API_BASE_URL}/api/v1/workspaces/${wid}/meetings/${id}/export?format=${format}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) throw new Error("내보내기에 실패했습니다");
  return res.blob();
}
```

- [ ] **Step 2: notes/api.ts에 exportNote 추가**

동일 패턴으로 `exportNote` 함수 추가.

- [ ] **Step 3: ExportButton 컴포넌트 생성**

재사용 가능한 ExportButton: Download 아이콘 + DropdownMenu (MD / JSON). 클릭 시 API 호출 → blob → download trigger.

```typescript
// frontend/src/features/meetings/components/export-button.tsx
"use client";

import { Download } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { exportMeeting } from "../api";

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

interface MeetingExportButtonProps {
  meetingId: string;
  meetingTitle: string;
}

export function MeetingExportButton({ meetingId, meetingTitle }: MeetingExportButtonProps) {
  const { getToken } = useAuth();
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);

  const handleExport = async (format: "md" | "json") => {
    try {
      const token = await getToken();
      if (!token || !wid) return;
      const blob = await exportMeeting(token, wid, meetingId, format);
      const ext = format === "md" ? "md" : "json";
      triggerDownload(blob, `${meetingTitle}.${ext}`);
      toast.success("내보내기 완료");
    } catch {
      toast.error("내보내기에 실패했습니다");
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="inline-flex items-center justify-center h-8 w-8 rounded-md cursor-pointer transition-colors duration-150 hover:bg-[var(--surface-active)]"
      >
        <Download className="w-4 h-4" style={{ color: "var(--text-secondary)" }} />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem className="cursor-pointer" onClick={() => handleExport("md")}>
          Markdown (.md)
        </DropdownMenuItem>
        <DropdownMenuItem className="cursor-pointer" onClick={() => handleExport("json")}>
          JSON (.json)
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

노트용 ExportButton도 동일 패턴으로 생성 (`exportNote` 사용).

- [ ] **Step 4: 회의 상세 페이지 헤더에 ExportButton 추가**

`meeting-detail.tsx`의 제목 영역에 `<MeetingExportButton meetingId={meetingId} meetingTitle={meeting.title} />` 추가.

- [ ] **Step 5: tsc --noEmit 확인**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/features/meetings/ frontend/src/features/notes/ frontend/src/app/
git commit -m "feat: 회의/노트 내보내기 FE — ExportButton + MD/JSON 다운로드"
```

---

## Verification

전체 완료 후:

1. **BE 테스트:** `.venv/bin/python -m pytest tests/ -v` — 기존 + 신규 테스트 모두 통과
2. **FE 타입:** `npx tsc --noEmit` — 오류 없음
3. **코드 리뷰:** `superpowers:requesting-code-review` 실행
4. **QA:** `/qa` 스킬로 /settings 페이지 + 내보내기 버튼 검증
5. **TODO.md 업데이트:** ADR-006 11/11 완료 기록
