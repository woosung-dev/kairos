# ADR-030: `apps/backend` → `apps/api` 개명

**Status**: Accepted
**Date**: 2026-08-16
**관련**: [ADR-027](027-apps-monorepo-and-contract-governance.md) D1 (본 ADR 이 부분 대체) · [ADR-028](028-oci-selfhosting.md) (배포 단위) · `docs/architecture/directory-map.md` · `justfile`
**선례**: ADR-027 §3 "과거 문서의 구 경로는 역사 기록으로 보존한다"

---

## 1. 배경

ADR-027 D1 이 `backend/` → `apps/backend/`, `frontend/` → `apps/web/` 로 App-first 레이아웃을 세울 때
앱 이름을 각각 `backend` / `web` 으로 정했다. 당시 근거는 "기존 폴더명 보존 + 이동 비용 최소화" 였고
이름 자체를 검토한 기록은 없다.

2026-08-16 모노레포 표준 구조 점검에서 다음이 드러났다.

1. **레포 안에서 이미 `api` 가 사실상의 이름이다.** 배포 이미지명 `kairos-api`,
   compose 서비스명 `api`, `docker-entrypoint.sh` 의 role `api`, 프로덕션 도메인
   `kairos-api.woosung.dev`. `apps/backend` 만 다른 단어를 쓰고 있었다.
2. **`backend` 는 레이어 이름이고 `api` 는 배포 단위 이름이다.** `apps/*` 의 분류 규칙은
   ADR-027 D1 이 "독립 실행·빌드·배포되는 소프트웨어 단위" 로 정의했다. 그 규칙에
   레이어 이름을 넣으면 `apps/worker` 가 생기는 날 `apps/backend` 와 의미가 겹친다.
3. 반대 논거도 실재한다 — 이 앱은 FastAPI `BackgroundTasks` 로 STT·AI 파이프라인을
   같은 프로세스에서 돌리므로 순수 API 서버가 아니다. 다만 그것은 **분리되지 않았다는 사실**이지
   이름이 `backend` 여야 한다는 근거는 아니다. worker 가 분리되는 날(트리거는 BL-OCI-4)
   `apps/api` + `apps/worker` 가 되고, 그때 `apps/backend` 라는 이름은 남을 자리가 없다.

## 2. 결정

### D1. `apps/backend/` → `apps/api/` (ADR-027 D1 부분 대체)

`apps/web` 은 그대로 둔다. `apps/*` 분류 규칙(ADR-027 D1 표)과 `contracts/` · `packages/` 정책은
변경 없이 유효하다.

이동은 ADR-027 D1 과 같은 **2-commit 구조**로 수행한다.

1. 순수 `git mv apps/backend apps/api` — 경로 참조 0줄 수정 (rename 검출 R100 보존, 실측 367/367)
2. 경로 참조 일괄 수정 + 본 ADR

### D2. 과거 문서의 구 경로 읽는 법

**2026-08-16 이전 문서(`docs/adr/001~029`, `CHANGELOG.md`, `docs/archive/**`)의 `apps/backend/` 는
`apps/api/` 로 읽는다.** 역사 기록은 수정하지 않는다 — ADR-027 §3 이 세운 원칙을 그대로 잇는다.
`backend/`(2026-08-13 이전 표기) 는 ADR-027 §3 규칙을 거쳐 최종적으로 `apps/api/` 로 읽는다.

### D3. 수반 작업

| 대상 | 내용 |
|---|---|
| `justfile` | recipe 5개의 `cd apps/backend`, `deploy-build` 의 **빌드 컨텍스트** |
| `.github/workflows/` | `test.yml` paths-filter 2 필터 + `working-directory`, `nightly-e2e.yml`, `r2-cleanup.yml` |
| `pyrightconfig.json` (루트) | `venvPath` · `extraPaths` · `include` · `executionEnvironments` 전부 |
| `.worktreeinclude` | `apps/api/.env` — **틀리면 워크트리 세션이 `.env` 없이 조용히 부팅 실패한다** |
| `.gitignore` | 7건 |
| `pyproject.toml` + `uv.lock` | `name = "backend"` → `"kairos-api"`. 가상 패키지명이라 `uv lock` 재생성 필요 (의존성 해석 변화 0) |
| 수동 | `cd apps/api && uv sync` — venv 는 절대 경로가 구워져 있어 디렉터리 이동으로 무효가 된다 |

### D4. 영향받지 않는 것 (수정 금지)

- `deploy/oci/docker-compose.prod.yml` — 빌드 컨텍스트 없이 완성 이미지(`kairos-api:${TAG}`)만 참조
- `apps/api/Dockerfile` · `docker-entrypoint.sh` · `alembic.ini` — 전부 앱 내부 상대 경로
- `apps/web/package.json` `gen:api` — `../../contracts/...` 상대 경로
- `contracts/openapi/v1/openapi.json` — 경로 문자열 0건. **`just contracts-check` 는 이 개명으로 깨지지 않는다**

### D5. 재확인 — CODEOWNERS 는 여전히 기각

ADR-027 D5 의 CODEOWNERS 기각(1인 개발, PERSONA-001)을 본 ADR 에서 재확인한다.
같은 라운드에서 신설한 `.github/PULL_REQUEST_TEMPLATE.md` 는 성격이 다르다 —
**리뷰어가 없기 때문에** 검증 증거 표준(`AGENTS.md` §4)과 Atomic Update 규칙(§5)을 강제할
지점이 PR body 밖에 없다. 소유권 표(CODEOWNERS)는 리뷰어가 2명 이상일 때 의미가 생긴다.

## 3. 결과

- `apps/` 아래 이름이 배포 단위 이름으로 통일된다 — `api` / `web`, 그리고 훗날 `worker`.
- **프로덕션 영향 0.** 이미지명·컨테이너 내부 경로·compose 가 모두 그대로다.
  배포 중인 서버는 이 변경의 영향을 받지 않고, 다음 `just deploy-build` 부터 새 경로를 쓴다.
- 비용: 경로 참조 168 파일 일괄 수정(역사 문서 제외), `uv.lock` 재생성, `.venv` 재생성 1회.
- **CI 가 GitHub Actions 결제 실패로 중단된 상태**에서 수행하므로, 회귀 증거는 로컬 게이트
  (`just ci-local`, 같은 라운드에서 신설)의 출력이 전부다. 특히 `test.yml` paths-filter 수정
  누락은 결제 복구 전까지 노출되지 않는다 — `docs/TODO.md` Blocked 에 "결제 복구 시 재확인" 을 등재했다.
