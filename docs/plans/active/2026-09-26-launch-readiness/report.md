# 전체 정검 보고서 — 실사용 준비 (2026-09-26)

> 산출물: [`checklist.md`](checklist.md) (실사용 준비 체크리스트) · [`phase2-test-list.md`](phase2-test-list.md) (Gate 0 수정 후 재테스트 리스트) · [`decisions-log.md`](decisions-log.md) (판정 불일치 기록) ·
> [`generator-scenarios.json`](generator-scenarios.json) (설계 시나리오 217 + 문서 주장 45) · [`probe-results.log`](probe-results.log) (라이브 탐침 원본) · [`doc-drift-e3.json`](doc-drift-e3.json) (문서 45건 판정)

## 0. 한 줄 결과

**외부 사용자를 받기 전에 권한 누수 P0 4건을 먼저 고쳐야 한다.**
네 건 모두 원인이 같다. 회의를 private 프로젝트에 연결해도 그 회의에서 파생된 데이터(RAG 청크·인박스 요약·추출 액션)는 가려지지 않는다.
연결 API 에도 가시성 검사가 없다. 인증·테넌트 격리·역할 게이트·cross-tenant 차단은 표본 재검증까지 모두 통과했다.

| 구분 | 건수 |
|---|---|
| 확정 결함 | P0 **4** · P1 **3** · P2 **11** · P3 **11** (+ 운영 갭은 체크리스트) |
| 반증·철회 | 2 (C-005, G3-020 Ctrl+K) |
| 문서 주장 45건 | ACCURATE 0 · STALE 34 · MISLEADING 10 · MINOR 1 |
| 라이브 탐침 | 111줄 — PASS 90 · FAIL 16 · CHECK 3 (+ 형식 예외 2줄은 PASS) |
| PASS 표본 재검증 | 12건 — 거짓 PASS 0 |

## 1. 방법

- **Generator 3개** (읽기 전용 서브에이전트): 문서와 코드를 읽고 시나리오 217개를 설계했다 (P0 34 · P1 92 · P2 75 · P3 16). 영역은 접근·권한 / 콘텐츠 파이프라인 / 탐색·UX·문서다.
- **실행** (메인 세션, 직렬): Playwright MCP 로 UI 를, 역할별 JWT 로 API 를 호출했다. UI 에서 숨겨지는지와 API 가 거부하는지를 **둘 다** 대조했다. 결과는 `QAPROBE::` 한 줄 규약으로 남겼다.
- **Evaluator 3개** (fresh context, 브라우저 없음): Generator 의 추론은 빼고 주장·재현 절차·증거 경로만 넘겼다. 각자 코드 추적과 curl/psql 재현으로 판정했다.
  - E1: 권한·파이프라인
  - E2: UX·인증·인프라
  - E3: 문서·운영
- **codex 교차검증**: P0/P1 7건을 `codex exec -s read-only` 로 검증했다. 코드는 줄 번호를 붙여 inline 으로 넣었다. 불일치 2건은 메인이 증거로 판정했다 (`decisions-log.md`).
- **계정 6개** (`@kairos.test`):
  - QA Team: owner · admin · member · viewer
  - outsider: 별도 팀 WS 소유자
  - newbie: 신규 가입자
  - 비밀번호는 scratchpad 에만 두었다.

## 2. 기준선

| 항목 | 값 |
|---|---|
| 코드 | `main` **1d2eac0** (PR #194) |
| 로컬 스택 | `pnpm build && pnpm start` (production 모드) · uvicorn 단일 프로세스 · `pgvector/pgvector:0.8.0-pg17` 격리 컨테이너 `kairos-qa-db:5436` · alembic head `c1a7e0b5d3f2` |
| 외부 API | 실제 Gemini `gemini-3.1-flash-lite` · OpenAI whisper-1 / text-embedding-3-small · R2 (합성 음성 21.5초 1건) |
| 프로덕션 | `kairos.woosung.dev` / `kairos-api.woosung.dev` — **로그인 없는 공개 GET 만**. **프로덕션은 #194 이전 빌드다** (OPS-2: BE 405 vs 로컬 401, FE CSP-Report-Only 헤더 부재) |

## 3. 커버리지

### 3.1 라우트 × 역할 (23 라우트)

`/dashboard` `/inbox` `/actions` `/notes` `/notes/{public·private·draft}` `/new` `/meetings/{3종}` `/projects` `/projects/{public·draft·private}`
`/search` `/memory` `/settings?tab={members·invites·general·integrations·audit}` `/admin/recall-metrics`

| 역할 | 방문 | console.error | 비고 |
|---|---|---|---|
| owner | 23/23 | 0 | founder 라우트 렌더 |
| admin | 23/23 | 0 | founder 라우트 "접근 권한 없음", 연동 탭 없음 + 폴백 |
| member | 23/23 | 0 | Gamma(프로젝트 멤버)·Beta(본인 draft) 보임 |
| viewer | 23/23 | 0 | private/draft 404, `/new` 차단 |
| outsider | 9 ID 탐침 | 0 | QA Team 리소스 전부 404/403 |
| newbie | 온보딩 1·2회차 + 초대 수락 3회 | 0 | 툴팁 1회성 확인 |
| member @375px | 13/13 | 0 | scrollWidth 375, BottomNav 있음 |

### 3.2 시나리오 실행률

- P0/P1 126개 중 94개는 ID 로 실행 기록이 있다 (탐침 로그 + 후보 증거로만 남긴 G2-021~028, G3-012/013/015).
- ID 기록이 없는 32개 중 18개는 이름이 다른 탐침이 같은 경로를 덮었다. 예: G1-016~018 → AUTH-RATELIMIT, G3-050~054 → PROD-* 탐침.
- **실제로 남은 것은 14개다** (미실행 8 · 부분 실행 6). 목록과 매핑은 [`phase2-test-list.md`](phase2-test-list.md) §5 에 있다.
- P2/P3 91개 중 실행 3개. **이번 정검은 P0/P1 중심이다.**

## 4. 확정 결함

판정 열:
- **E**: Evaluator (E1/E2)
- **cx**: codex
- **최종**: 메인 판정. 불일치 사유는 `decisions-log.md`

### P0 — 권한 밖 데이터 노출 (4)

| ID | 결함 | 근거 | E / cx / 최종 |
|---|---|---|---|
| **C-014** | 회의를 private 프로젝트에 **수동 연결하거나 인박스 확정으로 연결**해도 `embedding_chunks.project_id` 가 NULL 로 남는다. 비멤버 viewer 의 RAG 답변에 그 회의 내용이 나온다. 같은 viewer 가 회의 상세를 열면 404 다. | 청크 project_id 는 파이프라인 자동 확정 때만 설정된다 (`meetings/pipeline_service.py:141-155`). NULL 은 필터를 통과한다 (`common/visibility.py:154-157`). 링크 경로는 청크를 갱신하지 않는다 (`projects/service.py:310-337`, `inbox/service.py:122-125`). 라이브: viewer 가 cached=false 로 받은 답에 "10월 20일" 포함 | P0 / P0 / **P0** |
| **C-015** | `GET /inbox` 에 가시성 필터가 없다. viewer 가 private 프로젝트 회의의 AI 요약 원문을 받는다. 응답의 `sourceId` 는 C-018 에 필요한 회의 id 도 알려준다. | `inbox/router.py:19-33` → `inbox/service.py:59-76` → `inbox/repository.py:27-39` (워크스페이스·is_processed 만 거름) | P0 / INSUFFICIENT→증거 보강 / **P0** |
| **C-016** | 회의에서 추출된 액션은 project_id 가 NULL 로 저장되고, 목록 필터가 NULL 을 통과시킨다. viewer 가 private 회의의 액션을 본다. 원인은 BL-UX-8 과 같지만 보안 영향은 등재되지 않았다. | `pipeline_service.py:86-101`, `actions/repository.py:63`, `visibility.py:141-146`. 라이브: viewer 목록에 Gamma 회의 액션 2건 | P1 / P0 / **P0** |
| **C-018** | `POST/DELETE /meetings/{mid}/projects` 가 테넌트만 검사한다. member 가 (a) 숨겨진 회의의 private 연결을 끊거나 (b) 그 회의를 아무 public 프로젝트에 연결하면, 회의 전문이 전 멤버에게 공개된다. 필요한 회의 id 는 C-015 와 C-016 에서 이미 노출된다. | `projects/router.py:193-214` (require_member), `projects/service.py:310-337`. E1 라이브: POST 201 → member·viewer GET 200 | P0 / P0 / **P0** |

**공통 수정 방향**
- 회의 가시성 규칙(`meetings._meeting_visibility_filter`: 링크 0개면 통과, 접근 가능한 링크가 1개라도 있으면 통과)을 청크·인박스·액션에도 똑같이 적용한다. 청크 컬럼을 동기화하는 방식보다 이쪽이 N:M 구조에 맞다.
- 링크 변경 API 는 요청자가 그 회의와 대상 프로젝트를 모두 볼 수 있을 때만 허용한다.

### P1 (3)

| ID | 결함 | 근거 | E / cx / 최종 |
|---|---|---|---|
| **C-002** | AI 가 **새 프로젝트**를 제안하고 신뢰도가 임계값 이상이면, 인박스 항목을 `is_processed=true` 로 저장하면서 링크는 만들지 않는다. 그래서 인박스에서 사라지고 회의는 미연결로 남는다. UI 에는 회의를 프로젝트에 연결하는 다른 경로가 없다 (FE `addMeetingProject` 는 PUT 을 보내고 BE 는 POST 만 받으며, 호출부도 0개). | `pipeline_service.py:125-135`, `features/inbox/components/smart-inbox.tsx:47-49`, `features/projects/api.ts:87-97` | P1 / DISAGREE P2 (FE 미제공) / **P1** |
| **C-017** | member 가 볼 수 없는(GET 404) 프로젝트를 `PATCH` 로 수정할 수 있다 (title·description·`status=archived`). admin 전용 `/archive` 를 우회하고, status 에 임의 문자열도 저장된다. 빈 PATCH 로 메타데이터를 읽을 수도 있다. 단 프로젝트 UUID 를 알아야 한다. | `projects/router.py:105-124`, `projects/service.py:251-279`, `projects/schemas.py:22-27` | P1 / P0 / **P1** |
| **C-020** | Memory recall 과 `GET /memory/{id}` 가 워크스페이스 범위다. 팀 WS 에서 admin 이 캡처한 "개인 메모"(치과 예약·비밀번호 힌트)를 viewer 가 원문까지 읽는다. 그런데 문서 8곳은 "개인 메모리 레이어" 라고 서술한다 (`memory/CONTEXT.md:13`, `prd.md:157,496` 등). | `memory/router.py:90-122`, `memory/service.py:235-316` | P1 / P0 / **P0** — 2026-09-27 사용자 결정 (a) 작성자 전용으로 P0 확정 |

### P2 (11)

| ID | 결함 | 근거 |
|---|---|---|
| C-001 | 초대 수락 직후 활성 WS 가 수락한 WS 가 아니라 목록 첫 WS 가 된다. 조건은 브라우저 저장소의 소유자 값이 비었을 때다. 대조 실험: 빈 브라우저 FAIL, 앱을 쓰던 브라우저 PASS. | `invite/[code]/page.tsx:34-39`, `panel-layout.tsx:62-92`, workspace store `ensureOwner:42-47`, `workspaces/repository.py:35-41` (ORDER BY 없음) |
| E2-X01 | 초대 페이지에는 "로그인하고 참여" 버튼만 있다. 가입 화면으로 전환하면 `callbackURL` 이 버려져, **계정 없는 첫 초대자**는 가입 뒤 초대 페이지로 돌아오지 못한다. (E2 는 P3, 메인이 P2 로 상향) | `invite/[code]/page.tsx:176`, `auth-form.tsx:201-205` |
| C-003 | 분류기 후보가 요청자 없이 조회돼 **public 프로젝트만**(최대 20개) 들어간다. private/draft 는 추천되지 않고, archived/completed 도 후보에 섞인다. | `pipeline_service.py:70`, `projects/repository.py:48-66`, `visibility.py:122-123` |
| C-004 | 회의 생성·캡처 API 와 `/new` 에 projectId 가 없다. 생성 순간부터 워크스페이스 전체에 공개된다. | `meetings/schemas.py:9-36`, `app/(app)/new/page.tsx` |
| C-011 | 프로덕션 두 호스트가 평문 HTTP 로 200 을 준다 (https 리다이렉트 없음). HSTS 도 없다. http 로 연 로그인 폼은 비밀번호를 평문으로 보낸다 [가정: 프로덕션 POST 미검증]. | `curl -sI http://kairos.woosung.dev/` |
| C-019 | 프로젝트 멤버 목록이 프로젝트 GET 이 404 인 사용자에게 200 을 준다. 숨겨진 프로젝트가 존재하는지 알려주는 오라클이 된다. | `projects/router.py:130-138`, `projects/service.py:171` |
| C-022 | RAG 캐시 키가 `sourceType` 을 무시한다. note 필터로 만든 답이 meeting 필터 질문에 cached=true 로 나온다. | `rag/service.py:74-83`, `embeddings/repository.py:348-370` |
| C-023 | 회의 처리가 실패하면 `errorMessage=str(e)` 가 그대로 저장되어 viewer 이상에게 반환된다. 실측 값에 R2 계정 endpoint·버킷명·access key id·1시간 서명 URL 이 들어 있었다. UI 는 표시하지 않는다. promote 하면 대상 WS 로도 복제된다. | `pipeline_service.py:247-251,305-309`, `meetings/service.py:241,307,511` |
| C-026 | 노트 편집 후 자동저장 디바운스(1초) 안에 페이지를 떠나면 편집 내용이 유실된다. 대조군(2.5초 대기)은 저장된다. | `note-detail.tsx:88-94` (unmount 에서 flush 없음), beforeunload 0건 |
| C-027 | 인박스 "확정" 직후의 "되돌리기" 는 로컬 상태만 바꾼다. 서버의 분류는 그대로 남는다. 자동처리 분기의 "되돌리기" 는 실제로는 "무시" 다. | `inbox-item-card.tsx:137-139,153-186,398-416` |
| E1-N1 | 노트를 만들고 곧바로 삭제하면 백그라운드 임베딩이 뒤늦게 청크를 삽입해 **고아 청크**가 남고, RAG 소스로 등장한다 (3/3 재현, 6초 뒤 삭제한 대조군은 0). | `notes/router.py:87-108`, `notes/pipeline_service.py:45-70` |

### P3 (11)

| ID | 결함 |
|---|---|
| C-006 | 접근 불가 회의에서 "잠시 후 다시 시도" 문구가 뜨고 404 를 1회 재시도한다 (`meetings/hooks.ts:46` 이 전역 4xx no-retry 규칙을 덮어씀). 노트는 원인을 구분하지 않는 문구다. |
| C-007 | member/viewer 가 `?tab=audit` 로 들어오면 선택된 탭 없이 권한 안내 패널만 뜬다 (`settings/page.tsx:83-87`). |
| C-008 | RAG 캐시가 요청자 권한을 키에 넣지 않는다. 낮은 권한 사용자가 만든 답이 높은 권한 사용자에게 제공된다. **반대 방향 누수는 없다**. |
| C-009 | Better Auth rate limit 의 IP 판정 설정(`advanced.ipAddress`)이 없다. XFF 가 여러 값이면 공유 버킷에 묶인다. 프로덕션 영향은 좁은 DoS 다 [가정: Cloudflare 가 XFF 끝에 실제 IP 를 붙임]. |
| C-010 | `/new` 온보딩 툴팁이 한 번도 연결된 적이 없다 (정의만 있음). `/search` 는 설계대로 ⌘K 팔레트에 붙어 있다. |
| C-012 | 프로덕션 `/robots.txt`, `/sitemap.xml` 이 `/sign-in` 으로 307 된다. robots.ts·sitemap.ts 자체가 없다. |
| C-013 | `x-powered-by: Next.js` 가 노출된다. CSP 는 Report-Only 이고 그마저 프로덕션에는 미배포다. |
| C-021 | `/memory/metrics` 가 viewer 이상에게 열려 있다 (FE 는 founder 전용). 노출은 집계 숫자 5개뿐이다. |
| C-024 | 중복 가입 시 영어 원문 "User already exists. Use another email." 가 뜬다 (`auth-form.tsx:42` 매핑 누락, `:48` 이 원문을 fallback 으로 씀). |
| C-025 | FastAPI 422 의 detail 배열이 "[object Object]" 로 표시된다 (`lib/api-client.ts:53`). 이모지 25자는 FE 에서 50자로 세어 통과하고 BE 에서는 25자라 422 가 난다. 같은 증상이 나는 화면은 약 4~5곳이다. |
| C-028 | 같은 회의를 두 번 promote 하면 사본이 2개 생긴다. 회의 삭제 기능이 없어 사용자가 지울 수 없다 (BL-UX-4). |

### 관찰 (결함 아님 · 기지 항목 재현)

- BL-UX-8 을 재현했다: 추출 액션 11건 전부 `projectId` null 이고 담당자도 null 이다. 그래서 "내 액션만" 필터는 항상 0건이다.
- 화자 분리가 없다: 모든 segment 가 `speaker="Speaker"` 다. 문서 4곳이 pyannote 가 있다고 적었다 (D-007/D-008).
- member 는 private/draft 프로젝트를 직접 만들 수 있지만, 나중에 visibility 를 바꾸는 것은 admin 이상만 된다. → **2026-09-27 결정 (U-4)**: 작성자는 role 과 무관하게 자기 프로젝트 visibility 를 바꿀 수 있다. Gate 0 수정에 포함.

## 5. 반증·철회된 후보

| ID | 원래 주장 | 결론 |
|---|---|---|
| C-005 | 분류기가 존재하지 않는 프로젝트 id 를 만들어냈다 | 철회. `5adcc865` 는 W-5 시드 "📋 회의록" 이다 |
| G3-020 | Ctrl+K 로 팔레트가 안 열린다 | 반증. 측정 셀렉터 오류였다 (팔레트에 `role=dialog` 가 없음). 스크린샷으로 열림 확인 |

그 밖의 메인 초기 주장 4건은 Evaluator 가 **정정**했다 (C-001 정렬 원인, C-006 노트 범위, C-009 XFF 부재 시 동작, C-010 /search). 정정 내용은 `decisions-log.md` 에 있다.

## 6. 문서 드리프트 (E3, 45건)

**영향 큼 (3)**
- **D-001 / D-002** — `docs/operations/r2-cleanup-cron.md:8` 과 `docs/TODO.md:109`(BL-OCI-5) 는 `r2-cleanup.yml` 을 "고아 정리" 수단으로 안내한다.
  - 실제로 `scripts/r2_cleanup.py:64-97` 은 DB 참조를 보지 않고 `uploads/` 아래 **나이만으로** 전부 지운다. 안내대로 `delete=true` 로 실행하면 30일 넘은 **살아 있는 회의 원본까지** 삭제된다. 실행 이력이 0건이라 지금까지 피해는 없다.
  - 반대로 voice 메모 30일 TTL 은 실행 수단이 전혀 없다 (`POST /admin/memory/r2-cleanup` 호출부 0).
- **D-038** — ADR-031 컷오버 +7일(2026-08-24) 정리 작업이 34일째 밀려 있다: `clerk_id` DROP, 서버 `.env` 의 CLERK_* 제거, Clerk dev 인스턴스 삭제. 레포는 PUBLIC 이다.

**MISLEADING 나머지 (7)**
- D-004/005: RAG Layer 0 거부는 SSE 시작 전이 아니라 "200 + 스트림 안 error 이벤트" 로 온다
- D-007/008: pyannote 서술
- D-010: 모델 고정 위치가 config 가 아니라 상수 2곳에 중복
- D-011: memory·*PromoteOut 11개 스키마가 snake_case
- D-013: deploy-preflight 가 회의 처리만 센다
- D-041: ⌘K 는 명령 팔레트다

**STALE (34)** — 주로 세 묶음이다. 항목별 근거·정정 문구는 [`doc-drift-e3.json`](doc-drift-e3.json) 에 있다.
- 이미 해소됐는데 백로그에 남은 항목 (BL-S27c-1/3/5/6/7, BL-073, BL-F5/F7, S15-T1~T4, S16-T1~T6)
- Cloud Run·Neon·Sentry 전제
- 숫자 드리프트: FE features 16→17 이다. 이 숫자는 AGENTS.md 를 통해 모든 세션에 들어간다. 그 밖에 pytest 126, vitest 41, web 메모리 768m.
- 실제 장애로 이어지는 항목: **D-016** — `deploy/oci/README.md` 의 수동 빌드 명령에 Google `--build-arg` 2개가 빠져 있다. 그대로 빌드하면 Picker 만 조용히 죽는다.

## 7. 정리 · 잔여물

- **R2 업로드 1건** (공유 버킷 `nexus-core-storage`, 사용자가 삭제):
  `uploads/a3e294c1-2835-46e7-bca5-c810e9835c75/beta-meeting.m4a`
  promote 사본 2건은 같은 키를 공유하므로 추가 객체가 없다.
- **로컬 DB** `kairos-qa-db` 는 다음 QA 재사용을 위해 유지한다. 초기 QA 가 남긴 고아 청크 3건('QA-TMP note')이 로컬 DB 에만 남아 있다.
- **프로덕션 변경 0건** (GET 만). Neon 접촉 0건.
- 스크린샷은 `.playwright-mcp/qa-2026-09-26/shots/` 에 있다 (gitignored).
