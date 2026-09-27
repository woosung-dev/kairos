# 실사용 준비 체크리스트 (2026-09-26 정검 기준)

> 근거: [`report.md`](report.md) (결함 ID) · [`doc-drift-e3.json`](doc-drift-e3.json) (D-ID) · `docs/TODO.md` · `docs/REFACTORING-BACKLOG.md`
> 기준 코드 `main 1d2eac0`. **프로덕션은 #194 이전 빌드다** (OPS-2).
> 담당: **사용자** = 대시보드·계정·법률·결정 / **Claude** = 코드·문서·스크립트.
> 시간은 작업자 기준의 실작업 시간이다 (리뷰·배포 대기 제외).

## 게이트 정의

| 게이트 | 의미 | 진입 조건 |
|---|---|---|
| **Gate 0** | 첫 외부 사용자 (초대제 클로즈드 베타, 수십 명) | 아래 Gate 0 전 항목 ✅ |
| **Gate 1** | 공개 가입 오픈 (누구나 가입) | Gate 0 + Gate 1 전 항목 ✅ |
| **Gate 2** | 유료화 | Gate 1 + Gate 2 전 항목 ✅ |

---

## Gate 0 — 첫 외부 사용자 전 (반드시)

### A. 권한 누수 차단 (P0/P1) — 합계 약 2.5~3일

| # | 항목 | 담당 | 시간 | 검증 | 근거 |
|---|---|---|---|---|---|
| 0-1 | [x] ✅ 2026-09-27 Phase 2 PASS (T-01~T-08, [`phase2-results.md`](phase2-results.md)) · e2e spec 은 추가하지 않았다 — pytest 통합 테스트 + 라이브 Playwright 탐침(T-05/T-07 UI 포함)으로 검증, spec 은 BL-LR-14 — **회의 가시성 규칙을 파생 데이터에 적용** — RAG 청크 검색·인박스 목록·추출 액션 목록에 `_meeting_visibility_filter` 와 같은 규칙(링크 0개 통과, 접근 가능한 링크가 1개라도 있으면 통과)을 적용한다 | Claude | 1~1.5일 | viewer 가 private 회의에 대해: RAG 소스 0 · `/inbox` 요약 0 · `/action-items` 0. pytest 회귀 + e2e 1건 | C-014 · C-015 · C-016 |
| 0-2 | [x] ✅ 2026-09-27 Phase 2 PASS (T-09~T-13, [`phase2-results.md`](phase2-results.md)) — **회의↔프로젝트 링크 API 에 가시성 검사** — POST/DELETE 와 inbox classify 에서 요청자가 회의와 대상 프로젝트를 모두 볼 수 있어야 한다. 아니면 404 | Claude | 3h | member 가 숨겨진 회의 링크 POST/DELETE → 404, 그 뒤 viewer GET 회의 → 여전히 404 | C-018 |
| 0-3 | [x] ✅ 2026-09-27 Phase 2 PASS (T-14~T-17 · T-18c, [`phase2-results.md`](phase2-results.md)) — **프로젝트 PATCH 가시성 게이트 + status 검증** — `get_project` 와 같은 접근 판정을 쓴다. status 는 `Literal`, archived 전환은 admin 만. **visibility 변경은 admin 또는 프로젝트 작성자** (2026-09-27 결정 U-4) | Claude | 2h | 비멤버 member PATCH → 404, `status="zzz"` → 422, 작성자 member 가 자기 프로젝트 visibility 변경 → 200, 남의 프로젝트 → 403 | C-017 · U-4 |
| 0-4 | [x] ✅ 2026-09-27 Phase 2 PASS (T-18 · NF-E2-*, [`phase2-results.md`](phase2-results.md)) — **Memory 작성자 전용 적용** — 2026-09-27 결정 **(a)**: 팀 WS 메모도 작성자만 본다. recall·GET·promote·RAG·RAG 캐시 모두 (I-24) | Claude 2~4h | viewer·owner 가 남의 메모 recall 0건 · GET 404 · RAG 소스 0 | C-020 · OPS-3 · U-2 |
| 0-5 | [x] ✅ 2026-09-27 Phase 2 PASS (T-19 · T-20, [`phase2-results.md`](phase2-results.md)) — **새 프로젝트 제안이 인박스에서 사라지는 문제** — existingProjectId 가 없으면 `is_processed=false` 로 둔다. FE `addMeetingProject` 를 POST 로 고치고 회의 상세에 링크 UI 를 추가한다 | Claude | 4h | 신뢰도 0.95 새 프로젝트 제안이 `/inbox` 에 남음, 회의 상세에서 링크 가능 | C-002 |
| 0-6 | [x] ✅ 2026-09-27 Phase 2 PASS (T-21 · T-22, [`phase2-results.md`](phase2-results.md)) — **실패 회의 errorMessage 정제** — 분류 코드와 일반 문구만 저장하고 원문은 logger 로만 남긴다. 기존 failed 행도 정리 | Claude | 1h | `GET /meetings/{failed}` 응답에 `r2.cloudflarestorage` 0건 | C-023 |
| 0-7 | [x] ✅ 2026-09-27 Phase 2 PASS (T-23, [`phase2-results.md`](phase2-results.md)) — **Next.js ≥ 16.3.3 업그레이드** — critical GHSA-2xp9 (AVIF 최적화 RCE). 현재 16.2.11. remotePatterns 설정이 없어 실제 악용 조건은 좁다 | Claude | 30분 + 빌드 | `node -e "require('next/package.json').version"` ≥ 16.3.3, dependabot next 알림 4건 해소 | dependabot #154~157 |

### B. 초대 → 첫 사용 흐름 — 약 3h

| # | 항목 | 담당 | 시간 | 검증 | 근거 |
|---|---|---|---|---|---|
| 0-8 | [x] ✅ 2026-09-27 Phase 2 PASS (T-24 · T-25, [`phase2-results.md`](phase2-results.md)) — 초대 수락 뒤 활성 WS 고정 — 수락 onSuccess 에서 ownerUserId 까지 세팅한다. `find_by_user` 에 ORDER BY 명시 | Claude | 1h | 빈 브라우저에서 두 번째 팀 초대 수락 → 그 팀에 착지 | C-001 |
| 0-9 | [x] ✅ 2026-09-27 Phase 2 PASS (T-26 · T-27, [`phase2-results.md`](phase2-results.md)) — 초대 페이지에 "가입하고 참여" 추가 + 로그인↔가입 전환 링크가 `callbackURL` 을 유지 | Claude | 1h | 계정 없는 사용자: 초대 링크 → 가입 → 초대 페이지 복귀 → 참여 | E2-X01 |
| 0-10 | [x] ✅ 2026-09-27 Phase 2 PASS (T-28 · T-29 · T-30, [`phase2-results.md`](phase2-results.md)) — 중복 가입 한국어 문구 + 422 "[object Object]" 수정 | Claude | 1h | 기존 이메일 가입 → "이미 가입된 이메일입니다", 😀×25 캡처 → 읽을 수 있는 문구 | C-024 · C-025 |

### C. 운영 안전망 — 사용자 약 1h + Claude 약 4h

| # | 항목 | 담당 | 시간 | 검증 | 근거 |
|---|---|---|---|---|---|
| 0-11 | [ ] **Claude 부분 ✅ 2026-09-27** (스크립트 + 복원 리허설 T-31 PASS, 32 테이블 일치. `--local-only` 로 돌렸고 R2 업로드는 stub 으로만 검증) · **사용자: 서버 cron 등록 · R2 lifecycle(`backups/kairos/` N일 `[확인 필요]`) · `.env` 별도 보관 남음 — 첫 서버 실행이 실제 R2 업로드 검증** — **DB 백업 자동화 + 복원 리허설 1회** — 일 1회 `pg_dump` → R2(별도 prefix) | Claude 스크립트 2h · **사용자** 서버 cron 등록 10분 | 새 컨테이너에 복원 → 주요 테이블 row count 가 원본과 일치 | BL-OCI-1 (TODO.md:105) |
| 0-12 | [x] ✅ 2026-09-27 Phase 2 PASS (T-32, [`phase2-results.md`](phase2-results.md)) · 근거의 D-001(voice 메모 TTL 실행 수단)은 1-12 로 남음 — **`r2-cleanup.yml` 삭제 모드 차단** — 문서의 "고아 정리" 안내를 고치고, 스크립트를 `meetings.file_key` 대조 방식으로 바꾸거나 워크플로를 비활성화한다. **그 전까지 `delete=true` 실행 금지** | Claude | 1h | dry-run 목록에 참조 중인 회의 원본 0건 | D-001 · D-002 · OPS-1 |
| 0-13 | [ ] **HTTPS 강제 + HSTS** — Cloudflare "Always Use HTTPS" + HSTS, 두 호스트 모두 | **사용자** | 10분 | `curl -sI http://kairos.woosung.dev/` → 301, `curl -sI https://kairos.woosung.dev/ \| grep -i strict-transport` 1줄 | C-011 |
| 0-14 | [ ] **프로덕션을 main 최신으로 배포** (#194 포함, 위 수정 반영 후) | Claude 실행 · **사용자** 승인 | 30분 | 인증 없이 `GET .../integrations/google-drive/documents` → 401(405 아님), 응답에 CSP-Report-Only 헤더 | OPS-2 |
| 0-15 | [ ] **Google 동의 화면 "테스트 중" 대응** — 베타 사용자 이메일을 테스트 사용자로 등록한다 (최대 100명). [가정: 테스트 모드에서는 Google 로그인이 등록된 사용자만 되고, Drive refresh token 이 7일 뒤 만료됨] | **사용자** | 15분 | 등록하지 않은 계정으로 Google 로그인 → 차단 확인, 등록한 계정 → 성공 | ADR-031:45 |
| 0-16 | [x] ✅ 2026-09-27 Phase 2 PASS (T-36, [`phase2-results.md`](phase2-results.md)) — **비밀번호 분실 = 운영자 수동 재설정 runbook** (2026-09-27 결정 U-3: 이것으로 충분) | Claude runbook 30분 | 로컬에서 runbook 대로 테스트 계정 재설정 1회 | TODO.md:259 · U-3 |
| 0-17 | [ ] **Clerk 잔재 정리** — Clerk dev 인스턴스 삭제(노출된 dev secret 무효화), 서버 `.env` 의 CLERK_* 제거. `clerk_id` DROP 은 프로덕션 레거시 행 확인 뒤 2단계로 (BL-LR-11, Gate 0 밖) | **사용자** 15분 | Clerk 대시보드에 인스턴스 없음, `grep CLERK ~/kairos/.env` 0건 | D-038 · TODO.md:263 · BL-LR-11 |
| 0-18 | [ ] **nightly e2e 복구** — 2026-08-17 이후 40회 연속 실패 중. ★2026-09-27 워크플로 이식 완료(PR-A, 주 1회 + 배포 전 dispatch · CI 전용 R2 · pg17) — dispatch success 확인 전까지 `[ ]`. ★2026-09-27 정정: secret 등록만으로는 안 된다 — `nightly-e2e.yml` 이 Better Auth 이전 구성이라 FE build/start 에 `BETTER_AUTH_SECRET` 을 넘기지 않고 BE 에 `AUTH_JWKS_URL`·`AUTH_JWT_ISSUER` 도 없다 (`test.yml` e2e job 은 env 로 직접 넘긴다). 워크플로 이식 필요 (BL-LR-15) | Claude 워크플로 이식 1h · **사용자** dispatch 확인 5분 | 1h | `gh workflow run nightly-e2e.yml --repo woosung-dev/kairos` → success | 실패 로그 "You are using the default secret" |
| 0-19 | [ ] **main 보호** — ruleset 으로 `ci-required` 를 required check 로 등록 | **사용자** | 5분 | `gh api repos/woosung-dev/kairos/rulesets` 가 빈 배열이 아님 | TODO.md:254 (현재 "Branch not protected") |
| 0-20 | [ ] **stuck 회의 대응 절차 확인** — 배포 전 `mise run deploy-preflight` 결과가 0 인지 사람이 본다. 멈춘 회의는 runbook 으로 복구 | **사용자** | 10분 (1회 숙지) | `docs/operations/runbooks/stuck-pipeline.md` 를 1회 따라 해 봄 | BL-OCI-4 · D-013 |

**Gate 0 합계**: Claude 약 4~5일 · 사용자 약 1.5h. 결정 2건(0-4 · 0-16)은 2026-09-27 완료.

---

## Gate 1 — 공개 가입 오픈 전

| # | 항목 | 담당 | 시간 | 검증 | 근거 |
|---|---|---|---|---|---|
| 1-1 | [ ] **이용약관 · 개인정보처리방침** — 국외 이전 고지·동의 포함 (OpenAI·Google Gemini 는 미국, Cloudflare R2). 가입 화면에 동의 체크 | **사용자** 법률 검토 · Claude 페이지 2h | `/terms` `/privacy` 200, 가입 시 동의 기록 | 해당 라우트 0건 (`app/(landing)` 에 pricing 만) |
| 1-2 | [ ] **회원 탈퇴 + 데이터 삭제 경로** — 개인 WS·메모·R2 원본 포함 | Claude | 1일 | 탈퇴 후 `auth_user`·개인 WS·청크 0, 팀 WS 소유권 처리 규칙 | 코드에 deleteUser 없음 |
| 1-3 | [ ] **이메일 발송 인프라** — 가입 인증 + 비밀번호 재설정 (Resend 등 + `sendResetPassword`) | Claude 0.5~1일 · **사용자** 도메인 DNS 30분 | 재설정 메일 수신 → 새 비밀번호 로그인 | TODO.md:259 |
| 1-4 | [ ] **Google OAuth 앱 게시 + 브랜드 검증** | **사용자** | 1h 작업 + 심사 대기 수일~수주 | 테스트 사용자가 아닌 계정으로 Google 로그인 성공 | ADR-031:39-45 |
| 1-5 | [ ] **BE rate limit + AI 비용 상한** — 사용자·워크스페이스별 일 한도 (캡처·RAG·음성 분) | Claude | 1일 | 한도 초과 시 429 + 안내, 일일 비용 상한 알림 | BE 에 rate limit 코드 0건 |
| 1-6 | [ ] **외부 uptime 감시 + 에러 알림** — 관측이 `docker logs` 뿐이다 | Claude 2h · **사용자** 서비스 가입 15분 | `/health` 를 5분 간격으로 감시, 장애 시 알림 수신 테스트 1회 | ADR-028 (Sentry 제거) |
| 1-7 | [ ] **회의 삭제** (+ R2 원본 삭제, promote 사본 처리) | Claude | 0.5~1일 | 회의 삭제 → 청크·링크·액션·R2 객체 정리 | BL-UX-4 · C-028 |
| 1-8 | [ ] **P2 결함 묶음** — 분류 후보를 요청자 기준 active 로 · 생성 시 projectId · 멤버 목록 게이트 · RAG 캐시 키에 sourceType · 노트 flush · 인박스 되돌리기 · 고아 청크 | Claude | 1.5~2일 | 각 ID 의 재현 절차가 모두 차단됨 | C-003 · C-004 · C-019 · C-022 · C-026 · C-027 · E1-N1 |
| 1-9 | [ ] **헤더 하드닝** — CSP enforcing 전환 (Report-Only 위반 0건 확인 뒤), `poweredByHeader:false`, robots/sitemap | Claude | 2h + 배포 후 1일 관찰 | 응답에 `content-security-policy` 있음 · `x-powered-by` 없음 · `/robots.txt` 200 | C-012 · C-013 · BL-S27e-3 |
| 1-10 | [ ] **로그인 rate limit IP 설정** — `advanced.ipAddress.ipAddressHeaders=['cf-connecting-ip','x-forwarded-for']` | Claude | 30분 | 프로덕션 로그에 "could not determine a client IP" 0건 | C-009 |
| 1-11 | [ ] **stuck 파이프라인 자동 복구** — 기동 시 오래 멈춘 회의를 재시도하거나 failed 로 전환 | Claude | 0.5일 | 처리 중 재시작 → 회의가 완료 또는 failed 로 끝남 | BL-OCI-4 |
| 1-12 | [ ] **voice 메모 30일 TTL 실행 수단** | Claude | 1h | 30일 지난 `memory/` 객체 정리 dry-run 확인 | D-001 |
| 1-13 | [ ] **의존성 high 37건 triage** + anyio critical 1건 | Claude | 1h | runtime scope 의 실제 영향 건만 상향 | dependabot (critical 5 · high 37) |
| 1-14 | [ ] **문서 드리프트 정리** — STALE 34 · MISLEADING 10 (먼저 D-016 수동 빌드 명령) | Claude | 2h | `doc-drift-e3.json` 의 각 정정 반영 | E3 |
| 1-15 | [ ] **public 노출 표면 점검** — `deploy/oci/README.md` 등의 SSH 별칭·포트 정보 | **사용자** 결정 · Claude 30분 | 정찰성 정보 제거 또는 유지 결정 기록 | TODO.md:257 |
| 1-16 | [ ] **P3 UX 묶음** | Claude | 3h | 각 재현이 해소됨 | C-006 · C-007 · C-010 · C-021 |

**Gate 1 합계**: Claude 약 7~9일 · 사용자 약 3h + 외부 심사 대기.

---

## Gate 2 — 유료화 전

| # | 항목 | 담당 | 시간 | 검증 | 근거 |
|---|---|---|---|---|---|
| 2-1 | [ ] 요금제 확정 + 결제 연동 (구독·환불) | **사용자** 결정 · Claude 3~5일 | 테스트 결제 → 구독 상태 반영 → 해지 | 결제 코드 0건, pricing = "베타 기간 무료" |
| 2-2 | [ ] 사용량 계측 — 워크스페이스별 AI 토큰·음성 분·저장량 | Claude | 1~2일 | 요금제 한도와 대조되는 대시보드 | 현재 memory 집계 5개뿐 |
| 2-3 | [ ] 전자상거래 고지 (사업자 정보·환불 정책) + 개인정보 처리 위탁 고지 | **사용자** | 반나절 | 푸터·약관에 반영 | — |
| 2-4 | [ ] 백업 RPO/RTO 명시 + 오프사이트 2차 백업 + 분기 복원 리허설 | 사용자 + Claude | 반나절 | 복원 리허설 기록 | 0-11 확장 |
| 2-5 | [ ] 단일 VM 장애 대응 판단 (Oracle A1 1대 + Tunnel) — 장애 시 복구 절차와 목표 시간 | **사용자** 결정 · Claude runbook 2h | 모의 장애 1회 | ADR-028 |
| 2-6 | [ ] 권한·보안 재정검 (이번 P0 수정 뒤 같은 방식으로 1회 더) | Claude | 반나절 | 이번 `probe-results.log` 의 FAIL 전부 PASS | 본 보고서 |

---

## 지금 바로 할 수 있는 5분 작업 (사용자)

1. ~~GitHub secret `BETTER_AUTH_SECRET` 등록 (0-18)~~ — 2026-09-27 정정: 워크플로 이식이 먼저다 (0-18 참고)
2. Cloudflare "Always Use HTTPS" + HSTS 켜기 (0-13)
3. main ruleset 에 `ci-required` 등록 (0-19)
4. R2 QA 업로드 2건 삭제 — [`phase2-results.md`](phase2-results.md) §6 의 키 (Phase 1 1건 + Phase 2 1건)
5. ~~`r2-cleanup.yml` 을 `delete=true` 로 실행하지 않기~~ — 2026-09-27 워크플로가 읽기 전용 인벤토리로 바뀌어 삭제 입력 자체가 없다 (0-12)
