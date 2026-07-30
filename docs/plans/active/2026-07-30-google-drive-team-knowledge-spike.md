# Google Drive 선택형 팀 지식화 — 기술·제품 Spike 계획

> **상태**: Revised (2026-07-30 사실 교정) — 사용자 승인 후 Plan → Code → Test 진입
> 
> **작성일**: 2026-07-30
> 
> **위험도**: Heavy — 외부 OAuth/API · refresh token · DB migration · RAG API/Source Viewer 계약 변경
> 
> **관련**: `CONTEXT-MAP.md` I-2/I-5/I-9/I-13/I-20/I-21 · `backend/src/rag/CONTEXT.md` R-1~R-13 · ADR-014 · ADR-020 · ADR-023 · `docs/requirements/prd.md` §3.6 (X축 v3/v5 선행 인프라)

> **교정 이력 (2026-07-30)**
> - Drive 기능 자체가 아닌 외부 소스 ingest 레일 v0로 근거를 재프레이밍했다.
> - 현재 저장소의 RAG 타입 제약, 암호화·재시도 인프라, 헌법 예외와 보존 정책을 사실에 맞게 바로잡았다.
> - ADR-026(W1)에서 결정할 Picker 토큰·청크 저장 경로·E2E 인프라 갭을 명시했다.
> - Drive 단일 구현과 기존 제외 범위는 유지한다.

---

## 1. 결정 요약

### 제안

Google Drive를 Kairos의 정식 "전체 동기화" 기능으로 즉시 출시하지 않는다. 이 Spike는 **외부 소스 ingest 레일 v0**를 검증하며, Drive는 가장 얇은 첫 provider로만 사용한다. 즉 Workspace owner가 Google Picker에서 명시적으로 선택한 Google Docs를 특정 Project의 팀 지식으로 발행하는 읽기 전용 Spike를 구현·검증한다. 이는 PRD §3.6 X축의 v3 Slack 및 v5 웹·이메일이 공통으로 요구하는 `integrations` 도메인, 암호화 OAuth 연결, 외부 원본 엔티티, `source_type` 확장, sync-run polling 선행 인프라를 가장 좁은 범위에서 검증하는 일이다.

Spike가 제품·보안·운영 기준을 모두 통과하면, 선택된 개별 파일에 한해 변경분 자동 동기화를 v1 후속으로 승인한다. 폴더, Shared Drive, Sheets/Slides, 전체 Drive 탐색 및 양방향 쓰기는 이번 범위에서 제외한다.

### 한 문장 가설

외부 소스 ingest 레일 v0에서 선택된 Drive 문서가 회의·노트만으로 답하기 어려운 "왜 이 결정을 했는가" 질문의 인용 가능한 근거를 제공하면, 이후 v3 Slack 및 v5 웹·이메일에도 재사용할 선행 인프라의 타당성과 Kairos 프로젝트 RAG 가치·신규 팀원 맥락 습득 속도를 함께 검증할 수 있다.

### 최종 판단 기준

Drive import가 단순 파일 보관 기능이 아니라 **기존 소스에는 없던 근거 있는 RAG 답변을 반복적으로 만드는가**를 판별한다.

---

## 2. 확인된 사실과 가정

### 확인된 사실

- 현재 `EmbeddingChunk`는 Workspace/Project 범위, 부모 청크, `source_type`을 통해 다수 원본을 RAG에 연결한다. 검색 대상은 `chunk_level=2`이며, RAG는 출처를 반환한다.
- BE RAG API의 `source_type`은 `str | None`이며 Literal·Enum·validator로 값을 제한하지 않는다. 실제 제약은 `backend/src/embeddings/repository.py:17-19`의 `_ALLOWED_SOURCE_TYPES`와 `save_chunk`의 검증 경로(`:61-75`, `:91-93`; `save_chunks` 우회 경로는 `:55-59`) 및 다음 FE 확장 지점에 있다. 2026-07-30 코드 관측에서 writer는 `meeting`/`note`/`memory`이며, Source Viewer의 full-content 조회는 Meeting/Note만 지원하므로 Drive에는 새 원본 엔티티와 Viewer API 계약이 필요하다.
  - **확인된 지점 (2026-07-30 grep 기준)**
    - **(A) 타입 union — 확장 필수, 누락 시 `tsc` 차단:** `frontend/src/features/rag/types.ts:20`의 `RagSource.sourceType: "meeting" | "note"`, `frontend/src/features/rag/types.ts:30`의 `SearchFilter.sourceType?: "meeting" | "note" | null`, `frontend/src/features/sources/types.ts:6`의 `SourceDocument.type: "meeting" | "note" | "file"`, `frontend/src/components/layout/sidebar.tsx:59`의 `type: "meeting" | "note" | "file"`.
    - **(B) 좁은 캐스트 / const 목록 — 컴파일은 통과하므로 가장 위험:** `frontend/src/features/rag/components/search-scope.tsx:20-24`의 검색 필터 드롭다운 `SOURCE_OPTIONS as const`와 `frontend/src/features/rag/components/search-scope.tsx:96-99`의 `as "meeting" | "note" | null`. 전자에 없으면 사용자는 `external_document`를 선택 자체를 못 한다. 좁은 캐스트는 union 확장 시 `tsc` 오류를 내지 않으므로, Phase 2-5 FE 정렬에서 컴파일러에만 의존하면 누락된다. 파일:라인 체크리스트로 수동 확인해야 한다.
    - **(C) 라벨 / 아이콘 / 분기 — 런타임 폴백:** `frontend/src/features/rag/components/rag-sources.tsx:17-20`의 라벨 Record는 미매칭 시 raw 문자열을 보이고, `frontend/src/features/sources/components/source-viewer.tsx:31-35`의 아이콘 Record는 `📄`로 폴백한다. 같은 파일 `:285`의 3항 삼항 라벨은 미매칭 시 `파일`을 보이며, `:96-138` full-content 분기는 `:136-137`에서 전용 API 없음 → RAG 스니펫으로 떨어진다.
    - **(D) 범위 밖 — 확장하지 말 것:** `frontend/src/features/inbox/types.ts:3`의 `InboxSourceType`, `frontend/src/features/audit/types.ts:3`의 `AuditItemType`, `frontend/src/components/shared/ItemPromoteModal.tsx`의 promote 대상 매핑은 다른 개념이며 `source_type` 확장 대상이 아니다.
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
| Drive 삭제/권한 회수 | 외부 원본(`external_document`)이 소실되었거나 접근 불가로 확인되면 RAG에서 즉시 제외하고 추출 텍스트·임베딩·관련 SemanticCache를 purge한다. 이는 ADR-023 D-6.5의 **부분 개정**으로, 내부 소스(트랜스크립트/노트/액션)는 사용자 명시적 삭제 전 무기한 보존 원칙을 유지한다. |
| 일시 Google 장애 | 데이터 삭제 금지. stale 상태 + 마지막 동기화 표시 + 사용자가 트리거한 수동 재동기화(자동 retry 없음) |

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
       ├─ EmbeddingService            # external_document 청크 생성/삭제
       └─ drive_breaker                # `services/ai_resilience.py`의 vendor-agnostic `_CircuitBreaker` 확장 재사용

rag/RagPipelineService
  └─ 기존 visibility 검증 후 source_type="external_document" 검색 허용
```

`GoogleDriveSyncPipelineService`만 여러 도메인의 write를 조율한다. 서비스 간 직접 호출 금지는 `CONTEXT-MAP.md` §4.2 의존 규칙 표를, cross-domain transaction은 I-2와 ADR-014를 따른다. Journey A의 `pending → processing → completed | failed`는 I-2의 BackgroundTask polling 상태 전이별 commit 예외가 직접 지지한다.

### 6.2 최소 데이터 모델

| 엔티티 | 주요 필드 | 책임 |
|---|---|---|
| `IntegrationConnection` | `id`, `workspace_id`, `provider`, `authorized_by_id`, `encrypted_refresh_token`, `status`, `scope`, `token_expires_at` | Workspace별 OAuth 연결 |
| `ExternalDocument` | `id(UUID)`, `workspace_id`, `connection_id`, `project_id`, `drive_file_id(str)`, `title`, `mime_type`, `origin_url`, `revision_id`, `content_hash`, `plain_text`, `sync_status`, `last_synced_at` | Drive 문서의 Kairos 내부 원본 |
| `IntegrationSyncRun` | `id`, `workspace_id`, `connection_id`, `status`, `requested_by_id`, `started_at`, `completed_at`, `error_summary` | 202 polling과 감사 가능한 동기화 실행 |

`EmbeddingChunk.source_id`에는 UUID인 `ExternalDocument.id`를 쓰고, `source_type`은 `external_document`로 확장한다. 외부 Drive file ID를 직접 넣지 않는다.

모든 엔티티 및 보조 FK는 `workspace_id`를 포함해 I-9 격리를 강제한다. `ExternalDocument.project_id`에는 Project의 composite FK를 적용한다.

`external_document` 청크는 기존 `EmbeddingChunk.embedding`의 `halfvec(1536)` 컬럼을 그대로 사용하므로 I-20을 자동 충족하며, 신규 벡터 컬럼은 만들지 않는다. 검색은 R-13/I-21의 `embeddings/repository.py` `_apply_hnsw_session_params` 경로를 그대로 경유한다.

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
  `integrations` 도메인 소유: 접근 가능한 멤버 → Source Viewer full content
```

OAuth callback은 redirect 제약상 Workspace prefix 예외 목록에 추가되는 항목이므로, 2026-07-30 기준 기존 예외(`/api/v1/users`, `/api/v1/feedback`)에 callback을 추가하도록 헌법 I-13 원문을 개정해야 한다. nonce·PKCE·만료·Workspace ID·요청자 ID를 포함한 서명 state를 검증해야 한다.

---

## 7. 작업 단계

### Phase 0 — UX 가설 확인 (완료, 배포 대상 아님)

- 개발 환경 설정 화면에 A(권한 우선), B(가져오기 흐름), C(지식 현황) 시안을 추가했다.
- 후보 UX: **A의 권한 설명 → B의 단계형 import**. C는 실제 데이터가 생긴 뒤 관리 화면으로 사용한다.
- 산출물: `frontend/src/features/workspaces/components/google-drive-prototype.tsx` 및 인접 `NOTES.md`.
- 알려진 이슈: 후보 시안 A/B의 카피가 확정 범위를 넘는다. A의 `Docs · PDF · Markdown`, B의 `파일 또는 폴더` 및 하위 파일 수 표시는 W2에서 각각 `Google Docs`와 `파일`로 정정한다. 이 Spike에서는 prototype 파일을 수정하지 않는다.

### Phase 1 — 승인 전 설계 고정

1. ADR-026에 선택형 Drive 지식화 결정을 기록한다.
   - 최소 scope, 읽기 전용, Drive ACL ≠ Kairos 발행, 지원 파일 유형, 회수 조건
   - ADR-023 D-6.5를 부분 개정한다. 외부 원본(`external_document`)은 소실·접근 불가가 확인되면 Kairos 파생물을 purge하는 예외로 신설하고, 내부 소스(트랜스크립트/노트/액션)의 무기한 보존 원칙은 변경하지 않는다.
2. Google Cloud OAuth consent screen·redirect URI·테스트 사용자 준비
3. data retention과 권한 회수 시 외부 원본 파생물 purge 정책을 사용자 승인으로 확정
4. `CONTEXT-MAP.md` §4.1 모듈 목록에 `integrations`를 추가하고 모듈 수를 함께 갱신한다. I-13 원문도 OAuth callback을 Workspace prefix 예외 목록에 추가하며, `backend/src/integrations/CONTEXT.md`를 새로 작성한다.
5. `docs/api/endpoints.md`, `docs/architecture/erd.md`, `docs/architecture/rag-pipeline.md`의 변경 지점을 확정

### Phase 2 — 기술 Thin Slice

1. `integrations` 모델·migration·repository·schemas·exceptions 생성
2. server-side OAuth code flow와 refresh token 암호화 저장을 구현한다. **신규 작성 필요**: `backend/src/common/crypto.py`의 Fernet 유틸, `Settings.integrations_encryption_key: SecretStr`, non-dev validator. `cryptography`는 `pyjwt[crypto]`의 transitive dependency로 이미 설치되어 있으므로 신규 의존성은 추가하지 않는다. 키는 현행 `deploy.yml` `env_vars` 경로로 주입하며 Secret Manager 이관은 ADR-008의 미완 항목이다. validator는 부팅을 차단하지 않고 loud warning + alert를 낸다(ADR-024의 prod 전체 다운 사고 교훈).
3. Picker-selected Google Docs 1~3개를 수동 import하는 endpoint 구현
4. BackgroundTask에서 export → revision 비교 → `ExternalDocument` 저장 → 임베딩 → cache invalidation 구현
5. **Low 위험도**: `external_document` RAG 검색·SSE source metadata·Source Viewer를 확장한다. BE RAG API는 `source_type` 값을 제한하지 않으므로 API enum 확장은 필요 없고, `save_chunk` 화이트리스트와 §2의 **확인된 지점 (2026-07-30 grep 기준)** 체크리스트를 정렬한다.
   - **(A) 타입 union — 확장 필수, 누락 시 `tsc` 차단:** `rag/types.ts`, `sources/types.ts`, `sidebar.tsx`의 타입 union을 확장한다.
   - **(B) 좁은 캐스트 / const 목록 — 컴파일은 통과하므로 가장 위험:** `search-scope.tsx`의 `SOURCE_OPTIONS as const`와 좁은 캐스트는 파일:라인 체크리스트로 수동 확인한다. Phase 2-5 FE 정렬에서 컴파일러에만 의존하지 않는다.
   - **(C) 라벨 / 아이콘 / 분기 — 런타임 폴백:** `rag-sources.tsx`와 `source-viewer.tsx`의 라벨·아이콘·full-content 분기를 `external_document` 계약과 정렬한다.
   - **(D) 범위 밖 — 확장하지 말 것:** inbox·audit·promote 대상 매핑은 이번 `source_type` 확장에 포함하지 않는다.
6. owner-only 설정 UI를 실제 API와 연결하고 polling을 추가

### Phase 3 — 신뢰성 Thin Slice

1. 수정 문서 수동 재동기화: 새 revision만 반영, 이전 청크/캐시 제거
2. 삭제·휴지통·실제 permission loss: RAG 즉시 제외 및 파생 데이터 cleanup
3. transient 429/5xx/network: stale 표시, 데이터 보존, **사용자 트리거 수동 재동기화**만 제공한다. 자동 retry는 `services/ai_resilience.py`의 확립된 비용 증폭 방지 결정을 따라 도입하지 않는다.
4. race 방지: `(document_id, revision_id)` 단위 idempotency와 최신 revision guard
5. 연결 해제: token 폐기 + 모든 연결 문서 unpublish 처리

### Phase 4 — 가치 검증 및 결정 (인프라 복구 후 이연)

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
- 두 번째 provider(Slack ingest)를 가정했을 때 `integrations` 도메인의 모델, sync-run, 상태 전이, 암호화 연결 중 재작성 없이 재사용 가능한 부분이 과반이며, provider-specific 코드는 `GoogleDriveClient`와 export/MIME 처리에 국지화되어 있다.

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
| Google API 장애·rate limit을 권한 회수로 오판 | High | 401/403의 세부 reason과 429/5xx/network를 분리한다. 장애는 stale 표시·데이터 보존·사용자 트리거 수동 재동기화(자동 retry 없음), 실제 권한 회수만 purge한다. |
| OAuth refresh token 유출 | Critical | **신규 작성 필요**: `backend/src/common/crypto.py` Fernet 유틸 + `Settings.integrations_encryption_key: SecretStr` + non-dev validator. 키는 현행 `deploy.yml` `env_vars` 경로로 주입하며 Secret Manager 이관은 ADR-008 미완 항목이다. API 반환·로그 기록은 금지한다. validator는 부팅 차단 대신 loud warning + alert를 사용한다. |
| owner 개인 Drive 문서의 의도치 않은 Workspace 공개 | Critical | owner-only + 파일별 명시 선택 + Project visibility 확인 + Workspace-wide 기본 비활성 |
| 구버전 sync job이 새 버전을 덮어씀 | High | revision monotonic guard + idempotency key + source별 lock/상태 전이 |
| 파일 형식별 텍스트 품질 저하 | Medium | Docs plain text만 지원. unsupported MIME은 명시적 failed 상태 |
| 기능 범위가 connector 플랫폼으로 비대화 | High | v1은 file-only/manual-only/read-only. folder/Shared Drive/webhook은 Go 이후 별도 ADR |

### 미해결 설계 갭 — ADR-026(W1)에서 결정

- **G1 · Google Picker 브라우저 토큰**: Picker는 `apis.google.com` 스크립트, Google API key, 브라우저 내 단기 OAuth access token(별도 GIS token client)을 요구한다. 서버 측 authorize/callback과 refresh token 비노출만 정의되어 있어 브라우저 access token의 존재·수명·CSP 정책이 미정의다. **본 Spike 최대 기술 리스크**이며 ADR-026(W1)에서 결정한다.
- **G2 · 화이트리스트 우회 경로**: `backend/src/embeddings/repository.py:61-75`, `:91-93`의 `source_type` assert는 `save_chunk`에만 있고, Meeting/Note가 실제 사용하는 `save_chunks`(`:55-59`)는 검증을 우회한다. 화이트리스트는 `:17-19`에 있으며, 2026-07-30 기준 등재값 중 `action`/`inbox`는 화이트리스트에만 있고 `EmbeddingChunk` 실 insert가 없다. 즉 화이트리스트 등재 ≠ 실제 writer라는 선례가 있다. Drive 경로를 어느 저장 경로로 보낼지는 ADR-026(W1)에서 결정한다.
- **G3 · 검증 불능**: §8의 Playwright multi-account E2E는 `docs/TODO.md` `## Blocked`의 `T-INFRA-E2E-API`(2026-07-30 사용자 기록 — **main 체크아웃 미커밋 working tree에만 존재, HEAD `7322fc8`에는 없음**)를 blocker 근거로 삼는다. 커밋되지 않은 항목에 blocker 근거를 두면 다른 체크아웃·CI에서 재현되지 않으므로 커밋이 필요하다. [확인 필요] 2026-07-30 사용자 관측에 따르면 로컬 `E2E_API_URL`의 `/api/v1/health`는 404다. [확인 필요] 문서상 legacy Cloud Run URL의 `/api/v1/health`도 404다. [확인 필요] `jetaime-dev`에서 `kairos-api` 서비스는 조회되지 않는다. 이 환경 관측은 저장소 정적 검증으로 재현할 수 없다. 반례로 `docs/adr/024-ga-readiness.md:9`와 `.github/workflows/deploy.yml:95-98`은 2026-06-30 `CLERK_PROD_HARDENING=false` 게이트로 prod 백엔드 crash-loop를 복구했다고 기록하므로, 현재도 404라고 재측정 없이 단정할 수 없다. Phase 4는 인프라 복구 후로 이연하며 ADR-026(W1)에서 판정 전제조건을 기록한다.
- **부수 발견 · `httpx` 의존성**: `httpx`는 `backend/pyproject.toml`의 dev dependency group에만 있지만 `common/notifications.py`와 `services/transcription.py`가 module-level import 한다. 현재는 `openai`/`google-genai`의 transitive dependency로 우연히 해결되며, Drive client가 `httpx`를 쓰면 프로덕션 의존성으로 승격해야 한다.

---

## 10. 검증 계획

Heavy 변경 표준을 적용한다.

### Backend

- OAuth state/PKCE/owner/RBAC/Workspace isolation pytest
- migration alembic dry-run 및 upgrade/rollback 검증
- 신규 3 엔티티 추가 시 `test_alembic_upgrade.py` drift gate가 실제로 누락을 검출하는지 확인한다. BL-051의 `_is_pr2_scope_drift` 필터와의 상호작용으로 alembic 누락 검출이 약화될 수 있다.
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

`docs/TODO.md` `## Blocked`의 `T-INFRA-E2E-API`는 2026-07-30 사용자 기록으로 **main 체크아웃 미커밋 working tree에만 존재하며 HEAD `7322fc8`에는 없다**. 커밋되지 않은 blocker 근거는 다른 체크아웃·CI에서 재현되지 않으므로 커밋이 필요하다. [확인 필요] 같은 사용자 관측에서 로컬 `E2E_API_URL`의 `/api/v1/health`는 404다. [확인 필요] 문서상 legacy Cloud Run URL의 `/api/v1/health`도 404다. [확인 필요] `jetaime-dev`에서 `kairos-api` 서비스는 조회되지 않는다. 이 관측은 저장소 정적 검증으로 재현할 수 없고, `docs/adr/024-ga-readiness.md:9` 및 `.github/workflows/deploy.yml:95-98`에는 2026-06-30 `CLERK_PROD_HARDENING=false` 게이트로 prod 백엔드 crash-loop를 복구한 반례가 있어 현재 404를 재측정 없이 단정할 수 없다. 따라서 Phase 4는 인프라 복구 후 재개한다.

### Heavy 실행 흐름

- `verify → /codex + agy 교차 검증 → /review → /qa Exhaustive → /ship → Monitor` 순서로 진행한다.
- 이 Spike는 Generator(codex)-Evaluator(claude) 루프로 `/codex 교차 검증`을 충족한다.

---

## 11. 운영·관측성

- sync run: `workspace_id`, 문서 수, 성공/실패 수, 사용자 트리거 수동 재동기화 횟수, provider error code, 총 소요 시간
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
2. **데이터 정책 결정**: 실제 권한 회수/삭제가 확인되면 외부 원본(`external_document`)의 Kairos 파생물(plain text·임베딩·캐시)을 즉시 purge한다. 이는 ADR-023 D-6.5의 부분 개정이며, 내부 소스(트랜스크립트/노트/액션)의 사용자 명시적 삭제 전 무기한 보존 원칙은 유지한다.

두 결정이 승인되기 전에는 Google OAuth credential 생성, migration, 실제 Drive API 호출을 시작하지 않는다.
