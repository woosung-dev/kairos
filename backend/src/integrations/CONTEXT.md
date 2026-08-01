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
| `IntegrationOAuthState` | authorize가 발급한 단명 OAuth `nonce` | callback에서 1회만 소비되는 재사용 방지 행. 만료 후 GC |

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

OAuth callback은 고정 redirect URI 제약으로 I-13 예외이며, 서명 state의 workspace·요청자·nonce·PKCE·만료 검증으로 격리를 보전한다. `nonce`는 authorize에서 `IntegrationOAuthState` 행으로 저장되고 callback에서 원자적으로 소비돼 재사용을 막는다 (§6).

## 6. 엣지 케이스

- Drive 삭제·휴지통·실제 권한 회수가 확인되면 `ExternalDocument` plain text, `EmbeddingChunk`, 관련 `SemanticCache`를 즉시 제거한다 (ADR-023 D-6.5 부분 개정).
- 401/403은 세부 reason을 판별한다. 판별할 수 없으면 purge하지 않고 `reauth_required`로 보류한다.
- unsupported MIME은 조용히 건너뛰지 않는다. metadata 수신 직후 지원 여부를 판별해, 최초 import에서도 metadata 기반의 빈 문서 행을 먼저 만든 뒤 `DriveUnsupportedMimeTypeError`를 raise한다. 기존 오류 흐름이 그 행을 `failed`로 확정하므로 선택한 파일이 polling 목록에서 사라지지 않는다.
  - **사유는 문서별로 남지 않는다** (ADR-026 D4 부분 충족). `ExternalDocument`에 사유 컬럼이 없어 사유는 `sync_status="failed"`와 sync run의 `error_summary` 한 줄로만 표현된다. 문서별 사유 컬럼 신설은 마이그레이션이 필요해 백로그로 남긴다.
  - 미지원 MIME 실패 행의 `origin_url`은 Google Docs 전용 형식이 아니라 MIME 독립 Drive 링크를 쓴다. 이 값은 FE가 원본 앵커 href로 그대로 렌더한다.
- `purged`는 원본 소실·권한 회수가 확인된 상태이며, `stale`·`reauth_required`·`failed`는 본문과 청크를 보존한다.
- 같은 Drive 파일을 두 sync run이 동시에 최초 import하면 문서 생성이 `ON CONFLICT DO NOTHING`으로 충돌을 흡수한다. 경쟁에서 진 쪽은 확정된 행을 확인한 뒤 **조기 반환**하며 갱신·임베딩·상태 전이·캐시 무효화를 하지 않는다. 따라서 그 sync run에는 문서가 연결되지 않는다 — 실제로 새로 가져온 것이 없는 run이다.
- Drive revision은 `version`만 사용한다. `headRevisionId`는 바이너리 콘텐츠 파일에만 제공되어 v0 대상인 Google Docs에는 부재이며, 불투명 값이 숫자 `version`을 가리면 단조성 비교가 무력해진다.
- 본문 갱신은 진입 시 읽은 revision을 기대값으로 하는 compare-and-swap이다. 다른 동기화가 먼저 갱신했으면 본문·임베딩·상태 전이를 모두 건너뛰고 정상 반환한다("이미 최신"이지 실패가 아니다).
  - **CAS는 "최신 보존"이 아니라 "선착순 보존"이다.** 느린 run이 먼저 커밋하면 더 최신 revision의 결과가 버려지고, 문서는 사용자의 수동 재동기화로 회복한다. v0는 자동 동기화가 없는 사용자 트리거 전용이라 이 창을 수용한다.
  - 완료·오류 **상태 전이는 CAS로 보호되지 않는다.** 본문 CAS 실패 뒤 경로는 조기 반환으로 차단되지만, CAS를 시도하지 않는 분기(숫자 guard 조기 반환 / 동일 revision 생략 / 오류 경로)는 `last_synced_at`과 `sync_run_id`를 여전히 덮는다. 본문과 revision은 무손상이다.
- BL-EXT-REVISION-1의 숫자 단조성 guard는 유지된다. 저장된 값과 수신한 Drive revision이 모두 숫자이면 문서 상태와 무관하게 구 revision의 본문 덮어쓰기를 조기 차단하고, 불투명 revision은 순서를 비교하지 못하므로 guard 없이 CAS에 맡긴다.
- OAuth state의 `nonce`는 서버에 저장되고 callback에서 **`DELETE ... RETURNING` 단문으로 원자 소비**된다. 소비는 Google 토큰 교환보다 **앞**에 두어 재사용 요청이 외부 호출 없이 차단된다. 소비에 실패하면(재사용·만료) 400이다. 성공한 callback을 브라우저가 재전송하면 같은 400이 뜬다 — 일회성 정책의 의도된 결과다.
- Project를 선택하지 않은 문서는 Drive 동기화 성공 후 본문을 저장하지만 `EmbeddingChunk`를 만들지 않아 기본 RAG 제외 상태를 유지한다. 이전 정책에서 남은 청크가 있으면 문서 조회 직후 cache를 삭제 전·후로 무효화하고 청크를 회수하므로 revision·본문 변화·Drive metadata 실패와 무관하게 불변식을 복구한다.
