<!-- integrations 도메인 — 외부 소스 ingest 레일 v0 (ADR-026) -->

# integrations CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`. 상세 결정: `docs/adr/026-external-source-ingest-rail.md`.
>
> **현재 상태 (2026-07-31)**: ADR-026의 모델·repository/service·GoogleDriveClient·동기화 pipeline·외부 문서 임베딩 경로와 OAuth authorize/callback 라우터가 구현됐다.

---

## 1. 책임

- Google OAuth 연결과 해제의 도메인 소유
- Workspace owner가 명시 선택한 외부 파일과 `ExternalDocument`의 저장·발행 상태 소유
- `IntegrationSyncRun`의 sync 상태, 수동 재동기화, 외부 원본 생명주기 소유
- Drive → Kairos 단방향 읽기 전용의 Google Docs plain-text export 조율
- 원본 소실이 확인된 경우 `purged` 상태로 본문·청크·관련 캐시를 정리하고 이력 행을 보존

## 2. 비책임

- R2 파일 전송·검증은 `upload` 도메인 책임이며, Drive 연동을 그 도메인에 넣지 않는다.
- 노트의 Drive 저장·편집은 `notes` 도메인 책임이 아니며, Drive를 노트 원본으로 취급하지 않는다.
- RAG 검색 조립과 visibility 검증은 `rag/RagPipelineService` 및 기존 visibility 경계를 따른다.
- provider abstraction은 도입하지 않는다. v0는 Google Drive 단일 구현이다.

## 3. 엔티티 (ADR-026 D6/D9)

| 엔티티 | 책임 | 핵심 경계 |
|---|---|---|
| `IntegrationConnection` | Workspace별 Google OAuth 연결 | 암호화 refresh token, 연결 상태, 승인 사용자 |
| `ExternalDocument` | 선택된 Drive 문서의 Kairos 내부 원본 | `workspace_id`·`project_id`·Drive file ID·plain text·revision·sync 상태 |
| `IntegrationSyncRun` | 202 응답 뒤 polling 가능한 동기화 실행 | 요청자, 파일별 상태, 시작·완료·오류 요약 |

## 4. 핵심 불변식

| # | 불변식 | 강제 위치 |
|---|---|---|
| I-EXT-1 | 연결·선택·동기화·발행 취소는 Workspace owner만 실행한다. | router의 `require_owner` |
| I-EXT-2 | 모든 엔티티와 조회·수정·삭제는 `workspace_id`를 포함해 I-9 격리를 강제한다. | repository + composite FK |
| I-EXT-3 | 장기 import/sync는 BackgroundTasks + `202 Accepted` + GET status polling으로 처리한다. | router + pipeline_service (I-5) |
| I-EXT-4 | 여러 도메인의 write는 `GoogleDriveSyncPipelineService` 같은 pipeline/orchestrator만 조율한다. | pipeline_service (I-2, §4.2) |
| I-EXT-5 | Drive → Kairos는 읽기 전용이며, v0는 Google Docs `text/plain` export만 지원한다. | Google Drive client |
| I-EXT-6 | 자동 retry를 두지 않는다. 429/5xx/network/circuit open은 stale로 보존하고 사용자가 수동 재동기화한다. | sync 상태 전이 |

## 5. 엔드포인트 (ADR-026 D9)

```text
POST   /api/v1/workspaces/{workspace_id}/integrations/google-drive/authorize
GET    /api/v1/integrations/google-drive/callback
GET    /api/v1/workspaces/{workspace_id}/integrations/google-drive
POST   /api/v1/workspaces/{workspace_id}/integrations/google-drive/documents
GET    /api/v1/workspaces/{workspace_id}/integrations/sync-runs/{sync_run_id}
POST   /api/v1/workspaces/{workspace_id}/integrations/google-drive/documents/{document_id}/sync
DELETE /api/v1/workspaces/{workspace_id}/integrations/google-drive/documents/{document_id}
GET    /api/v1/workspaces/{workspace_id}/external-documents/{document_id}
```

OAuth callback은 고정 redirect URI 제약으로 I-13 예외이며, 서명 state의 workspace·요청자·nonce·PKCE·만료 검증으로 격리를 보전한다.

## 6. 엣지 케이스

- Drive 삭제·휴지통·실제 권한 회수가 확인되면 `ExternalDocument` plain text, `EmbeddingChunk`, 관련 `SemanticCache`를 즉시 제거한다 (ADR-023 D-6.5 부분 개정).
- 401/403은 세부 reason을 판별한다. 판별할 수 없으면 purge하지 않고 `reauth_required`로 보류한다.
- unsupported MIME은 조용히 건너뛰지 않고 문서별 `failed` 상태와 사유를 남긴다.
- `purged`는 원본 소실·권한 회수가 확인된 상태이며, `stale`·`reauth_required`·`failed`는 본문과 청크를 보존한다.
- BL-EXT-REVISION-1은 부분 해소 상태다. 저장된 값과 수신한 Drive revision이 모두 숫자이면 문서 상태와 무관하게 구 revision의 본문 덮어쓰기를 막고 기존 상태를 보존한다. 불투명 revision은 순서를 비교하지 못하므로 guard를 적용하지 않고 갱신한다.
