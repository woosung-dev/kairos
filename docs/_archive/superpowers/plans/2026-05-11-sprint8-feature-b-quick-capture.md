# Sprint 8 Feature B — Quick Capture (텍스트 → Inbox) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 텍스트를 붙여넣으면 AI가 분석하여 Inbox에 적재하는 영구 캡처 기능을 `/new` 페이지에 탭으로 추가한다.

**Architecture:** BE는 `POST /workspaces/{wid}/meetings/capture` 엔드포인트를 추가하고 `pipeline_service.process_meeting`에서 STT 단계를 건너뛰는 `capture_text` 메서드를 신설한다. FE는 `/new/page.tsx`의 meeting 카드에 "오디오 업로드 | 텍스트로 입력" 탭을 추가한다. 기존 AI 분석(`summarize`, `extract_actions_and_link`) 로직을 그대로 재활용한다.

**Tech Stack:** FastAPI, SQLModel, Alembic, Next.js (App Router), React 19, TypeScript strict, zod/v4

---

## 파일 구조

| 작업 | 경로 |
|------|------|
| **수정** | `backend/src/meetings/models.py` — `Meeting.source` 컬럼 추가 |
| **신규** | `backend/alembic/versions/<hash>_add_meeting_source.py` |
| **수정** | `backend/src/meetings/schemas.py` — `CaptureTextRequest` 추가 |
| **수정** | `backend/src/meetings/pipeline_service.py` — `capture_text` 메서드 추가 |
| **수정** | `backend/src/meetings/router.py` — `/capture` 엔드포인트 추가 |
| **수정** | `frontend/src/features/meetings/api.ts` — `captureText` 함수 추가 |
| **수정** | `frontend/src/features/meetings/hooks.ts` — `useCaptureText` 훅 추가 |
| **수정** | `frontend/src/app/(app)/new/page.tsx` — 텍스트 탭 추가 |

---

## Task 1: `Meeting.source` 컬럼 + 마이그레이션

**Files:**
- Modify: `backend/src/meetings/models.py`
- Create: `backend/alembic/versions/<hash>_add_meeting_source.py`

- [ ] **Step 1: `Meeting` 모델에 `source` 컬럼 추가**

`backend/src/meetings/models.py`에서 `Meeting` 클래스에 `source` 필드를 추가한다.

기존 `file_key` 필드 아래에 추가:
```python
source: str | None = None  # None=오디오, "text"=텍스트 캡처
```

전체 Meeting 클래스 관련 변경 결과:
```python
class Meeting(SQLModel, table=True):
    __tablename__ = "meetings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    title: str
    file_key: str  # R2 저장 경로 (source="text"이면 빈 문자열)
    source: str | None = None  # None=오디오, "text"=텍스트 캡처
    recorded_at: datetime | None = None
    duration_sec: int | None = None
    status: str = "uploading"
    error_message: str | None = None
    has_transcript: bool = False
    has_summary: bool = False
    action_item_count: int = 0
    created_by_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 2: Alembic 마이그레이션 생성**

```bash
cd /Users/woosung/project/agy-project/kairos/backend
alembic revision --autogenerate -m "add_meeting_source"
```

생성된 파일을 열어 `upgrade()`가 아래처럼 됐는지 확인:
```python
def upgrade() -> None:
    op.add_column('meetings', sa.Column('source', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('meetings', 'source')
```

- [ ] **Step 3: 마이그레이션 적용 (로컬 DB)**

```bash
alembic upgrade head
```

Expected: `Running upgrade ... -> <hash>, add_meeting_source`

- [ ] **Step 4: 커밋**

```bash
cd /Users/woosung/project/agy-project/kairos
git add backend/src/meetings/models.py backend/alembic/versions/
git commit -m "feat(meetings): Meeting.source 컬럼 추가 (Quick Capture BE-T14)"
```

---

## Task 2: BE — `CaptureTextRequest` 스키마 + `capture_text` 서비스 메서드

**Files:**
- Modify: `backend/src/meetings/schemas.py`
- Modify: `backend/src/meetings/pipeline_service.py`

- [ ] **Step 1: `CaptureTextRequest` 스키마 추가**

`backend/src/meetings/schemas.py` 하단에 추가:

```python
class CaptureTextRequest(BaseModel):
    title: str
    transcript_text: str = Field(alias="transcriptText", min_length=50)

    model_config = {"populate_by_name": True}
```

- [ ] **Step 2: `MeetingPipelineService`에 `capture_text` 메서드 추가**

`backend/src/meetings/pipeline_service.py`에서 `process_meeting` 메서드 아래에 추가.
파일 상단 import를 확인하고 빠진 것이 있으면 추가한다.

```python
async def capture_text(self, meeting_id: uuid.UUID, transcript_text: str) -> None:
    """텍스트 캡처 파이프라인 — STT 건너뛰고 분석부터 시작."""
    try:
        meeting = await self.meeting_repo.find_by_id(meeting_id)
        if meeting is None:
            return

        workspace = await self.workspace_repo.find_by_id(meeting.workspace_id)
        threshold = workspace.inbox_threshold if workspace else 0.9

        await self.meeting_repo.update_status(meeting_id, "analyzing")
        await self.meeting_repo.commit()

        # 트랜스크립트 세그먼트 1개로 저장
        segment = TranscriptSegment(
            meeting_id=meeting_id,
            speaker="텍스트",
            start_sec=0.0,
            end_sec=0.0,
            text=transcript_text,
        )
        await self.meeting_repo.save_segments(meeting_id, [segment])
        await self.meeting_repo.set_has_transcript(meeting_id, True)

        # 요약
        summary_data = await self.ai_service.summarize(transcript_text)
        await self.meeting_repo.save_summary(meeting_id, summary_data)
        await self.meeting_repo.set_has_summary(meeting_id, True)

        # 액션 추출 + 프로젝트 연결
        existing_projects = await self.project_repo.find_by_workspace(meeting.workspace_id)
        project_list = [
            {"id": str(p.id), "title": p.title, "status": p.status}
            for p in existing_projects
        ]
        actions_data = await self.ai_service.extract_actions_and_link(
            transcript_text, summary_data.get("summary", ""), project_list
        )

        action_count = 0
        for ai_action in actions_data.get("actionItems", []):
            action_item = ActionItem(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                title=ai_action["title"],
                description=ai_action.get("description"),
                priority=ai_action.get("priority", "medium"),
            )
            due_date_str = ai_action.get("dueDate")
            if due_date_str:
                try:
                    action_item.due_date = date.fromisoformat(due_date_str)
                except ValueError:
                    pass
            await self.action_repo.save(action_item)
            action_count += 1

        meeting = await self.meeting_repo.find_by_id(meeting_id)
        if meeting:
            meeting.action_item_count = action_count

        # InboxItem 생성
        suggested = actions_data.get("suggestedProject", {})
        confidence = suggested.get("confidence", 0.0)
        existing_project_id_str = suggested.get("existingProjectId")

        inbox_item = InboxItem(
            workspace_id=meeting.workspace_id,
            title=f"{meeting.title} 요약",
            summary=summary_data.get("summary", ""),
            source_type="meeting",
            source_id=meeting.id,
            ai_suggested_project_id=(
                uuid.UUID(existing_project_id_str) if existing_project_id_str else None
            ),
            ai_suggested_project_title=suggested.get("newProjectTitle"),
            ai_suggested_tags=actions_data.get("suggestedTags", []),
            ai_confidence=confidence,
            is_processed=confidence >= threshold,
        )
        await self.inbox_repo.save(inbox_item)

        if confidence >= threshold and existing_project_id_str:
            await self.project_repo.add_meeting_link(
                meeting.id, uuid.UUID(existing_project_id_str)
            )

        # 임베딩 (비치명적)
        try:
            project_id = uuid.UUID(existing_project_id_str) if (confidence >= threshold and existing_project_id_str) else None
            chunk_count = await self.embedding_service.embed_meeting(
                meeting_id=meeting.id,
                workspace_id=meeting.workspace_id,
                project_id=project_id,
                title=meeting.title,
                segments=[{"speaker": "텍스트", "text": transcript_text, "start_sec": 0.0, "end_sec": 0.0}],
            )
            await self.embedding_service.invalidate_cache(meeting.workspace_id, project_id)
        except Exception as emb_err:
            logger.warning("임베딩 생성 실패 (비치명적, meeting=%s): %s", meeting_id, emb_err)

        await self.meeting_repo.update_status(meeting_id, "completed")
        await self.meeting_repo.commit()

    except Exception as e:
        logger.exception("capture_text 파이프라인 실패 (meeting=%s): %s", meeting_id, e)
        await self.meeting_repo.update_status(meeting_id, "failed", error_message=str(e))
        await self.meeting_repo.commit()
```

`capture_text`가 사용하는 import가 이미 파일 상단에 있는지 확인한다 (`ActionItem`, `InboxItem`, `TranscriptSegment`, `date`, `logger`). 없으면 추가.

- [ ] **Step 3: 커밋**

```bash
cd /Users/woosung/project/agy-project/kairos
git add backend/src/meetings/schemas.py backend/src/meetings/pipeline_service.py
git commit -m "feat(meetings): CaptureTextRequest 스키마 + capture_text 파이프라인 메서드"
```

---

## Task 3: BE — `/capture` 엔드포인트

**Files:**
- Modify: `backend/src/meetings/router.py`

- [ ] **Step 1: import에 `CaptureTextRequest` 추가**

`router.py` 상단 import에 추가:
```python
from src.meetings.schemas import CaptureTextRequest, CreateMeetingRequest
```

- [ ] **Step 2: `/capture` 엔드포인트 추가**

`router.py`에서 `create_meeting` 엔드포인트 아래에 추가:

```python
@router.post("/capture", status_code=202)
async def capture_text_meeting(
    workspace_id: uuid.UUID,
    data: CaptureTextRequest,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member),
    service: MeetingService = Depends(get_meeting_service),
    pipeline: MeetingPipelineService = Depends(get_pipeline_service),
):
    """텍스트 캡처 — STT 없이 직접 AI 분석. 202 Accepted."""
    result = await service.create_meeting(
        workspace_id=workspace_id,
        title=data.title,
        file_key="",  # 텍스트 캡처는 파일 없음
        created_by_id=member.user_id,
        source="text",
    )
    meeting_id = uuid.UUID(result["id"])
    background_tasks.add_task(pipeline.capture_text, meeting_id, data.transcript_text)
    return result
```

- [ ] **Step 3: `MeetingService.create_meeting`에 `source` 파라미터 추가**

`backend/src/meetings/service.py`의 `create_meeting` 메서드 시그니처 수정:

기존:
```python
async def create_meeting(
    self,
    workspace_id: uuid.UUID,
    title: str,
    file_key: str,
    created_by_id: uuid.UUID,
    recorded_at=None,
) -> dict:
```

수정:
```python
async def create_meeting(
    self,
    workspace_id: uuid.UUID,
    title: str,
    file_key: str,
    created_by_id: uuid.UUID,
    recorded_at=None,
    source: str | None = None,
) -> dict:
```

그리고 `Meeting(...)` 생성 부분에 `source=source` 추가:
```python
meeting = Meeting(
    workspace_id=workspace_id,
    title=title,
    file_key=file_key,
    created_by_id=created_by_id,
    recorded_at=recorded_at,
    status="uploading",
    source=source,
)
```

- [ ] **Step 4: 서버 기동 확인**

```bash
cd /Users/woosung/project/agy-project/kairos/backend
uvicorn src.main:app --reload --port 8001 2>&1 | head -20
```

Expected: `Application startup complete.` (에러 없음)

- [ ] **Step 5: 커밋**

```bash
cd /Users/woosung/project/agy-project/kairos
git add backend/src/meetings/router.py backend/src/meetings/service.py
git commit -m "feat(meetings): POST /meetings/capture 엔드포인트 추가 (Quick Capture)"
```

---

## Task 4: FE — `captureText` API + `useCaptureText` 훅

**Files:**
- Modify: `frontend/src/features/meetings/api.ts`
- Modify: `frontend/src/features/meetings/hooks.ts`

- [ ] **Step 1: `captureText` API 함수 추가**

`frontend/src/features/meetings/api.ts` 하단에 추가:

```typescript
export interface CaptureTextRequest {
  title: string;
  transcriptText: string;
}

export async function captureText(
  token: string,
  wid: string,
  data: CaptureTextRequest
): Promise<{ id: string; status: string; message: string }> {
  return apiClient(`/workspaces/${wid}/meetings/capture`, {
    token,
    method: "POST",
    body: JSON.stringify(data),
  });
}
```

- [ ] **Step 2: `useCaptureText` 훅 추가**

`frontend/src/features/meetings/hooks.ts` 하단에 추가:

```typescript
export function useCaptureText(wid: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CaptureTextRequest) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return captureText(token, wid!, data);
    },
    onSuccess: () => {
      if (wid) {
        queryClient.invalidateQueries({ queryKey: meetingKeys.list(wid) });
      }
    },
  });
}
```

`captureText`와 `CaptureTextRequest`를 import에 추가:
```typescript
import {
  meetingKeys,
  fetchMeetings,
  fetchMeetingDetail,
  fetchMeetingStatus,
  createMeeting,
  captureText,
  type CaptureTextRequest,
} from "./api";
```

- [ ] **Step 3: TypeScript 컴파일 확인**

```bash
cd /Users/woosung/project/agy-project/kairos/frontend
pnpm tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 4: 커밋**

```bash
cd /Users/woosung/project/agy-project/kairos
git add frontend/src/features/meetings/api.ts frontend/src/features/meetings/hooks.ts
git commit -m "feat(meetings): captureText API + useCaptureText 훅 추가"
```

---

## Task 5: FE — `/new/page.tsx` 텍스트 탭 추가

**Files:**
- Modify: `frontend/src/app/(app)/new/page.tsx`

- [ ] **Step 1: import 추가**

`new/page.tsx` 상단에 추가:

```typescript
import { useCaptureText } from "@/features/meetings/hooks";
```

- [ ] **Step 2: 탭 상태 추가**

`NewContentPage` 함수 내부에서 기존 state 아래에 추가:

```typescript
const [meetingTab, setMeetingTab] = useState<"audio" | "text">("audio");
const [captureTitle, setCaptureTitle] = useState("");
const [captureText, setCaptureText] = useState("");
const [captureError, setCaptureError] = useState<string | null>(null);

const captureTextMutation = useCaptureText(activeWorkspaceId ?? undefined);
const isCapturing = captureTextMutation.isPending;
```

- [ ] **Step 3: 텍스트 캡처 핸들러 추가**

기존 `handleUpload` 아래에 추가:

```typescript
const handleCapture = async () => {
  if (!captureTitle || captureText.length < 50 || !activeWorkspaceId) return;
  setCaptureError(null);
  try {
    const result = await captureTextMutation.mutateAsync({
      title: captureTitle,
      transcriptText: captureText,
    });
    router.push(`/meetings/${result.id}`);
  } catch (err) {
    setCaptureError(err instanceof Error ? err.message : "캡처 실패");
  }
};
```

- [ ] **Step 4: meeting 카드 선택 시 탭 UI 추가**

기존 `{selected === "meeting" && (...)}` 블록의 `<h2>회의 녹음</h2>` 아래에 탭 버튼을 추가한다.

`<div className="space-y-4">` 바로 위에:

```typescript
{/* 탭 */}
<div className="flex gap-1 mb-4 border-b" style={{ borderColor: "var(--border-subtle)" }}>
  {(["audio", "text"] as const).map((tab) => (
    <button
      key={tab}
      onClick={() => setMeetingTab(tab)}
      className="px-4 py-2 text-sm font-medium transition-colors"
      style={{
        color: meetingTab === tab ? "var(--accent)" : "var(--text-muted)",
        borderBottom: meetingTab === tab ? "2px solid var(--accent)" : "2px solid transparent",
      }}
    >
      {tab === "audio" ? "🎙️ 오디오 업로드" : "📝 텍스트로 입력"}
    </button>
  ))}
</div>
```

- [ ] **Step 5: 탭별 폼 분기**

기존 오디오 업로드 폼 전체를 `{meetingTab === "audio" && (...)}` 로 감싸고,
텍스트 탭 폼을 추가한다.

```typescript
{meetingTab === "audio" && (
  <div className="space-y-4">
    {/* 기존 오디오 업로드 폼 전체 그대로 */}
  </div>
)}

{meetingTab === "text" && (
  <div className="space-y-4">
    {/* 제목 */}
    <div>
      <label className="block text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
        회의 제목
      </label>
      <input
        type="text"
        placeholder="회의 제목을 입력하세요"
        value={captureTitle}
        onChange={(e) => setCaptureTitle(e.target.value)}
        className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none"
        style={{
          borderColor: "var(--border)",
          color: "var(--text-primary)",
          borderRadius: "var(--radius-sm)",
        }}
      />
    </div>

    {/* 텍스트 입력 */}
    <div>
      <label className="block text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
        회의 내용 <span style={{ color: "var(--text-muted)" }}>(최소 50자)</span>
      </label>
      <textarea
        placeholder="회의록, 스크립트, 메모를 붙여넣으세요"
        value={captureText}
        onChange={(e) => setCaptureText(e.target.value)}
        rows={10}
        className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none resize-y"
        style={{
          borderColor: "var(--border)",
          color: "var(--text-primary)",
          borderRadius: "var(--radius-sm)",
        }}
      />
      <p className="text-xs mt-1" style={{ color: captureText.length < 50 ? "var(--error)" : "var(--text-muted)" }}>
        {captureText.length}자 {captureText.length < 50 ? `(${50 - captureText.length}자 더 필요)` : ""}
      </p>
    </div>

    {captureError && (
      <div
        className="px-3 py-2 rounded text-sm"
        style={{ background: "rgba(248,113,113,0.1)", color: "var(--error)", borderRadius: "var(--radius-sm)" }}
      >
        {captureError}
      </div>
    )}

    {isCapturing && (
      <div
        className="px-3 py-2 rounded text-sm"
        style={{ background: "var(--accent-subtle)", color: "var(--accent)", borderRadius: "var(--radius-sm)" }}
      >
        ⏳ AI가 처리 중입니다...
      </div>
    )}

    <div className="flex justify-end">
      <button
        onClick={handleCapture}
        disabled={!captureTitle || captureText.length < 50 || isCapturing || !activeWorkspaceId}
        className="px-6 py-2 rounded text-sm font-medium transition-opacity"
        style={{
          background: captureTitle && captureText.length >= 50 && !isCapturing ? "var(--accent)" : "var(--surface-active)",
          color: captureTitle && captureText.length >= 50 && !isCapturing ? "var(--background)" : "var(--text-muted)",
          borderRadius: "var(--radius-sm)",
          cursor: (!captureTitle || captureText.length < 50 || isCapturing) ? "not-allowed" : "pointer",
        }}
      >
        {isCapturing ? "처리 중..." : "AI 분석 시작"}
      </button>
    </div>
  </div>
)}
```

- [ ] **Step 6: TypeScript 컴파일 확인**

```bash
cd /Users/woosung/project/agy-project/kairos/frontend
pnpm tsc --noEmit 2>&1 | head -20
```

Expected: 에러 없음

- [ ] **Step 7: 커밋**

```bash
cd /Users/woosung/project/agy-project/kairos
git add frontend/src/app/\(app\)/new/page.tsx
git commit -m "feat(capture): /new 페이지 텍스트 캡처 탭 추가 (Quick Capture FE)"
```

---

## 검증 체크리스트

- [ ] `/new` 페이지 → "회의 녹음" 카드 선택 → 탭 두 개 표시
- [ ] "텍스트로 입력" 탭 → 50자 미만 입력 시 "X자 더 필요" 표시 + 버튼 비활성화
- [ ] 50자 이상 입력 + 제목 + 제출 → "AI가 처리 중입니다..." → 회의 상세 페이지로 이동
- [ ] Inbox 페이지에서 새 InboxItem 생성 확인
- [ ] 오디오 업로드 탭은 기존 동작 유지
- [ ] `GET /meetings?projectId=...` 응답에 텍스트 캡처 회의 포함
