# Kairos TODO

> 마지막 업데이트: 2026-05-21 (Sprint 25 moonlit-sutton closeout — Wave 1+2+3 단일 PR. 17 task 완료, backend pytest 452 PASS / FE typecheck 0 / vitest 56 / build 12/12)
> 이 파일은 리빙 문서입니다. 주요 작업 후 반드시 업데이트하세요.
> 형식 규칙: `.ai/common/global.md` §2 참조 — Completed / Blocked / Questions / Next Actions 4섹션 운영.

---

## 🚨 Sprint 25 진입 직전 — 사용자 협력 필요 (정정)

> Multi-Agent QA 결과(2026-05-21) — 사용자가 처리해야 다음 단계 진행 가능한 항목.
> **정정**: 사용자 Clerk Production 발급 SKIP 결정 반영 → 2번 항목 제거.

1. **production DB 더미 user 정리** — BUG-SENTINEL-005 PoC 잔존. Neon SQL editor에서 `DELETE FROM users WHERE clerk_id='user_QA20260521_sentinel_test_doNotUse'` 실행. Sprint 25 첫 commit 전.
2. **가격 정책 결정** — Sprint 25 Wave 2 T-GTM-2 의존. 3-tier (Free Beta/Team/Enterprise) 또는 "Pricing coming soon — 베타 무료" 명시.
3. ~~Clerk Production 인스턴스 발급~~ — **사용자 의도적 SKIP 결정 (2026-05-21, memory `project_gcp_migration_jetaime_dev_done.md`)**. Sprint 25 의존 0. GA launch 시점 별도 sprint.

---

## Blocked

> 차단(Blocked) 항목은 이유 + 필요한 조치를 함께 기록. AI가 사용자에게 빈번하게 질문하는 대신 본 섹션에 누적 후 자연스러운 타이밍에 일괄 전달.

- ~~Clerk Production key 발급~~ — **2026-05-21 사용자 의도적 SKIP 결정** (memory `project_gcp_migration_jetaime_dev_done.md`). GA launch 시점 별도 sprint. Sprint 25 의존 0.
- [ ] **Sentry DSN 발급** — Sprint 22 conditional init 활성화. 발급 + Vercel/Cloud Run env 등록 + 알람 verify. Sprint 24 Wave 2 BL-NEW-BE-PERF-COLD-START 진단 선행 조건.
- [ ] **외부 user 1명 실제 dogfooding** — Sprint 22 spec `git history` 12분 walkthrough.

---

## Next Actions

> **2026-07-31 Drive Spike codex 리뷰 (PR #143) — 미해소 발견** (`.claude/spike-gdrive/artifacts/CARRY.md` 상세)
> CDX-1(프로젝트 미선택 문서 RAG 노출)은 같은 날 수정됨.
> **2026-08-01 브랜치 `fix/bl-ext-backlog` 에서 코드 6건 해소** — 아래 체크 표시 참조.

- [x] **BL-EXT-OAUTH-1** (P1) OAuth `nonce` 미소비 → **해소** (`6bc5ab8`). `integration_oauth_states` 테이블 + callback 의 `DELETE ... RETURNING` 단문 원자 소비. 소비를 Google 토큰 교환보다 앞에 두어 재사용 요청이 외부 호출에 도달하지 않는다. 브라우저 실측 — callback 3회에 Google 아웃바운드 1회.
- [x] **BL-EXT-CACHE-3** (P1) **해소 (2026-08-01).** 비-admin `max_visibility='public'` fast path를 제거하고, 캐시 저장 직전에 source chunk 존재 fence를 둬 사라진 source를 참조하는 캐시행을 저장하지 않는다.
- [x] **BL-EXT-CACHE-1** (P1) **해소 (2026-08-01).** `ALL_CHUNKS_VISIBLE_SQL` anti-join이 source chunk 행 부재를 위반으로 판정하는 fail-closed가 됐다.
  - (2026-08-01 사용자 결정; `backend/src/embeddings/repository.py:389-400`, `backend/src/rag/service.py:234-265` 기준) 기존 캐시행은 일회성 전량 무효화하지 않고 TTL 7일로 자연 배출한다. admin/owner 우회는 유지하며, 안3 epoch 카운터는 기각했고 fence에 `FOR SHARE`를 도입하지 않는다.
  - 비-admin source 재검사에 따른 캐시 miss 증가는 노출 차단을 위한 감수한 트레이드오프다.
- [x] **BL-EXT-REVISION-2** (P1) revision guard 가 경쟁 동기화에서 무력 → **해소** (`87e1963`). `version` 단독 + 본문 갱신 CAS. ⚠ CAS 는 "최신 보존" 이 아니라 **"선착순 보존"** 이며 완료·오류 상태 전이는 CAS 미보호 (`integrations/CONTEXT.md` §6 기록).
- [x] **BL-EXT-SYNC-1** (P2) 최초 import 의 unsupported MIME 무상태 → **해소** (`5af8261`). metadata 직후 판별 → 빈 행 생성 → raise. ⚠ ADR-026 D4 **부분 충족** — 사유는 문서별로 남지 않는다 (아래 신규 BL 참조).
- [x] **BL-EXT-EMBED-1** (P2) L1 임베딩 무제한 입력 → **해소** (`8038e27`). 임베딩 입력만 절단하고 `chunk_text` 는 전문 유지 (L1 텍스트가 LLM 프롬프트 근거 본문이므로).
- [x] **BL-EXT-HTTP-1** (P2) background sync 의 `AsyncClient` 미종료 → **해소** (`f985d2f`). `aclose()` + `try/finally`.
- [x] **BL-EXT-SYNC-2** (P2) 중복 import 경쟁 → **해소** (`6a43541`). `ON CONFLICT DO NOTHING` + 경쟁 패자 조기 반환.

> **2026-08-01 BL-EXT 세션에서 신규 발견 — 미해소**

- [ ] **BL-EXT-CACHE-2** (P2) **정밀 캐시 무효화.** 캐시 `sources`가 참조하는 chunk id를 기준으로 대상 캐시행만 삭제하는 방식은 아직 구현하지 않았다. 읽기 시점 fail-closed로 노출은 닫혔고, 남은 목적은 캐시 효율을 높이는 성능 과제다.
- [ ] **BL-NOTES-CACHE-2** (P2) **노트 캐시 무효화의 scope 갭.** `embed_note_async`는 `invalidate_cache(workspace_id, note.project_id)`로 project scope만 무효화한다. 전역 질의로 만들어진 `project_id IS NULL` 캐시행은 그 노트의 청크를 참조해도 살아남는다. 읽기 시점 fail-closed로 노출은 닫혔고, 남은 것은 cache miss와 재검색에 따른 캐시 효율이다.
  - ⚠ **정정 기록**: 2026-08-01 설계 라운드가 이 항목을 "무효화 DELETE 가 커밋되지 않고 롤백된다(P1 프로덕션 결함)" 로 보고했으나 **사실이 아니다.** `EmbeddingService.invalidate_cache`(`embeddings/service.py:329-336`, 2026-08-01 기준)가 `delete_caches` 뒤에 이미 commit 한다. 설계 에이전트는 `delete_caches`(flush만)와 호출부만 읽고 그 사이 한 줄짜리 함수를 열지 않았으며, "실측" 은 실제 코드 경로가 아니라 **가설한 패턴을 합성 재현**한 것이었다. 회귀 테스트를 쓰고 결함 상태로 mutation 했을 때 테스트가 죽지 않아 발견했다. 남는 것은 위의 scope 갭뿐이다.

- [ ] **BL-EXT-REASON-1** (P2) `ExternalDocument` 에 문서별 실패 **사유** 컬럼이 없다. ADR-026 D4 "문서별 `failed` 상태와 사유를 남긴다" 의 사유 절반이 미충족. 현재는 sync run `error_summary` 한 줄뿐. 마이그레이션 필요.
- [ ] **BL-EXT-SYNC-3** (P2) 최초 import 의 export 5xx/timeout 은 여전히 문서 행을 남기지 않는다. BL-EXT-SYNC-1 과 같은 UX 결함 클래스이나 트리거가 다르다 (이번엔 미지원 MIME 만 좁게 수정).
- [ ] **BL-EMBED-2** (P2) `embed_note` 도 노트 전문을 L1 임베딩 입력으로 보내고 단일 `generate_embeddings` 호출을 쓴다 — BL-EXT-EMBED-1 과 동일한 구조적 결함. `embed_meeting` 은 요청당 입력 배열 한도 쪽 노출이 더 크다.
- [ ] **BL-EMBED-3** (P3) external_document 의 L1 `embedding` 컬럼은 **소비처가 없다** (검색은 `chunk_level = 2` 만, enrich 는 `chunk_text` 만). 생성 비용 + halfvec(1536) 저장이 낭비다. L1 행 자체는 부모 컨텍스트 본문 때문에 필요하다.

> **2026-06-17 멀티 에이전트 팀 QA 후속** (`git history`)
- [ ] **(선택) 풍부한 음성 샘플 1개 확보** — 알려진 트랜스크립트 + 명명된 사실 2개 이상. 현재 픽스처는 무음 10초 webm + test.m4a 뿐 → 회의 오디오 파이프라인의 **콘텐츠** 검증(transcription/화자분리/요약 품질) 갭. 텍스트 캡처로 RAG 경로는 검증 완료(오디오는 기계동작만).
- [ ] **(선택) 전용 admin/viewer Clerk dev 계정 발급** — 현재 2계정(owner d@e.com + member a@e.com)으로 role 변경하며 4 role 전수했으나, 동시 다중 role 라이브 시나리오엔 전용 계정이 편함. `frontend/.env.local` QA_LOCAL_ADMIN_*/QA_LOCAL_VIEWER_* 추가.

> Sprint 25 moonlit-sutton 완료 — PR draft 진입 (2026-05-21). 다음 Sprint 진입 계획은 Recently Completed 섹션 참조.

### 📋 사용자 작업 대기
- [ ] **T-SEC-CLERK-ROTATE** (운영자) Clerk dev `CLERK_SECRET_KEY` **rotation** — 노출 키(`sk_test_mvhptL…`) 무효화. 파일 redaction 은 PR #115(d5463cc) 완료됐으나 라이브 키 무효화가 진짜 fix. Clerk 대시보드 → API Keys → Secret key regenerate 후 `.env.local`/`backend/.env`·Cloud Run/Vercel env 갱신. **시급 아님**(dev 키 + repo private, 2026-05-29 사용자 판단). git 히스토리 1 commit 잔존(SEC-CLERK-SECRET-COMMITTED).
- [ ] **T-CLEANUP-1** production DB Neon SQL editor에서 `DELETE FROM users WHERE clerk_id='user_QA20260521_sentinel_test_doNotUse'` (Sprint 25 PoC 잔존 정리)
- [ ] **PR #102 (Sprint 25 moonlit-sutton) ready review + squash merge** — 사용자 승인 후 main 머지
- [ ] **post-merge 배포 verify** — Cloud Run rollout 후 `POST /api/v1/users/sync` 404 응답 + `/health` 200 + `/dashboard` 회귀 0건

### Sprint 25 carry-over (Sprint 26+ 권고)
- [ ] **T-UI-1 모바일 햄버거 nav** — 본 sprint 폰트 반응형(17→16) 만 완료, 햄버거 nav 는 모바일 dev 환경 + manual QA 필요로 carry. 현재 LandingNav 가 "로그인" + "시작하기" 는 mobile 노출, "기능" + "요금" 만 sm:block 으로 숨김 (기본 기능 손실 0).
- [ ] **T-INFRA-1 qa-*.spec.ts CI 게이트 부활** — 5계정 Clerk dev fixture 사용자 작업 의존. Owner/Viewer dual storageState 도 같은 fixture 도입 후 묶음 진행.
- [ ] **BL-NEW-DELTA3-REMEASURE** Phase B swap DELTA-3 P/R n=20 재측정 — Cloud Run trace + Sentry + 실 API 비용 필요 (Sprint 24 carry, T-AI-1 contract 가드만 lock-in)
- [ ] **T-GTM-1 창업자 LinkedIn 링크** — 외부 URL 미수령으로 본 sprint 는 text-only 인프라 transparency 로 대체. URL 수령 시 별도 patch (~30min)
- [ ] **agy CLI hang BL 등재** — 시스템 외부 도구 이슈, Multi-Agent QA cross-check 자동화 차단

### 🟡 Sprint 25 candidates (Sprint 24 Wave 2 carry — 후순위)
- [ ] **BL-NEW-RAG-SOURCE-SELECT** RAG source-level selection v1 — Power persona 데이터 후 B path 검토 (Sprint 25+)
- [ ] **BL-NEW-OBN-DATA-RETRY** Onboarding 재설계 data-driven retry — F4 외부 인터뷰 후 (Sprint 25+)
- [ ] **BL-NEW-BE-PERF-COLD-START** Cloud Run + Neon cold start 진단 — production Sentry trace 후 (Sprint 25+)
- [ ] **BL-NEW-BE-PERF-PARALLEL-API** Dashboard 4 API 병렬화 — useDashboardStats → Promise.all (Sprint 25+)
- [ ] **BL-NEW-DELTA3-REMEASURE** Phase B swap DELTA-3 P/R n=20 재측정 — Phase 2 완료 후 (Sprint 24 Wave 2 carry)

### Sprint 24 Wave 2 잔여 (P2+ carry)
- [ ] **T-LAND-01/02** 마케팅 (landing wedge headline + use case)
- [ ] **BL-T2 P2** 5건 (input/security headers)
- [ ] **Power P2** (BUG-POW-002 Inbox bulk + 004 zip export + 007 PAT)
- [ ] **BUG-CASUAL P2/P3** (VOCAB + INBOX-COPY + CMD-K-SEQ + CMD-K-STATE)
- [ ] **a11y P2** (T-A11Y-SKIP + T-A11Y-CC + T-MOBILE-NAV + T-NAV-BADGE)
- [ ] **BL-068/069** Sprint 23 D1/D3 Playwright reproduce

### 기존 carry-over
- CO-1~14 (Sprint 22 carry, BACKLOG 등재)
- BL-065 Member.last_active_at 필드 (Sprint 23 D2 carry CO-17, P3)
- BL-067 pyright `_update(...).where(...)` false-positive (Sprint 23 CO-19, P4)
- BL-024 pg_prewarm Cloud Run cold start
- BL-026 옵션 A — dev DB export + ground truth (production scale recall)

---

## Recently Completed (2026-05-21 Sprint 25 — moonlit-sutton, PR draft)

- [x] **Sprint 25 — moonlit-sutton Multi-Agent QA P0/P1/P2 17 task fix bundle (2026-05-21, PR pending, 11 commits + 2 docs pre-commits)**
  - [x] **Pre-PR (commit A+B)** branch + 산출물 정리 + Wave 1 코드/docs 2 commit 분리
  - [x] **Wave 1 P0** T-SEC-1 BUG-SENTINEL-005 `/api/v1/users/sync` endpoint 비활성화 (handler + service 제거 + auth/CONTEXT.md §5/§6 + 회귀 4 case)
  - [x] **Wave 2 P1** T-SEC-3 upload validation 4계층 (size/MIME/확장자/signature, upload 도메인 service/exceptions/dependencies 신설, 회귀 6 case)
  - [x] **Wave 2 P1** T-GTM-2 ★★★ PRICING `/pricing` 라우트 신설 ("Pricing coming soon — 베타 무료") + LandingNav 요금 링크 교체
  - [x] **Wave 2 P1** T-GTM-1 ★★★ TRUST TrustSignals 섹션 (인프라/데이터 정책/베타 솔직성 3카드 + Built with 마이크로카피)
  - [x] **Wave 2 P1** T-GTM-3 ★★ PRODUCT-SHOT 실 제품 스크린샷 3장 (QA evidence 재활용 — RAG/요약/대시보드)
  - [x] **Wave 2 P1** T-GTM-4 BUG-CASUAL-003 한국어 부연 라벨 inline (PipelineSection + Hero 배지)
  - [x] **Wave 2 P1** T-GTM-5 BUG-CURIOUS-004/005/006 Hero "한국팀을 위한" + "5분 설정 분 단위 분해"
  - [x] **Wave 2 P1** T-INFRA-1 BL-069 Inbox dismiss API wire + Playwright spec (BL-068 spec 기존 확인)
  - [x] **Wave 3 P2** T-SEC-4/5 + T-GTM-6 batch (transcript max_length / prod docs_url None / sign-up Pre-GA 텍스트 + 회귀 6 case)
  - [x] **Wave 3 P2** T-A11Y-1 + T-UI-1 partial (skip-link + main 랜드마크 + aria-hidden + CTA 대비 + 반응형 폰트)
  - [x] **Wave 3 P2** T-AI-1 ADR-019 Phase B post-swap LLM 계약 13 case (model lock-in + prompt contract + post-processing guards + Pydantic schema)
  - [x] **Phase 4** Atomic docs sync — upload/CONTEXT.md 신설 + endpoints.md sync + ADR-022 신설 + auth/CONTEXT.md ADR cross-link
  - [x] **Phase 5** 검증 — backend pytest **452 passed + 1 skipped** (baseline 427 + 25 신규) / FE typecheck 0 / vitest 56 / build 12/12 OK / production BE smoke
  - 산출물: PR pending (push 사용자 승인 대기) + ADR-022 (`docs/adr/022-clerk-webhook-skip.md`)
  - 잔여 사용자 작업: production DB cleanup (T-CLEANUP-1) + PR ready review + post-merge 배포 verify

---

## Recently Completed (2026-05-20 Sprint 24 Wave 2 — trusty-heron, PR draft)

- [x] **Sprint 24 Wave 2 — trusty-heron (PR draft, 2026-05-20)**: Multi-Agent QA P0/P1 16 task fix bundle + 헌법/production carry
  - [x] **Phase 1** T-2 Post-Swap Delta gate PASS (Phase B swap DELTA-1/2/4/5 통과, DELTA-3 carry → BL-NEW-DELTA3-REMEASURE)
  - [x] **Phase 2** T-AI-DATE + T-RAG-MOCK-REMOVE (P0 Critical: AI 날짜 후처리 + RAG real-DB mock 제거)
  - [x] **Phase 3** T-OBN-05 D 옵션 + T-MOBILE-HEADER (P0 High UX: onboarding 4번째 옵션 + mobile sticky header)
  - [x] **Phase 4** T-PROJ-LIST + T-NOTE-DETAIL + T-CMD-K-FIX (P1 FE: 누락 페이지 신설 + Cmd+K 안정화)
  - [x] **Phase 5** T-RAG-TIME-FILTER + T-AUDIT-VIEW (P1 RAG time_range + compliance audit UI)
  - [x] **Phase 6** T-BE-PERF spike + JWT cache Top 1 fix (BUG-MOBILE-005, dashboard cold path)
  - [x] **Phase 7** T-N+1 BL-006 cross-domain import 해소 (헌법 §4.2 위반 closed — memory → embeddings pipeline_service 분리)
  - [x] **Phase 8** T-N+4 BL-T2-003 Whisper 4hr+ chunked transcription (production, ffmpeg subprocess + asyncio.gather)
  - [x] **Phase 9** T-N+2 composite FK fixture (SCN-FK-01~12 회귀 안전망 — Sprint 21 BL-050 가드) + docs closeout
  - 검증: pytest **423 passed + 1 skipped** (baseline 411 + 12 신규 SCN-FK) / FE typecheck 0 / vitest 50 / Playwright 신규 PASS
  - 산출물: `git history` + `git history` + per-task report

---

## Recently Completed (2026-05-19 Sprint 23 cozy-crystal — PR #98 draft)

- [x] **Sprint 23 — cozy-crystal dogfood fix (D1~D4) + Sprint 22 sync (F1~F4) (2026-05-19, PR #98 draft, 19 commits)**
  - [x] **D1** WorkspaceSwitcher 클릭 컨텍스트 전환 → `queryClient.clear()` → `invalidateQueries(predicate)` + dashboard render-time setState → useEffect + router.refresh() 제거 (`9e2eee2`)
  - [x] **D2** Settings Variant C Compact 시안 구현 + Suspense wrap (`96997bb` + Codex 2.5차 polish `a33d86b`)
  - [x] **D3** Inbox dismiss UX → `useInbox({ isProcessed: false })` + queryKey 격리 + invalidate prefix + autoProcessed 그룹 제거 (`928fc7c` + Codex 2.5차 camelCase param `a33d86b`)
  - [x] **D4 BE** ItemPromotionAudit + promote_helpers + 4 도메인 promote endpoint (meetings/notes/inbox/actions) — 6 commits (`6b1dce1`/`2f724f0`/`dc20757`/`ce8fd6c`/`7c54438`/`e3e9ee8`)
  - [x] **D4 FE** ItemPromoteModal generic + 4 entry mount + memory wrapper (`ede91eb`)
  - [x] **F1** TODO.md + REFACTORING-BACKLOG.md Sprint 19-22 closeout sync (`afa55a5`)
  - [x] **F2** memory `project_sprint22_done.md` final (외부 storage, 본 PR 외)
  - [x] **F3** HTML 결과 보고서 Codex 2차 APPROVE + CI 5/5 final 갱신 (`5d960f9`)
  - [x] **F4** G7 spec storageState key fix + skip 가드 제거 (`5d960f9`)
  - [x] Codex 6 cycle review 11 finding 100% 수락 (P1 memory alias, P1 Suspense, P1 RBAC viewer, P2 meeting status/non-terminal, P2 inbox source/camelCase, P2 BG rollback, P2 RAG cache notes/meetings, P2 note chunk 0, P3 meeting action count, P3 error_message) — polish 6 commits (`3fbb0ef`/`a33d86b`/`b8dddd2`/`e78096f`/`d1fa88d`/`1141c37`)
  - 검증: pytest **379 passed + 1 skipped** (baseline 352 + 27 신규) / FE typecheck 0 / build 12/12 OK / vitest 49/49 PASS
  - 산출물: 메모리 `project_sprint23_cozy_crystal_done.md`
  - 잔여 사용자 작업: PR ready → squash merge, D1/D3 dev server dogfood, Codex 7차 재시도 (7:46 PM 이후 또는 GitHub Codex action)

---

## Recently Completed (2026-05-19 Sprint 22 expressive-squirrel — PR #97 `22da49b`)

- [x] **Sprint 22 — Onboarding (OBN-01~04) + Playwright G2/G7/G8 NEW + Sentry FE+BE observability (2026-05-19, PR #97 `22da49b`, 32 commits)**
  - [x] OBN-01: personal workspace lazy seed 회귀 test 3건 (`tests/auth/test_personal_workspace_race.py`). partial unique index + ON CONFLICT idempotency PASS.
  - [x] OBN-02: `User.onboarding_step` (0~4) + `onboarded_at` + alembic backfill + 새 onboarding 도메인 모듈 + 4 단계 BE event hook + FE useOnboarding + OnboardingBanner refactor.
  - [x] OBN-03: EmptyState onboarding-aware copy (meetings/projects/notes) + Export discoverability (BUG-C04).
  - [x] OBN-04: FAB↔BottomNav collision fix (BL-017 ✅) + banner flex-wrap + mobile-responsive spec.
  - [x] Sentry BE + FE conditional init (ADR-021) + PII scrub before_send.
  - [x] Playwright NEW 3 (G2/G7/G8) + G1 보강 + e2e baseline fix 4 commit.
  - [x] Codex 1차 (REVISE 7 finding plan v2 patch) + 1.5차 (Schema APPROVE) + 2차 (REVISE 3 P2 polish 수락) 3-cycle 100% 수락.
  - 검증: pytest **352 passed + 1 skipped** (baseline 325 + 27 신규) / pyright 신규 0 / FE typecheck 0 / FE build 12/12 OK.
  - 산출물: `git history` + `git history`.

## Recently Completed (2026-05-18 Sprint 20/21 cleanup PR)

- [x] **Sprint 21 BL-050 Simple 4 — cross-workspace composite FK hardening (PR #96 `1a83af6`)** — 4 entity composite FK + drift gate allowlist + Codex 1차 REVISE→수락 + 2차 APPROVE. BL-050 잔여 3 entity (memory_items / memory_ai_calls / promotion_audit) carry-over Sprint 24+.
- [x] **Sprint 20 BL-054 cleanup — session.execute → session.exec migration (PR #93 `3eb141c` → PR #95 cherry-pick `c1b29c1` 보정)** — 57 변환 + manifest 5 카테고리 + 헌법 I-14/B-10 patch + Codex 1차+2차 REVISE 5 finding 100% 수락. ⚠️ PR #93 base 사고 사례 ([[feedback_stack_pr_base_check]]).
- [x] **Sprint 20 BL-053 — AsyncSession Level 3 (SM) cleanup (PR #92 `48e7aab`)** — 6 commits, 29 파일, 321 PASS, pyright 131 -1, Codex 2차 APPROVE 4.6/5.
- [x] **Sprint 20 BL-052 — SQLAlchemy → SQLModel import 통일 (PR #91 `195b8e3`)** — 8 commits, 21 code/test + 2 docs, 317 PASS, pyright 72 감소, Codex 2차 APPROVE.

## Recently Completed (2026-05-17~18 Sprint 19 tenant/auth boundary)

- [x] **Sprint 19 PR #2 BUG-C01-EXT-FK — composite FK + alembic (PR #90 `5789822`)** — 4 entity composite FK + drift detection (`compare_metadata`) + 12 commits. Codex 1차 BLOCK→PASS + 2차 REVISE→PASS. 317 PASS.
- [x] **Sprint 19 PR #1 closeout — BUG-C01-EXT v3 잔여 27 endpoint (PR #89 `3f3679d`)** — 45/45 matrix 100% 완료 (PR #88 18 + PR #89 27). Codex 1차+2차 PASS.
- [x] **Sprint 19 PR #1 진입 — BUG-C01-EXT v3 18 endpoint (PR #88 `e2e3805`)** — 10 commits, 4 도메인 real DB + audit, Codex 1차/2차 PASS.

## Recently Completed (2026-05-17 Multi-Agent QA + BUG-C01)

- [x] **Multi-Agent QA Sprint 18 → 19 (2026-05-17)** — 1세션 단일 PR 통합
  - [x] Sentinel-P0 28/28 PASS 재검증 (BUG-C01 fix 후 v2)
  - [x] BUG-C01 (workspace IDOR) fix (`19eb363`) + 회귀 테스트 2/2 PASS
  - [x] 4 페르소나 smoke (Curious / Casual / Mobile / Power) + Sentinel-P1
  - [x] 통합 HTML + Sprint 19 plan 초안 (4축: 캐리오버 BL + QA 후속 + Mobile + 온보딩)
  - [x] Secret 격리 (~/.kairos-qa-secrets/) + .gitignore + spec PASSWORD ENV화
  - [x] QA harness (seed_qa_fixtures.py 489 LOC + founder guard) + Playwright spec 2개
  - 산출물: `git history` + `git history`

> Sprint 18 본 작업(BL-029/031/041~045 + RBAC 매트릭스 + CI vitest + R2 cleanup + observability) 은 2e426c2 머지에서 closeout.

---

## Completed

- [x] **Sprint 17 Closeout (2026-05-16)** — 19 PR / 2일 / C1~C6 8/8 PASS
  - [x] Phase A (#39~#46) — 3 P1 fix + BL-034/035/036/038/039 + ISSUE-040 보안
  - [x] Phase B (#47~#67) — 회귀 가드 21건 + BL-041/042 보안 후속 + e2e local BE 자립
  - [x] 보안 3-layer 정합 (pipeline / vector_search / find_similar_cache + max_visibility fast path)
  - [x] 회귀 0 — typecheck / pytest 108+ / lint baseline 동등
  - [x] qa-fix 통합 브랜치 + sub-branch /loop 워크플로우 검증 완료
  - 산출물: `git history` 참조

- [x] Sprint 17 Exhaustive QA + 3 atomic fix (2026-05-15)
  - [x] ISSUE-005 fix (P1): /notes mock 데이터 제거, BE API 연결 (`6791783`)
  - [x] ISSUE-008 fix (P1): /invite/[code] HTTP 500 → 200 (QueryProvider root 이동, `33c9f1c`)
  - [x] ISSUE-009 fix (P1): /projects/[id] hooks order 회귀 (`ae35f53`)
  - [x] ISSUE-001 closed (외부 `1e903e8`): script tag warning (ThemeProvider 위치)
  - [x] BL-034~039 등재 (asyncpg pool · workspace 중복 · sidebar perf · Satoshi FOIT · invite cache · settings 403 UX)
  - [x] 성공 조건 C1~C6 PASS (C2 음성 full e2e / C.3b RAG private deep 은 후속)
  - [x] 회귀 0 — typecheck clean / pytest 108 pass / lint baseline 동등
  - 산출물: `git history` · `.gstack/qa-reports/qa-report-kairos-sprint17-2026-05-15.md`
- [x] Sprint 18: CLAUDE.md 10원칙 정렬 리팩토링 (머지 2026-05-15, PR #34, 18 commits)
  - [x] PR-A: 헌법/규칙 위반 4건 fix (embeddings AsyncSession · workspaces wrapper · CONTEXT-MAP §9 · ADR gap log)
  - [x] PR-B: docs 정리 (superpowers revert · L0~L4 single source · README/TODO 갱신 · stale 2건 git rm)
  - [x] PR-C: backend 단순화 (ProjectService Optional 제거 · memory wrapper inline · rag/pipeline 유지 결정)
  - [x] PR-D/E: frontend Thin Component (project-dashboard · today-feed 461→339 · sidebar ProjectsList 분리)
  - [x] PR-F: cleanup (미사용 shadcn 4 · ui.ts cross-domain decouple · (app) ErrorBoundary/Suspense)
  - [x] BL-028~033 등재 (memory 분할 · rag SSE helper · transcription fixture · ErrorBoundary 도메인별 · superpowers archive 정책 · pyright/SQLModel 진단)
- [x] Phase 0: 기획 · 아키텍처 · 디자인 (PRD, ERD, API 명세, DESIGN.md)
- [x] ADR-001: 기술 스택 선정
- [x] ADR-002: 실행 전략 — Vertical Slice Sprint 채택
- [x] ADR-003: 디자인 도구 선정
- [x] ADR-004: PARA → 프로젝트 구조 전환
- [x] ADR-005: 랜딩 페이지 AIDA 리디자인
- [x] Phase 1 FE: 3-Panel 레이아웃, Inbox 목록, Dashboard 스캐폴딩
- [x] Phase 1 FE: 랜딩 페이지 리디자인 (13개 컴포넌트)
- [x] Sprint 1 BE: 백엔드 스캐폴딩 + 핵심 도메인 CRUD + Auth [검증됨 2026-04-04]
- [x] Sprint 2: AI 파이프라인 + 프론트엔드 API 연동 [검증됨 2026-04-04]
- [x] Sprint 3: RAG + 노트 [검증됨 2026-04-04]
- [x] Sprint 4: 배포 설정 [검증됨 2026-04-04 — BE/FE 프로덕션 헬스체크 OK]
- [x] Sprint 5: RBAC + 초대 시스템 [검증됨 2026-04-05 — QA 통과, 57 BE 테스트 passed]
  - [x] RoleChecker RBAC 미들웨어 + 전체 라우터 적용
  - [x] WorkspaceInvite 모델 + Alembic 마이그레이션
  - [x] 초대/멤버 관리 API (11개 엔드포인트)
  - [x] FE: /settings 페이지 (멤버/초대/일반 탭)
  - [x] FE: /invite/[code] 초대 수락 페이지
  - [x] FE: 사이드바 설정 링크 + Viewer 쓰기 버튼 숨김
  - [x] ADR-007: LLM Knowledge Base 인사이트 (연구/Phase 4 적용 예정)
- [x] ADR-006 서비스 전면 UI/UX 개편 — 완료 (11/11)
  - [x] 홈 Today 피드 + 온보딩 배너
  - [x] 인라인 출처 [1][2][3] citation-badge
  - [x] C|D 2-Panel 레이아웃 (RAG 오버레이 전환)
  - [x] RAG 소스 범위 선택 (3단계 스코프)
  - [x] 프로젝트 대시보드형 (인사이트 + 2컬럼)
  - [x] Inbox 스마트 일괄 처리 (2그룹)
  - [x] 회의 상세 3뷰 (요약/트랜스크립트/액션)
  - [x] 빠른 메모 + 소스 가져오기 모달
  - [x] 모바일 BottomNav
  - [x] 사이드바 소스 트리 펼침 — 프로젝트 클릭 시 하위 회의/노트/파일 목록 (mock)
  - [x] [1] 클릭 → 소스 뷰어 열림 flow 연결 — CitationBadge → UI Store → SourceViewer
  - [x] Inbox 신뢰도 임계값 설정 UI (프리셋 70/80/90/95%)
  - [x] 내보내기 포맷 MD/JSON (회의/노트)
  - [ ] 내보내기 포맷 PDF (향후 구현)

## Recently Completed — Multi-Agent QA (3 페르소나 통합 검증, 2026-05-13)

- [x] **Sentinel (시니어 QA, 27분)** — 적대적 검증. Critical 1 / High 4 / Medium 6 / Low 2 = 13 결함. Health 6.8/10. Sprint 4-13 핵심 회귀 모두 PASS (CORS / RBAC / 멀티테넌시 / 오디오 / RAG 배치화). 산출: `git history`.
- [x] **Curious (32세 PM, 35분)** — 잠재 고객 도입 결정 시뮬레이션. 5/30/1분 룰 PASS, TTFV 측정 불가 (Blocker), **도입 결정 Maybe** (Dev 배지 + 404 + 카운트 불일치 + 가격 부재). 산출: `git history`.
- [x] **Casual (28세 직장인, 32분)** — 데스크톱 + 모바일 (375x667) UX. 막힘 12건, 용어 해독률 37.5%, 모바일 UX 5/10. Top 1 권고: "RAG" → "AI 검색" 카피 일괄 치환. 산출: `git history`.
- [x] **통합 HTML 보고서** — 3 페르소나 매트릭스 + Critical/High 결함 + 우선순위 매트릭스. `git history`.
- [x] **Sprint 14 계획 작성** — `git history` (T-1~T-11, ~28시간). AD-36~39 자의 결정 라벨.

## Recently Completed — E2E password 전환 + 마이크 녹음 TODO 정리 (2026-05-13)

- [x] **E2E 로그인 OTP → password 방식 전환** — `e2e/auth.setup.ts` Clerk testing mode OTP 흐름 제거. email+password 계정으로 로그인하도록 변경. `test.yml` `E2E_USER_OTP` → `E2E_USER_PASSWORD` 교체.
- [x] **브라우저 마이크 직접 녹음** — Sprint 11 기구현 확인 (`/new` 페이지 "직접 녹음" 탭 + `useRecording.ts` + `RecordingView`). stale TODO 정리.

## Recently Completed — Sprint 10 E2E 검증 + R2 CORS 수정 (2026-05-12)

- [x] **E2E 검증 완료 (2026-05-12)**: 실제 오디오 파일 업로드 → status=completed → 트랜스크립트 세그먼트 + InboxItem 생성 확인. **검증 범위: 오디오 업로드 → STT → 요약 → Inbox 적재까지. RAG/Source Viewer E2E는 ADR-008 후속.**
- [x] **ISSUE-R2-CORS-001 수정**: R2 CORS 정책 미설정으로 브라우저 직접 PUT 차단 → 백엔드 프록시 업로드(`POST /upload/file`, BE→R2 경유)로 수정. TDD 3 테스트 추가 + FE 훅 전환 (commit 9a62d02 + 08cae59).

## Recently Completed — Sprint 9 오디오 파이프라인 수리 (2026-05-12)

- [x] **CRITICAL 버그 수정**: `MeetingPipelineService` BackgroundTask 세션 수명 버그 — request-scoped `AsyncSession`이 HTTP 응답 직후 닫혀 BackgroundTask가 실패하던 문제. `session_factory` 패턴으로 교체 (독립 세션 생성). `database.py` + `dependencies.py` + `pipeline_service.py` + `test_pipeline.py` 수정. 82 테스트 통과.
- [x] **D-11 해소**: `MeetingSummary.key_decisions / topics` 타입 어노테이션 `dict` → `list` 수정 (`models.py`).
- [x] **FE 폴링 수정**: `POLLING_STATUSES`에서 `"embedding"` 제거 (백엔드가 설정하지 않는 상태, `hooks.ts`).

## Recently Completed — Sprint 7 "guarded-doors" 잔여 (2026-05-11)

- [x] **BE-T4/T11/T5**: CORS exception handler — 5xx/4xx/422 응답에 CORS 헤더 보장 (c60ad90)
- [x] **BE-T12**: GET `/workspaces/{wid}/projects/{pid}` workspace mismatch 검증 추가 (2b7c2d4)
- [x] **BE-T6**: TestContainers PostgreSQL 통합 테스트 6개 시나리오 (d1e65e2)
  - add_member 성공 / cross-ws 403 / notfound 404 / ws-mismatch 404 / 중복 / GET mismatch
- [x] **BE-BUG-1**: ProjectRepository.add_member workspace_id 누락 수정 (d1e65e2 포함)
- [x] **T-DOC-1**: `docs/requirements/interview-guide.md` 신설 — ADR-011 §2 7필드 우회 질문 (c2e5198)
- [x] **erd.md + endpoints.md Atomic Update**: cross-workspace 주석(I-17) + BE-T12 GET 404 (c2e5198)
- [x] **AD-33**: cross-workspace ProjectMember 차단 완전 구현 (Sprint 7 BE-T1~T3 + T13 + T12 통합)

## In Progress

- (없음 — 다음 Next Actions 참조)

## Recently Completed — Sprint 17 Workspace Switcher UI (BL-014/015/018, 2026-05-15)

- [x] **BL-014** Workspace switcher dropdown — `frontend/src/features/workspaces/components/WorkspaceSwitcher.tsx` 신설. header.tsx topbar 좌측에 wire. trigger = `{name} + WorkspaceTypeBadge + (team only) memberCount + ChevronDown`. options에 type badge inline + 활성 워크스페이스 Check 마크 + 새 워크스페이스 inline create.
- [x] **BL-015 (부분)** `WorkspaceTypeBadge` shared 컴포넌트 — `Lock`(Personal) / `Users`(Team) + 11px Geist Mono. Switcher trigger + options 2곳 적용. F-17 Recall card는 topbar context redundancy 회피로 wontfix. F-40 PromoteModal은 기존 Users icon + Team only filter 유지.
- [x] **BL-018** DESIGN.md atomic update — §Recall UI `capture row` + `tabs` 제거 (search-first FAB 실제 구현 반영). Bottom Nav 5th [검색] → [메모]. Workspace Switcher Dropdown Spec 인라인 lock-in. Decisions Log 2026-05-15 entry 추가.
- [x] **BE 수정** `WorkspaceResponse` schema + `create_workspace` / `get_workspace` service dict에 `type` 필드 노출 (legacy row default 'team'). list_workspaces는 기존 노출 유지.
- [x] **FE util** `inferWorkspaceType()` — BE 응답 누락 시 `"...의 개인 Kairos"` suffix match fallback.

**Atomic Update sync**: DESIGN.md (§Workspace Types + §Recall UI + Decisions Log + Bottom Nav) / REFACTORING-BACKLOG (BL-014/015/018 closeout).
**검증**: BE pytest 155 pass / FE tsc clean / eslint clean / 회귀 0건.

## Recently Completed — Sprint 6 Dogfooding + Critical 회귀 fix (2026-05-11, PR #14)

- [x] **Sprint 6 dogfooding 자동 검증** — Playwright MCP + BE API 직접 호출. owner 1 user 세션으로 8 케이스 자동 통과 (1G/1H/2A/3A/3B/3G + SETUP). 결과는 `git history`.
- [x] **PR #14 fix(workspaces): timezone-naive 통일** — dogfooding에서 발견한 Critical 회귀 patch. `datetime.now(UTC)` → `datetime.utcnow()` (workspaces 모듈 3 파일). 회귀 시점 `da33af54` (2026-04-04, Sprint 4/5, **Sprint 6 무관**). 다른 도메인 모듈 패턴과 통일. 신규 사용자 가입 직후 워크스페이스 생성 정상화.

## Recently Completed — Sprint 6 멤버십 + Private 프로젝트 (2026-05-11, PR #12 머지)

- [x] **Sprint 6 — 멤버십 + Private 프로젝트** (ADR-009 F1 + ADR-014 옵션 A 적용, 11 commits)
  - [x] BE-T1~T3 Project.visibility 컬럼 + 마이그레이션 c4c5709a4ab4 (commit e779541)
  - [x] BE-T5~T8 + T15 ProjectMember 엔티티 + 마이그레이션 754f571d5544 + visibility 권한 분기 (commit cecc888)
  - [x] BE-T9~T14 notes/rag pipeline_service 도입 — D-2/D-3 부채 해소 1차 (commit 8096314)
  - [x] BE-T17~T19 WorkspaceInvite default_project_visibility + 마이그레이션 2d128def6779 (commit 05957c8)
  - [x] V-T1 backend test 회귀 fix (commit d5b325d, 65 passed)
  - [x] T-CONST-1 + T-CONST-2 헌법 §4.2/§7 갱신 + ADR-009 F8 closeout (commit 12f031b)
  - [x] FE-T1/T2a/T2b/T3/T5 visibility 배지 + 변경 모달 + 초대 default visibility (commit 575c613, 시안 1A+1C / 3A)
  - [x] FE-T4 Project 멤버 관리 패널 (commit 9a975e7, 시안 2A inline 단순화)
  - [x] FE-T7 RAG 검색 Private 자동 제외 안내 (commit 6e3f87f)
  - [x] **ADR-014 신설** (`docs/adr/014-service-boundary.md`) — service-to-service 경계 정책 (commit 038fe37, PR #11)
  - [x] **F10 closeout patch** — ADR-011 §1을 PERSONA- 접두사 권위 출처로 확정 (commit 589a1aa, PR #10)
  - [x] **docs Atomic Update retrofit** (commit b1b24a4) — Critical 5 + High 3 = 8 문서 동기화 (per-context CONTEXT.md + ERD + endpoints + cross-domain-pipeline + rag-pipeline + directory-map)

**Sprint 6 자의 결정 라벨**: AD-19~35 (`/Users/woosung/.claude/plans/sprint-6-vivid-clarke.md` §5 + ADR-014 §"자의 결정")
**시안 산출물**: `~/.gstack/projects/woosung-dev-kairos/designs/sprint-6-visibility-20260511/` (9 PNG + design-board.html + approved.json)

## Recently Completed — Phase A (Stage 0 헌법 retrofit, 2026-05-11)

- [x] **Phase A — Stage 0 헌법 retrofit** (커밋 `cea0be9`) — 워크플로우 `.ai/templates/workflow.md` Stage 0 retrofit 완료.
  - [x] `CONTEXT-MAP.md` 도메인 헌법 신규 (14 엔티티 + I-1~I-16 불변식 + D-1~D-11 부채 식별)
  - [x] per-context `CONTEXT.md` 7개 (frontend, backend 전역, meetings, inbox, rag, projects, actions)
  - [x] CONTEXT.md ↔ ERD ↔ PRD 정합 lock-in

## Recently Completed — Phase B Stage 1 retrofit (2026-05-11)

- [x] **Phase B Stage 1 — 메타 retrofit** — 워크플로우 `.ai/templates/workflow.md` 정식 Stage 1 (`/office-hours` → `/autoplan`) 누락분 retrofit 완료. 6 forcing question 결과 + product-first demand 시그널 정의 + thesis lock-in. **코드 변경 없음**.
  - [x] **ADR-010** Future-Fit Thesis (`docs/adr/010-future-fit-thesis.md`) — 9.2/10 PASS (Round 3). 3-year vision · 3 위협(ChatGPT/Notion AI/Granola) · 4 moat(M1~M4) · L4 timeline risk · AD-5~9 자의 라벨.
  - [x] **ADR-011** Persona Definition (`docs/adr/011-persona-definition.md`) — 9.25+/10 PASS (Round 2 + 라벨 동기화). 상태 라벨 4단계(interview-confirmed/self-confirmed/[가설]/deprecated) · 필수 필드 7개 · Wedge W1~W4 · 폐기 기준 a/b/c · AD-10~12 자의 라벨.
  - [x] **ADR-009** Stage 1 Retrofit 총괄 (`docs/adr/009-stage1-retrofit.md`) — 9.0/10 PASS + 3건 정정 = 9.5+. 6 Q 결과 매핑 · S1~S6 demand 시그널 + 60% 통일 · D-2/D-3 보류(AD-15) · 후속 F1~F10.
  - [x] **personas.md** (`docs/requirements/personas.md`) — 9.33/10 PASS + 4건 정정 = 9.5+. PERSONA-001 self-confirmed + PERSONA-002~003 `[가설]` + Wedge 매트릭스 분화 점검 + 후속 인터뷰 패치 절차.
  - [x] **competitive-analysis.md** (`docs/requirements/competitive-analysis.md`) — 9.3/10 PASS + 5건 정정 = 9.5+. 5개 경쟁자(Otter/Granola/Reflect/Mem/Tana) 4차원 비교 · ADR-010 moat 정렬 · AD-16~18.
  - [x] **PRD 4개 섹션 batch PATCH** (`docs/requirements/prd.md`) — 9.5/10 PASS + 4건 정정 = 9.7+. §2 Persona 보강 + §2.5 Competitive Analysis + §3.5 Future-Fit Thesis + §7.5 Demand Signal Definition.
  - [x] **TODO.md PATCH** (본 문서) — Stage 1 retrofit 완료 마크 + 후속 등재.

## Recently Completed (온보딩 직전 릴리즈 스프린트)

- [x] 랜딩 페이지 다크 모드 하이드레이션 수정 — `(landing)` · `(app)` · `(auth)` 라우트 그룹 분리 (커밋 `13d5041`, `117f920`)
- [x] Smart Inbox · 회의 상세 3뷰 · 프로젝트 대시보드 실 API 훅 전환 (커밋 `13d5041`)
- [x] Today 피드 mock→실 API 전환 + Dashboard 상단 병합 (커밋 `d8a6d27`)
- [x] 온보딩 템플릿 프로젝트 자동 시딩 — `create_workspace()` 가 🚀 시작하기 · 💡 아이디어 · 📋 회의록 3개 프로젝트 자동 생성 + OnboardingBanner 안내 개편 (커밋 `1e54a5c`)
- [x] 사이드바 소스 트리 + Source Viewer 실 API 연동 — meetings 엔드포인트에 projectId 필터 추가, 펼침 시 하위 회의/노트 실 데이터 렌더, SourceViewer가 `useMeetingDetail`/`useNote`로 풀콘텐츠 보강 (커밋 `7aea79b`)
- [x] **DevEx 이니셔티브 (ADR-008)** — Playwright E2E 환경(골든패스 2개), BE 배포 자동화(deploy.yml + WIF + Secret Manager 가이드), `test.yml` 에 e2e 잡 추가 (이번 커밋)
- [x] 문서 정합성 통합 정리 (ADR-006 기준 전체 문서 정렬)
  - [x] cross-domain-pipeline.md: Claude → Gemini 수정
  - [x] para-methodology.md: deprecated 배너 추가
  - [x] ui-ux-spec.md: ADR-006 기준 전면 재작성 (C|D 2-Panel, Today 피드, Inbox 2그룹, RAG 오버레이)
  - [x] directory-map.md: PARA 라우트 제거, [paraId]→[projectId]
  - [x] 001-tech-stack-decisions.md: PARA 섹션 superseded 표시
  - [x] mvp-phase1.md + second-brain.md: Inbox 정책 ADR-006 통일 (0.8→0.9)
  - [x] DESIGN.md: C|D 2-Panel 레이아웃 + Project Status Colors 전환
  - [x] erd.md: camelCase → snake_case 통일
  - [x] prd.md: Inbox 임계값 + Phase/Sprint/Stage 용어 매핑 추가
  - [x] README.md: ADR-006 문서 목록 추가

## Blocked

(없음)

## 미구현 (요청됨)

(없음)

## Questions

- AI 모델 참조 통일 완료: Gemini `gemini-2.5-flash` 확정 (비용 사유)
  → `backend.md`, `global.md`에서 Anthropic → Gemini로 수정 완료

## Blocked — 사용자 작업 필요

- [ ] **T-3 Sprint 14 Clerk Production 인스턴스 발급** [확인 필요]
  - 위치: Clerk Dashboard → New Application → Production
  - 발급 후: `frontend/.env.local` + Vercel env 의 `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` / `CLERK_SECRET_KEY` 를 `pk_live_*` / `sk_live_*` 로 교체
  - 효과: 사인인 화면 "Development mode" 배지 제거 (Curious 핵심 망설임 #1)
  - 코드 측 (커밋 완료): `@clerk/localizations` koKR + SignIn/SignUp `forceRedirectUrl="/dashboard"`

## Next Actions

### Sprint 12 — Architecture Deepening (BL 등재, 2026-05-12) ✅ 완료

- [x] **BL-003 등재** (rag/ 도메인) — `RagService._enrich_context` N+1 → `find_chunks_by_ids` 배치화. `docs/REFACTORING-BACKLOG.md` 등재 완료.
- [x] **BL-004 등재** (services/ 도메인) — co-change 재분석으로 발굴. `ai_processing.py` ↔ `common/prompts.py` 암묵적 JSON 계약 → Pydantic 경계 검증 추가. `docs/REFACTORING-BACKLOG.md` 등재 완료.
- [x] **meetings/ 도메인 audit** — BL-001 미실행 항목 이미 등재됨. export 중복 쿼리 발견, BL-001과 묶어 처리 결정. 추가 BL 불필요.
- 발굴 산출물: BL-003/BL-004 신규 등재. BL-002 완료 마킹. rag/services audit dev-log 신설.

### Sprint 13 — BL-003/004 구현 (2026-05-12) ✅ 완료 (PR #21 머지)

- [x] **BL-003 구현** — `EmbeddingRepository.find_chunks_by_ids()` 추가 + `_enrich_context` N+1 → 배치 1회. 테스트 3개 추가.
- [x] **BL-004 구현** — `MeetingSummaryResult` / `MeetingActionsResult` Pydantic 모델 추가 + `ai_processing.py` 경계 검증. 테스트 4개 추가.
- [x] **pyrightconfig.json** — backend/ + 루트 추가. IDE Pyright venv 경로 설정.
- 테스트: 신규 7개 추가 (BL-003: 3, BL-004: 4) / 전체 87 passed

### Sprint 14 — 가입 첫 5분 신뢰 회복 + RAG 안정화 (2026-05-14 완료, PR 대기)

> 입력: Multi-Agent QA 통합 보고서 (`git history`)
> 상세: `git history` · 검증: `git history`
> 브랜치: `sprint-14/trust-stabilize` (origin/main off)

**P0 (Critical) — 4건 ✅**
- [x] **T-1 BUG-C01** RAG `/rag/ask` 5xx graceful degrade (`4eb6f3a`) — Gemini try/except + SSE error event + RagAskRequest max_length=500 + strip→≥2자. 신규 테스트 12개.
- [x] **T-2** "오늘 할 일" 사이드바 메뉴 404 숨김 (`c22684d`).
- [x] **T-3** Clerk koKR localization + /dashboard force redirect (`9ea1a78`). Production 키 발급은 사용자 Blocked.
- [x] **T-4** "RAG" → "AI 검색" 사용자 노출 카피 11곳 + 시드 2곳 치환 (`26ab7d5`) + `features/rag/CONTEXT.md` 카피 정책 lock-in.

**P1 (High) — 7건 ✅**
- [x] **T-5 BUG-H03** UpdateWorkspaceSettingsRequest 헌법 I-16 위반 fix + AST introspection 회귀 차단 (`3699b9d`). 11 Request audit 결과 1건 위반 → 0건.
- [x] **T-6 BUG-H02** visibility 모달 race condition fix (`0bf01e6`) — useWorkspaceRole isLoading + onClick closure 회피.
- [x] **T-7 BUG-H01** dashboard stale ws + setState-in-render fix (`1d246eb`) — useEffect 분리 + Header useWorkspaces 가드 + 로그아웃 queryClient.clear.
- [x] **T-8 BUG-H04** meeting detail projects 동기화 (`8532ab5`) — ProjectRepository.find_projects_by_meeting 호출. 신규 테스트 3개.
- [x] **T-9** Inbox 카운트 사이드바↔페이지 동기화 (`79872a2`) — 정책 lock-in: 사이드바 = 미처리 항목 수.
- [x] **T-10** 모바일 햄버거 토글 숨김 (`1a6d3b3` 묶음).
- [x] **T-11** 모바일 BottomNav "메모" 진입점 (`1a6d3b3` 묶음) — 검색 자리 swap.

**검증 + dogfooding** — `sprint-14-verification.md` 산출. Backend 110 PASS / FE typecheck PASS / 신규 테스트 18개 모두 PASS / 회귀 0건.

**메트릭**: Composite Health 6.8 → ~8.0/10 (추정) · Curious Maybe → Yes (조건부) · Casual 용어 해독률 37.5% → ~50%+ · 자의 결정 AD-36~39.

### Sprint 14 — Out of Scope (Sprint 15+ 보류)
- 신규 가입자 onboarding tour (빈 워크스페이스 첫 5분 가치 도달 경로 — 별도 디자인 필요)
- BUG-M01~M06 + L01~L02 (Sentinel polish)
- 마케팅 트랙 (가격 / 고객 로고 / 비교표 / 보안 페이지) — dev 단독 처리 불가
- AD-35 multi-user E2E (Clerk testing mode 도입 후)

### Sprint 15 — DRAFT PR #29 pushed (2026-05-14)

> **상태**: 단일 draft PR https://github.com/woosung-dev/kairos/pull/29 (52 commits, 76 files, +12570/-20). R8 14일 stagger 결과 후 main 머지.
> **Stage 5 진행**: 5-1~5-7 완료. 5-8/5-9 머지 후.
> **R8 미시작**: PR 본문 §"R8 외부 검증 결과" TBD placeholder. retro fill-in 후 PR 댓글로 결과 추가.
> **Sprint 16 진입 조건**: R8 결과 → Best/Medium/Min 분기 (`git history`).

### Sprint 15 후보 — Personal Workspace + IA 확장 (2026-05-14 PRD v3.0 lock-in)

> 입력: `docs/requirements/prd.md` v3.0 §3.6 IA 2축 로드맵 + 사용자 의견 (개인↔팀 전환 IA, CLAUDE.md/local.md 비유)
> ADR 신규 예정: ADR-016 Personal↔Team IA + Promotion flow

**v1.5 — Personal workspace 자동 생성 + switcher (Sprint 15 핵심)**
- [ ] **S15-T1** 신규 가입 시 "{사용자명}의 개인 Kairos" personal workspace 자동 시드 (BE)
- [ ] **S15-T2** Workspace switcher UI 우상단 (FE — Notion 패턴 차용)
- [ ] **S15-T3** Personal workspace 권한 모델 lock-in — 항상 1명, 팀 초대 불가 (BE schema 제약)
- [ ] **S15-T4** ADR-016 작성 — Personal↔Team IA 결정 근거 + visibility=personal 신설 여부 (현 분석: workspace 단위 분리 채택, project visibility 4번째 추가 안 함)
- [ ] **S15-T5** 온보딩 UX — 초기에는 personal만 노출, "팀 합류" 액션 시 team workspace 안내
- [ ] **S15-T6** PRD §7-Marketing tagline 외부 테스트 — 인디해커즈/X DM 50명 A/B 반응 → 1개 lock-in

**Sub-task — RAG 인프라 모니터링 (Qdrant 트리거 #3 자동 감지)**
- [ ] **S15-T7** RAG p50/p95 응답 시간 + 벡터 수 카운터 OpenTelemetry/Sentry 메트릭 추가 (부록 B 트리거 #3)

**검증**: 1인 founder가 신규 가입 → 7일 자기 personal에서만 사용 → 팀 합류 시점 시뮬레이션. 메모리 누락 0건 + workspace 전환 클릭 0 confusion.

### Sprint 16 — pgvector 최적화 ✅ 완료 (PR pending, 2026-05-15)

> 코드네임: `karrot-eager-marshmallow` (Stage 0~4) + `pure-clover` (Stage 5/6)
> 워크트리: `~/project/agy-project/kairos-pgvector-opt` (`sprint-16/pgvector-optimization` 브랜치)
> ADR-020 Accepted — `docs/adr/020-pgvector-hnsw-halfvec.md`
> Verification — `git history`

- [x] Stage 0~6 풀워크플로우 + Atomic Update 매트릭스 강제
- [x] HNSW + halfvec + iterative_scan 전환 (alembic b2c3d4e5f6a7)
- [x] **AD-56 정정** (Stage 5 측정 발견) — 컬럼 타입 변경 마이그레이션은 ivfflat drop 동일 revision 강제 (operator class 호환성). expression index 패턴 전용 별도 PR drop 원칙과 분리
- [x] memory 도메인 `HalfVector` 직렬화 회귀 fix (`src/memory/repository.py:275` — `to_list()` 폴백)
- [x] bench_vector_search.py 런타임 init 누락 fix (init_engine + get_session_factory 명시)
- [x] test_halfvec_migration.py `:uid::uuid` asyncpg cast syntax fix (`CAST(:uid AS uuid)`)
- [x] BL-022(파티셔닝) / BL-023(컬럼분리) / BL-024(pg_prewarm) / BL-025(read replica) / BL-026(측정강화) 등재
- [x] 통합 테스트 10/10 PASS + Sprint 16 격리 BE 155/155 PASS

**후속 (별도 PR / Sprint)**:
- [x] ADR-019 Phase B (Gemini 2.5-flash → 3.1-flash-lite swap, 6 spots) — **2026-05-15 적용 완료** (AD-57 정정으로 R8 demo 종료 전 앞당김. EOL D-33 압박 + R8 미시작 확인). 브랜치 `sprint-17/adr-019-phase-b-gemini-swap`. pytest 155 pass 회귀 0건.
- BL-024 pg_prewarm Cloud Run cold start
- BL-026 옵션 A — dev DB export + ground truth 절차 (production scale recall 측정)

---

### Sprint 17 후보 (전 Sprint 16 후보) — Promotion Action + 음성 메모 ingest (2축 동시 진입)

> 입력: PRD v3.0 §3.6 2축 로드맵 (X v2 음성 + Y v1.6 promote). pgvector 최적화가 Sprint 16 점유 → 본 후보 Sprint 17로 이동.

**v1.6 — Promotion 액션**
- [ ] **S16-T1** 아이템(노트/회의/액션)에 "Promote to Team..." 액션 + 대상 workspace+project 선택 모달 (FE)
- [ ] **S16-T2** Promotion BE API — 메타데이터 + 임베딩 복제 (이동 아님, 원본 tombstone 유지)
- [ ] **S16-T3** Promotion audit log + 헌법 I-18 신설 ("Promotion은 항상 복제 + tombstone, 이동 금지") — I-17 slot은 Sprint 7 BE-T13 cross-ws ProjectMember 차단으로 점유

**v2 — 음성 메모 ingest (회의 외 단독 녹음)**
- [ ] **S16-T4** `/new` 페이지에 "음성 메모" 탭 추가 (회의와 분리, transcript 부재 OK)
- [ ] **S16-T5** Voice note 모델 (Meeting과 별개) + STT + Gemini 요약 + 태그 자동
- [ ] **S16-T6** Personal workspace에서 음성 메모 첫 진입 시나리오 lock-in

### Sprint 17+ candidates (Sprint 15 lock-in)

- [x] **P0 S17-T-GEMINI-EOL** — Gemini 2.5 Flash EOL 2026-06-17 대응. **ADR-019 Accepted** (Phase A spike 2026-05-14 / Phase B swap 2026-05-15). `gemini-3.1-flash-lite` GA 채택. spike 결과: distill 5.76x speedup / 20% cost 절감 / schema 3/3. 별도 Pro/Flash 2.0 마이그레이션 plan 불필요 (단일 단계 swap으로 종료).

### 진행 중 (ADR-008 DevEx 후속)

- [ ] **GCP WIF 초기 설정 + Secret Manager 9개 이관** (사용자 작업) — `docs/guides/deployment.md` §2.5.1 참조
- [ ] Clerk testing mode 계정 생성 + GitHub `E2E_*` Secrets 등록 (E2E 활성화)
- [x] **FE ↔ BE 오디오 파이프라인 E2E 검증** (업로드 → STT → Inbox — Sprint 9/10 완료, 2026-05-12)
- [ ] FE ↔ BE 전체 E2E 시나리오 (신규 계정 → 템플릿 프로젝트 3개 → RAG → `[1]` → Source Viewer 풀콘텐츠 렌더) — ADR-008 후속

### Sprint 6 잔여 (sprint 7+ 보류, AD-32~35) — 2026-05-11 dogfooding 결과 반영

- [ ] **AD-32** BE-T16 Project update 권한 강화 — 현재 require_member 유지 결정. creator-only 또는 admin 강화 필요 시 sprint 7+ 검토 (협업 마찰 우려).
- [x] **AD-33** ProjectMember 추가 cross-workspace 차단 — **Sprint 7 완료** (BE-T1~T3 + T12 + T13). FK violation 500 → 의도된 403으로 전환. TestContainers 통합 테스트 검증.
- [ ] **AD-34** FE RBAC 정밀 분기 — visibility 변경 버튼이 모든 멤버에 활성 + BE-T15 403 위임 (1차). useUser+useMembers 매칭으로 정밀화 = sprint 7+ design-review. dogfooding scope 외, sprint 7+ design-review 보류 **확정**.
- [ ] **AD-35** Playwright E2E (V-T2) + schemathesis (V-T4) + RAG 권한 누설 E2E (V-T5) — sprint 7+ devex-review와 묶음. **2026-05-11 dogfooding으로 1A~1F viewer/member 읽기 + 2D Private RAG 누설 + 2E/2F member/viewer visibility 변경 시도 + CORS-1 (BE 5xx CORS 헤더 누락) + SCHEMA-1 (Project `title` vs ERD `name` 정합성) 추가 묶음**.
- [x] **사용자 수동 dogfooding** — Playwright MCP 자동화로 진행 (8 케이스 자동 통과 + Critical TZ-1 회귀 발견 PR #14). 결과 `git history`.

### Sprint 6 후속 docs (Medium 보류 4개 중 1개 완료)

- [x] **T-CONST-3** TODO.md Sprint 6 완료 마크 (본 patch)
- [ ] docs/requirements/prd.md — Sprint 6 phase 표 업데이트 (다음 sprint 또는 별도 patch)
- [ ] docs/requirements/second-brain.md §8 — visibility로 "개인↔팀 경계" 부분 해소 표기
- [ ] AGENTS.md — visibility 도메인 용어 추가 (작음)

### Phase B Stage 1 retrofit 후속 (ADR-009 §"후속" F1~F10)

- [ ] **F2** Demand 시그널 S1~S4 측정 (Sprint 6 완료 후 1개월) — usage analytics 도입 + S1(DAU)/S2(회의 빈도)/S3(RAG 만족도)/S4(Inbox 수용률) 실측. 결과물: demand 시그널 1차 보고서.
- [x] **F3** 외부 인터뷰 가이드 작성 — `docs/requirements/interview-guide.md` Sprint 7 T-DOC-1 완료 (c2e5198).
- [ ] **F4** 외부 인터뷰 5-10명 + S5/S6 측정 (진행 중, 2026-05-12 착수) — ADR-010 AD-8 60% + ADR-011 §4-b 60% + ADR-009 S5/S6. 결과물: `docs/requirements/interview-results.md`, ADR: `docs/adr/015-f4-demand-signals.md`.
- [ ] **F5** 5분 사용자 세션 관찰 도입 (Sprint 7+, Q5) — 도그푸딩 사용자 1-3명 세션 녹화. 결과물: `docs/requirements/observation-notes.md`.
- [ ] **F6** Wedge 선정 ADR 신규 (Sprint 6 완료 + F2/F4 결과 후) — 페르소나-Wedge 매트릭스 + S5/S6. 결과물: `docs/adr/012-wedge-selection.md`.
- [ ] **F7** L4 우선화 검토 ADR 신규 (Sprint 6 완료 + F4 결과 후) — ADR-010 §4 O1/O2/O3 옵션 선택 + ADR-007 Phase 4 진입 결정. 결과물: `docs/adr/013-l4-prioritization.md`.
- [ ] **F8** 부채 D-2/D-3 처리 ADR 신규 (Sprint 6 킥오프 시 결정 — 진입 직전 vs 완료 후) — service-to-service 경계 정책. 결과물: `docs/adr/014-service-boundary.md`.
- [ ] **F9** ADR-009 본 ADR 갱신 검토 (Sprint 7+ 외부 인터뷰 완료 후) — S1~S6 실측 결과로 임계값 재조정.
- [x] **F10** `.ai/common/global.md` §2 ID 체계 표 갱신 — `PERSONA-` 접두사 추가. Sprint 10 확인 (global.md line 47에 이미 존재, git-ignored 로컬 파일).

### `[가설]` 페르소나 패치 일정

- [ ] PERSONA-002 (김PM) — F4 외부 인터뷰 결과로 `interview-confirmed` 또는 `deprecated` 결정 (ADR-011 §4-b 60% / 3필드 임계값).
- [ ] PERSONA-003 (박PM) — 동상.

### 향후

- [ ] 내보내기 포맷 PDF (향후 구현)
