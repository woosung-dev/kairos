# Sprint 8 — 프로젝트 대시보드 완성 + Quick Capture 설계

## Context

Sprint 7까지 BE RBAC·멤버십·FE RBAC가 완성됐다. 프로덕션이 라이브 상태이나
두 가지 핵심 UX 구멍이 남아 있다.

1. **프로젝트 대시보드가 빈 화면** — stat 카드 전부 0, 탭 콘텐츠 EmptyState 고정.
   실제 사용자가 프로젝트에 들어가도 연결된 회의·노트·액션이 보이지 않는다.
2. **신규 사용자 이탈** — 오디오 파일 없이는 Kairos의 AI 가치를 체험할 방법이 없다.
   텍스트로 바로 캡처하는 경로가 없어 첫 인상에서 막힌다.

Sprint 8은 이 두 구멍을 동시에 메운다.

---

## Feature A: 프로젝트 대시보드 데이터 연결 (BE-T14 + AD-46)

### 목표
`ProjectDashboard`를 정식 라우트로 전환하고 실제 데이터를 연결한다.

### BE-T14 — 프로젝트 콘텐츠 조회 API 3개

```
GET /workspaces/{wid}/projects/{pid}/meetings
  응답: MeetingProjectLink 경유, 완료된 Meeting 목록 (id/title/status/createdAt)
  권한: viewer 이상

GET /workspaces/{wid}/projects/{pid}/notes
  응답: Note.project_id 기준 목록 (id/title/createdAt)
  권한: viewer 이상

GET /workspaces/{wid}/projects/{pid}/action-items
  응답: ActionItem.project_id 기준 목록 (id/content/status/createdAt)
  권한: viewer 이상
```

세 엔드포인트 모두 `workspace_id` 격리 적용 (I-9).

### AD-46 — FE ProjectDashboard 전환

1. **라우팅 변경** — `app/workspace/[wid]/projects/[pid]/page.tsx`가 `ProjectDashboard`를 렌더링하도록 교체
2. **훅 추가** — `useProjectMeetings`, `useProjectNotes`, `useProjectActionItems` (React Query)
3. **stat 카드** — 각 목록의 `.length`로 실제 숫자 표시
4. **탭 콘텐츠** — 회의/노트/액션 탭에 카드 리스트 연결 (로딩·에러 상태 포함)
5. **ProjectDetail 라우팅 제거** — 코드는 파일로 유지, import·라우트에서만 제거

---

## Feature B: Quick Capture (텍스트 → Inbox)

### 목표
오디오 없이 텍스트를 붙여넣으면 AI가 분석하여 Inbox에 적재한다.
영구 기능으로, 새 미팅 페이지에 탭으로 통합된다.

### BE — `POST /workspaces/{wid}/meetings/capture`

```python
# Request Body
class CaptureRequest(BaseModel):
    title: str
    transcript_text: str  # min 50자

# 처리 흐름
Meeting(source="text", status="analyzing") 생성
→ BackgroundTask: analyze_meeting(transcript_text) 재활용
→ status="completed" + InboxItem 생성 + 임베딩
```

STT 단계만 건너뛰고 기존 `analyze_meeting` 서비스 로직을 그대로 재활용.
`Meeting.source` 컬럼 추가 (nullable, default NULL = 오디오).

### FE — 새 미팅 페이지 탭 추가

**위치:** `/workspace/{wid}/meetings/new` (기존 업로드 페이지)

```
[ 🎙️ 오디오 업로드 ]  [ 📝 텍스트로 입력 ]
```

**텍스트 탭 필드:**
- `title` — 필수, 최소 1자
- `transcript_text` — 필수, 최소 50자, textarea (placeholder: "회의록이나 스크립트를 붙여넣으세요")
- 제출 버튼 → "AI가 처리 중입니다..." 상태 → Inbox 페이지로 이동

**훅:** `useCaptureText(workspaceId)` — `POST /capture` 호출

---

## 기술 품질 — E2E 시나리오 2개

```
시나리오 1 (Quick Capture):
  1. 새 미팅 페이지 → "텍스트로 입력" 탭 클릭
  2. 제목 + 텍스트(50자 이상) 입력 → 제출
  3. Inbox 페이지에서 InboxItem 생성 확인

시나리오 2 (프로젝트 대시보드):
  1. 특정 프로젝트에 미팅 연결
  2. 프로젝트 대시보드 진입
  3. 회의 stat 카드 숫자 ≥ 1 확인, 탭에 카드 노출 확인
```

---

## 파일 구조 요약

### 신규
- `backend/src/meetings/router.py` — `/capture` 엔드포인트 추가
- `frontend/src/features/projects/hooks.ts` — `useProjectMeetings`, `useProjectNotes`, `useProjectActionItems` 추가
- `frontend/src/features/meetings/api.ts` — `captureText` API 함수 추가
- `frontend/src/features/meetings/hooks.ts` — `useCaptureText` 훅 추가

### 수정
- `backend/src/meetings/models.py` — `Meeting.source` 컬럼 추가
- `backend/alembic/versions/` — 마이그레이션 추가
- `frontend/src/features/projects/components/project-dashboard.tsx` — 실제 데이터 연결
- `frontend/src/app/workspace/[wid]/projects/[pid]/page.tsx` — ProjectDashboard로 전환
- `frontend/src/app/workspace/[wid]/meetings/new/page.tsx` — 탭 UI 추가

---

## 검증 체크리스트

- [ ] `GET /projects/{pid}/meetings|notes|action-items` 정상 응답
- [ ] 프로젝트 대시보드 stat 카드 실제 숫자 표시
- [ ] 탭 클릭 시 연결된 콘텐츠 카드 노출
- [ ] Quick Capture 제출 → Inbox InboxItem 생성 확인
- [ ] 50자 미만 텍스트 제출 시 validation 에러
- [ ] E2E 시나리오 2개 통과
