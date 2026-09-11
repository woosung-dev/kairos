# Google Drive 연동 — 회수 경로 완결 + FE 쓰기 경로 관통

**작성**: 2026-09-11 · **관련**: ADR-026 (외부 소스 ingest 레일 v0) · ADR-024 (부팅 차단형 validator 교훈) · `CONTEXT-MAP.md` I-2/I-9/I-13/I-15 · `apps/api/src/integrations/CONTEXT.md` I-EXT-1~6
**선행 계획**: `docs/plans/active/2026-07-30-google-drive-team-knowledge-spike.md` (Phase 2-6 · Phase 3-5 미완분을 본 계획이 인수)

---

## 1. 왜 지금 이 순서인가

2026-09-11 레포 실측 결과, Drive 연동은 **BE 2,373 LOC + 테스트 5,672 LOC 로 v0 범위를 거의 완주했고 FE 쓰기 경로가 0** 이다. 그런데 그 사이에 **회수(revoke) 경로가 비어 있다.**

- `IntegrationService.disconnect_connection` 은 구현돼 있으나 **라우터에 노출돼 있지 않다** → API 로 연결을 끊을 방법이 없다.
- 레포 전체에 Google `oauth2/revoke` 호출이 **0건** → ADR-026 "되돌리기 전략" 3단계(refresh token 폐기)가 Kairos 쪽 망각일 뿐 Google 쪽 무효화가 아니다.
- 연결 해제 시 **전체 문서 unpublish** (되돌리기 전략 2단계) 가 없다. 문서 단건 unpublish 만 존재한다.

FE 를 먼저 붙이면 *끊을 수 없는 연결* 이 만들어진다. 따라서 W1(회수) → W2(목록) → W3(FE) 순서가 강제된다.

`list_documents` 서비스 메서드도 소비처가 0이라, 관리 화면(Phase 0 Variant C) 을 붙이려면 목록 엔드포인트가 선행돼야 한다.

## 2. 확정된 사용자 결정 (2026-09-11)

| # | 결정 | 파급 |
|---|---|---|
| D-A | Picker key 는 **`NEXT_PUBLIC_` 빌드 인자로 공개** | **ADR-026 D10 개정 필요** — `google_picker_api_key: SecretStr` 선언이 근거를 잃는다. web `.env.example` · `apps/web/Dockerfile` · `deploy/oci/build.env.example` · `mise.toml [tasks.deploy-build]` 동시 갱신 |
| D-B | **단일 PR** 로 W1~W4 전부 | contract drift 게이트가 같은 PR 안 자기참조가 되므로, `api.gen.ts` 재생성이 **BE 변경 커밋과 분리된 커밋**이 되도록 커밋을 쪼갠다 |
| D-C | Google Cloud OAuth 클라이언트 **미발급** | 실 Google API 왕복 검증 불가 → **Phase 4 Go/No-Go 이연**. `docs/TODO.md` `## Blocked` 에 명시 등재 |

## 3. 범위

### 포함

- **W1** 회수 경로: `revoke_refresh_token` + `disconnect_connection` orchestrator + `DELETE .../integrations/google-drive`
- **W2** 목록: `GET .../integrations/google-drive/documents`
- **W3** FE 쓰기 경로: api/hooks 8종 + Picker + settings 실 UI + CSP
- **W4** 문서: ADR-026 D5/D10 개정 · `integrations/CONTEXT.md` · `docs/TODO.md` · `docs/development/secrets.md` · contracts 재생성

### 제외 (근거를 남기고 하지 않는다)

- **자동 동기화** — ADR-026 이 v0 범위에서 영구 제외. BL-EXT-INGEST-3
- **BL-EXT-REASON-1** (문서별 실패 사유 컬럼) — 마이그레이션이 필요하고 회수 경로와 무관. 본 PR 을 Heavy 변경으로 만들지 않는다
- **BL-EXT-SYNC-3 / BL-EMBED-3 / BL-EXT-CACHE-2** — 등재된 별건 부채
- **실 Google API 왕복 검증** — D-C 로 불가

## 4. 설계 결정

### 4.1 회수 순서 — 로컬 파기 먼저, 원격 revoke 나중

**순서: ① 토큰 복호화(메모리) → ② 전체 문서 파기 → ③ 연결 비활성화 + 토큰 삭제 → ④ Google revoke(best-effort)**

근거 — 두 실패 모드를 비교한다.

| 순서 | revoke 후 로컬 파기 실패 시 | 로컬 파기 후 revoke 실패 시 |
|---|---|---|
| revoke 먼저 | 토큰은 죽었는데 **문서가 계속 검색된다** ← 보안 결함 | — |
| **로컬 먼저 (채택)** | — | 문서는 사라졌고(안전) Google 에 grant 만 남는다 |

로컬 파기가 Kairos 데이터를 지키는 유일한 조치이므로 먼저 간다. 원격 revoke 는 best-effort 이며 **실패해도 연결 해제를 되돌리지 않는다** — Google 장애 때문에 연결을 못 끊는 것이야말로 이 작업이 없애려는 상태다.

대신 **결과를 숨기지 않는다.** 응답에 `revoked: bool` 을 실어 owner 가 `myaccount.google.com/permissions` 에서 수동 해제해야 하는지 알 수 있게 한다.

### 4.2 revoke 실패의 분류

Google `POST /revoke` 는 이미 무효한 토큰에 **400 `invalid_token`** 을 준다. 이건 "이미 회수됨" 이므로 **성공으로 취급**한다 (멱등). 그 외 오류는 `revoked=false`.

### 4.3 disconnect 는 왜 `pipeline_service` 인가

I-2 / §4.2 — integrations + embeddings 두 도메인 write 를 한 트랜잭션 경계에서 조율하므로 orchestrator 소유다. `service.py` 에 두면 `_invalidate_document_caches` 를 위해 service 가 `EmbeddingRepository` 를 들어야 해서 경계가 깨진다.

### 4.4 캐시 무효화는 문서당이 아니라 배치 1쌍

`unpublish_document` 의 사전/사후 이중 무효화 패턴을 **배치 전체에 1쌍**으로 적용한다. 문서 N건마다 workspace 전량 무효화를 N번 도는 것은 같은 보장에 N배 비용이다.

### 4.5 목록 엔드포인트는 owner-only

`GET .../external-documents/{id}` (상세) 는 `require_viewer` + visibility 검증 — RAG 인용 클릭 경로이기 때문이다. 반면 **목록은 발행 관리 표면**이므로 다른 관리 엔드포인트와 같이 `require_owner` (I-EXT-1). 본문은 `defer` 된 `find_documents_by_workspace` 를 그대로 쓴다.

### 4.6 CSP — Picker 도입과 동시

ADR-026 D5 가 요구한 대로 `script-src` 에 `https://apis.google.com`(Picker loader) · `https://accounts.google.com`(GIS) 을 허용하는 CSP 를 같은 변경에 넣는다. BL-S27e-3 의 전면 `strict-dynamic` + nonce 도입은 범위 밖이며, 본 작업은 **Picker 가 요구하는 최소 지시문**만 연다.

---

## 5. 검증 방식 (generator / evaluator 분리)

### 5.1 이 컨테이너에서 실행 가능한 것 — 실측 결과

| 게이트 | 가능? | 근거 |
|---|---|---|
| BE 단위 테스트 | ✅ | uv 0.8.17 + py3.12 venv 설치 성공 |
| **BE 통합 테스트** | ❌ | **Docker 데몬 부재** — `conftest.py:40` `PostgresContainer` 가 unix socket `FileNotFoundError` |
| FE typecheck | ✅ | exit 0 |
| FE vitest | ✅ | pnpm install 성공 |
| FE build | ✅ | — |
| contracts-check | ✅ | openapi export + openapi-typescript 모두 로컬 실행 |
| Playwright E2E | ❌ | 실행 중인 BE+DB 필요 |
| 실 Google API | ❌ | D-C — OAuth 클라이언트 미발급 |

**베이스라인 (착수 전 실측, 2026-09-11)**
- BE 전체: **581 passed · 174 errors · 173 deselected** — 174 errors 는 **전부** Docker 소켓 `FileNotFoundError`
- BE `tests/integrations` (`-m "not integration"`): **92 passed · 11 Docker errors · 46 deselected**
- FE typecheck: **exit 0**

→ **판정 규칙**: 착수 후 `passed` 수가 베이스라인 이상이고, `errors` 가 전부 Docker 기인이며, 새 실패가 0 이어야 통과. Docker 오류를 "원래 그랬다"로 뭉개지 않기 위해 **오류 사유를 매번 grep 으로 확인**한다.

### 5.2 anti-hollow-green — 테스트가 진짜 잡는지

새로 쓴 테스트는 **mutation 으로 죽는지 확인한 것만** 인정한다. 구체적으로:

| 테스트 | 주입할 변이 | 죽어야 함 |
|---|---|---|
| disconnect 가 문서를 전부 파기 | `unpublish` 루프를 `break` 로 1건만 처리 | ✅ |
| revoke 실패가 연결 해제를 막지 않음 | revoke 예외를 `raise` 로 전파 | ✅ |
| revoke 가 로컬 파기 **뒤** 호출 | 호출 순서를 뒤집음 | ✅ |
| 400 `invalid_token` 을 성공 취급 | `revoked=False` 반환으로 변경 | ✅ |
| 목록 owner-only | `require_owner` → `require_member` | ✅ |
| 목록이 workspace 격리 | WHERE 에서 `workspace_id` 제거 | ✅ |

### 5.3 evaluator — 독립 검증 에이전트

구현자(나)와 **분리된 에이전트**가 다음을 적대적으로 검증한다. 구현 의도를 모른 채 코드와 계약만 보고 판정한다.

1. **회수 순서 역전 / 부분 실패** — 중간 실패 시 문서가 남는 경로가 있는가
2. **I-9 격리** — 새 엔드포인트 2종에 cross-workspace 누수가 있는가
3. **I-EXT-1 owner 강제** — 새 엔드포인트가 `require_owner` 를 우회할 수 있는가
4. **토큰 노출** — refresh token 이 응답·로그·FE state 어디로도 새지 않는가 (ADR-026 D5)
5. **Picker 브라우저 토큰** — `localStorage`/`sessionStorage`/cookie/Zustand persist 에 저장되지 않는가, BE 로 전송되지 않는가
6. **계약 정합** — `api.gen.ts` 가 실제 라우터와 drift 0 인가
7. **테스트가 hollow green 인가** — §5.2 변이를 실제로 잡는가

evaluator 가 올린 지적은 **반박하지 않고 먼저 재현**한다. 재현되면 고치고, 재현되지 않으면 그 근거를 기록한다.

### 5.4 검증 증거 (AGENTS.md §4 표준)

- BE: pytest 결과 요약 + Docker 오류 사유 grep
- FE: typecheck + vitest + build 결과
- API 시그니처 변경: `contracts` 재생성 후 `git diff` 로 drift 0 확인
- ⚠ **스크린샷·E2E·alembic dry-run 은 이 환경에서 산출 불가** — 미산출 사실을 PR 에 명시한다. 없는 증거를 있다고 쓰지 않는다.

---

## 6. 배포

### 6.1 이 세션에서 배포는 불가능하다

| 필요 조건 | 상태 |
|---|---|
| `ssh` | ❌ 미설치 |
| Docker 데몬 | ❌ 미기동 (`docker info` 실패) |
| `buildx` arm64 | ❌ 데몬 부재로 불가 |
| 오라클 호스트 자격증명 | ❌ 세션에 없음 |
| `mise` | ❌ 미설치 |

`mise.toml [tasks.deploy-ship]` 은 `docker save … | ssh {{vars.oci_host}}` 다. **넷 중 하나도 충족되지 않는다.**

### 6.2 따라서 인계한다

코드·문서·검증을 완결해 브랜치에 푸시하고, 사용자 맥에서 실행할 배포 절차를 **정확한 명령**으로 인계한다. 새 `NEXT_PUBLIC_*` 빌드 인자가 생겼으므로 `deploy/oci/build.env` 갱신이 배포의 선행 조건이다 — 이걸 빠뜨리면 2026-08-17 Better Auth 컷오버 사고(빈 값이 조용히 주입돼 web 전면 500)와 같은 실패 모드가 재현된다.

---

## 7. 작업 단계

- [x] **W1** revoke + disconnect orchestrator + DELETE 엔드포인트 + 테스트
- [x] **W2** 목록 엔드포인트 + 테스트
- [x] **W3** FE api/hooks + Picker + settings UI + CSP + vitest
- [x] **W4** 문서 개정 + contracts 재생성
- [x] **V1** 게이트 실행 + 베이스라인 대조
- [ ] **V2** evaluator 독립 검증 + 지적 해소
- [ ] **D1** 커밋 + 푸시
- [ ] **D2** 배포 절차 인계
