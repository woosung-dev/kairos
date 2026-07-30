# ADR-026 — 외부 소스 ingest 레일 v0 — Google Drive를 첫 provider로

**Status**: Accepted  
**Date**: 2026-07-30  
**관련**: `docs/requirements/prd.md` §3.6 X축 v3/v5 · ADR-014 (orchestrator 진입 권한 검증) · ADR-020 (I-20/I-21) · ADR-023 D-6.4/D-6.5 · ADR-024 (부팅 차단형 validator 교훈) · ADR-025 (4단계 역할 위계) · `CONTEXT-MAP.md` I-2/I-9/I-13/I-15/I-20/I-21  
**부분 개정 대상**: ADR-023 D-6.5 — supersede가 아닌 `external_document` 예외 조항 추가

---

## 배경 (Context)

Kairos의 현 원본은 회의·노트·메모 중심이다. PRD §3.6 X축의 v3 Slack과 v5 웹·이메일은 외부 원본, OAuth 연결, 비동기 sync-run과 검색 가능한 청크라는 공통 기반을 요구한다. 이 ADR은 그 공통 기반을 가장 좁은 형태로 검증하기 위한 v0를 확정한다.

따라서 이는 Google Drive 기능 일반화가 아니라 **외부 소스 ingest 레일 v0**이다. Google Drive는 사용자가 Google Picker로 명시 선택한 Google Docs만 다루는 가장 얇은 첫 provider다. 명분은 로드맵이지만, 코드는 단일 구현이어야 한다. 즉 `integrations` 도메인 내부에 provider abstraction을 도입하지 않으며, 두 번째 provider가 실제로 생길 때만 추상화를 검토한다.

W0의 미해결 갭 중 G1은 Picker가 요구하는 브라우저 토큰 모델, G2는 `source_type` 화이트리스트의 검증 경로다. 본 ADR이 두 갭을 결정한다. 실 Google API 호출이 없는 Wave 1(문서·ADR)과 BE thin slice(암호화·모델·마이그레이션·파이프라인·fixture 기반 contract test)는 인프라 복구와 무관하게 진행할 수 있지만, Phase 4 완료와 Go/No-Go 판정은 Google Cloud OAuth client 생성 및 E2E API 인프라 복구 두 blocker가 해소된 뒤에만 가능하다. E2E API blocker는 [확인 필요] `docs/TODO.md` `## Blocked`의 `T-INFRA-E2E-API`가 main 체크아웃 미커밋 working tree에만 존재하는 2026-07-30 사용자 기록이므로, 다른 체크아웃·CI에서 재현되려면 커밋이 필요하다. 이 ADR은 그 환경 관측을 사실 판정하지 않는다.

## 결정 (Decision)

### D1. 프레이밍과 구현 범위

- 이 결정은 PRD §3.6 X축 v3(Slack) / v5(웹·이메일)가 요구하는 공통 인프라의 v0다.
- Google Drive는 가장 얇은 첫 provider이며, `integrations` 도메인 내부는 Drive 단일 구현으로 유지한다.
- provider abstraction은 도입하지 않는다. 두 번째 provider가 실제로 구현 범위에 들어올 때에만 재검토한다.
- 이 긴장은 의도적이다. **명분은 로드맵, 코드는 단일 구현**이다.

### D2. OAuth scope와 읽기 전용 경계

- Google OAuth는 `drive.file`만 요청한다. `drive.readonly`를 포함한 광역 scope는 금지한다.
- 데이터 흐름은 Drive → Kairos 단방향 읽기 전용이다.
- 원문 편집, Drive 권한 변경, 양방향 sync는 v0 범위에서 영구 제외한다.
- scope 선택 근거는 [Google Drive API-specific auth guide](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)를 따른다.

### D3. Drive ACL과 Kairos 발행의 권한 경계

Drive에서 문서를 볼 수 있음과 Kairos에 팀 지식으로 발행함은 다른 사건이다. Kairos는 Drive ACL을 실시간으로 미러링하지 않는다.

- import 실행자는 Workspace owner로 한정한다. 라우터에서 `backend/src/auth/rbac.py:132`의 `require_owner`로 강제하며, service 계층에 같은 권한 검사를 중복하지 않는다. 이는 `backend/src/workspaces/service.py:118`의 owner 전용 작업 관례와 같다.
- `require_owner`는 admin/owner gate의 15초 in-process 멤버 캐시를 bypass하고 DB fresh 조회를 수행한다(`rbac.py:24-36`, `:105-113`). 따라서 강등된 역할이 캐시 stale 상태로 import·연결 해제 같은 파괴적 작업을 통과하지 못한다.
- 발행된 문서는 대상 Project의 `public` / `draft` / `private` visibility를 그대로 따른다. RAG visibility 필터를 우회하는 별도 권한 모델은 만들지 않는다. admin/owner의 private bypass는 ADR-023 D-6.4의 기존 동작을 유지한다.
- Project를 선택하지 않은 문서는 기본 RAG 제외 상태로 만든다. Workspace 전체 검색 포함은 owner의 별도 확인이 있어야 한다.

### D4. 지원 문서 유형

- v0는 Google Docs의 `text/plain` export만 지원한다.
- PDF, Google Sheets, Google Slides, 이미지 및 OCR은 제외한다.
- unsupported MIME은 조용히 건너뛰지 않는다. 문서별 `failed` 상태와 사유를 남긴다.
- export 제약은 [Google Workspace export formats](https://developers.google.com/workspace/drive/api/guides/ref-export-formats)와 [files.export](https://developers.google.com/workspace/drive/api/reference/rest/v2/files/export)를 따른다.

### D5. Google Picker 2-토큰 모델 (G1 해결)

이 항목은 Spike의 최대 기술 리스크다. 서버 토큰과 브라우저 토큰을 분리하고, **같은 OAuth `client_id`**를 사용한다.

| 구분 | 서버 토큰 | 브라우저 토큰 |
|---|---|---|
| 획득 | authorization code flow (offline access) | Google Identity Services `initTokenClient` |
| 종류 | refresh token과 파생 access token | access token만, 약 1시간 |
| 저장 | 암호화한 `IntegrationConnection.encrypted_refresh_token` | 메모리 전용 |
| 용도 | `files.get`, `files.export` 등 모든 Drive API 읽기 | Picker 열기 전용 |
| 노출 | 서버 밖으로 절대 나가지 않음 | 브라우저 안에만 존재 |

강제 규칙은 다음과 같다.

- 브라우저 access token은 `localStorage`, `sessionStorage`, cookie, Zustand `persist`에 저장하지 않는다. 메모리 변수만 사용한다.
- 브라우저 토큰을 Kairos 백엔드로 전송하지 않는다. backend POST 본문에는 Picker가 반환한 `fileId[]`와 최소 메타데이터만 넣는다.
- refresh token은 API 응답, SSE, 프론트엔드 state, Sentry, 애플리케이션 로그에 절대 넣지 않는다.
- `drive.file`은 앱과 파일 단위 grant다. 브라우저가 **동일 `client_id`** 토큰으로 Picker를 열고 사용자가 파일을 선택하면, 해당 grant가 그 OAuth client에 기록된다. 같은 `client_id`와 같은 사용자의 서버 refresh token으로 그 파일을 읽는다. 따라서 서버와 브라우저의 `client_id` 동일성은 이 설계의 필수 불변식이다.
- `frontend/next.config.ts:5`는 현재 CSP를 의도적으로 SKIP한 상태이므로 명시적 CSP 설정은 없다. Picker 도입 시 CSP를 함께 도입·개정하여 `script-src`에 `https://apis.google.com`(Picker loader)과 `https://accounts.google.com`(GIS)을 허용한다.
- 브라우저 토큰 획득에 실패하면 서버 상태 변화는 0이다. Picker를 열지 못할 뿐 connection, sync run, 문서의 부분 상태를 만들지 않는다.

### D6. `source_type` 화이트리스트와 임베딩 경로 (G2 해결)

Drive 임베딩 경로는 검증하는 메서드를 사용한다.

- `backend/src/embeddings/repository.py:17-19`의 `_ALLOWED_SOURCE_TYPES`에 `external_document`를 추가한다. (2026-07-30 기준 등재값: `meeting`, `note`, `action`, `inbox`, `memory` — 이 중 `action`/`inbox`는 등재만 되어 있고 실제 `EmbeddingChunk` insert가 없다.)
- Drive 청크 저장은 assert가 있는 `save_chunk`(`:61-75`, `:91-93`)만 경유한다. Meeting/Note가 사용하는 `save_chunks`(`:55-59`)는 `source_type` 검증을 우회하므로 Drive에 사용하지 않는다.
- 새 코드는 검증된 경로를 타야 하며, 단건 assert 비용은 무시할 수 있다. `external_document` 등재는 의도적인 source 추가의 증거가 된다.
- `save_chunks`의 검증 우회 자체는 이 Spike에서 고치지 않는다. Meeting/Note hot path 변경은 범위 밖이며, 후속 BL로 등재한다.
- 화이트리스트 등재 ≠ 실제 writer라는 선례를 인정한다(`backend/src/inbox/service.py:9`).
- `chunk_level=2`를 준수한다. RAG 검색 대상은 L2뿐이며, vector/text 검색의 SQL 필터도 이를 강제한다(`backend/src/rag/CONTEXT.md` R-1, `backend/src/embeddings/repository.py:206`, `:266`).
- `EmbeddingChunk.embedding`의 기존 `halfvec(1536)`을 재사용한다. 신규 벡터 컬럼은 만들지 않으므로 I-20을 자동 충족한다. 검색은 R-13/I-21의 `_apply_hnsw_session_params` 경로를 경유한다.

### D7. ADR-023 D-6.5의 부분 개정 — 외부 원본 데이터 생명주기

ADR-023 D-6.5의 내부 텍스트 보존 원칙을 supersede하지 않는다. 다음 예외 조항을 추가하는 **부분 개정**으로 처리한다. ADR-023 원문 파일의 실제 수정은 W2 담당이다.

- 외부 원본(`external_document`)은 예외다. 원본의 삭제, 휴지통 이동, 실제 접근 권한 회수가 **확인되면** Kairos의 추출 plain text, 임베딩 청크, 관련 `SemanticCache`를 즉시 제거한다.
- 내부 소스(트랜스크립트/노트/액션)는 Kairos가 원본 보유자이므로 사용자 명시적 삭제 전 무기한 보존한다. 이 원칙은 변경하지 않는다.
- 외부 원본은 Drive가 source of truth다. 원본 접근 권한이 사라진 뒤 Kairos 사본을 보존하면 권한 회수가 무의미해져 보안 결함이 된다.

판정은 **권한 회수·삭제가 확인된 경우에만 purge를 허용하는 fail-closed 규칙**으로 한다. 확인하지 못한 오류는 삭제하지 않고 상태를 보존한다.

| 관측 | 조치 |
|---|---|
| 실제 권한 회수 또는 삭제 확인 | purge |
| 429, 5xx, network timeout, circuit open | 삭제 금지, `stale` 표시, `last_synced_at` 노출, 사용자 수동 재동기화 가능 상태 유지 |
| 401/403 | 세부 reason을 판별한다. 상태 코드만으로 purge하지 않는다. reason을 판별할 수 없으면 `reauth_required`로 보류하고 삭제하지 않는다. |

### D8. 자동 retry 배제와 circuit breaker 재사용

- `backend/src/services/ai_resilience.py:10-12`의 자동 retry 배제 결정을 유지한다. 자동 retry는 외부 장애 중 비용을 증폭할 수 있다.
- 재동기화는 사용자 트리거 수동 endpoint로만 제공한다. 회의 실패도 사용자 재시도 트리거로 처리하는 현재 원칙을 따른다(`backend/src/meetings/CONTEXT.md` M-3). [확인 필요] W1 입력이 관례로 가리킨 `backend/src/meetings/router.py:145`는 이 체크아웃에서 promote route이므로, retry endpoint의 정확한 라우터 위치는 W2 구현 전에 다시 확정한다.
- `ai_resilience.py:40-137`의 vendor-agnostic `_CircuitBreaker`를 그대로 재사용한다. 같은 파일에 `drive_breaker = _CircuitBreaker("google_drive")`와 `with_drive_timeout()`을 추가한다. 별도 circuit-breaker 유틸은 만들지 않는다.
- `tenacity`와 `backoff` 의존성은 추가하지 않는다.

### D9. 이 결정이 요구하는 헌법·문서 개정

아래 실제 개정은 W2 담당이다.

1. `CONTEXT-MAP.md` I-13: Workspace prefix 예외 목록에 고정 OAuth redirect URI인 `/api/v1/integrations/google-drive/callback`을 추가한다. 2026-07-30 기준 기존 예외는 `/api/v1/users`, `/api/v1/feedback`다. Google Cloud Console에 사전 등록하는 고정 경로에는 `workspace_id`를 경로로 넣을 수 없으므로, 서명된 state에 `workspace_id`, 요청자 ID, nonce, PKCE, 만료를 넣어 검증해 격리를 보전한다.
2. `CONTEXT-MAP.md` §4.1: 백엔드 모듈 목록에 `integrations`를 추가하고 헤더의 모듈 수를 함께 갱신한다. 2026-07-30 기준 헤더는 16개다.
3. `backend/src/rag/CONTEXT.md`: 현재 없는 `source_type` 규칙을 신설한다. `external_document` 검색 허용과 화이트리스트 SSOT 위치를 명시한다.
4. `backend/src/integrations/CONTEXT.md`: 새 도메인 컨텍스트를 작성한다.
5. `docs/adr/023-second-brain-context-boundaries.md` D-6.5: D7의 `external_document` 예외 조항을 추가한다.
6. `docs/api/endpoints.md`, `docs/architecture/erd.md`: 신규 endpoint와 엔티티를 기록한다.

### D10. 보안 config와 ADR-024 교훈

다음 키를 도입한다: `INTEGRATIONS_ENCRYPTION_KEY`(Fernet), `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_PICKER_API_KEY`.

- `Settings`에는 `SecretStr`로 선언해 I-15를 따른다.
- `backend/src/core/config.py`에서 재사용하는 것은 `_is_non_dev_env`와 `_enforce_or_warn` 두 개뿐이다.
- 신규 작성하는 Fernet 키 전용 validator는 `Fernet(key)` 생성을 시도한다. 성공하면 유효한 키로, `ValueError`가 발생하면 무효한 키로 처리한다. 이 방법은 길이와 urlsafe-base64 유효성을 함께 검증한다.
- `_validate_cron_token`의 32 byte 최소 길이 규칙은 cron token 전용이며 Fernet 키에는 적용하지 않는다. 현재 Fernet validator는 없으므로 위 validator를 새로 작성한다.
- 그러나 새 integration key validator는 부팅을 차단하지 않는다. 누락·약한 값은 **loud warning + alert**로 남긴다. ADR-024 Status update가 기록한 2026-06-30 부팅 차단형 validator의 prod crash-loop 사고를 재발시키지 않는다.
- 현재 `.github/workflows/deploy.yml:99-113`은 `env_vars:`로 값을 주입하고 `--set-secrets`를 쓰지 않는다. Secret Manager 이관은 `docs/adr/008-devex-initiative.md:43`의 미완 항목이므로, v0 키 주입은 현행 `env_vars` 경로를 사용하고 이관은 ADR-008 후속으로 남긴다. 존재하지 않는 KMS 또는 Secret Manager를 전제하지 않는다.
- 새 키 추가 시 `backend/.env.example`, `backend/src/core/config.py`의 `Settings`, `.github/workflows/deploy.yml` `env_vars`를 동시에 갱신한다.

### D11. Go/No-Go에 인프라 재사용성 추가

W0 계획의 가설은 Drive 가치뿐 아니라 v3 Slack과 v5 웹·이메일에 재사용할 ingest 인프라의 타당성을 검증한다. 따라서 W2에서 §8 Go 기준에 다음 항목을 추가한다.

> 두 번째 provider(Slack ingest)를 가정했을 때 `integrations` 도메인의 모델, sync-run, 상태 전이, 암호화 연결 중 재작성 없이 재사용 가능한 부분이 과반이며, provider-specific 코드는 `GoogleDriveClient`와 export/MIME 처리에 국지화되어 있다.

이 기준의 실제 계획서 수정은 W2 담당이다.

## 근거 (Rationale)

1. **최소 권한과 명시 발행**: `drive.file`과 owner-only import를 결합해 광역 Drive 탐색이나 자동 공개 없이 제품 가설을 검증한다. Project visibility는 기존 RBAC/visibility 경계를 재사용한다.
2. **기존 도메인 경계 보존**: `GoogleDriveSyncPipelineService`가 `integrations` 내부에서 외부 호출과 여러 write를 조율해 I-2와 ADR-014 옵션 A를 따른다. RAG는 기존 visibility 검증 뒤 검색만 수행한다.
3. **토큰 권한 분리**: Picker의 브라우저 토큰을 메모리에만 두고 서버 refresh token을 암호화 저장하면 UI 편의와 서버 API 읽기를 분리할 수 있다.
4. **검증 경로 우선**: `save_chunk`를 선택하면 새 source가 `workspace_id`, source workspace, 화이트리스트 assertion을 통과해야 한다. 기존 `save_chunks` hot path를 고치지 않아 Spike 범위를 지킨다.
5. **권한 회수의 의미 보존**: 외부 원본의 실제 권한 회수 시 파생 데이터를 지우되, 일시 장애에 purge하지 않아 데이터 유실을 방지한다.
6. **운영 단순성**: 자동 retry와 provider abstraction은 둘 다 조기 복잡도다. 수동 재동기화와 Drive 단일 구현으로 v0의 실패 면적을 제한한다.

## 결과·영향 (Consequences)

### 긍정적 영향

- 선택한 Google Docs가 기존 Meeting/Note와 같은 RAG 검색·인용 경로에 들어가면서, 외부 근거가 프로젝트 맥락을 보완하는지 측정할 수 있다.
- OAuth 연결, 외부 원본, sync-run, 상태 전이, 암호화 연결의 재사용 가능성을 두 번째 provider 가정으로 평가할 수 있다.
- owner-only 발행, 기존 visibility, 실제 권한 회수 purge가 결합되어 별도 ACL 시스템 없이 권한 경계를 유지한다.

### 제약과 위험

- Picker/GIS와 동일 `client_id` 및 CSP 변경이 필요하다. 토큰 획득 실패는 partial state 없이 실패해야 한다.
- `drive.file` grant와 Google API 오류의 세부 reason 처리를 구현·테스트해야 한다. reason 판별 불가 401/403은 `reauth_required`로 보류한다.
- 신규 Fernet 키의 누락은 경고와 alert로 관측해야 하며, 부팅 차단으로 바꾸지 않는다.
- 실 Google API 호출이 없는 Wave 1(문서·ADR)과 BE thin slice(암호화·모델·마이그레이션·파이프라인·fixture 기반 contract test)는 인프라 복구와 무관하게 진행할 수 있지만, Phase 4 완료와 Go/No-Go 판정은 Google Cloud OAuth client 생성 및 E2E API 인프라 복구 두 blocker가 해소된 뒤에만 가능하다. E2E API blocker는 [확인 필요] `docs/TODO.md` `## Blocked`의 `T-INFRA-E2E-API`가 main 체크아웃 미커밋 working tree에만 존재하는 2026-07-30 사용자 기록이므로, 다른 체크아웃·CI에서 재현되려면 커밋이 필요하다.

### 되돌리기 전략

보안 결함 또는 품질 실패 시 다음 순서로 회수한다.

1. connection을 disable한다.
2. 연결된 모든 문서를 unpublish하여 RAG에서 제외한다.
3. refresh token을 폐기한다.
4. 영향을 받은 Workspace owner에게 재연결을 요구한다.

### v0가 검증하지 않는 것

폴더, Shared Drive, Google Sheets, Google Slides, PDF, webhook, 자동 동기화, 양방향 쓰기는 검증하지 않는다. 이는 Drive 단일 구현과 최소 범위를 지키기 위한 제외이며, 후속 결정 전 v0에 추가하지 않는다.

## 헌법·문서 개정 항목

D9에 열거한 항목은 코드 구현과 같은 PR에서 W2가 갱신한다. 본 ADR은 개정 방향을 확정하는 문서이며, `CONTEXT-MAP.md`, ADR-023, RAG 컨텍스트, 엔드포인트/ERD를 이 변경에서 수정하지 않는다.

## 후속 BL

- **BL-EXT-INGEST-1**: `EmbeddingRepository.save_chunks`의 `source_type` 검증 우회를 통합한다. Meeting/Note hot path 성능과 회귀를 별도로 검증한다.
- **BL-EXT-INGEST-2**: ADR-008의 Secret Manager 이관을 완료한다. 현행 `env_vars` 주입을 `--set-secrets`로 전환한다.
- **BL-EXT-INGEST-3**: 자동 동기화를 검토한다. Drive changes API와 changes token으로 변경분을 처리하고, webhook은 변경 신호로만 사용한다. webhook 단독 운영은 금지한다.
- **BL-EXT-INGEST-4**: 두 번째 provider가 실제 범위에 들어올 때 provider abstraction 필요성을 재평가한다.

## 참고 링크

- PRD `docs/requirements/prd.md` §3.6 — X축 v3 Slack / v5 웹·이메일
- `docs/plans/active/2026-07-30-google-drive-team-knowledge-spike.md` — W0 사실 교정 계획과 G1/G2/G3
- `backend/src/auth/rbac.py:24-36`, `:105-132` — owner gate와 fresh DB 조회
- `backend/src/embeddings/repository.py:17-19`, `:55-93` — source whitelist와 검증 경로
- `backend/src/rag/CONTEXT.md` R-1/R-13 — L2 검색과 HNSW 세션 변수
- `backend/src/services/ai_resilience.py:10-12`, `:40-137` — 자동 retry 배제와 circuit breaker
- `frontend/next.config.ts:4-5` — 현재 CSP 의도적 SKIP
- [Google Drive API-specific auth guide](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
- [Google Workspace export formats](https://developers.google.com/workspace/drive/api/guides/ref-export-formats) · [files.export](https://developers.google.com/workspace/drive/api/reference/rest/v2/files/export)
