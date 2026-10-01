# Phase 2 재테스트 결과 — 2026-09-27

- 기준 코드: `qa/2026-09-26-launch-readiness` (base `main 1d2eac0` + Gate 0 수정) · Phase 1: `main 1d2eac0`
- 실행: Claude 메인 (MCP Playwright 라이브 + API 탐침) / Evaluator: E-BE1 · E-BE2 · E-FE (fresh context) / codex (P0 SQL 교차검증) — 판정 처리는 [`decisions-log.md`](decisions-log.md)
- 범위: Gate 0 §0~§5 (사용자 결정 U-5). §6 은 Gate 1 작업 때 실행한다
- 환경: 로컬 격리 풀스택 (`kairos-qa-db` 127.0.0.1:5436 · BE :8000 · FE `next build` + `next start` :3000). 실제 Gemini/OpenAI 호출 · R2 업로드 1건 · 프로덕션은 익명 GET 만 · Neon 접촉 0

## 0. 합계

| 구분 | 결과 | 비고 |
|---|---|---|
| §1 Gate 0-A 권한 누수 (T-01 ~ T-23, T-18c 포함, T-18b 제외) | **24/24 PASS** | API 와 UI 둘 다 봤다. T-05/T-07 UI · T-18 viewer·member RAG(+작성자 대조군) · T-18c UI 는 Evaluator 지적으로 보강 실행 |
| §2 Gate 0-B 초대 → 첫 사용 (T-24 ~ T-30) | **7/7 PASS** | T-25 는 처음에 추론으로 적었다가 Evaluator 지적으로 실제 실행했다 |
| §3 Gate 0-C 운영 (T-31 ~ T-40) | **PASS 3** · 배포 대기 1 · 사용자 5 · Claude 코드 1 → 2026-09-27 **PASS 5** (+T-34 · T-39) · 부분 1 (T-38) · Gate 1 이동 1 (T-33) · 사용자 3 (T-35 · T-37 · T-40) | T-31 · T-32 PASS · T-36 은 로컬 리허설 PASS (0-16 검증 기준 = 로컬 1회. 프로덕션 재설정은 요청이 올 때 runbook 으로) / T-34 = 배포 후 / T-38 = nightly 워크플로 이식(Claude) 뒤 사용자 dispatch / T-33 · T-35 · T-37 · T-39 · T-40 = 사용자 |
| §4.1 과잉 차단 대조군 (R-01 ~ R-04) | **4/4 PASS** | |
| §4.2 Phase 1 PASS 재실행 (92) | **92/92 PASS** · FAIL 0 | API 79 + UI 13 + 섞인 탐침의 UI 부분 9 |
| §5 Phase 1 미실행 P0/P1 (14) | **14/14 PASS** | G1-086 은 새 계정 가입으로 실행 |
| Evaluator 판정으로 추가한 수정 탐침 (NF-*) | **24/24 PASS** | [`phase2-evidence/probe-newfixes.log`](phase2-evidence/probe-newfixes.log) |

**Gate 0 판정: 코드 조건 충족 · 운영 조건 미충족 → 현재 NO-GO.**
- 조건 "§1 · §2 · §4.1 전부 PASS, §4.2 FAIL 0" 은 충족했다.
- 조건 "§3 전부 PASS" 는 아직이다. 남은 것은 배포(0-14) · 사용자 작업 5건(계정·대시보드·서버 권한) · Claude 코드 작업 1건(T-38, nightly 워크플로를 Better Auth 구성으로 이식 — BL-LR-15) 이다 (§5).
- **2026-09-27 갱신 — 여전히 NO-GO.** 해소: 0-14 배포(T-34 PASS) · 0-19 ruleset(T-39 PASS) · 0-18 부분(워크플로 이식 #198, team 38/40) · 롤백 경로 결함(BL-LR-16, #197). 0-13 은 사용자 결정으로 Gate 1(1-17)로 이동.
  남은 사유: **0-11 · 0-17 · 0-20** (운영자 작업 — `docs/TODO.md` Blocked "Gate 0 잔여") · **0-15** (Google 테스트 사용자, 사용자 준비 대기) · **0-18** (T15·T20 2건, BL-LR-15 P1).

## 1. 검증 증거 (AGENTS.md §4 표준)

| 항목 | 결과 | 증거 |
|---|---|---|
| BE pytest | **998 passed · 1 skipped · 0 failed** (191s) | `apps/api` 에서 `env -u AUTH_JWT_AUDIENCE -u AUTH_JWT_ISSUER -u AUTH_JWKS_URL uv run pytest -q` (testcontainers). qa.env 의 AUTH_JWT_* 가 새면 `test_audience_skipped_when_unset` 3건이 환경 탓으로 실패한다 — 코드 결함 아님 |
| alembic dry-run | 2 리비전 (`c1a7e0b5d3f2 → a9c4e2f7b1d0 → b3d5f8a1c2e4`) | [`phase2-evidence/alembic-dryrun.sql`](phase2-evidence/alembic-dryrun.sql) — `memory_items.is_shared` 추가 + 작성자 본인 promote 사본만 true 백필 · 실패 회의 error_message 정제 |
| 계약 drift | 없음 | `openapi-export` + `types-gen` 강제 재생성 → `openapi.json` · `api.gen.ts` 바이트 동일 |
| FE | vitest 48 파일 · 295 PASS · `tsc --noEmit` 0 · `next build` 성공 · eslint 신규 오류 0 (`pnpm lint` 오류 23건 = src 5 + e2e 18, 전부 이 PR 이 건드리지 않은 파일이며 main 과 동일) | |
| FE 스크린샷 · console.error | 4역할 sweep console.error 0 (의도한 404/409/503 리소스 줄만) | [`shot-t20-confirm-public-link.png`](phase2-evidence/shot-t20-confirm-public-link.png) · [`shot-g3-018-search-retest.png`](phase2-evidence/shot-g3-018-search-retest.png) |
| Playwright 라이브 | UI 탐침 전부 PASS | [`phase2-evidence/probe.log`](phase2-evidence/probe.log) (80줄) |

## 2. FAIL

없음.

## 3. BLOCKED · 대기

| T | 사유 |
|---|---|
| T-34 | ✅ **2026-09-27 PASS** — `2694847` 배포 후 같은 명령: documents 비인증 GET 401 · FE `content-security-policy-report-only` 있음 (0-14) |
| T-33 | ↪ 0-13 을 Gate 1(1-17)로 옮겼다 (2026-09-27 사용자 결정). 여전히 http → 200 |
| T-35 · T-37 · T-40 | Google 콘솔 · Clerk 대시보드 · 프로덕션 서버 권한 필요 (0-15 · 0-17 · 0-20). T-37·T-40 절차 = `docs/TODO.md` Blocked "Gate 0 잔여" |
| T-38 | ◐ 2026-09-27 이식(#198) → dispatch 3차 heavy ✅ · team 38/40. 남은 2건 T15·T20 (0-18 · BL-LR-15 P1) |
| T-39 | ✅ **2026-09-27 PASS** — ruleset `main-protection` (id 24073517) (0-19) |

## 4. 새 결함

| 임시 ID | 등급 | 재현 | 증거 | 처리 |
|---|---|---|---|---|
| G3-018 | P3 | `/search` 에서 한글 입력 → 조합 중 Enter(`isComposing=true`) → rag/ask 1회 발생 | `probe.log` G3-018 1차 `duringComposition=1` | **이번 PR 에서 수정**: `isComposing` 가드 4곳 + 회귀 테스트 2건(가드 제거 시 2 FAIL — [`fe-g3018-mutation.log`](phase2-evidence/fe-g3018-mutation.log)) → 재빌드 후 재검증 PASS. 규칙 F-13 |

반증된 후보 2건(G2-062 UI 판정 · G3-020 Esc)은 [`decisions-log.md`](decisions-log.md) 마지막 표에 있다.

## 5. 머지 후 남은 작업 (대부분 사용자 · 4번의 nightly 이식은 Claude 후속 PR)

1. **배포 승인** (0-14) — 머지 후 배포하면 alembic 2 리비전이 적용된다. 배포 뒤 T-34 명령 재실행
2. **Cloudflare HTTPS 강제 + HSTS** (0-13, 10분)
3. **백업 cron 등록** (0-11) — [`db-backup-restore.md`](../../../operations/runbooks/db-backup-restore.md) 대로. R2 lifecycle(`backups/kairos/` N일 — runbook 기본 제안 30일, `[확인 필요]`)과 `.env` 별도 보관도 같이. 첫 서버 실행이 실제 R2 업로드 검증이다 (리허설은 stub)
4. **GitHub**: main ruleset 에 `ci-required`(0-19). nightly e2e(0-18)는 secret 등록만으로 안 된다 — 워크플로 이식(Claude, BL-LR-15) 뒤 dispatch 로 확인
5. **Google 테스트 사용자 등록 · Clerk 정리 · stuck 회의 확인** (0-15 · 0-17 · 0-20)

## 6. 정리 · 잔여물

- **R2 업로드 2건** (공유 버킷 `nexus-core-storage`, 사용자가 삭제한다 — R2 이전 전에 지운다, `docs/TODO.md` "Gate 0 잔여" R1):
  - Phase 1: `uploads/a3e294c1-2835-46e7-bca5-c810e9835c75/beta-meeting.m4a`
  - Phase 2: `uploads/68be2290-9a8a-4f69-a379-a3b7634ef2af/beta-meeting.m4a` (AUDIO-UPLOAD-UI · 회의 `324b09b7`)
  - 삭제 예: `aws s3 rm "s3://nexus-core-storage/<키>" --endpoint-url "https://<ACCOUNT_ID>.r2.cloudflarestorage.com"`
- **로컬 DB** `kairos-qa-db` 는 유지한다. Phase 2 에서 만든 임시 WS 3개(REG · WS-CREATE-UI · T-25)는 삭제했다 (204). REG 노트 2건의 고아 청크가 남아 있다 (E1-N1, BL-LR-8 — 로컬 DB 만).
- **계정**: 새 계정 2개(T-26 가입 · G1-086 첫 호출)는 로컬 DB 에만 있다. T-26 계정은 T-36 리허설로 비밀번호가 바뀌었다.
- **프로덕션 변경 0건** (익명 GET 만).
- 탐침 스크립트와 비밀번호 파일은 scratchpad 에만 있다 (커밋하지 않음). 스크린샷 원본 126장은 `.playwright-mcp/shots/2026-09-27/` (gitignored).
