# Kairos Web (Next.js 16)

Kairos 의 사용자 인터페이스. App Router + React 19 + Tailwind v4 + shadcn/ui v4.
OCI 단일 VM 위 컨테이너로 배포된다 ([ADR-028](../../docs/adr/028-oci-selfhosting.md)).

## 실행

**pnpm 전용이다 — npm / yarn 을 쓰지 않는다.** 명령은 루트 `justfile` 이 단일 진입점이다.

```bash
just install   # pnpm install --frozen-lockfile
just fe-dev    # next dev :3000
just fe-test   # vitest
just fe-build  # next build (타입 검사 포함)
just e2e       # playwright
```

환경변수는 `.env.example` → `.env.local`. **BE 가 떠 있어야 화면이 동작한다** (Mock 모드 없음).
셋업 전체는 [`docs/development/getting-started.md`](../../docs/development/getting-started.md).

## 구조

`app/`(route group `(landing)` / `(auth)` / `(app)`) + `features/`(FSD) + `components/` + `lib/`.
미들웨어는 Next.js 16 명칭인 **`src/proxy.ts`** 다 (`middleware.ts` 아님).

정본: [`CONTEXT.md`](CONTEXT.md) §3 · 전체 트리는
[`docs/architecture/directory-map.md`](../../docs/architecture/directory-map.md).

## ★ 타입

`src/types/api.gen.ts` 는 **OpenAPI 계약 생성물이다 — 손으로 수정하지 않는다.**
wire 타입은 여기서 import 하고, 재생성은 루트에서 `just contracts`
([I-22](../../CONTEXT-MAP.md), [ADR-027](../../docs/adr/027-apps-monorepo-and-contract-governance.md) D2).

## 테스트

- 단위: 코드 옆 `__tests__/` (vitest)
- e2e: `e2e/` (playwright) — project `chromium` / `public-only`(보안 헤더) / `team`(RBAC 회귀 T1~T23)
- 상세: [`docs/development/testing.md`](../../docs/development/testing.md)

## 규칙

- 스택 함정 (Next 16 / Zod v4 / shadcn v4 / 반응형 / e2e): [`AGENTS.md`](AGENTS.md)
- 불변식 (F-NN) + 디렉터리 + feature 매핑: [`CONTEXT.md`](CONTEXT.md)
- 시각·UI 정본: [`/DESIGN.md`](../../DESIGN.md) — `components/ui/` 수정 금지 (F-1)
