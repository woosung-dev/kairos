# Kairos TODO

> 마지막 갱신: **2026-08-16** (레포 public 전환 → Actions 복구. ADR-030 라운드 후속)
> 4 섹션 운영: Completed / Blocked / Questions / Next Actions (`AGENTS.md` §5)
> 완료 이력 정본 = `git log` + `docs/REFACTORING-BACKLOG.md`. 분할 직전 원본 = [`archive/todo-2026h1.md`](archive/todo-2026h1.md)
>
> ⚠ **아래 항목 일부는 전제가 사라졌다** — Cloud Run / Vercel / GCP / Sentry / Neon-prod 는
> ADR-028 로 철거됐다. 각 항목의 전제를 먼저 확인하고 착수한다. 정리는 다음 sprint 진입 시.

---

## Completed

현행 sprint 완료분만 여기 적는다. 지난 sprint 이력은 `git log` 와 아카이브를 본다.

- [x] **ADR-030 `apps/backend` → `apps/api` rename + docs 재구성** (2026-08-16) —
  경로 참조 168 파일, docs 3분할(development/operations/product), TODO/백로그 아카이브 분할,
  `.github` 위생, 드리프트 12건 정정. 게이트: pytest 886 / fe-build OK / contracts drift 0

---

## Blocked

> 차단 사유 + 필요한 조치를 함께 기록한다. 빈번한 질문 대신 여기 누적 후 일괄 전달.
- [x] ~~🔴 **GitHub Actions 결제 복구**~~ — **2026-08-16 해소.** 레포를 public 으로 전환해 Actions 가 복구됐다
  (public 레포는 standard 러너가 무료). 결제 자체를 고친 게 아니라 **과금 대상에서 벗어난 것**이다 —
  private 로 되돌리면 즉시 재발한다. 복구 확인: dependabot PR #163 재실행에서 `changes` success /
  `contract-check` success (그 전 5 run 은 전부 4~8초 만에 실패).
- ~~Sentry DSN 발급~~ — **2026-08-14 ADR-028 로 Sentry 자체를 제거**했다. DSN 이 한 번도 설정된 적 없어 BE·FE 모두 비활성 상태였고, 의존성·번들 비용만 지불 중이었다. 재도입 지점은 `apps/web/src/lib/track-error.ts` seam. 현재 관측은 `docker logs`.
- [ ] **외부 user 1명 실제 dogfooding** — Sprint 22 spec `git history` 12분 walkthrough.
- [x] ~~**T-3 Sprint 14 Clerk Production 인스턴스 발급**~~ — **ADR-031 로 무효.** Clerk 를 걷어냈으므로 Production 인스턴스 발급 자체가 대상이 아니다.
- [ ] **T-SEC-CLERK-ROTATE → 인스턴스 삭제로 대체** (운영자) 노출된 dev `CLERK_SECRET_KEY`(`sk_test_mvhptL…`)는 **rotation 이 아니라 Clerk dev 인스턴스 삭제**로 무효화한다 (ADR-031 종료 조건). ⚠️ "시급 아님(dev 키 + repo private)" 이라는 2026-05-29 판단은 **레포가 public 이 된 시점에 무효**다. git 히스토리 675 커밋에 키가 남아 있다. **컷오버 +7일(롤백 창 종료) 시점에 실행**한다 — 그 전에 지우면 구 이미지로 롤백할 수 없다.
- [ ] **T-CLEANUP-1** production DB 에서 `DELETE FROM users WHERE clerk_id='user_QA20260521_sentinel_test_doNotUse'` (Sprint 25 PoC 잔존 정리). ADR-031 의 `clerk_id` DROP 리비전과 함께 처리하면 자동 소멸.
- [ ] **PR #102 (Sprint 25 moonlit-sutton) ready review + squash merge** — 사용자 승인 후 main 머지
- [ ] **post-merge 배포 verify** — Cloud Run rollout 후 `POST /api/v1/users/sync` 404 응답 + `/health` 200 + `/dashboard` 회귀 0건

---

## Questions

> 사용자 결정이 필요한 항목.

- [x] ~~레포 public/private 여부~~ — **2026-08-16 public 전환 확정.** 따라서:
  - `.github/SECURITY.md` 는 형식적이 아니라 **실효**다. ★Settings → Security 에서
    **private vulnerability reporting 을 켜야** `ISSUE_TEMPLATE/config.yml` 의 advisories 링크가 동작한다
  - `ISSUE_TEMPLATE/` 3종도 존치 — 외부 제보 창구가 실제로 생겼다
- [ ] **LICENSE 선택** `[신규 · 2026-08-16]` public 레포에 라이선스가 없으면 법적으로
  "all rights reserved" 다. 공개 제품 의도와 다를 가능성이 크다. 상용화 계획과 함께 결정할 것.
- [ ] **`apps/api/tests/` flat 잔여 9개 정리 시점** — 유일하게 코드를 움직이는 정리 작업이고,
  `justfile:be-test` 와 `test.yml` 의 `--ignore` 경로를 동시 수정해야 한다.
  CI 부재 상태에서는 pytest 수집 손실이 드러나지 않아 미뤄 뒀는데, **2026-08-16 CI 복구로 그 사유가
  사라졌다.** 이동 전후 `collected N` 이 같은지 CI 가 판정해 준다 — 이제 단독 PR 로 진행 가능.

---

## Next Actions

### 운영 · 인프라 (ADR-027/028 후속)
- [ ] **BL-OCI-1** (P1) **DB 백업 자동화.** 오라클 셀프호스팅 DB 에 백업이 없다. 개발 단계라 의도적으로 제외했고, 운영 전환 시 착수한다(일 1회 `pg_dump` → R2). 그때까지 **`docker compose down -v` 금지** — `-v` 가 `db-data` 볼륨을 지운다. 현재 안전망은 Neon 원본(오라클 DB 가 그 복사본)뿐이므로 **Neon 프로젝트를 지우지 말 것.**
- [ ] **BL-OCI-2** (P3) **presigned URL 업로드 전환.** Cloudflare Free/Pro 는 요청 바디를 100MB 에서 자른다. 운영 실측 최대 파일이 5MB 라 지금은 무해하고, `MAX_UPLOAD_BYTES=90MB` + FE 사전 가드로 막아 뒀다. 100MB 초과 파일이 실제로 필요해지면 착수(약 5시간). BL-070(500MB RAM 적재)도 함께 해소된다. 2026-05 기각 사유는 "R2 버킷 CORS 미설정"이었고 여전히 미설정이다.
- [ ] **BL-OCI-3** (P3) **GitHub Actions 자동 배포.** 진입 조건 = 수동 배포 3회 연속 성공 + 컷오버 후 7일 무사고 + 장시간 오디오 1건 end-to-end 완주. GH 러너가 amd64 라 arm64 빌드에 QEMU 가 붙는 문제를 먼저 풀어야 한다.
- [ ] **BL-OCI-4** (P2) **stuck 상태 복구 경로.** `BackgroundTasks` 는 재시도가 없어 프로세스 재시작 시 진행 중이던 회의가 `transcribing`/`analyzing` 으로 영구 정지한다. 2026-08-14 에 그렇게 좌초한 8건(E2E 6 + uploading 2)을 수동 삭제했다. `just deploy-preflight` 가 최근 2시간만 검사하도록 우회했을 뿐 근본 해결이 아니다.
- [ ] **BL-OCI-5** (P3) **R2 고아 파일 정리.** 삭제된 회의의 원본이 버킷에 남는다. `r2-cleanup.yml` 은 `workflow_dispatch` 전용(cron 미설정)이라 수동 실행이 필요하다. 현재 잔여량은 수십 KB 수준이라 급하지 않다. CI 복구(2026-08-16)로 실행 가능 — `gh workflow run r2-cleanup.yml -f delete=false` dry-run 먼저.
- [ ] **BL-OCI-6** (P2) **dev 와 prod 가 같은 Neon DB(`neondb`) 를 쓰고 있었다.** 로컬 개발이 운영 데이터를 직접 건드리는 구조. 오라클 이전으로 prod 는 분리됐지만 로컬 개발 DB 분리는 미해결.
- [ ] **BL-ADR027-OASDIFF** (P3) OpenAPI breaking-change 게이트(oasdiff). 트리거: 외부/모바일 API 소비자 첫 등장. 현재는 FE·BE 가 같은 PR 원자 변경 → `api.gen.ts` diff + FE typecheck 이 그 역할 대행 (ADR-027 D5).
- [ ] **BL-ADR027-NX** (P4) Nx/Turborepo 도입. 트리거: 지속적 CI 병목(>15분) 또는 영향도 계산 수동 유지 불가. test.yml change-detection(2026-08-13 도입)을 먼저 소진 (ADR-027 D5).
- [ ] **BL-ADR027-PACKAGES** (P4) `packages/` 공유 패키지 신설. 트리거: 동일 언어 소비자 2개 + 변경 주기 동일 증명 (ADR-027 D5).
- [ ] **BL-EXT-CACHE-2** (P2) **정밀 캐시 무효화.** 캐시 `sources`가 참조하는 chunk id를 기준으로 대상 캐시행만 삭제하는 방식은 아직 구현하지 않았다. 읽기 시점 fail-closed로 노출은 닫혔고, 남은 목적은 캐시 효율을 높이는 성능 과제다.
- [ ] **BL-NOTES-CACHE-2** (P2) **노트 캐시 무효화의 scope 갭.** `embed_note_async`는 `invalidate_cache(workspace_id, note.project_id)`로 project scope만 무효화한다. 전역 질의로 만들어진 `project_id IS NULL` 캐시행은 그 노트의 청크를 참조해도 살아남는다. 읽기 시점 fail-closed로 노출은 닫혔고, 남은 것은 cache miss와 재검색에 따른 캐시 효율이다.
  - ⚠ **정정 기록**: 2026-08-01 설계 라운드가 이 항목을 "무효화 DELETE 가 커밋되지 않고 롤백된다(P1 프로덕션 결함)" 로 보고했으나 **사실이 아니다.** `EmbeddingService.invalidate_cache`(`embeddings/service.py:329-336`, 2026-08-01 기준)가 `delete_caches` 뒤에 이미 commit 한다. 설계 에이전트는 `delete_caches`(flush만)와 호출부만 읽고 그 사이 한 줄짜리 함수를 열지 않았으며, "실측" 은 실제 코드 경로가 아니라 **가설한 패턴을 합성 재현**한 것이었다. 회귀 테스트를 쓰고 결함 상태로 mutation 했을 때 테스트가 죽지 않아 발견했다. 남는 것은 위의 scope 갭뿐이다.
- [ ] **BL-EXT-REASON-1** (P2) `ExternalDocument` 에 문서별 실패 **사유** 컬럼이 없다. ADR-026 D4 "문서별 `failed` 상태와 사유를 남긴다" 의 사유 절반이 미충족. 현재는 sync run `error_summary` 한 줄뿐. 마이그레이션 필요.
- [ ] **BL-EXT-SYNC-3** (P2) 최초 import 의 export 5xx/timeout 은 여전히 문서 행을 남기지 않는다. BL-EXT-SYNC-1 과 같은 UX 결함 클래스이나 트리거가 다르다 (이번엔 미지원 MIME 만 좁게 수정).
- [ ] **BL-EMBED-2** (P2) `embed_note` 도 노트 전문을 L1 임베딩 입력으로 보내고 단일 `generate_embeddings` 호출을 쓴다 — BL-EXT-EMBED-1 과 동일한 구조적 결함. `embed_meeting` 은 요청당 입력 배열 한도 쪽 노출이 더 크다.
- [ ] **BL-EMBED-3** (P3) external_document 의 L1 `embedding` 컬럼은 **소비처가 없다** (검색은 `chunk_level = 2` 만, enrich 는 `chunk_text` 만). 생성 비용 + halfvec(1536) 저장이 낭비다. L1 행 자체는 부모 컨텍스트 본문 때문에 필요하다.
- [ ] **BL-BE-RBAC-FRESH-REMAINING-1** (P3) `[신규 · 2026-08-02 G4 교차 리뷰]` 남은 **상태 변경** 라우트는
  여전히 캐시 게이트(`require_member`)다 — inbox dismiss/classify · memory · upload · meetings capture ·
  notes create · projects create/delete 등. 이들은 `member.role` 을 admin 우회 판정에 쓰지 않으므로
  위 항목의 스코프 밖이었으나, **viewer 로 강등된 사용자가 15초 창에서 member 급 쓰기를 통과**할 수 있다.
  BL-BE-RBAC-CACHE-DESTRUCTIVE-1 과 같은 방식(`require_member_fresh`)으로 확대할지 판단 필요.
  ⚠ 확대 시 **성능 회귀 주의** — 캐시를 넣은 이유가 Stage 2 #6 이다.
- [ ] **BL-FE-RAW-ANCHOR-REMAINING-1** (P4) `[신규 · 2026-08-02]` 같은 원시 `<a>` 패턴이
  `features/meetings/components/meeting-detail.tsx` · `app/(app)/{meetings,projects}/[id]/error.tsx` ·
  `components/empty-state.tsx` 에 남아 있다. error boundary 는 **풀 리로드가 의도일 수 있어** 판단 필요.
- [ ] **BL-FE-HOOK-RETRY-OVERRIDE-1** (P4) `[신규 · 2026-08-02]` `features/{integrations,meetings}/hooks.ts`
  의 개별 `retry: (failureCount) => failureCount < 1` 은 전역 기본값을 덮으므로 4xx 에도 여전히 재시도한다.
  전역과 같은 status 분기를 적용할지 판단 필요.
- [ ] **BL-FE-WID-GUARD-REMAINING-1** (P4) `[신규 · 2026-08-02 G4 교차 리뷰]` `notes`·`meetings`·
  `actions`·`memory`·`onboarding`·`integrations` 훅은 여전히 `enabled: !!wid` 라 stale wid 로
  `/notes` 등에 직접 진입하면 self-heal 전에 403 을 발사한다. 확대 적용 시 **위 3종 파생 결함을
  반드시 함께 처리**할 것.
- [ ] **BL-RAG-CITATION-CODE-GUARD-1** (P4) `[신규 · 2026-08-02]` 인용 번호는 **100% LLM 산출물**이고
  코드가 파싱·검증하지 않는다(`rag/service.py` 는 토큰을 그대로 스트리밍). 프롬프트 수정만으로는
  비결정적 재발을 막지 못한다. **재발이 관측되면** 코드측 결정론 가드를 검토할 것
  (SSE 스트리밍이라 BE 후처리는 버퍼링을 강요 → FE 렌더층이 현실적 후보. 단 부분 인용 답변 오탐 위험).
- [ ] **BL-BE-CACHE-COMMENT-DRIFT-1** (P4) `[신규 · 2026-08-02]` `workspaces/invite_service.py` 의
  캐시 관련 주석이 "최대 60s" 라고 적혀 있으나 실제 `_MEMBER_CACHE_TTL_SEC` 는 **15s** 다. 주석 드리프트.
- [ ] **(선택) 풍부한 음성 샘플 1개 확보** — 알려진 트랜스크립트 + 명명된 사실 2개 이상. 현재 픽스처는 무음 10초 webm + test.m4a 뿐 → 회의 오디오 파이프라인의 **콘텐츠** 검증(transcription/화자분리/요약 품질) 갭. 텍스트 캡처로 RAG 경로는 검증 완료(오디오는 기계동작만).
- [ ] **(선택) 전용 admin/viewer QA 계정 발급** — 현재 2계정(owner d@e.com + member a@e.com)으로 role 변경하며 4 role 전수했으나, 동시 다중 role 라이브 시나리오엔 전용 계정이 편함. `apps/web/.env.local` QA_LOCAL_ADMIN_*/QA_LOCAL_VIEWER_* 추가.

### 제품 · UX carry
- [ ] **T-LAND-01/02** 마케팅 (landing wedge headline + use case)
- [ ] **BL-T2 P2** 5건 (input/security headers)
- [ ] **Power P2** (BUG-POW-002 Inbox bulk + 004 zip export + 007 PAT)
- [ ] **BUG-CASUAL P2/P3** (VOCAB + INBOX-COPY + CMD-K-SEQ + CMD-K-STATE)
- [ ] **a11y P2** (T-A11Y-SKIP + T-A11Y-CC + T-MOBILE-NAV + T-NAV-BADGE)
- [ ] **BL-068/069** Sprint 23 D1/D3 Playwright reproduce
- [ ] **T-UI-1 모바일 햄버거 nav** — 본 sprint 폰트 반응형(17→16) 만 완료, 햄버거 nav 는 모바일 dev 환경 + manual QA 필요로 carry. 현재 LandingNav 가 "로그인" + "시작하기" 는 mobile 노출, "기능" + "요금" 만 sm:block 으로 숨김 (기본 기능 손실 0).
- [ ] **T-INFRA-1 qa-*.spec.ts CI 게이트 부활** — 5계정 QA fixture 사용자 작업 의존 (ADR-031 이후 `/sign-up` 으로 직접 생성 가능 — Clerk 대시보드 수동 발급 의존이 사라졌다). Owner/Viewer dual storageState 도 같은 fixture 도입 후 묶음 진행.
- [ ] **BL-NEW-DELTA3-REMEASURE** Phase B swap DELTA-3 P/R n=20 재측정 — Cloud Run trace + Sentry + 실 API 비용 필요 (Sprint 24 carry, T-AI-1 contract 가드만 lock-in)
- [ ] **T-GTM-1 창업자 LinkedIn 링크** — 외부 URL 미수령으로 본 sprint 는 text-only 인프라 transparency 로 대체. URL 수령 시 별도 patch (~30min)
- [ ] **agy CLI hang BL 등재** — 시스템 외부 도구 이슈, Multi-Agent QA cross-check 자동화 차단
- [ ] **BL-NEW-RAG-SOURCE-SELECT** RAG source-level selection v1 — Power persona 데이터 후 B path 검토 (Sprint 25+)
- [ ] **BL-NEW-OBN-DATA-RETRY** Onboarding 재설계 data-driven retry — F4 외부 인터뷰 후 (Sprint 25+)
- [ ] **BL-NEW-BE-PERF-COLD-START** Cloud Run + Neon cold start 진단 — production Sentry trace 후 (Sprint 25+)
- [ ] **BL-NEW-BE-PERF-PARALLEL-API** Dashboard 4 API 병렬화 — useDashboardStats → Promise.all (Sprint 25+)
- [ ] **BL-NEW-DELTA3-REMEASURE** Phase B swap DELTA-3 P/R n=20 재측정 — Phase 2 완료 후 (Sprint 24 Wave 2 carry)

### 장기 후보 (진입 미정)
- [ ] **S15-T1** 신규 가입 시 "{사용자명}의 개인 Kairos" personal workspace 자동 시드 (BE)
- [ ] **S15-T2** Workspace switcher UI 우상단 (FE — Notion 패턴 차용)
- [ ] **S15-T3** Personal workspace 권한 모델 lock-in — 항상 1명, 팀 초대 불가 (BE schema 제약)
- [ ] **S15-T4** ADR-016 작성 — Personal↔Team IA 결정 근거 + visibility=personal 신설 여부 (현 분석: workspace 단위 분리 채택, project visibility 4번째 추가 안 함)
- [ ] **S15-T5** 온보딩 UX — 초기에는 personal만 노출, "팀 합류" 액션 시 team workspace 안내
- [ ] **S15-T6** PRD §7-Marketing tagline 외부 테스트 — 인디해커즈/X DM 50명 A/B 반응 → 1개 lock-in

**Sub-task — RAG 인프라 모니터링 (Qdrant 트리거 #3 자동 감지)**
- [ ] **S15-T7** RAG p50/p95 응답 시간 + 벡터 수 카운터 OpenTelemetry/Sentry 메트릭 추가 (부록 B 트리거 #3)

**검증**: 1인 founder가 신규 가입 → 7일 자기 personal에서만 사용 → 팀 합류 시점 시뮬레이션. 메모리 누락 0건 + workspace 전환 클릭 0 confusion.
- [ ] **S16-T1** 아이템(노트/회의/액션)에 "Promote to Team..." 액션 + 대상 workspace+project 선택 모달 (FE)
- [ ] **S16-T2** Promotion BE API — 메타데이터 + 임베딩 복제 (이동 아님, 원본 tombstone 유지)
- [ ] **S16-T3** Promotion audit log + 헌법 I-18 신설 ("Promotion은 항상 복제 + tombstone, 이동 금지") — I-17 slot은 Sprint 7 BE-T13 cross-ws ProjectMember 차단으로 점유

**v2 — 음성 메모 ingest (회의 외 단독 녹음)**
- [ ] **S16-T4** `/new` 페이지에 "음성 메모" 탭 추가 (회의와 분리, transcript 부재 OK)
- [ ] **S16-T5** Voice note 모델 (Meeting과 별개) + STT + Gemini 요약 + 태그 자동
- [ ] **S16-T6** Personal workspace에서 음성 메모 첫 진입 시나리오 lock-in
- [ ] **GCP WIF 초기 설정 + Secret Manager 9개 이관** (사용자 작업) — `docs/operations/deployment.md` §2.5.1 참조
- [ ] E2E 계정(email/password) 생성 + GitHub `E2E_USER_EMAIL`/`E2E_USER_PASSWORD` 등록 (E2E 활성화)
- [ ] FE ↔ BE 전체 E2E 시나리오 (신규 계정 → 템플릿 프로젝트 3개 → RAG → `[1]` → Source Viewer 풀콘텐츠 렌더) — ADR-008 후속
- [ ] **AD-32** BE-T16 Project update 권한 강화 — 현재 require_member 유지 결정. creator-only 또는 admin 강화 필요 시 sprint 7+ 검토 (협업 마찰 우려).
- [ ] **AD-34** FE RBAC 정밀 분기 — visibility 변경 버튼이 모든 멤버에 활성 + BE-T15 403 위임 (1차). useUser+useMembers 매칭으로 정밀화 = sprint 7+ design-review. dogfooding scope 외, sprint 7+ design-review 보류 **확정**.
- [ ] **AD-35** Playwright E2E (V-T2) + schemathesis (V-T4) + RAG 권한 누설 E2E (V-T5) — sprint 7+ devex-review와 묶음. **2026-05-11 dogfooding으로 1A~1F viewer/member 읽기 + 2D Private RAG 누설 + 2E/2F member/viewer visibility 변경 시도 + CORS-1 (BE 5xx CORS 헤더 누락) + SCHEMA-1 (Project `title` vs ERD `name` 정합성) 추가 묶음**.
- [ ] docs/requirements/prd.md — Sprint 6 phase 표 업데이트 (다음 sprint 또는 별도 patch)
- [ ] docs/requirements/second-brain.md §8 — visibility로 "개인↔팀 경계" 부분 해소 표기
- [ ] AGENTS.md — visibility 도메인 용어 추가 (작음)

### 리서치 · 검증 (F-시리즈)
- [ ] **F2** Demand 시그널 S1~S4 측정 (Sprint 6 완료 후 1개월) — usage analytics 도입 + S1(DAU)/S2(회의 빈도)/S3(RAG 만족도)/S4(Inbox 수용률) 실측. 결과물: demand 시그널 1차 보고서.
- [ ] **F4** 외부 인터뷰 5-10명 + S5/S6 측정 (진행 중, 2026-05-12 착수) — ADR-010 AD-8 60% + ADR-011 §4-b 60% + ADR-009 S5/S6. 결과물: `docs/requirements/interview-results.md`, ADR: `docs/adr/015-f4-demand-signals.md`.
- [ ] **F5** 5분 사용자 세션 관찰 도입 (Sprint 7+, Q5) — 도그푸딩 사용자 1-3명 세션 녹화. 결과물: `docs/requirements/observation-notes.md`.
- [ ] **F6** Wedge 선정 ADR 신규 (Sprint 6 완료 + F2/F4 결과 후) — 페르소나-Wedge 매트릭스 + S5/S6. 결과물: `docs/adr/012-wedge-selection.md`.
- [ ] **F7** L4 우선화 검토 ADR 신규 (Sprint 6 완료 + F4 결과 후) — ADR-010 §4 O1/O2/O3 옵션 선택 + ADR-007 Phase 4 진입 결정. 결과물: `docs/adr/013-l4-prioritization.md`.
- [ ] **F8** 부채 D-2/D-3 처리 ADR 신규 (Sprint 6 킥오프 시 결정 — 진입 직전 vs 완료 후) — service-to-service 경계 정책. 결과물: `docs/adr/014-service-boundary.md`.
- [ ] **F9** ADR-009 본 ADR 갱신 검토 (Sprint 7+ 외부 인터뷰 완료 후) — S1~S6 실측 결과로 임계값 재조정.
- [ ] PERSONA-002 (김PM) — F4 외부 인터뷰 결과로 `interview-confirmed` 또는 `deprecated` 결정 (ADR-011 §4-b 60% / 3필드 임계값).
- [ ] PERSONA-003 (박PM) — 동상.
- [ ] 내보내기 포맷 PDF (향후 구현)

### 이번 라운드에서 생긴 후속 (2026-08-16, ADR-030)

- [x] ~~**CI paths-filter 재확인**~~ — **2026-08-16 검증 완료.** dependabot PR #163
  (`apps/web/{package.json,pnpm-lock.yaml}` 만 변경) 에서 필터가 기대대로 판정했다 —
  `api` false → `backend-test` **skip**(올바름), `web`/`contracts` true → `frontend-build`/
  `contract-check` 실행·success. 식별자 `backend`→`api` 개명이 소비 지점과 정합함을 실측으로 확인.
- [x] ~~**`.github/dependabot.yml`**~~ — **2026-08-16 파일 삭제.** 버전 업데이트를 끈다.
  실측: monthly+limit3 에서 9개, weekly+limit5 로 올린 직후 **15개**가 열렸다. 1인 개발(PERSONA-001)이
  감당할 트리아지 양이 아니고, 그중 실제 신호는 1건이었다(내 CI PORT 버그 — 다음 실 PR 이 30분 뒤
  똑같이 잡았을 것).
  ★**Dependabot 보안 업데이트는 이 파일과 별개 기능**이다 (Settings → Code security).
  파일을 지워도 **CVE PR 은 계속 온다** — 실제 안전 가치는 그쪽이 갖고 있다.
  **[확인 필요]** Settings 에서 Dependabot alerts / security updates 가 켜져 있는지 한 번 볼 것.
  **재검토 트리거**: 팀원 2명 이상 **또는** 릴리스 케이던스가 생겨 의존성 최신화가 정기 업무가 될 때.
- [ ] **액션 SHA 수기 갱신 루틴** `[신규 · 2026-08-16]` dependabot 을 끈 대가로 3rd-party 액션이
  SHA 로 고정된다. 분기 1회 또는 CI 가 deprecation 경고를 낼 때 갱신한다 —
  이번이 정확히 그 사례다(`Node.js 20 is deprecated` 경고 → checkout/setup-node/pnpm 3종 갱신).
- [ ] **`.github/actions/` composite 추출** — uv/pnpm/node setup 이 4곳 중복이다.
  CI 복구로 보류 사유는 사라졌으나, **dependabot #155/#156/#157 이 같은 워크플로 파일을 건드리고 있어**
  그 3건을 먼저 머지한 뒤 착수한다(충돌 회피).
- [ ] **`ci-required` 를 required check 로 등록** `[신규 · 2026-08-16]` public 전환으로 Free 에서도
  ruleset 을 쓸 수 있다. `test.yml` 주석이 "branch protection 도입 시 이 job 하나만 등록" 이라고
  적어둔 그 지점이다. 등록 전까지는 CI 가 red 여도 머지가 물리적으로 가능하다.
- [ ] **public 노출 표면 점검** `[신규 · 2026-08-16]` `deploy/oci/README.md` 등 7파일에 SSH 별칭
  (`truewords-oracle`) · 포트 매핑 · 배포 절차가 있다. 시크릿은 아니지만 정찰 정보다.
- [ ] **비밀번호 재설정 경로 부재** `[신규 · ADR-031 제외 갭]` 레포에 이메일 발송 인프라가 0건이라
  이메일/비밀번호 사용자가 비밀번호를 잊으면 복구 경로가 없다. 현재는 사인인 화면에 "Google 로그인을
  쓰거나 운영자 문의" 안내만 노출한다. 도그푸딩 규모에서는 수동 처리로 버티되, 외부 사용자 확대 전에
  Resend 등 발송 수단 + `sendResetPassword` 배선이 필요하다. **컷오버와 같은 창에서 하지 않는다.**
- [ ] **Clerk dev 인스턴스 삭제** `[ADR-031 종료 조건 · 컷오버 +7일]` git 히스토리 675 커밋에
  Clerk dev secret 이 남아 있고 레포가 public 이다. 전환 완료로 키가 무의미해지는 것과, 키가
  **실제로 무효화되는 것**은 다르다 — 인스턴스 삭제까지가 종료 조건이다.
