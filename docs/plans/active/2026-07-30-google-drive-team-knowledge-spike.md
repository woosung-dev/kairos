# Google Drive 선택형 팀 지식화 — 기술·제품 Spike 계획

> **상태**: Proposed — 사용자 승인 후 Plan → Code → Test 진입
> 
> **작성일**: 2026-07-30
> 
> **위험도**: Heavy — 외부 OAuth/API · refresh token · DB migration · RAG API/Source Viewer 계약 변경
> 
> **관련**: `CONTEXT-MAP.md` I-2/I-5/I-9/I-13/I-20 · `backend/src/rag/CONTEXT.md` R-1~R-13 · ADR-014 · ADR-020 · ADR-023 · `docs/requirements/prd.md` §3.6

---

## 1. 결정 요약

### 제안

Google Drive를 Kairos의 정식 "전체 동기화" 기능으로 즉시 출시하지 않는다. 대신 **Workspace owner가 Google Picker에서 명시적으로 선택한 Google Docs를 특정 Project의 팀 지식으로 발행하는 읽기 전용 Spike**를 구현·검증한다.

Spike가 제품·보안·운영 기준을 모두 통과하면, 선택된 개별 파일에 한해 변경분 자동 동기화를 v1 후속으로 승인한다. 폴더, Shared Drive, Sheets/Slides, 전체 Drive 탐색 및 양방향 쓰기는 이번 범위에서 제외한다.

### 한 문장 가설

회의·노트만으로 답하기 어려운 "왜 이 결정을 했는가" 질문에 대해, 선택된 Drive 문서가 인용 가능한 근거를 제공하면 Kairos의 프로젝트 RAG 가치와 신규 팀원 맥락 습득 속도가 유의미하게 높아진다.

### 최종 판단 기준

Drive import가 단순 파일 보관 기능이 아니라 **기존 소스에는 없던 근거 있는 RAG 답변을 반복적으로 만드는가**를 판별한다.

---

## 2. 확인된 사실과 가정

### 확인된 사실

- 현재 `EmbeddingChunk`는 Workspace/Project 범위, 부모 청크, `source_type`을 통해 다수 원본을 RAG에 연결한다. 검색 대상은 `chunk_level=2`이며, RAG는 출처를 반환한다.
- 현재 RAG 외부 API는 `source_type`을 `meeting`/`note`로 제한하고, Source Viewer의 full-content 조회도 Meeting/Note만 지원한다. Drive 문서는 새 원본 엔티티와 API 계약이 필요하다.
- `upload` 도메인은 R2 파일 전송·검증만 책임지며 원본 엔티티·동기화·권한 생명주기를 소유하지 않는다. Drive 연동을 여기에 넣지 않는다.
- 현재 장기 처리 표준은 `BackgroundTasks` + `202 Accepted` + 상태 polling이다.
- Google은 Google Picker와 `drive.file` 조합을 권장한다. 이는 사용자가 선택한 파일만 앱에 제공하는 좁은 권한 모델이다. `drive.readonly` 같은 넓은 scope는 초기 범위에서 요청하지 않는다. [Google Drive scope guide](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)

### 가정

- 초기 사용자 집단은 Google Docs를 회의·노트의 보충 근거로 사용하며, 엄격한 enterprise DLP/보존 정책은 아직 요구하지 않는다.
- Drive ACL을 Kairos에서 실시간·완전하게 미러링하지 않는다. 사용자는 선택 문서를 Workspace/Project 지식으로 **발행**한다.
- Team Workspace의 import 실행자는 owner로 한정한다. admin 확장은 Spike 결과 후 별도 결정한다.

---

## 3. 범위

### 포함 (Spike)

1. Workspace owner의 Google OAuth 연결 및 해제
2. Google Picker에서 선택한 **개별 Google Docs** 복수 선택
3. 선택 문서의 plain-text export, 내부 원본 엔티티 저장, Project 연결
4. 비동기 임베딩, RAG 검색, Drive 문서 인용, Kairos Source Viewer와 원본 Drive 링크
5. 수동 "지금 동기화"와 파일별 상태 polling
6. 수정·삭제·권한 회수·일시 API 장애에 대한 명시적 생명주기 처리
7. 제품 가치 및 신뢰성 Go/No-Go 측정

### 제외

- Drive 전체 탐색·전체 동기화·자동 발견
- 폴더 재귀 import, Shared Drive, Google Sheets/Slides, PDF/OCR
- Drive 원문 편집·권한 변경·양방향 sync
- webhook 기반 실시간 동기화 및 recurring scheduler
- 개인 Workspace와 Team Workspace를 넘는 자동 promote
- enterprise DLP, legal hold, domain-wide delegation

---

## 4. 제품 정책

### 4.1 원본과 파생본

| 구분 | 정책 |
|---|---|
| 원본(Source of Truth) | Google Drive 문서 |
| Kairos 저장물 | 제목, 원본 URL, MIME, revision/hash, 추출 plain text, 동기화 메타데이터, 임베딩 |
| 동기화 방향 | Drive → Kairos 단방향 읽기 전용 |
| 문서 수정 | 새 revision을 확인한 경우에만 재추출·재임베딩 |
| Drive 삭제/권한 회수 | RAG에서 즉시 제외하고 추출 텍스트·임베딩·관련 SemanticCache 제거 |
| 일시 Google 장애 | 데이터 삭제 금지. stale 상태 + 재시도 + 마지막 동기화 표시 |

### 4.2 권한·발행 경계

- Drive에서 "볼 수 있음"과 Kairos에서 "팀 지식으로 발행함"은 다르다.
- import 확인 화면은 대상 Project와 해당 Project의 visibility를 표시한다.
- Project 미선택은 기본적으로 RAG 제외 상태로 생성한다. Workspace 전체 검색 포함은 owner의 별도 확인을 요구한다.
- 선택 문서는 해당 Project의 접근 규칙(`public`/`draft`/`private`)을 따른다. RAG visibility 필터를 우회하는 별도 권한 모델을 만들지 않는다.
- Workspace owner가 떠나거나 연결이 해제된 경우의 재연결 권한은 owner에게 있다. refresh token은 프론트엔드·로그·SSE에 절대 노출하지 않는다.

### 4.3 지원 문서 유형

v1 Spike는 Google Docs의 `text/plain` export만 지원한다. Google Workspace 문서는 Drive export API로 형식별 export가 가능하지만, 지원 형식에 따라 텍스트 손실·크기 제약이 다르다. PDF/Sheets/Slides는 별도 품질 기준이 생긴 뒤 추가한다. [Google Workspace export formats](https://developers.google.com/workspace/drive/api/guides/ref-export-formats) · [files.export](https://developers.google.com/workspace/drive/api/reference/rest/v2/files/export)

---

## 5. 사용자 여정

### Journey A — owner가 문서를 팀 지식으로 발행

1. owner가 설정 → 연동에서 "Google Drive 연결"을 선택한다.
2. Kairos는 `drive.file` 최소 scope와 "선택한 파일만 접근, Drive 수정 없음"을 설명한다.
3. Google Picker에서 Google Docs 여러 개를 선택한다.
4. owner는 파일별로 Project를 연결하고, Project 접근자가 검색 가능한 팀 지식이 된다는 사실을 확인한다.
5. owner가 가져오기를 확정하면 API는 `202`와 sync run ID를 반환한다.
6. UI는 파일별 `pending → processing → completed | failed` 상태를 polling한다.
7. 완료된 문서는 프로젝트 RAG에서 "자료" 소스로 검색·인용된다.

### Journey B — 팀 멤버가 근거를 검증

1. 멤버가 프로젝트 RAG에 "왜 freemium을 선택했어?"라고 질문한다.
2. RAG는 Meeting/Note/ExternalDocument 청크를 함께 검색하되, Project visibility 필터를 먼저 적용한다.
3. 답변의 인용을 클릭하면 Kairos에 저장된 해당 문서 텍스트와 정확한 청크를 보여 준다.
4. 사용자는 "Drive에서 열기"로 원본을 확인할 수 있다.
5. Source Viewer에는 원본 수정일과 `lastSyncedAt`을 표시해 최신성을 판단할 수 있다.

### Journey C — 외부 원본이 바뀜

1. owner가 "지금 동기화"를 실행한다.
2. 서버는 Drive revision/hash를 비교한다.
3. 변경 없음이면 상태·동기화 시각만 갱신한다.
4. 변경 있음이면 기존 `EmbeddingChunk`를 제거하고 새 plain text를 임베딩한 뒤 관련 SemanticCache를 무효화한다.
5. Drive 삭제 또는 실제 접근 권한 회수면 해당 문서를 RAG에서 제외하고 파생 데이터를 삭제한다.

---

## 6. 목표 아키텍처

### 6.1 도메인 경계

새 백엔드 `integrations` 도메인이 Google OAuth, 선택 파일, 동기화 상태, 외부 원본 생명주기를 소유한다. `upload` 및 `notes`에는 Drive 책임을 넣지 않는다.

```text
integrations/router
  └─ IntegrationService              # 연결/목록/해제, owner 권한
  └─ GoogleDriveSyncPipelineService  # 외부 호출 + Project 검증 + 임베딩 조율
       ├─ GoogleDriveClient           # OAuth token refresh, Picker-selected file get/export
       ├─ IntegrationRepository       # connection/document/sync run 영속화
       ├─ ProjectRepository           # workspace + Project FK/visibility 검증 (read)
       └─ EmbeddingService            # external_document 청크 생성/삭제

rag/RagPipelineService
  └─ 기존 visibility 검증 후 source_type="external_document" 검색 허용
sources/Source Viewer
  └─ ExternalDocument full-content 조회 + origin URL 렌더
```

`GoogleDriveSyncPipelineService`만 여러 도메인의 write를 조율한다. 서비스 간 직접 호출 금지와 cross-domain transaction 규칙은 `CONTEXT-MAP.md` I-2 및 ADR-014를 따른다.

### 6.2 최소 데이터 모델

| 엔티티 | 주요 필드 | 책임 |
|---|---|---|
| `IntegrationConnection` | `id`, `workspace_id`, `provider`, `authorized_by_id`, `encrypted_refresh_token`, `status`, `scope`, `token_expires_at` | Workspace별 OAuth 연결 |
| `ExternalDocument` | `id(UUID)`, `workspace_id`, `connection_id`, `project_id`, `drive_file_id(str)`, `title`, `mime_type`, `origin_url`, `revision_id`, `content_hash`, `plain_text`, `sync_status`, `last_synced_at` | Drive 문서의 Kairos 내부 원본 |
| `IntegrationSyncRun` | `id`, `workspace_id`, `connection_id`, `status`, `requested_by_id`, `started_at`, `completed_at`, `error_summary` | 202 polling과 감사 가능한 동기화 실행 |

`EmbeddingChunk.source_id`에는 UUID인 `ExternalDocument.id`를 쓰고, `source_type`은 `external_document`로 확장한다. 외부 Drive file ID를 직접 넣지 않는다.

모든 엔티티 및 보조 FK는 `workspace_id`를 포함해 I-9 격리를 강제한다. `ExternalDocument.project_id`에는 Project의 composite FK를 적용한다.

### 6.3 API 초안

```text
POST /api/v1/workspaces/{workspace_id}/integrations/google-drive/authorize
  owner → OAuth authorization URL 또는 redirect

GET  /api/v1/integrations/google-drive/callback
  OAuth signed state 검증 → connection 저장 → settings 복귀

GET  /api/v1/workspaces/{workspace_id}/integrations/google-drive
  owner → connection 상태 + 마지막 동기화

POST /api/v1/workspaces/{workspace_id}/integrations/google-drive/documents
  owner → selected file IDs + projectId → 202 { syncRunId }

GET  /api/v1/workspaces/{workspace_id}/integrations/sync-runs/{sync_run_id}
  owner → file별 status polling

POST /api/v1/workspaces/{workspace_id}/integrations/google-drive/documents/{document_id}/sync
  owner → 단일 문서 재동기화, 202

DELETE /api/v1/workspaces/{workspace_id}/integrations/google-drive/documents/{document_id}
  owner → RAG 발행 취소 + 파생 데이터 cleanup

GET /api/v1/workspaces/{workspace_id}/external-documents/{document_id}
  접근 가능한 멤버 → Source Viewer full content
```

OAuth callback만 redirect 제약상 Workspace prefix 예외이며, nonce·PKCE·만료·Workspace ID·요청자 ID를 포함한 서명 state를 검증해야 한다.

---

## 7. 작업 단계

### Phase 0 — UX 가설 확인 (완료, 배포 대상 아님)

- 개발 환경 설정 화면에 A(권한 우선), B(가져오기 흐름), C(지식 현황) 시안을 추가했다.
- 후보 UX: **A의 권한 설명 → B의 단계형 import**. C는 실제 데이터가 생긴 뒤 관리 화면으로 사용한다.
- 산출물: `frontend/src/features/workspaces/components/google-drive-prototype.tsx` 및 인접 `NOTES.md`.

### Phase 1 — 승인 전 설계 고정

1. 다음 available ADR에 선택형 Drive 지식화 결정 기록
   - 최소 scope, 읽기 전용, Drive ACL ≠ Kairos 발행, deletion 정책, 지원 파일 유형, 회수 조건
2. Google Cloud OAuth consent screen·redirect URI·테스트 사용자 준비
3. data retention과 권한 회수 시 plain text 즉시 삭제 정책을 사용자 승인으로 확정
4. `docs/api/endpoints.md`, `docs/architecture/erd.md`, `docs/architecture/rag-pipeline.md`의 변경 지점을 확정

### Phase 2 — 기술 Thin Slice

1. `integrations` 모델·migration·repository·schemas·exceptions 생성
2. server-side OAuth code flow + encrypted refresh token 저장
3. Picker-selected Google Docs 1~3개를 수동 import하는 endpoint 구현
4. BackgroundTask에서 export → revision 비교 → `ExternalDocument` 저장 → 임베딩 → cache invalidation 구현
5. `external_document` RAG 검색·SSE source metadata·Source Viewer 확장
6. owner-only 설정 UI를 실제 API와 연결하고 polling을 추가

### Phase 3 — 신뢰성 Thin Slice

1. 수정 문서 수동 재동기화: 새 revision만 반영, 이전 청크/캐시 제거
2. 삭제·휴지통·실제 permission loss: RAG 즉시 제외 및 파생 데이터 cleanup
3. transient 429/5xx/network: stale 표시, 재시도 가능 상태, 데이터 보존
4. race 방지: `(document_id, revision_id)` 단위 idempotency와 최신 revision guard
5. 연결 해제: token 폐기 + 모든 연결 문서 unpublish 처리

### Phase 4 — 가치 검증 및 결정

1. owner가 서로 다른 목적의 Google Docs 3개를 하나의 Project에 발행
2. Meeting/Note만으로 답할 수 없는 질문 5개를 정의해 RAG 질의
3. 인용 클릭 → 정확한 Kairos 원문 청크 + Drive origin link 확인
4. 문서 수정, 삭제, 접근 권한 회수, 일시 Google API 실패를 각각 재현
5. 아래 Go/No-Go 기준으로 자동 동기화 v1 여부 결정

---

## 8. Go / No-Go 기준

### Go — 선택 파일 자동 동기화 v1 승인

- 선택한 Drive 자료가 없는 경우보다 근거 있는 답변이 최소 3개 이상의 실제 질문에서 추가된다.
- 모든 Drive 인용은 원문·동기화 시각·origin URL을 노출하며, Source Viewer가 정확한 문맥을 연다.
- 수정 문서는 수동 sync 뒤 이전 내용이 검색되지 않는다.
- 삭제·실제 permission loss 문서는 RAG 결과와 SemanticCache 어디에서도 다시 노출되지 않는다.
- OAuth token은 브라우저 state, API 응답, Sentry/애플리케이션 로그에 노출되지 않는다.
- owner가 "어떤 파일이 어느 Project에 발행됐는지"를 혼동 없이 설명할 수 있다.

### No-Go / 보류

- Drive 자료가 단순 파일 보관함으로만 쓰이고, RAG 질문의 근거·품질 차이가 없다.
- 원본 삭제/권한 회수 후 파생 데이터가 남는 보안 결함을 해결하지 못한다.
- 사용자 테스트에서 "이 문서가 팀에 공개되는지"를 반복적으로 오해한다.
- broad scope 없이는 제품 가설을 검증할 수 있는 구현을 만들 수 없다.

---

## 9. 위험과 대응

| 위험 | 심각도 | 대응 |
|---|---:|---|
| 문서 최신성 불일치 | High | revision/hash + manual sync + `lastSyncedAt` + stale 표시 |
| 권한 회수 뒤 민감 데이터 노출 | Critical | permission loss 원인 식별 후 fail-closed de-index + plain text/임베딩/cache cleanup |
| Google API 장애·rate limit을 권한 회수로 오판 | High | 401/403의 세부 reason과 429/5xx/network를 분리. 장애는 stale/retry, 실제 권한 회수만 purge |
| OAuth refresh token 유출 | Critical | 서버 전용 code flow, 암호화 저장, key는 Secret Manager/KMS, 로그 redaction, API 반환 금지 |
| owner 개인 Drive 문서의 의도치 않은 Workspace 공개 | Critical | owner-only + 파일별 명시 선택 + Project visibility 확인 + Workspace-wide 기본 비활성 |
| 구버전 sync job이 새 버전을 덮어씀 | High | revision monotonic guard + idempotency key + source별 lock/상태 전이 |
| 파일 형식별 텍스트 품질 저하 | Medium | Docs plain text만 지원. unsupported MIME은 명시적 failed 상태 |
| 기능 범위가 connector 플랫폼으로 비대화 | High | v1은 file-only/manual-only/read-only. folder/Shared Drive/webhook은 Go 이후 별도 ADR |

---

## 10. 검증 계획

Heavy 변경 표준을 적용한다.

### Backend

- OAuth state/PKCE/owner/RBAC/Workspace isolation pytest
- migration alembic dry-run 및 upgrade/rollback 검증
- Google Drive client는 fixture 기반 contract test: export success, revision unchanged, modified, deleted, permission loss, 429, 5xx
- `ExternalDocument`의 모든 find/update/delete에 `workspace_id` 누락이 없는지 architecture test
- update/delete 뒤 `EmbeddingChunk`와 `SemanticCache` cleanup 단언

### API 계약·E2E

- 새 API signature에 schemathesis contract test
- Playwright: owner import → 202 polling → RAG 질문 → `[N]` 인용 → Source Viewer → Drive link
- member가 private Project의 Drive 문서를 RAG/Source Viewer에서 보지 못하는 multi-account E2E
- owner 이외 import/connection delete가 403인지 E2E/API 단언

### Frontend

- import/processing/failed/reauth-required/stale 상태 각각 캡처
- 완료 전 console.error 0 증거
- 실제 OAuth는 테스트 전용 Google 계정과 전용 문서로만 수동 검증

현재 `T-INFRA-E2E-API`가 복구되기 전에는 전체 E2E 완료를 주장하지 않는다. 로컬/스테이징 API URL과 Playwright 환경을 먼저 정상화한다.

---

## 11. 운영·관측성

- sync run: `workspace_id`, 문서 수, 성공/실패 수, 재시도 횟수, provider error code, 총 소요 시간
- 문서: `last_synced_at`, `source_modified_at`, `revision_id`, `sync_status`, `failure_reason`
- RAG: `source_type=external_document` 인용 수, stale source 인용 수, citation open 수
- 보안: reauth 수, permission-loss cleanup 수, cross-workspace attempt 수
- refresh token·exported content·원문 전체는 관측 로그에 기록하지 않는다.

자동 동기화가 승인되는 후속 단계에서는 Drive changes API와 scheduler를 조합한다. changes token을 저장해 변경분만 처리하고, webhook은 변경 신호로만 사용한 뒤 재조회한다. Drive notification channel은 만료·교체가 필요하므로 webhook 단독 운영은 금지한다. [Retrieve changes](https://developers.google.com/workspace/drive/api/guides/manage-changes) · [Drive push notifications](https://developers.google.com/workspace/drive/api/guides/push)

---

## 12. 회수 전략

- Spike 실패 시: `integrations` API/모델/migration을 제품에 merge하지 않는다. UI prototype은 사용자 피드백을 기록한 뒤 제거한다.
- v1 출시 후 품질 미달 시: 자동 동기화만 비활성화하고, 이미 발행된 문서는 owner가 수동 sync 또는 unpublish할 수 있게 유지한다.
- 보안 결함 시: 해당 connection을 즉시 disable하고 모든 연결 문서를 RAG에서 제외한다. refresh token을 폐기하고 affected Workspace owner에게 재연결을 요구한다.
- Drive 의존성을 다른 provider로 일반화하지 않는다. provider abstraction은 Google Docs Spike가 통과한 뒤 필요한 최소 수준에서만 도입한다.

---

## 13. 승인 요청

이 계획은 다음 두 결정을 승인받으면 Phase 1로 진입한다.

1. **제품 결정**: Google Drive 선택형 Google Docs import Spike를 실행한다.
2. **데이터 정책 결정**: 실제 권한 회수/삭제가 확인되면 Kairos에 저장된 해당 문서의 plain text·임베딩·캐시를 즉시 제거한다.

두 결정이 승인되기 전에는 Google OAuth credential 생성, migration, 실제 Drive API 호출을 시작하지 않는다.
