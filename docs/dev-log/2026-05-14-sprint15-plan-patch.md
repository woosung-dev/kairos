<!-- Sprint 15 Plan FIX iter 1 — codex 적대적 검토 (Q4) 결과 반영 patch -->

# Sprint 15 Plan — FIX iter 1 Patch (2026-05-14)

> **출처**: codex 적대적 검토 (`docs/dev-log/2026-05-14-sprint15-codex-review.md`) 20 finding 중 13 must-fix inline patch.
> **base plan**: `docs/dev-log/sprint-15-plan.md` (Q3 writing-plans 산출).
> **이 doc**: Stage 4 R1~R8 implementation 시 base plan + 본 patch 함께 참조. patch 우선 적용.

---

## §1. Patch scope summary

| Patch ID | Codex finding | Task 영향 | Priority |
|----------|---------------|----------|----------|
| P-T1 | A12 fixtures + A2 ffmpeg + Dockerfile | 신규 Task T-1 (T0 다음, R1 이전) | must |
| P-T0 | A4 Gemini EOL ADR | T0 추가 commit | must |
| P-R1 | A3 BackgroundTask + A6 embedding + C2 memory_ai_calls + C4 latency metric 분리 | R1 architecture 재정의 | must |
| P-R2 | A8 user backfill + A9 race condition + C3 embedding cache + C7 memory_events table | R2 alembic 확장 | must |
| P-R3 | A7 pgvector typed bind + C3 cache 적용 | R3 repository fix | must |
| P-R4 | A1 MediaRecorder MIME negotiation | R4 hooks.ts patch | must |
| P-R5 | A11 ProjectMember invariant | R5 추가 코드 | must |
| P-NEW-CRON | A10 R2 30일 TTL Cloud Scheduler endpoint | 신규 Task R-CRON (R7 다음) | must |
| P-R7 | C7 memory_events DB-backed metrics | R7 service rewrite | must |
| P-R8 | B1+B2+B3 funnel + Day 1 gate + Minimum redef | R8 rewrite | must |
| P-DAY0 | C1 Whisper 비용 정정 + C5 Day 0 spike scope | Day 0 spike doc 별도 | must |
| P-R1.5 | A2 ffmpeg normalize_audio | R1 service 부수 | must |
| P-DEPS | Whisper 모델 재선택 + cost recalc | Dependencies 섹션 정정 | must |

R5/A1/A4/B4/B5/B7/C6 = R5~R7 시점에 분산 fix (별도 patch 불요, 본문에 inline noted).

---

## §2. P-T1 신규 Task: Fixtures + ffmpeg Dockerfile (T0 다음, R1 이전)

**Files:**
- Modify: `backend/tests/conftest.py` (auth_user / bearer_header / personal_ws / team_ws / seed_memory fixtures)
- Modify: `backend/Dockerfile` (`apt-get install -y ffmpeg`)
- Create: `backend/tests/fixtures/__init__.py`

- [ ] **Step 1: Conftest 확장 — Clerk JWT mock + workspace fixtures**

`backend/tests/conftest.py`에 추가:

```python
import pytest
from fastapi.testclient import TestClient
from src.auth.models import User
from src.workspaces.models import Workspace, WorkspaceMember
from src.memory.models import MemoryItem


@pytest.fixture
async def auth_user(integration_session) -> User:
    """Test user + bearer header helper."""
    user = User(clerk_id="test_clerk_user", display_name="테스터", email="test@kairos.test")
    integration_session.add(user)
    await integration_session.flush()
    user.bearer_header = {"Authorization": "Bearer test_jwt_mock"}
    return user


@pytest.fixture
async def personal_ws(integration_session, auth_user) -> Workspace:
    ws = Workspace(name="테스터의 개인 Kairos", owner_id=auth_user.id, type="personal")
    integration_session.add(ws)
    await integration_session.flush()
    integration_session.add(WorkspaceMember(workspace_id=ws.id, user_id=auth_user.id, role="owner"))
    await integration_session.flush()
    return ws


@pytest.fixture
async def team_ws(integration_session, auth_user) -> Workspace:
    ws = Workspace(name="테스트 팀", owner_id=auth_user.id, type="team")
    integration_session.add(ws)
    await integration_session.flush()
    integration_session.add(WorkspaceMember(workspace_id=ws.id, user_id=auth_user.id, role="owner"))
    await integration_session.flush()
    return ws


@pytest.fixture
def memory_client(test_app, monkeypatch, auth_user):
    """TestClient with Clerk JWT verification monkeypatched."""
    from src.auth import dependencies as auth_deps
    async def fake_verify(authorization: str = "") -> dict:
        return {"sub": auth_user.clerk_id, "name": auth_user.display_name, "email": auth_user.email}
    monkeypatch.setattr(auth_deps, "verify_clerk_token", fake_verify)
    return TestClient(test_app)


@pytest.fixture
async def seed_memory(integration_session, auth_user, personal_ws) -> MemoryItem:
    item = MemoryItem(
        user_id=auth_user.id, workspace_id=personal_ws.id,
        type="text", raw_content="Sprint 15 wedge 결정 Recall-first",
        distilled_json={"title": "Sprint 15 wedge", "atomic_notes": ["Recall-first wedge"], "suggested_visibility": "personal"},
        status="active",
    )
    integration_session.add(item)
    await integration_session.flush()
    return item


@pytest.fixture
async def seed_memories(integration_session, auth_user, personal_ws) -> list[MemoryItem]:
    items = []
    for i in range(5):
        m = MemoryItem(
            user_id=auth_user.id, workspace_id=personal_ws.id,
            type="text", raw_content=f"테스트 메모 {i}",
            distilled_json={"title": f"테스트 메모 {i}", "atomic_notes": [f"atomic notes content {i}"], "suggested_visibility": "personal"},
            status="active",
        )
        integration_session.add(m)
        items.append(m)
    await integration_session.flush()
    return items
```

- [ ] **Step 2: Dockerfile ffmpeg 설치**

`backend/Dockerfile` 적절한 base apt section에:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 3: Run conftest sanity check**

```bash
cd backend && pytest tests/conftest.py --collect-only -v
```

- [ ] **Step 4: Commit T-1**

```bash
git add backend/tests/conftest.py backend/Dockerfile backend/tests/fixtures/__init__.py
git commit -m "feat(test): T-1 fixtures + ffmpeg Dockerfile — codex A12+A2 fix"
```

---

## §3. P-T0 patch: T0 commit에 Gemini EOL ADR 추가

T0 commit (ADR-016 AD-41 reframe)에 추가 변경:

`docs/TODO.md` Sprint 17+ candidates 섹션에 신규 라인:

```markdown
- [ ] **P0 S17-T-GEMINI-EOL** — Gemini 2.5 Flash EOL 2026-06-17 대응 ADR + Gemini 2.5 Pro / Flash 2.0 마이그레이션 plan. Day 0 spike에 모델 호출 가능 기간 확인 포함.
```

T0 commit message에 EOL 위험 명시.

---

## §4. P-R1 patch: R1 architecture 재정의 (BackgroundTask + capture embedding + memory_ai_calls)

### R1 acceptance criteria 변경

기존 plan의 R1 latency 명시:
> R1: `POST /api/v1/memory` returns 202 + `{memory_id, distilled_json}` ≤2s p95.

**변경**:
> R1: `POST /api/v1/memory` returns 202 + `{memory_id, status: "processing"}` ≤500ms p95 (enqueue only).
> 후속 BackgroundTask: transcribe (Whisper) → distill (Gemini) → embed (OpenAI) → save EmbeddingChunk.
> FE는 `GET /api/v1/workspaces/{workspace_id}/memory/{memory_id}` polling으로 distilled_json + embedding_chunk_id 확인.

### R1 service architecture (BackgroundTask 분리)

`backend/src/memory/service.py` `capture_text` / `capture_voice` 메소드 재구조:

```python
async def capture_text(
    self,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    text: str,
    background_tasks: BackgroundTasks,
) -> MemoryCreateOut:
    """즉시 enqueue + 202 반환. distill/embed는 background에서."""
    item = MemoryItem(
        user_id=user_id, workspace_id=workspace_id,
        type="text", raw_content=text,
        status="processing",
    )
    await self.repo.save(item)
    await self.repo.commit()
    # background: distill → embed
    background_tasks.add_task(
        self._distill_and_embed,
        memory_id=item.id, workspace_id=workspace_id, raw_text=text,
    )
    return MemoryCreateOut(memory_id=item.id, distilled_json=None, status="processing", created_at=item.created_at)


async def _distill_and_embed(self, memory_id: uuid.UUID, workspace_id: uuid.UUID, raw_text: str) -> None:
    """Background — distill + embed. AsyncSession 별도 — session_factory 패턴 재사용 (sprint 9 lesson)."""
    from src.common.database import async_session_factory
    async with async_session_factory() as session:
        repo = MemoryRepository(session)
        # 1. Distill
        try:
            distilled = await self._distill_with_gemini(raw_text)
            distilled_json = distilled.model_dump()
        except GeminiDistillError:
            distilled_json = self._fallback_distill(raw_text).model_dump()
        # 2. AI call tracking (C2 finding)
        await self._record_ai_call(session, memory_id, workspace_id, "distill", elapsed_ms=..., usage_metadata=...)
        # 3. Update memory_item
        await session.execute(
            update(MemoryItem)
            .where(MemoryItem.id == memory_id)
            .values(distilled_json=distilled_json, status="embedding_pending")
        )
        await session.commit()
        # 4. Embed (capture에서 항상 — A6 fix)
        try:
            embedding = await self._embed_with_openai(distilled["title"] + " " + " ".join(distilled["atomic_notes"]))
            chunk = await self._create_embedding_chunk(
                session, memory_id, workspace_id,
                content=" ".join(distilled["atomic_notes"]),
                embedding=embedding,
            )
            await session.execute(
                update(MemoryItem)
                .where(MemoryItem.id == memory_id)
                .values(embedding_chunk_id=chunk.id, status="active")
            )
            await session.commit()
        except Exception as e:
            await session.execute(
                update(MemoryItem)
                .where(MemoryItem.id == memory_id)
                .values(status="embedding_failed")
            )
            await session.commit()


async def capture_voice(
    self, user_id, workspace_id, audio_bytes: bytes, filename: str,
    background_tasks: BackgroundTasks,
) -> MemoryCreateOut:
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise AudioTooLargeError()
    # 1. normalize audio (A2 fix — ffmpeg)
    wav_bytes = await self._normalize_audio(audio_bytes, filename)
    # 2. R2 upload immediately
    r2_key = f"memory/{workspace_id}/{uuid.uuid4()}-{filename}"
    await self._upload_to_r2(wav_bytes, r2_key)
    # 3. save with status='transcription_pending'
    item = MemoryItem(
        user_id=user_id, workspace_id=workspace_id,
        type="voice", raw_content="",
        r2_audio_key=r2_key,
        status="transcription_pending",
    )
    await self.repo.save(item)
    await self.repo.commit()
    background_tasks.add_task(
        self._transcribe_distill_embed,
        memory_id=item.id, workspace_id=workspace_id, r2_key=r2_key,
    )
    return MemoryCreateOut(memory_id=item.id, distilled_json=None, status="transcription_pending", created_at=item.created_at)


async def _normalize_audio(self, audio_bytes: bytes, filename: str) -> bytes:
    """A2 fix — ffmpeg webm/mp4/aac → wav 16kHz mono."""
    import asyncio, subprocess, tempfile, os
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as f_in:
        f_in.write(audio_bytes)
        in_path = f_in.name
    out_path = in_path + ".wav"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", in_path, "-ar", "16000", "-ac", "1", "-f", "wav", out_path,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    await proc.wait()
    with open(out_path, "rb") as f_out:
        wav_bytes = f_out.read()
    os.unlink(in_path)
    os.unlink(out_path)
    return wav_bytes


async def _record_ai_call(self, session, memory_id, workspace_id, call_type, elapsed_ms, usage_metadata):
    """C2 fix — memory_ai_calls 테이블에 cost/latency 기록."""
    from src.memory.models import MemoryAICall
    record = MemoryAICall(
        memory_id=memory_id, workspace_id=workspace_id,
        call_type=call_type,  # 'transcription' | 'distill' | 'embedding'
        elapsed_ms=elapsed_ms,
        input_tokens=usage_metadata.get("input_tokens", 0),
        output_tokens=usage_metadata.get("output_tokens", 0),
    )
    session.add(record)
```

### Router 수정

`router.py` POST endpoint signature 변경:

```python
@router.post("", response_model=MemoryCreateOut, status_code=202)
async def capture_memory(
    workspace_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    text: str | None = Form(default=None),
    audio: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryCreateOut:
    ...
```

### Status polling endpoint 신설

```python
@router.get("/{memory_id}", response_model=MemoryCreateOut)
async def get_memory_status(
    workspace_id: uuid.UUID, memory_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryCreateOut:
    """FE polling endpoint — status / distilled_json 확인."""
    return await service.get_memory(memory_id, workspace_id)
```

### Test 변경

`test_api.py::test_post_memory_text_returns_distilled_json` 변경:

```python
def test_post_memory_text_returns_202_processing(memory_client, auth_user, personal_ws):
    response = memory_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/memory",
        data={"text": "Sprint 15 wedge"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "processing"
    assert body["distilled_json"] is None


def test_get_memory_polling_returns_distilled_after_bg(memory_client, auth_user, personal_ws):
    """Background 완료 후 status='active' + distilled_json 확인."""
    post = memory_client.post(...)
    memory_id = post.json()["memory_id"]
    # poll loop with timeout
    for _ in range(30):
        time.sleep(0.5)
        get = memory_client.get(f"/api/v1/workspaces/{personal_ws.id}/memory/{memory_id}")
        if get.json()["status"] == "active":
            break
    assert get.json()["status"] == "active"
    assert get.json()["distilled_json"]["title"] is not None
```

---

## §5. P-R2 patch: alembic 확장 (backfill + memory_ai_calls + memory_query_embedding_cache + memory_events)

R2 alembic migration에 추가:

```python
def upgrade() -> None:
    # ... 기존 workspaces.type + memory_items + promotion_audit (Q3 plan 본문)

    # A8 fix — 기존 user 모두에게 personal workspace backfill
    op.execute(
        """
        INSERT INTO workspaces (id, owner_id, name, type, created_at)
        SELECT gen_random_uuid(), u.id, COALESCE(u.display_name, '사용자') || '의 개인 Kairos', 'personal', now()
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM workspaces w WHERE w.owner_id = u.id AND w.type = 'personal'
        );
        """
    )
    op.execute(
        """
        INSERT INTO workspace_members (id, workspace_id, user_id, role, created_at)
        SELECT gen_random_uuid(), w.id, w.owner_id, 'owner', now()
        FROM workspaces w
        WHERE w.type = 'personal'
        AND NOT EXISTS (
            SELECT 1 FROM workspace_members m WHERE m.workspace_id = w.id AND m.user_id = w.owner_id
        );
        """
    )

    # C2 fix — memory_ai_calls 신설
    op.create_table(
        "memory_ai_calls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("memory_id", UUID(as_uuid=True), sa.ForeignKey("memory_items.id"), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("call_type", sa.String(), nullable=False),  # transcription | distill | embedding
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("elapsed_ms", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), default=0),
        sa.Column("output_tokens", sa.Integer(), default=0),
        sa.Column("status", sa.String(), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_memory_ai_calls_workspace_created", "memory_ai_calls", ["workspace_id", "created_at"])

    # C3 fix — query embedding cache
    op.create_table(
        "memory_query_embedding_cache",
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("normalized_query", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float), nullable=False),  # OR pgvector type
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("workspace_id", "normalized_query"),
    )

    # C7 fix — memory_events (DB-backed metrics for Cloud Run)
    op.create_table(
        "memory_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),  # capture | recall | promote
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),  # { match_type, query_len, ... }
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_memory_events_workspace_type_created", "memory_events", ["workspace_id", "event_type", "created_at"])
```

`MemoryItem.models.py`에 추가 model:

```python
class MemoryAICall(SQLModel, table=True):
    __tablename__ = "memory_ai_calls"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    memory_id: uuid.UUID = Field(foreign_key="memory_items.id", nullable=False)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", nullable=False)
    call_type: str = Field(nullable=False)
    model_name: str | None = None
    elapsed_ms: int = Field(nullable=False)
    input_tokens: int = 0
    output_tokens: int = 0
    status: str = Field(default="success")
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemoryEvent(SQLModel, table=True):
    __tablename__ = "memory_events"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", nullable=False)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    event_type: str = Field(nullable=False)
    latency_ms: int | None = None
    metadata: dict | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## §6. P-R3 patch: pgvector typed bind + I-9 patch + embedding cache

### A7 fix — pgvector Vector type

`backend/src/memory/repository.py` `_vector_search` 또는 `recall` SQL 변경:

```python
from pgvector.sqlalchemy import Vector
from sqlalchemy import bindparam

async def vector_search(self, workspace_id: uuid.UUID, query_embedding: list[float], top_k: int):
    stmt = (
        text("""
            SELECT mi.id, mi.distilled_json, mi.raw_content, mi.created_at,
                   1 - (ec.embedding <=> :qvec) AS score
            FROM embedding_chunks ec
            JOIN memory_items mi ON ec.source_id = mi.id
            WHERE ec.workspace_id = :wid AND ec.source_type = 'memory'
              AND mi.deleted_at IS NULL
            ORDER BY ec.embedding <=> :qvec
            LIMIT :limit
        """)
        .bindparams(bindparam("qvec", type_=Vector(1536)))
    )
    result = await self.session.execute(
        stmt, {"qvec": query_embedding, "wid": workspace_id, "limit": top_k},
    )
    return result.all()
```

### C3 fix — query embedding cache

```python
class MemoryService:
    async def _get_query_embedding(self, workspace_id, query: str) -> list[float]:
        normalized = " ".join(query.lower().split())
        # cache lookup
        cached = await self.repo.get_query_embedding_cache(workspace_id, normalized)
        if cached:
            return cached
        # 미스 — embed + cache
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.settings.openai_api_key.get_secret_value())
        resp = await client.embeddings.create(model="text-embedding-3-small", input=query)
        emb = resp.data[0].embedding
        await self.repo.save_query_embedding_cache(workspace_id, normalized, emb)
        return emb
```

`memory_query_embedding_cache` TTL = 7일 (별도 cron 또는 lazy delete). Sprint 17+ cache invalidation 정책 별도.

---

## §7. P-R4 patch: MediaRecorder MIME negotiation (A1)

`frontend/src/features/memory/hooks.ts` `useRecorder` 함수 변경:

```ts
const MIME_PRIORITY = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/aac",
];

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  for (const m of MIME_PRIORITY) {
    if (MediaRecorder.isTypeSupported(m)) return m;
  }
  return undefined;  // no options — browser default
}

export function useRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [unsupported, setUnsupported] = useState(false);
  // ...

  async function start(onStop: (blob: Blob, mimeType: string) => void) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = pickMimeType();
      const mr = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      const actualMime = mr.mimeType;  // 실제 사용된 MIME
      // ... ondataavailable, onstop with actualMime
      mr.onstop = () => {
        const blob = new Blob(chunks.current, { type: actualMime });
        onStop(blob, actualMime);
      };
      mr.start();
      setIsRecording(true);
    } catch {
      setPermissionDenied(true);
    }
  }
  // ...
}
```

`capture-sheet.tsx`에서 `useCaptureVoice`로 보낼 때 mime 정보 함께:

```tsx
const captureVoice = useCaptureVoice(workspaceId);
function handleStart() {
  start((blob, mime) => {
    // mime 정보로 file extension 결정
    const ext = mime.includes("mp4") ? "mp4" : mime.includes("webm") ? "webm" : "audio";
    captureVoice.mutate({ blob, filename: `voice.${ext}` }, { onSuccess: onClose });
  });
}
```

`api.ts` captureVoice signature 변경:

```ts
export async function captureVoice(workspaceId: string, { blob, filename }: { blob: Blob; filename: string }) {
  const fd = new FormData();
  fd.append("audio", blob, filename);
  return apiFetch(`/api/v1/workspaces/${workspaceId}/memory`, { method: "POST", body: fd });
}
```

---

## §8. P-R5 patch: ProjectMember invariant (A11)

`backend/src/projects/service.py` `add_member` / project membership 변경:

```python
async def add_member(self, project_id, user_id, role):
    project = await self.repo.get_by_id(project_id)
    ws = await self.ws_repo.get_by_id(project.workspace_id)
    if ws.type == "personal":
        raise PersonalWorkspaceProtected("add project member to personal workspace")
    # ... 기존 로직
```

테스트: `backend/tests/projects/test_personal_project_invariants.py`

```python
@pytest.mark.asyncio
async def test_add_project_member_to_personal_ws_blocked(integration_session, auth_user, personal_ws):
    from src.projects.service import ProjectService
    from src.projects.models import Project
    from src.workspaces.exceptions import PersonalWorkspaceProtected

    # Personal workspace 내 project 생성
    p = Project(name="개인 프로젝트", workspace_id=personal_ws.id, owner_id=auth_user.id)
    integration_session.add(p)
    await integration_session.flush()
    # 다른 user 멤버 추가 시도 → 403
    other = User(clerk_id="o2", display_name="x", email="x@test")
    integration_session.add(other)
    await integration_session.flush()
    service = ProjectService(...)
    with pytest.raises(PersonalWorkspaceProtected):
        await service.add_member(p.id, other.id, role="member")
```

R5 commit에 추가.

### A9 fix — race condition

`backend/src/auth/dependencies.py`의 `get_current_user`:

```python
# Personal workspace seed — ON CONFLICT DO NOTHING 패턴 사용
from sqlalchemy import text

if result.scalar_one_or_none() is None:
    new_ws_id = uuid.uuid4()
    await session.execute(
        text("""
            INSERT INTO workspaces (id, owner_id, name, type, created_at)
            VALUES (:id, :owner_id, :name, 'personal', now())
            ON CONFLICT ON CONSTRAINT uq_workspaces_owner_personal DO NOTHING;
        """),
        {"id": new_ws_id, "owner_id": str(user.id), "name": f"{user.display_name}의 개인 Kairos"},
    )
    # 실제 ID fetch — INSERT가 conflict로 무시되었을 수 있음
    actual_ws = await session.execute(
        select(Workspace).where(Workspace.owner_id == user.id, Workspace.type == "personal")
    )
    ws = actual_ws.scalar_one()
    # WorkspaceMember도 ON CONFLICT
    await session.execute(
        text("""
            INSERT INTO workspace_members (id, workspace_id, user_id, role, created_at)
            VALUES (gen_random_uuid(), :wid, :uid, 'owner', now())
            ON CONFLICT (workspace_id, user_id) DO NOTHING;
        """),
        {"wid": str(ws.id), "uid": str(user.id)},
    )
await session.commit()
return user
```

---

## §9. P-NEW-CRON 신규 Task: R2 30일 TTL cleanup endpoint (A10)

R7 commit 다음에 추가 Task **R-CRON**:

**Files:**
- Create: `backend/src/memory/admin_router.py` (founder-only cleanup endpoint)
- Modify: `backend/src/main.py` (admin_router include)
- Create: GCP Cloud Scheduler config (manual setup or `terraform/scheduler.tf`)

```python
# backend/src/memory/admin_router.py
from fastapi import APIRouter, Depends, Header, HTTPException
from src.core.config import get_settings
from src.memory.dependencies import get_memory_service

admin_router = APIRouter(prefix="/api/v1/admin/memory", tags=["memory-admin"])


async def verify_cron_token(x_cron_token: str = Header(...)):
    settings = get_settings()
    if x_cron_token != settings.cron_secret_token.get_secret_value():
        raise HTTPException(status_code=403, detail="invalid cron token")


@admin_router.post("/r2-cleanup", dependencies=[Depends(verify_cron_token)])
async def r2_cleanup(service = Depends(get_memory_service)):
    """R2 30일 TTL cleanup — Cloud Scheduler에서 daily invoke."""
    deleted = await service.cleanup_expired_r2_audio(days=30)
    return {"deleted_count": deleted}
```

Service method:

```python
async def cleanup_expired_r2_audio(self, days: int = 30) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    expired = await self.repo.list_expired_audio(cutoff)
    deleted = 0
    for item in expired:
        if item.r2_audio_key:
            await self._delete_from_r2(item.r2_audio_key)
            await self.repo.clear_r2_audio_key(item.id)
            deleted += 1
    await self.repo.commit()
    return deleted
```

GCP Cloud Scheduler 설정 (manual, Day 1 post-deploy):
```
gcloud scheduler jobs create http memory-r2-cleanup \
  --schedule="0 3 * * *" \  # 매일 03:00 KST
  --uri="https://<cloud-run-url>/api/v1/admin/memory/r2-cleanup" \
  --http-method=POST \
  --headers="X-Cron-Token=<secret>"
```

---

## §10. P-R7 patch: DB-backed metrics (C7)

`backend/src/memory/service.py` `get_metrics`:

```python
async def get_metrics(self, workspace_id: uuid.UUID) -> MemoryMetricsOut:
    from src.memory.models import MemoryEvent
    from sqlalchemy import func
    # capture / recall / promote count
    counts_q = select(MemoryEvent.event_type, func.count(MemoryEvent.id)).where(
        MemoryEvent.workspace_id == workspace_id
    ).group_by(MemoryEvent.event_type)
    counts = {r[0]: r[1] for r in (await self.repo.session.execute(counts_q)).all()}
    # recall latency percentile from memory_events
    p50_q = select(
        func.percentile_cont(0.5).within_group(MemoryEvent.latency_ms)
    ).where(MemoryEvent.workspace_id == workspace_id, MemoryEvent.event_type == "recall")
    p95_q = select(
        func.percentile_cont(0.95).within_group(MemoryEvent.latency_ms)
    ).where(MemoryEvent.workspace_id == workspace_id, MemoryEvent.event_type == "recall")
    p50 = (await self.repo.session.execute(p50_q)).scalar()
    p95 = (await self.repo.session.execute(p95_q)).scalar()
    return MemoryMetricsOut(
        capture_count=counts.get("capture", 0),
        recall_count=counts.get("recall", 0),
        promote_count=counts.get("promote", 0),
        recall_p50_ms=int(p50) if p50 else None,
        recall_p95_ms=int(p95) if p95 else None,
    )
```

각 capture/recall/promote service method 끝에 MemoryEvent insert:

```python
async def recall(self, workspace_id, query, top_k=3):
    start = time.time()
    result = await self._recall_impl(workspace_id, query, top_k)
    elapsed_ms = int((time.time() - start) * 1000)
    # 이벤트 기록
    await self.repo.save_event(workspace_id, user_id=..., event_type="recall", latency_ms=elapsed_ms, metadata={
        "query_len": len(query), "fallback_used": result.fallback_used, "source_count": len(result.sources),
    })
    return result
```

`_RECALL_LATENCIES_MS` deque + `_RECALL_COUNTER` 모듈-level state는 모두 제거.

---

## §11. P-R8 rewrite: outreach funnel (B1+B2+B3+B6+B7)

R8 task spec 완전 재작성:

### R8 acceptance (revised)

| Metric | Best | Medium | Minimum |
|--------|------|--------|---------|
| Outreach sent (Day 0) | 80 | 50 | 30 |
| Demos booked (Day 1~3) | 8+ | 5+ | 3+ |
| Demos completed (Day 3~6) | 5+ | 3+ | 2+ |
| Day-2 activation (capture ≥3 + recall ≥1) | 5/5 | 3/5 | 2/3 |
| Day-7 retained (active capture ≥1/day) | 3+ | 2+ | 1+ |
| Behavioral signal | "$10 결제 의향" yes 1+ | yes 1+ | "다음 주 5개 capture 약속" yes 1+ |

### Day-by-day gates (revised)

- **Day 0**: cold 50건 발송 (warm_intro 10 / indie_kr 20 / x_dm_kr 20)
- **Day 1**: bookings <3 → 즉시 cold expansion (LinkedIn warm intro / paid research panel $20/명)
- **Day 3**: completed demos <2 → Sprint freeze + outreach-only sprint pivot (Sprint 16 redefine)
- **Day 6**: Day-2 activation <2/3 → wedge re-evaluation
- **Day 14**: retrospective + Sprint 16 결정

### Interview questions (B7 fix — behavioral, not unprompted feeling)

각 PERSONA 인터뷰에서 행동 질문 강제:

1. "지난 7일 중 Kairos가 없었으면 어느 메모를 어디서 찾았을지 구체적 예시 1개?" — 행동 기반 demand 증거
2. "지금 이 기능 계속 쓰기 위해 월 $10 결제할 의향? Yes/No" — 결제 의향 binary
3. "다음 주에도 5개 이상 capture할 약속 가능?" — 미래 행동 약속
4. "Notion / Apple Notes 대비 가장 짜증났던 1가지?" — 비교 경쟁 친화도

**unprompted "이거 없으면 불편"** signal은 보너스, primary metric 아님.

### Replacement pool (B6 dropout 대응)

3 채널에 동시 발송한 80+ pool에서 dropout 발생 시 즉시 다음 응답자에 replacement booking. ongoing pool 5명 유지.

### Outreach message (B4)

problem-first opening (codex 추천 template):

```
혹시 창업 아이디어/결정 메모를 Notion, Apple Notes, DM에 흩어놓고 나중에 못 찾는 편인가요?
7일짜리 작은 prototype을 테스트 중입니다. 30분만 화면공유로 써보고, 마음에 안 들면 바로 끊어도 됩니다.
조건: 최근 7일 안에 실제로 다시 찾고 싶었던 메모/생각이 있어야 합니다.
```

### Sprint 16 정책 (B3 fix — Minimum redefine)

- **Best/Medium**: Sprint 16 v1.6 Promotion API 정식 build 진입 OK.
- **Minimum (founder + 1)**: Sprint 16 = "Build freeze + outreach sprint". Recall feature 동결 + 14일 추가 outreach + 10명 인터뷰 시도. founder dogfooding 결과는 product validation으로 인정 X — operational fallback log only.

---

## §12. P-DAY0 신규 Task: Day 0 spike (C1+C5)

**Files:**
- Create: `docs/dev-log/sprint-15-cost-spike.md` (Day 0 측정 결과 log)
- Create: `backend/scripts/sprint15_day0_spike.py` (10-sample 실측 스크립트)

`backend/scripts/sprint15_day0_spike.py`:

```python
"""Sprint 15 Day 0 spike — 10 sample 실측. Whisper + Gemini + OpenAI embedding cost / latency / failure rate."""
import asyncio, time, json, statistics
# samples: Chrome webm 10s / 60s / 5min, Safari mp4 10s / 60s, Korean filler 60s, silent 10s, text 500/3000/10000자
SAMPLES = [
    {"name": "chrome_webm_10s", "type": "audio", "path": "samples/chrome_10s.webm"},
    {"name": "chrome_webm_60s", "type": "audio", "path": "samples/chrome_60s.webm"},
    {"name": "chrome_webm_5min", "type": "audio", "path": "samples/chrome_5min.webm"},
    {"name": "ios_mp4_10s", "type": "audio", "path": "samples/ios_10s.mp4"},
    {"name": "ios_mp4_60s", "type": "audio", "path": "samples/ios_60s.mp4"},
    {"name": "ko_filler_60s", "type": "audio", "path": "samples/ko_filler_60s.webm"},
    {"name": "silent_10s", "type": "audio", "path": "samples/silent_10s.webm"},
    {"name": "text_500", "type": "text", "content": "한국어 텍스트 " * 50},
    {"name": "text_3000", "type": "text", "content": "한국어 텍스트 " * 300},
    {"name": "text_10000", "type": "text", "content": "한국어 텍스트 " * 1000},
]

async def main():
    results = []
    for sample in SAMPLES:
        # transcription + distill + embedding 각 단계 측정
        ...
        results.append({
            "sample": sample["name"],
            "transcription_ms": ..., "transcription_cost_usd": ...,
            "distill_ms": ..., "distill_input_tokens": ..., "distill_output_tokens": ...,
            "embedding_ms": ..., "embedding_cost_usd": ...,
            "total_ms": ..., "failure_step": None,
        })
    # 통계
    print(json.dumps(results, indent=2))
    # invalidate thresholds
    failures = sum(1 for r in results if r["failure_step"])
    e2e_p95 = statistics.quantiles([r["total_ms"] for r in results], n=20)[18]
    total_cost = sum(r["transcription_cost_usd"] + r["embedding_cost_usd"] for r in results)
    print(f"failures={failures}/{len(SAMPLES)}, e2e_p95={e2e_p95}ms, cost={total_cost}")
    # thresholds
    assert failures <= len(SAMPLES) * 0.05, "transcription failure > 5%"
    assert e2e_p95 <= 60000, "end-to-end job p95 > 60s"
```

### Day 0 invalidate thresholds (codex 정합)

| Metric | Threshold | 위반 시 action |
|--------|-----------|---------------|
| Transcription failure | > 5% | sample diversity 확장 + Whisper 모델 재선택 |
| End-to-end job p95 | > 60s | R1 BackgroundTask 확정 + R7 polling 최적화 |
| Gemini JSON invalid | > 10% | distill prompt revise + parse fallback 강화 |
| Cost per tester per week | > $2 | Whisper 모델 → `gpt-4o-mini-transcribe` 전환 |
| Recall p95 at 100 chunks | > 2s | embedding cache 활성 (C3 fix) |

### Whisper 모델 결정

Codex C1 finding 대응:
- **default**: `gpt-4o-mini-transcribe` (cheaper) — $0.003/min × 5min × 50 = $0.75
- 정확도 부족 발견 시 `gpt-4o-transcribe` 또는 `whisper-1` fallback
- Day 0 spike에서 확정

---

## §13. P-DEPS patch: Dependencies 섹션 정정

Q3 plan §3 Dependencies 표 정정:

| 항목 | 정정된 추정 |
|------|------------|
| Transcription quota | `gpt-4o-mini-transcribe` $0.003/min × 5min × 50 = **$0.75** (이전 $15 X) |
| Gemini distill | usage_metadata 측정 필수, ignored X |
| OpenAI embedding | query cache hit ratio 측정, latency 분리 |
| Gemini 2.5 Flash EOL | 2026-06-17 — 단기 OK, Sprint 16 ADR |
| ffmpeg | Dockerfile install — T-1에 추가됨 |
| GCP Cloud Scheduler | R2 cleanup endpoint — Day 1 setup |

---

## §14. Stage 4 진입 변경된 first failing test

기존 plan §5.1:
```bash
cd backend && pytest tests/test_alembic_memory.py::test_memory_items_table_exists -v
```

**변경**: Stage 4 진입 first task = **T-1 fixtures + ffmpeg Dockerfile**. first failing test:

```bash
cd backend && pytest tests/memory/test_api.py::test_post_memory_text_returns_202_processing -v
# Expected: FAIL — fixtures (auth_user/memory_client/personal_ws) 미존재
```

→ T-1 fixtures 우선 → R2 alembic → R1 BackgroundTask architecture → R3 vector + I-9 → R4 FE + MIME negotiation → R5 personal seed + race + ProjectMember + R-CRON → R6 promote → R7 DB metrics → R8 outreach (Day 0 parallel).

---

## §15. Final must-fix vs defer 분류

### Must-fix (R1 진입 전 plan patch 적용 — 본 doc)

| Finding | Patch | Task 영향 |
|---------|-------|----------|
| A2 ffmpeg | §2 | T-1 (T0 다음) |
| A3 BackgroundTask | §4 | R1 architecture |
| A4 Gemini EOL ADR | §3 | T0 추가 commit |
| A6 capture embedding | §4 | R1 _distill_and_embed |
| A8 user backfill | §5 | R2 alembic |
| A9 race condition | §8 | R5 ON CONFLICT |
| A10 R2 cron | §9 | R-CRON 신규 |
| A11 ProjectMember | §8 | R5 추가 |
| A12 fixtures | §2 | T-1 |
| C1 Whisper 비용 | §12 | Day 0 spike |
| C2 memory_ai_calls | §4 + §5 | R1+R2 |
| C3 embedding cache | §5 + §6 | R2+R3 |
| C4 latency metric | §4 | R1 |
| C5 Day 0 spike | §12 | Day 0 task |
| C7 memory_events | §5 + §10 | R2 + R7 |

### Defer (R5~R7 inline, 본문 plan 그대로)

| Finding | 처리 |
|---------|------|
| A1 MediaRecorder MIME | R4 hooks.ts에 inline 추가 (P-R4 §7) |
| A5 EmbeddingChunk signature | R3 진입 직전 caller grep 후 결정 |
| A7 pgvector typed bind | R3 repository에 inline (P-R3 §6) |
| B1+B2+B3+B6+B7 outreach | R8 rewrite (§11) |

---

## §16. Self-review

- [x] Codex 20 finding 모두 매핑 — 15 must-fix (본 patch) + 5 R3~R8 inline.
- [x] Task 순서 변경 — T0 → T-1 → R2 → R1 → R3 → R4 → R5 → R6 → R-CRON → R7 → R8.
- [x] R1 acceptance criteria 변경 — 202 + processing status 즉시, distill/embed background.
- [x] Day 0 task 신설 — cost/latency 실측 + 모델 결정.
- [x] R8 funnel 80→8→5→3 — 응답률 현실 반영.
- [x] DB-backed metrics — Cloud Run stateless 정합.

**STATUS**: FIX iter 1 patch complete. Stage 4 R1~R8 진입 준비. base plan + patch doc 함께 참조 → R1 진입 = T-1 fixtures + ffmpeg first.
