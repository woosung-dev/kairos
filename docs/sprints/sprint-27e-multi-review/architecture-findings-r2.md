<!-- Sprint 27e Round 2 — Architecture cross-check + 깊이 추가 -->

# Sprint 27e Round 2 — 아키텍처 Cross-Check + 깊이 추가

- 검사 일시: 2026-05-25 KST
- baseline commit: `b7e704e` (PR #109 머지된 main, Round 1 의 차단 6건 RESOLVED 반영)
- branch: `sprint-27e/round2-cross-check`
- 환경: 정적 + 헌법(`CONTEXT-MAP.md`) + ADR (014/019/020/021/022/023/024) + Round 1 산출물 cross-check
- Round 1 reviewer 출신: Architecture Guardian (Claude Opus 4.7)
- Round 2 reviewer 시각: (a) Round 1 위반 분류 검증 / (b) Round 1 이 놓친 영역 / (c) 헌법 토큰컷 정량 / (d) 외부 5명 직접 영향 재평가 + 추가 깊이 (fix 비용 + 본 sprint vs Sprint 28 권고 + cross-cutting concern)

---

## 0. 검증 환경 vs 시점 차이

- Round 1 baseline = `1b24898` (Sprint 27d merged, 차단 6건 unresolved). 본 Round 2 baseline = `b7e704e` (Round 1 의 차단 6건 RESOLVED 반영). delta = SEC-1/2 deps bump + SEC-3 JWT 검증 + SEC-4 cron token validator + TEST-1/2 회귀 가드.
- ARCH-1~7 은 모두 fix 적용 0건 — 비차단 carry. 따라서 (a) 는 "Round 1 의 file:line 정확성 + 분류 정합" 을 main HEAD `b7e704e` 기준 re-verify 로 대체.
- 신규 추가 코드 (config.py field_validator 2건, auth/dependencies.py JWT decode_kwargs) 의 헌법 정합도 본 Round 에서 검증.

---

## 1. Round 1 위반 분류 검증 (ARCH-1~7)

main HEAD `b7e704e` 기준 실 코드 re-read 결과.

| Round 1 ID | file:line 정확성 | 헌법 분류 정합 | Round 2 시각 |
|---|---|---|---|
| BUG-S27e-ARCH-1 | ✅ `backend/src/onboarding/service.py:18-20, 28-34` + `repository.py:14-27` verified. service 가 `self._session = session` 보유 (line 19) + `self._session.execute(text(...))` (line 28-34) 그대로. | ✅ I-1 ("Service 에서 AsyncSession 금지") 명백 위반, P1 적정. | Round 2 신규 시각: 이 anti-pattern 이 4 곳 호출 사이트 (`workspaces/service.py:57`, `projects/service.py:81`, `meetings/pipeline_service.py:165`, `rag/service.py:37`) 로 **번식** — ARCH-1 fix 시 4 호출 사이트 동시 정리 필요 (DI 그래프 변경). 본 deeper finding 은 §2 ARCH-r2-1 로 분리. |
| BUG-S27e-ARCH-2 | ✅ `backend/src/services/transcription.py:14` `from src.meetings.models import TranscriptSegment` verified. transcribe() 반환 line 125-133 + transcribe_with_chunking() line 188-196 모두 ORM 인스턴스 생성. | ✅ DIP + 헌법 §4.2 cross-domain shared service 경계 위반, P2 적정. | Round 2 추가: `chunked_transcription.py` 는 dict 반환 (line 187 dict_segments) — 같은 services 디렉토리 내 두 패턴 공존. DTO 도입 시 chunked 패턴으로 일관화 권고. |
| BUG-S27e-ARCH-3 | ✅ `backend/src/common/audit_router.py:14,18` (`from src.auth.rbac import require_admin` + `from src.workspaces.models import WorkspaceMember`) + `promote_helpers.py:173` (`from src.workspaces.models import WorkspaceMember` lazy) verified. | ✅ Layered violation, P2 적정. | Round 2 추가: `common/audit_repository.py` + `common/audit_schemas.py` + `common/promote_models.py` 도 audit 도메인 내용 — 분리 대상 ≥ 5 파일. |
| BUG-S27e-ARCH-4 | ✅ `CONTEXT-MAP.md:43` "백엔드 모듈 (13)" + line 60 "(11)" verified. 실재 BE = 15 (`ls backend/src/` 검증 — auth/workspaces/projects/inbox/meetings/notes/actions/memory/onboarding/upload/embeddings/rag/common/core/services), FE = 14 (actions/audit/home/inbox/meetings/members/memory/notes/onboarding/projects/rag/sources/upload/workspaces). | ✅ Atomic Update 위반, P2 적정. | Round 2 추가: `CONTEXT-MAP.md:45` 의 모듈 list 자체는 15개를 나열 (auth · workspaces · projects · inbox · meetings · notes · actions · memory · upload · embeddings · rag · common · core · services) — `onboarding` 빠짐, 그러나 카운트가 13 표기. 즉 텍스트 본문 모듈 list = 14개인데 카운트 = 13 — 두 곳 모두 stale. |
| BUG-S27e-ARCH-5 | ✅ `backend/src/rag/service.py:38-41` `session = self.embedding_repo.session` + `OnboardingService(session)` + `await session.commit()` verified. | ✅ Demeter / I-1 정신 위반, P3 적정. | Round 2 추가: 같은 패턴이 4 곳 — `workspaces/service.py:58` (`self.repo.session`), `projects/service.py:82` (`self.repo.session`), `meetings/pipeline_service.py:166` (`meeting_repo.session`), `rag/service.py:38` (`self.embedding_repo.session`). ARCH-5 의 P3 등급은 1 곳 가정 — 4 곳 산재이면 P2 로 격상 권고. |
| BUG-S27e-ARCH-6 | ✅ method LOC 13개 verified — `rag/service.py:45` ask 192 LOC + `meetings/service.py:256` promote 172 LOC 등 line offset 일치. | ✅ SRP/KISS 위반, P2 적정. | Round 2 추가: promote 외 long method 추가 7개 — RAG ask 192 LOC 가 가장 크나 promote 5 도메인 패턴이 횡적 결합. ARCH-6 fix = `common/promote_helpers.py` 확장 패턴 합리적. |
| BUG-S27e-ARCH-7 | ✅ `docs/refactoring-backlog.md:440-471` (BL-005) "★★★★★ P0" 잔존 verified. `memory/service.py:405-505` promote 코드는 `self.workspace_repo.find_by_id` + `self.workspace_repo.find_member` 사용 — `self.repo.session.execute` 호출 0 hit verified. | ✅ Atomic Update governance 위반, P3 적정. | Round 2 동의. |

**결론**: Round 1 의 ARCH-1~7 file:line + 분류 모두 정합. Round 2 추가 시각으로 ARCH-1/3/5 가 광범위함이 드러남 (1 곳 → 4 곳 산재 패턴).

---

## 2. Round 2 신규 발견 매트릭스

Round 1 이 다루지 않은 영역에서 정적 분석으로 추가 발견.

| ID | 헌법/ADR/원칙 | 심각도 | 차단 | file:line | 발견 요약 | 권장 fix |
|---|---|:-:|:-:|---|---|---|
| **BUG-S27e-ARCH-r2-1** | ADR-014 옵션 A + I-1 | P1 | NO | `workspaces/service.py:57-58`, `projects/service.py:81-82`, `meetings/pipeline_service.py:165-166`, `rag/service.py:37-38` | OnboardingService 가 4 곳에서 `self.<repo>.session` 우회 추출로 호출됨 — ARCH-1 (I-1) + ARCH-5 (Demeter) 의 직접 결과로 4 도메인 service.py 가 다른 도메인 service.py 직접 import. ADR-014 "service.py 끼리 직접 호출 금지" 명백 위반. Round 1 §5 "정합 OK 항목" 의 "service.py 끼리 직접 import 0건" 표기는 OnboardingService 4 사례 누락 (false negative). | ARCH-1 fix (Repository 경유) + DI 주입 (router/dependencies.py 에서 OnboardingService 주입) → 4 service.py 의 onboarding 호출은 `self._onboarding` 으로 통일. ADR-014 §4.2 "권한 검증 일원화" 옵션 A 명시화 — onboarding hook 도 같은 패턴 인정 (ADR 본문 patch). |
| **BUG-S27e-ARCH-r2-2** | I-1 (raw text() SQL layer 경계) | P3 | NO | `auth/dependencies.py:171-228` | dependency 함수 `get_current_user` 가 raw `text()` SQL 3건 직접 실행 (User INSERT + Workspace INSERT + WorkspaceMember INSERT). repository layer 우회 — I-1 의 service 가 아닌 dependency layer 라 직접 위반은 아니나 B-10 G3-keep-dialect (ON CONFLICT pg dialect) 명시 없음. lazy seed 책임이 dependency 에 누적되어 향후 step=5 등 hook 추가 시 같은 패턴 답습 가능. | (a) lazy seed 책임을 `auth/service.py` LazySeedService 로 추출 → repository 의 `pg_insert(...).on_conflict_do_nothing()` 패턴 (memory repository 와 동일) 사용. (b) auth/CONTEXT.md 에 lazy seed = G3-keep-dialect 예외 명시 추가. |
| **BUG-S27e-ARCH-r2-3** | ADR-014 §4.2 (cross-domain orchestrator 일관성) | P2 | NO | `services/transcription.py:188-196` ORM 인스턴스 직접 생성 vs `services/chunked_transcription.py:182-188` dict 반환 | 같은 services 디렉토리 두 모듈이 반환 형식 불일치 — transcription = ORM (`TranscriptSegment(...)`), chunked = `list[dict]`. 호출자 (`pipeline_service.py`) 가 두 진입점에 따라 다른 변환 처리. ARCH-2 의 확장 — DTO 패턴 도입 시 일관화. | ARCH-2 fix 와 묶음 — `TranscriptionSegmentDTO` 도입 후 transcribe / transcribe_with_chunking / chunked 의 transcribe_chunked 모두 DTO 반환. 호출자 ORM 변환 단일점. |
| **BUG-S27e-ARCH-r2-4** | Observability (Sentry SKIP 시 forensic) + Cross-cutting concern | P3 | NO | `backend/src/main.py:132-139` global_exception_handler | 5xx 발생 시 exception 객체 `_exc` 가 unused (underscore prefix). Sentry DSN 미설정 환경 (dev/staging 또는 cron job CLI) 에서는 5xx 발생 시 stack trace 손실 → forensic blind. ADR-021 Sentry scrubbing 정합은 OK 이나 Sentry SKIP fallback path 부재. SEC-11 (logging.warning authz_failure) 와 동일 cross-cutting concern. | `logger.exception("global 5xx", exc_info=_exc)` 1줄 추가. Sentry 가 별도 send 하더라도 stdout log 가 Cloud Run 로그에 영구 보존. |
| **BUG-S27e-ARCH-r2-5** | CONTEXT-MAP §4.1 모듈 list vs 카운트 불일치 (Atomic Update 내부 일관성) | P3 | NO | `CONTEXT-MAP.md:43-45` | "백엔드 모듈 (13)" 카운트와 line 45 의 모듈 list (`auth · workspaces · projects · inbox · meetings · notes · actions · memory · upload · embeddings · rag · common · core · services` = 14개) 가 헌법 한 문장 안에서도 불일치. ARCH-4 가 외부 stale (실재 15 대비 13) 을 지적했지만, 내부 stale (카운트 13 vs list 14 vs 실재 15) 은 별개 결함. | ARCH-4 fix 시 카운트 = list = 15 모두 정합. `onboarding` 모듈을 line 45 list 에 추가 + 카운트 15 로 갱신. |
| **BUG-S27e-ARCH-r2-6** | ADR-022/ADR-024 ↔ 코드 정합 (관찰) | INFO | NO | `backend/src/auth/repository.py` + ADR-022/024 | ADR-024 가 ADR-022 (Clerk webhook SKIP) supersedes — 코드는 `sync_user` 핸들러 0 hit + 회귀 가드 `test_auth_sync_disabled.py` 존재 (Round 1 §5 verified). 그러나 ADR-024 cutover 시 SEC-3 JWT issuer 검증 lock-in 이 본 sprint Round 1 fix 로 들어왔음 — config.py validator + dependencies.py decode_kwargs 모두 정합 verified. | 조치 불필요. ADR/코드 정합 양호. |

---

## 3. Sprint 27e 신규 코드 (Round 1 fix) 의 헌법 정합 검증

Round 1 이 추가한 신규 코드의 헌법 정합 — 본 Round 가 새로 audit.

| 신규 코드 위치 | 헌법/ADR | 정합 결과 |
|---|---|---|
| `core/config.py:8` `_CRON_TOKEN_DEV_FALLBACK` 모듈 상수 | I-15 (Secret 은 SecretStr) | ✅ line 49 `SecretStr(_CRON_TOKEN_DEV_FALLBACK)` 로 wrap, 정합. validator 진입 시 `v.get_secret_value()` 사용 (line 81). |
| `core/config.py:77-86` `_no_default_cron_in_prod` field_validator | Fail-closed startup | ✅ production env + dev fallback 일치 시 ValueError raise → lifespan 진입 차단. lru_cache get_settings() 첫 호출 시 trigger. |
| `core/config.py:89-98` `_no_dev_issuer_in_prod` field_validator | ADR-024 cutover lock-in | ✅ production + dev issuer substring 매치 시 raise. 단 dev issuer 문자열 hard-code (line 32 default + line 93 substring) — 환경 분리 시 두 곳 동기화 필요. 향후 dev issuer URL 변경 시 atomic update 책임 명시화 권고 (코멘트 1줄 추가). |
| `auth/dependencies.py:117-129` JWT decode_kwargs 분기 | ADR-024 SEC-3 lock-in | ✅ issuer 강제 + audience optional (Clerk JWT Template 미설정 환경 호환). InvalidIssuerError + InvalidAudienceError 분리 catch (line 137-141) — forensic 분리 양호. |
| `frontend/package.json` `next 16.2.6` + `@clerk/nextjs ^7.4.1` | Sprint 27e SCOPE Round 1 SEC-1/2 lock | ✅ pnpm-lock 동기화 확인 (package.json 갱신). |

**결론**: Round 1 신규 코드 모두 헌법 정합. 단 dev issuer 문자열 hard-code 2곳 (line 32 + line 93) 의 atomic update 책임 코멘트 추가 권고 (사소).

---

## 4. 헌법 토큰컷 정량 (BL-S26-1)

| 측정 시점 | bytes | lines | 비고 |
|---|---:|---:|---|
| Sprint 26 baseline | 5,742 | 91 | Sprint 26 glittery-tulip 직후 (memory `project_sprint26_glittery_tulip_done`) |
| Sprint 27a partial | 3,398 (Sprint 27a 보고) | - | 토큰컷 partial (3793→3398, 10%) |
| **Round 2 측정 (`b7e704e`)** | **7,960** | **106** | `wc -c` + `wc -l` `CONTEXT-MAP.md` 검증 |

**관찰**: Sprint 27a partial 보고 (3,398 bytes) 와 현 실측 (7,960 bytes) 간 ~2.3x 차이. Round 2 의 cli 측정이 fresh ground truth. 즉 BL-S26-1 의 "목표 ≤3,000 bytes" 잔여 비율은 보고된 13% 가 아니라 ~62%. Sprint 27a 이후 ADR-024 supersedes 항목 + I-21 HNSW 세션 변수 + I-22 (?) 등 추가로 헌법 본문 다시 확장됐을 가능성.

**조치**: BL-S26-1 의 progress 표시 갱신 (3398 → 7960 bytes, "Sprint 27a 이후 회귀 발생" 마크). 정량 baseline 재설정 필요. 본 발견은 ARCH-r2-7 로 분류.

| ID | 헌법/ADR | 심각도 | 차단 | file:line | 발견 | 권장 fix |
|---|---|:-:|:-:|---|---|---|
| **BUG-S27e-ARCH-r2-7** | BL-S26-1 (헌법 토큰컷) | P3 | NO | `CONTEXT-MAP.md` (전체) | Sprint 27a 후 partial 진행 (3,398 bytes) 후 다시 7,960 bytes 로 회귀 — 63% 회귀. BL-S26-1 의 "10% partial" 마크 stale. | BL-S26-1 progress 갱신 + ADR-024 supersede 마크 + I-21 HNSW 등 후속 추가 항목의 토큰 비용 표기. 별도 sprint 에서 ≤3,000 목표 달성 전략 (별 ADR 로 빼기 등) 재검토. |

---

## 5. 외부 5명 직접 영향 재평가 (Round 1 BL ARCH-1~7)

| BL | Round 1 분류 | 외부 5명 직접 영향 | 사용자 (founder/PERSONA-001) 영향 | Round 2 분류 동의? |
|---|---|---|---|---|
| ARCH-1 | P1 NO-BLOCK | 0 (production 동작 0 영향) | 다음 onboarding step 추가 시 raw SQL 2곳 동시 수정 비용 | ✅ 동의 |
| ARCH-2 | P2 NO-BLOCK | 0 | meetings TranscriptSegment schema 변경 시 services 동시 touch | ✅ 동의 |
| ARCH-3 | P2 NO-BLOCK | 0 | common 책임 비대화 → audit 도메인 확장 시 (BL-S27-3 AdminAccessAudit) common 누적 | ✅ 동의 |
| ARCH-4 | P2 NO-BLOCK | 0 | governance — 새 AI agent / contributor 가 모듈 경계 잘못 파악 (3개 contributor 가정 시 3회 잘못된 commit risk) | ✅ 동의 (governance risk 는 시간차 발현) |
| ARCH-5 | P3 NO-BLOCK | 0 | repository 캡슐화 약화 → 다른 도메인이 같은 패턴 답습 (이미 4 곳 산재 — ARCH-r2-1) | **격상 P2 권고** (1 곳 가정 → 4 곳 산재 = 광범위) |
| ARCH-6 | P2 NO-BLOCK | 0 | promote 정책 변경 (ADR-023 D-6.4 AdminAccessAudit 등) 시 5 도메인 동시 수정 비용 | ✅ 동의 |
| ARCH-7 | P3 NO-BLOCK | 0 | BL backlog 신뢰도 하락 — 같은 stale 가 다른 BL 도 답습 risk | ✅ 동의 |

**결론**: ARCH-1~7 모두 외부 5명 직접 영향 0건 — Round 1 의 "PASS-with-carry" 판정 정합. 단 ARCH-5 는 P3 → P2 격상 (4 곳 산재 광범위) 권고.

### ARCH-4 governance risk 정량

- 새 AI agent 진입 시 헌법 §4.1 첫 read → "BE 13 모듈" 가정 → 실재 15 모듈 모름 → onboarding/audit 모듈을 common 또는 다른 곳에 잘못 분류 risk.
- 발생 빈도 추정: 본 Round 2 reviewer 도 첫 read 시 13 가정 → ls 로 정정 (1 회 발생). 외부 contributor 1명당 평균 0.5회 mis-categorization 예상.
- 누적 비용: 잘못된 commit → review 에서 catch → revert → fix 의 사이클당 ~30분. 향후 contributor 5명 가정 시 ~2.5h.
- → Atomic Update 회복 (ARCH-4 fix) 의 ROI = ~30분 work vs ~2.5h saved.

---

## 6. Round 1 BL ARCH-1~7 fix 비용 정량 + 본 sprint vs Sprint 28 권고

| BL | fix 비용 (단순) | fix 비용 (테스트 포함) | 본 sprint | Sprint 28 | 권고 근거 |
|---|:-:|:-:|:-:|:-:|---|
| ARCH-1 | 4h (repository 2 method + service 변경 + 4 호출 사이트 DI) | 1d (회귀 가드 추가 — onboarding test 5건) | NO | **YES** | I-1 헌법 위반 + ARCH-r2-1 4 곳 산재 동시 정리 효과. Sprint 28 BL-S27e-F 묶음 첫 항목. |
| ARCH-2 | 2h (DTO + 2 호출자 변환) | 4h (transcription test 변경) | NO | YES (낮은 우선) | services DTO 일관성. chunked_transcription 패턴으로 통일. |
| ARCH-3 | 1d (5 파일 이전 + import 정리 + directory-map.md 갱신) | 1.5d (audit 모듈 회귀 test) | NO | YES (ARCH-4 와 묶음) | governance + 도메인 책임 정리. ARCH-4 와 같은 PR 권고. |
| ARCH-4 | 30분 (CONTEXT-MAP.md §4.1/§4.3 + directory-map.md + .claude/CLAUDE.md 4 곳 patch) | 30분 (manual diff) | **YES** | - | governance ROI 명확 (~30분 work vs 향후 ~2.5h saved). 본 Round 2 만에서도 1 회 confusion 발생 — 즉시 fix. |
| ARCH-5 | 1h (ARCH-1 fix 시 자연 해결) | 0 (ARCH-1 cover) | NO | YES (ARCH-1 동반) | ARCH-1 fix 하면 4 호출 사이트에서 `session = self.<repo>.session` 패턴 자동 제거. 독립 fix 불필요. |
| ARCH-6 | 1d (`promote_helpers.py` 확장 + 5 도메인 promote 50 LOC 미만 축소) | 1d (5 도메인 test 회귀) | NO | YES (Sprint 28 후반) | promote 정책 변경 (D-6.4 admin audit 등) 직전에 묶음 정리. |
| ARCH-7 | 5분 (BL-005 마크 + closed 추가) | 0 | **YES** | - | BL backlog 정확성 회복. ARCH-4 와 묶어 1 PR. |
| ARCH-r2-1 | (ARCH-1 cover) | (ARCH-1 cover) | NO | YES (ARCH-1 동반) | ARCH-1 fix 시 자연 해결. |
| ARCH-r2-2 | 4h (LazySeedService 추출 + repository pg_insert) | 4h | NO | YES (낮은 우선) | auth/dependencies.py 책임 분리. ARCH-1/3 묶음 후 별도 sprint 권고. |
| ARCH-r2-3 | (ARCH-2 cover) | (ARCH-2 cover) | NO | YES (ARCH-2 동반) | |
| ARCH-r2-4 | 5분 (`logger.exception` 1 line) | 30분 (test) | **YES** | - | 1 line fix, 외부 진입 후 5xx forensic 보장. 본 sprint 안. |
| ARCH-r2-5 | (ARCH-4 cover) | (ARCH-4 cover) | **YES** | - | ARCH-4 와 같은 patch. |
| ARCH-r2-6 | (조치 불필요) | - | - | - | INFO only. |
| ARCH-r2-7 | 30분 (BL-S26-1 progress 갱신 + 회귀 마크) | 0 | **YES** | - | BL 정확성 회복. governance. |

### 본 sprint 진입 권고 = ARCH-4 + ARCH-7 + ARCH-r2-4 + ARCH-r2-5 + ARCH-r2-7

총 비용 ~ 1h (모두 governance + 1 line fix). 본 Round 2 의 cross-check 산출과 같은 commit 묶음 가능.

### Sprint 28 진입 권고 = ARCH-1 + ARCH-2 + ARCH-3 + ARCH-5 + ARCH-6 + ARCH-r2-1 + ARCH-r2-2 + ARCH-r2-3

총 비용 ~ 5-6d (architecture deepening sprint). BL-S27e-F 묶음 단일 sprint 가능. ARCH-1 fix 가 ARCH-5 + ARCH-r2-1 자연 해결.

---

## 7. ARCH 영역 외 Cross-Cutting Concern 헌법 정합

Round 1 이 ARCH 7건만 다뤘으므로 본 Round 가 cross-cutting concern 추가 검토.

| Concern | 헌법/ADR 참조 | 정합 결과 |
|---|---|---|
| **Logging** | 명시 없음 (.ai/common/global.md §1 한국어 메시지 정도) | ⚠️ `backend/src/main.py:38-41` logging.basicConfig 만 — domain 별 logger 부재. `auth/dependencies.py:241` 등 inline `logging.getLogger(__name__)` 패턴 산재. 일관성 부족이나 차단 0. 별도 BL 권고 (BL-S27e-ARCH-r2-OBS). |
| **Metrics** | 명시 없음 | ⚠️ Prometheus / OpenTelemetry 미적용 — PERSONA-001 1인 운영 시 외부 5명 진입 후 latency / error rate 추적 어려움. Sentry traces_sample_rate=0.1 만. BL-S27e-1 (RAG p95) + BL-S27c-9 (Cloud Run min instance) 와 묶음 가능. |
| **Sentry SKIP path** | ADR-021 | ⚠️ Sentry DSN 미설정 환경 (dev/staging/CLI cron job) 에서 5xx 발생 시 stdout log 0건 (ARCH-r2-4). cron job (`r2-cleanup.yml`) 실패 시 silent. 본 ARCH-r2-4 fix 권고 동봉. |
| **Configuration management** | I-15 SecretStr | ✅ Sprint 27e SEC-4 fix 로 production validator 진입. `_CRON_TOKEN_DEV_FALLBACK` + `_no_default_cron_in_prod` 패턴 정합. clerk_jwt_issuer 도 같은 패턴 — 정합. |
| **Cron job 인증** | I-15 + ADR 명시 없음 | ✅ `core/config.py:49` `cron_secret_token: SecretStr` + validator. `memory/admin_router.py` 가 cron secret 검증 — 정합. |
| **Cross-tenant logging** | I-9 멀티테넌시 | ⚠️ workspace_id 가 모든 logger record 의 context 에 자동 부착되지 않음 — incident response 시 어느 workspace 영향인지 추적 어려움. BL 권고. |

**결론**: Cross-cutting concern 중 logging / metrics / Sentry SKIP path 가 헌법 명시 없는 회색 영역. PERSONA-001 1인 운영 + 외부 5명 진입 후 1-2회 incident 발생 가능성 고려 시 BL 등재 권고.

---

## 8. Summary

### 8.1 Round 1 분류 검증

- ARCH-1~7 모두 file:line + 분류 정합 ✅ (main HEAD `b7e704e` 기준 re-verify).
- ARCH-5 만 P3 → P2 격상 권고 (4 곳 산재 광범위, ARCH-r2-1 에서 정량).
- Round 1 §5 "정합 OK" 의 "service.py 끼리 직접 import 0건" 표기는 OnboardingService 4 사례 누락 — false negative (ARCH-r2-1).

### 8.2 Round 2 신규 발견 = 7건

| ID | 카테고리 | 심각도 | 차단 |
|---|---|:-:|:-:|
| ARCH-r2-1 | ADR-014 § service.py cross-import (OnboardingService 4 곳) | P1 | NO |
| ARCH-r2-2 | I-1 raw text() SQL — auth/dependencies.py | P3 | NO |
| ARCH-r2-3 | services DTO 일관성 (ARCH-2 확장) | P2 | NO |
| ARCH-r2-4 | global_exception_handler exception unlogged | P3 | NO |
| ARCH-r2-5 | CONTEXT-MAP §4.1 카운트 vs list 내부 불일치 | P3 | NO |
| ARCH-r2-6 | ADR-024 ↔ 코드 정합 (관찰) | INFO | NO |
| ARCH-r2-7 | BL-S26-1 토큰컷 회귀 (3,398→7,960 bytes) | P3 | NO |

**차단 0 / 외부 5명 직접 영향 0**.

### 8.3 본 sprint 권고 fix (~1h)

- ARCH-4 (헌법 BE/FE 모듈 수 정합)
- ARCH-7 (BL-005 closed 마크)
- ARCH-r2-4 (`logger.exception` 1 line)
- ARCH-r2-5 (CONTEXT-MAP 카운트=list=15 정합)
- ARCH-r2-7 (BL-S26-1 progress 갱신)

### 8.4 Sprint 28 권고 fix (~5-6d, architecture deepening sprint)

- ARCH-1 + ARCH-5 + ARCH-r2-1 (OnboardingService DI 통일, 4 호출 사이트 동시 정리)
- ARCH-2 + ARCH-r2-3 (services DTO 도입)
- ARCH-3 (audit 도메인 분리, BE 16 모듈)
- ARCH-6 (promote_helpers 확장, 5 도메인 SRP)
- ARCH-r2-2 (auth lazy seed LazySeedService 추출)

### 8.5 Round 2 추가 BL 권고 (등재 권고)

- BL-S27e-ARCH-r2-1 = OnboardingService DI 통일 (P1, Sprint 28)
- BL-S27e-ARCH-r2-2 = auth lazy seed repository 패턴 (P3, Sprint 28+)
- BL-S27e-ARCH-r2-3 = services DTO 일관화 (P2, Sprint 28, ARCH-2 동반)
- BL-S27e-ARCH-r2-4 = global_exception_handler logger.exception (P3, **본 sprint**)
- BL-S27e-ARCH-r2-5 = CONTEXT-MAP §4.1 카운트=list 정합 (P3, **본 sprint**)
- BL-S27e-ARCH-r2-7 = BL-S26-1 토큰컷 회귀 마크 (P3, **본 sprint**)
- BL-S27e-ARCH-r2-OBS = logging / metrics / workspace_id context propagation (P2, Sprint 29 observability sprint)

### 8.6 최종 판정

- 헌법/ADR 위반 = Round 1 의 1건 (ARCH-1 I-1) + Round 2 의 1건 (ARCH-r2-1 ADR-014, ARCH-1 의 직접 결과로 4 호출 사이트 cross-import)
- 차단 = 0건
- 외부 5명 직접 영향 = 0건
- **PASS-with-carry** (Round 1 판정 유지). 본 sprint 안에 ~1h governance fix 추가 권고 (ARCH-4/7/r2-4/r2-5/r2-7). 나머지 BL 은 Sprint 28 architecture deepening sprint 묶음.

---

*검사자: Architecture Cross-Check Reviewer (Round 2, Claude Opus 4.7, 1M context)*
*baseline: `b7e704e` (Round 1 차단 6건 RESOLVED 반영된 main)*
*branch: `sprint-27e/round2-cross-check`*
