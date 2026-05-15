# ADR-006 잔여 2개 설계: Inbox 임계값 설정 + 내보내기

**날짜:** 2026-04-05
**목표:** ADR-006 UI/UX 개편의 미완료 2개 항목을 마무리하여 11/11 완료로 닫는다.

---

## 1. Inbox 신뢰도 임계값 설정 UI

### 배경
- 현재 AI 자동 확정 임계값이 `pipeline_service.py:155,160`에서 `0.9`로 하드코딩
- ADR-006 §7: "신뢰도 임계값 사용자 조절 (기본 90%)"

### 설계 결정
- **저장:** Workspace 모델에 `inbox_threshold: float = 0.9` 컬럼 추가 (별도 Settings 테이블 불필요)
- **UI:** 프리셋 버튼 4개 (70% / 80% / 90% / 95%)
- **권한:** Owner만 변경 가능

### DB 변경
```sql
-- Alembic migration
ALTER TABLE workspaces ADD COLUMN inbox_threshold FLOAT NOT NULL DEFAULT 0.9;
```

### BE 변경

| 파일 | 변경 |
|------|------|
| `workspaces/models.py` | `inbox_threshold: float = 0.9` 추가 |
| `workspaces/schemas.py` | `UpdateWorkspaceSettingsRequest(inbox_threshold: float)` |
| `workspaces/router.py` | `PATCH /workspaces/{id}/settings` (require_owner) |
| `workspaces/service.py` | `update_settings()` 메서드 |
| `workspaces/repository.py` | `update_threshold()` 메서드 |
| `meetings/pipeline_service.py:155,160` | 하드코딩 `0.9` → `workspace.inbox_threshold` 참조 |

### FE 변경

| 파일 | 변경 |
|------|------|
| `app/(app)/settings/page.tsx` | 일반 탭에 프리셋 버튼 UI 추가 |
| `features/workspaces/api.ts` | `updateWorkspaceSettings()` API 함수 |
| `features/workspaces/hooks.ts` | `useUpdateWorkspaceSettings()` mutation 훅 |

### 프리셋 버튼 UI
```
AI 자동 확정 임계값
[70%] [80%] [90% ●] [95%]
90% 이상 신뢰도의 항목이 자동 확정됩니다.
낮은 값 = 자동 처리 많음 · 높은 값 = 수동 확인 많음
```

---

## 2. 내보내기 (MD / JSON)

### 배경
- 현재 회의/노트 데이터를 외부로 꺼낼 수 없음
- ADR-006 §5: "내보내기 포맷(MD/PDF/JSON) 미구현"
- PDF는 복잡도 높으므로 MD/JSON 우선, PDF는 Phase 4+ 이후

### 설계 결정
- **포맷:** Markdown + JSON (PDF 후순위)
- **대상:** 회의 상세, 노트 상세
- **진입점:** 각 상세 페이지 헤더에 다운로드 버튼 + 포맷 드롭다운
- **권한:** require_viewer (읽기 권한이면 내보내기 가능)

### BE 변경

| 파일 | 변경 |
|------|------|
| `meetings/router.py` | `GET /meetings/{id}/export?format=md\|json` |
| `meetings/service.py` | `export_meeting(id, format)` — 요약+결정+액션+트랜스크립트 변환 |
| `notes/router.py` | `GET /notes/{id}/export?format=md\|json` |
| `notes/service.py` | `export_note(id, format)` — Tiptap JSON → MD (plain_text 컬럼 활용) |

### 내보내기 데이터 구조

**회의 MD:**
```markdown
# {회의 제목}
> {날짜} · {참여자}

## 요약
{AI 요약}

## 핵심 결정사항
- {결정 1}
- {결정 2}

## 액션 아이템
- [ ] {액션 1} (@담당자, 기한: YYYY-MM-DD)
- [x] {액션 2} (완료)

## 트랜스크립트
**화자A** (00:00): {발언}
**화자B** (01:23): {발언}
```

**회의 JSON:** 기존 API 응답 구조 + 트랜스크립트 + 액션 아이템 포함한 full export

**노트 MD:** 제목 + plain_text (이미 DB에 저장됨)

**노트 JSON:** 제목 + Tiptap JSON content + metadata

### FE 변경

| 파일 | 변경 |
|------|------|
| `features/meetings/api.ts` | `exportMeeting(token, wid, id, format)` |
| `features/notes/api.ts` | `exportNote(token, wid, id, format)` |
| 회의 상세 페이지 | 헤더에 Download 아이콘 + 포맷 드롭다운 (MD/JSON) |
| 노트 상세 페이지 | 동일 |

### 다운로드 처리
- BE에서 `Content-Disposition: attachment` 헤더 + 파일 내용 반환
- FE에서 `blob` 응답 → `URL.createObjectURL` → `<a download>` 트리거

---

## 완료 기준

- [ ] /settings 일반 탭에서 임계값 프리셋 버튼 클릭 → DB 반영 → 파이프라인에서 사용
- [ ] 회의 상세에서 MD/JSON 내보내기 → 파일 다운로드
- [ ] 노트 상세에서 MD/JSON 내보내기 → 파일 다운로드
- [ ] ADR-006 구현 상태 11/11 완료
