# ADR-032 — just → mise 전환 (툴체인 고정 + task runner 통합)

**Status**: Accepted
**Date**: 2026-08-17
**Amends**: [ADR-027](027-apps-monorepo-and-contract-governance.md) D3 (단일 명령 진입점 = `justfile`)

---

## 배경

`justfile` 은 잘 동작하고 있었다. 이 전환의 출발점은 task runner 불만이 아니라 **툴 버전이 어디에도 선언돼 있지 않다**는 발견이다.

2026-08-17 실측:

| | Node | pnpm | uv |
|---|---|---|---|
| **프로덕션 이미지** | **22** (`apps/web/Dockerfile:9`) | **8.15.9** (`:11`) | **0.10.4** (`apps/api/Dockerfile:10`) |
| **CI** | **20** | **9** | **latest** |
| 로컬 | 22.23.1 | 8.15.9 | 0.10.4 |

**CI 가 배포되는 것과 다른 런타임에서 테스트하고 있었다.** 로컬이 프로덕션과 맞은 건 우연이다.

특히 uv 는 `apps/api/Dockerfile` 이 *"태그 고정. `:latest` 면 같은 커밋이 서로 다른 uv 로 빌드될 수 있다"* 라고 주석까지 달아 고정해뒀는데, CI 는 정확히 그 `latest` 를 쓰고 있었다. `.tool-versions` / `.nvmrc` / `packageManager` 어느 것도 없었다.

---

## 결정

### D1. `justfile` 을 폐기하고 `mise.toml` 로 전면 이관한다 (25 task)

툴 버전 관리만 도입하고 just 를 남기는 안도 검토했으나, **명령의 출처가 둘이 되면 문서 27개가 두 도구를 동시에 가리킨다.** 전환 비용의 대부분이 mise.toml 작성(30분)이 아니라 문서 스윕이므로, 나눠서 하면 그 비용을 두 번 낸다.

`mise tasks` (목록) · `mise run <task>` (실행) · `mise run deploy-build 9e7dcf8` (인자).

### D2. `[tools]` 의 값은 **프로덕션 Dockerfile** 에서 가져온다 (CI 아님)

```toml
[tools]
node = "22"        # apps/web/Dockerfile:9
pnpm = "8.15.9"    # apps/web/Dockerfile:11
uv = "0.10.4"      # apps/api/Dockerfile:10
```

배포되는 산출물이 진실이다. CI 를 기준으로 맞추면 "테스트는 통과했는데 프로덕션에서 다르게 도는" 상태를 고정하게 된다.

### D3. Python 은 `[tools]` 에 넣지 않는다

`apps/api/.python-version`(3.12) + `pyproject.toml` 의 `requires-python` 으로 **uv 가 이미 소유**한다. 여기에 또 쓰면 소유자가 둘이 되고, 그건 ADR-031 D4(스키마 소유권 = alembic 단독)와 같은 이유로 피한다.

### D4. 순서가 계약인 곳에 `depends` 를 쓰지 않는다 ★

**mise 의 `depends` 는 병렬 실행이다** (실측: 선언 순서 A,B,C 를 주면 완료 순서 B,C,A 로 끝난다). just 의 순차 의존과 의미가 다르다.

이 레포에는 순서가 계약인 곳이 둘 있다:

- `contracts` — `openapi-export` 산출물을 `types-gen` 이 먹는다
- `ci-local` — `contracts-check` 가 `fe-test`/`fe-build` **앞**이어야 한다 (`api.gen.ts` 재생성 순서, 2026-08-16 코드리뷰 지적). `fe-security-headers` 는 `fe-build` 의 `.next` 산출물에도 의존한다

`--jobs 1` 로도 순차가 되지만 **호출자가 플래그를 기억해야 하는 계약은 계약이 아니다.** 본문에 `mise run` 을 나열해 순서를 파일에 박는다.

### D5. `[task_config] shell` 로 `pipefail` 을 되찾는다 ★

mise 의 기본 셸은 **pipefail 이 꺼져 있다** (실측: `false | true` 가 성공으로 통과). 구 `justfile` 은 `set shell := ["bash", "-euo", "pipefail", "-c"]` 로 켜져 있었다.

그대로 옮겼다면 `deploy-ship` 의 `docker save ... | gzip | ssh 'gunzip | docker load'` 에서 **앞단이 죽어도 배포가 성공으로 보고**된다. 2026-08-17 컷오버에서 겪은 조용한 실패와 같은 계열이다.

```toml
[task_config]
shell = "bash -euo pipefail -c"
```

### D6. 인자는 `usage` 필드로 쓴다 (`{{arg()}}` 금지)

Tera 템플릿 함수 `arg()`/`option()`/`flag()` 는 **deprecated 이고 mise 2027.5.0 에서 제거**된다 (실행 시 경고가 뜬다). `usage` 필드는 경고가 없고 에러 메시지도 낫다 (`Missing required arg: <tag>`).

```toml
usage = 'arg "<tag>" help="이미지 태그"'
run = 'docker buildx build -t "kairos-api:$usage_tag" ...'
```

가변 인자는 `arg "<args>..."` 다. `var=true` 는 KDL 파싱 에러이며 `mise tasks validate` 가 잡아준다.

### D7. CI 도 `jdx/mise-action` 으로 통일한다 — **워크플로 3개 전부**

`setup-node` / `pnpm/action-setup` / `setup-uv` / `setup-just` 를 전부 걷어내고 잡마다 `mise-action` 하나로 대체한다. 이로써 **로컬 · CI · 프로덕션이 한 파일(`mise.toml`)에서 나온다** — 이게 이 ADR 의 실익이다.

부수 효과로 CI 가 Node 20 → 22, pnpm 9 → 8.15.9, uv latest → 0.10.4 로 프로덕션에 정렬된다. pnpm 은 락파일이 `lockfileVersion: '6.0'`(pnpm 8 포맷)이므로 이쪽이 원래 맞았다.

**★대상은 `test.yml` 만이 아니다.** 초판은 `test.yml` 만 옮기고 `nightly-e2e.yml` · `r2-cleanup.yml` 을 남겼는데, 그러면 **위 "한 파일에서 나온다" 가 착지하는 순간 거짓이 된다.** 특히 `nightly-e2e.yml` 은 meeting-upload + team spine T1~T21 의 **유일한** 게이트라, 거기만 pnpm 9 / Node 20 으로 남으면 nightly 결과가 PR CI 와 모순될 수 있다. 세 파일 모두 전환한다.

**액션 버전은 `v4.2.5` 로 핀한다.** `v2`(2025-07-27 이후 정지)는 `runs: using: node20` 이라, Node20 deprecated 액션을 걷어낸 PR #173 의 성과를 잡 4개에 되돌린다. `v4.2.5` 는 `node24` 다. 잡별로 `install_args` 를 줘서 필요한 툴만 깐다 (`backend-test: uv`, `frontend-build: node pnpm`, `r2-cleanup: uv`).

### D8. 툴체인 핀은 **주석이 아니라 게이트**로 강제한다

초판은 `[tools]` 값 옆에 `# apps/web/Dockerfile:9` 같은 출처 주석만 달고 "드리프트의 단일 소유자" 라고 선언했다. **그러나 주석은 아무도 검사하지 않는다.** 한쪽만 올리면 주석이 거짓말이 되고 CI ↔ 프로덕션이 다시 갈라진다 — 이 ADR 이 없애려던 바로 그 상태다.

`mise run toolchain-check` 가 `[tools]` 의 세 값을 Dockerfile 의 실제 핀과 대조한다. `contracts-check` 가 API 계약에 하는 일을 툴체인에 그대로 한다. `ci-local` 첫 단계이자 CI `contract-check` 잡의 스텝이다.

---

## 기각한 대안

**① just 유지 + mise 는 `[tools]` 만** — 가장 안전하지만 명령 출처가 둘로 남는다. 문서 27개가 "이건 just, 저건 mise" 를 설명해야 하고 그 상태가 영구화된다.

**② 2단계 분할 (비-deploy 먼저, deploy 는 컷오버 +7일 이후)** — `deploy-*` 8개가 2026-08-24 까지 롤백 경로라는 점은 실재하는 우려였다. 다만 **`mise run deploy-rollback 9e7dcf8`(현재 태그 = 실질 no-op)을 실행해 sed·ssh·`up -d` 경로 전체를 실증**할 수 있어 우려가 해소됐다. 분할하면 문서 스윕을 두 번 한다.

---

## 검증 (전부 프로덕션/실행 기반)

- `mise tasks validate` → 25 task 전부 통과
- 프로덕션 실행: `deploy-preflight`(회의 0 + 인코딩 게이트) · `deploy-verify-env`(3종 주입 OK) · `deploy-sync-config`(compose 문법 OK) · `deploy-status`(ready 200)
- **`deploy-rollback 9e7dcf8`** — 현재 태그로 실행해 전체 경로 실증. 직후 `api_ready=200` / `web=200`
- 인자 가드: `fe-security-headers abc` 거부 · `deploy-build`(인자 누락) 거부 · 기본값 3005 적용
- `mise ls --current` → node 22.23.2 / pnpm 8.15.9 / uv 0.10.4 (프로덕션과 일치)
- task cwd 는 **config 루트** 고정 — CI 의 `working-directory: apps/web` 과 충돌 없음 (실측)

---

## ADR-027 D3 와의 관계

ADR-027 D3 의 **"단일 명령 진입점" 원칙과 "CI invocation 과 문자 그대로 동일" 규약은 그대로 승계**한다. 진입점 파일만 `justfile` → `mise.toml` 로 바뀐다. ADR-027 본문은 역사 기록이라 수정하지 않는다.

---

## 초판 이후 리뷰에서 잡은 것 (2026-08-17, `/code-review` + `/codex`)

두 리뷰가 독립적으로 같은 P1 을 지목했다 — **`mise.toml` 이 `contracts` paths-filter 에만 있었다.** `[tools]` 가 런타임 버전을 소유하게 됐으므로 툴체인만 바꾼 PR 이 `backend-test`/`frontend-build` 를 skip 한 채 `ci-required` green 이 된다. 이 ADR 이 막으려던 사고를 이 ADR 이 새로 만든 셈이라 `api`/`web` 필터에 추가했다.

그 외 실측으로 확인해 고친 것:

| | 내용 |
|---|---|
| `verify-prod` 회귀 | `arg "<args>..."` 가 **필수** 라 무인자 실행이 죽었다. `scripts/verify-prod.sh:15` 가 `${1:-https://kairos-api.woosung.dev}` 로 무인자를 기본 경로로 삼는다 → `arg "[args]..."` 로 교정. ★`-u` 때문에 `${usage_args:-}` 의 `:-` 가 필수다 (생략 인자는 변수 자체가 없다) |
| 워크플로 2개 누락 | `nightly-e2e.yml` · `r2-cleanup.yml` (D7 참조) |
| 액션 런타임 | `mise-action` v2 = node20 → `v4.2.5` = node24 (D7 참조) |
| 주석뿐인 SSOT | `toolchain-check` 게이트 신설 (D8) |
| `install` task | 두 `cd` 가 한 셸에서 연쇄돼 두 번째가 첫 번째 착지점에 의존했다 → 각 줄을 서브셸로 |
| 문서 잔여 | `README.md`(`brew install just`), `export_openapi.py:5`, `build.env.example:3`, `testing.md` 의 CI 스텝명(전환 이전부터 어긋나 있었다), 인계문서의 죽은 라인 인용 |

## 이번 범위에서 제외한 갭

1. ~~pnpm store 캐시~~ — **실측으로 해소.** 전환 전후 CI 시간이 사실상 동일했다 (backend-test 3m35s→3m47s, frontend-build 1m33s→1m33s, e2e 2m16s→2m10s, contract-check 28s→28s). `actions/cache` 부착은 불필요.
2. ~~Node 22 첫 run~~ — **통과 확인.** e2e 포함 6개 잡 전부 green.
3. **`node = "22"` 는 major 핀이다** (pnpm/uv 는 exact). `apps/web/Dockerfile` 의 `node:22-alpine` 도 같은 방식이라 `toolchain-check` 는 "선언이 서로 같은가" 까지만 보장하고 "해석된 patch 가 같은가" 는 보장하지 않는다. 양쪽을 exact 로 올리려면 Dockerfile 재빌드가 동반되므로 별건.
4. `docs-check`(BL-S29-1) 는 여전히 미구현. 이름만 `mise run docs-check` 로 갱신했다.
