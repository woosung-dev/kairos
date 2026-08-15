<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

---

# Frontend Rules (Next.js 16)

> ★**본 파일은 코드 스켈레톤 + 스택 함정만 소유한다.**
> `F-NN`·`I-NN` 이 붙은 **불변식은 [`CONTEXT.md`](CONTEXT.md) §4 / `/CONTEXT-MAP.md` 소유이며 여기 재진술하지 않는다.**
> 충돌하면 CONTEXT 가 맞다. 규칙을 추가하고 싶으면 여기가 아니라 `CONTEXT.md` §4 에 `F-NN` 으로 넣어라
> ([ADR-029](../../docs/adr/029-ai-rules-relocation.md)).
>
> 시각·UI 정본은 `/DESIGN.md`. 프로젝트 전역 규칙은 `/AGENTS.md` — 본 문서는 그 둘을 **보강만** 한다.
> 이전 이력: 구 `.ai/stacks/nextjs/frontend.md` + `.ai/common/typescript.md` (2026-08-15 ADR-029).

## 1. Tech Stack

| 항목            | 기술                                  |
| --------------- | ------------------------------------- |
| Framework       | Next.js 16 (App Router)               |
| Language        | TypeScript Strict                     |
| Styling         | Tailwind CSS v4 + shadcn/ui v4        |
| Package Manager | `pnpm` (npm/yarn 금지)                |
| Server State    | React Query (`@tanstack/react-query`) |
| Client State    | Zustand                               |
| Form            | `react-hook-form` + `zod v4`          |
| Auth            | Clerk (`@clerk/nextjs`)               |
| 배포            | **Oracle Cloud A1 + Cloudflare Tunnel** (ADR-028 — Vercel 철거 완료) |

## 2. Next.js 16 필수 패턴

- `params`, `searchParams`는 **`Promise<>`** 타입 → `await` 필수
- `middleware.ts` 대신 **`proxy.ts`** 사용
- `node_modules/next/dist/docs/` 참조 필수 (위 마커 섹션)

```typescript
// ✅ Next.js 16
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <Detail id={id} />;
}
```

### Clerk (Next.js 16)

- 인증 보호: **`proxy.ts`** 에서 `clerkMiddleware()` 처리
- 서버 컴포넌트: `auth()` 또는 `currentUser()`
- 클라이언트 컴포넌트: `useAuth()`, `useUser()`
- 직접 JWT 파싱 금지

```typescript
// proxy.ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)", "/sign-up(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});
```

## 3. Zod v4

- `import { z } from "zod/v4"` 필수 (v3 경로 `"zod"` 금지)
- **Schema First:** 타입 중복 선언 금지 → `z.infer<typeof schema>` (필요 시 `z.input`)로 추출하여 재사용
- **Transform 강제:** Form 입력 타입(String)과 API 요청 타입(Number 등)이 다를 경우, `onSubmit` 내부에서
  수동 파싱 금지 → 스키마 레벨에서 `.transform()` 으로 일원화

```typescript
// ✅ 스키마에서 변환
const priceSchema = z.string().transform((v) => Number(v));

// ❌ onSubmit에서 수동 변환
const handleSubmit = (data: FormData) => {
  api.create({ price: Number(data.price) }); // 금지
};
```

## 4. shadcn/ui v4

- 내부 의존성: `@base-ui/react` (**Radix UI 아님**)
- `@radix-ui/*` 직접 import 금지
- 추가: `pnpm dlx shadcn@latest add [component]`
- `components/ui/` 수정 금지는 `CONTEXT.md` F-1 소유 — 확장은 래핑 컴포넌트로

## 5. 상태 관리 세부

3단계 분리(Server/Client Global/Local)와 에러 위임은 `CONTEXT.md` F-4 / F-5 소유.
아래는 거기 없는 운용 세부다.

- **React Query:** Query Key 하드코딩 금지 → 도메인별 **팩토리 패턴**. 호출 함수는 `features/<domain>/api.ts` 에 집중
- **Zustand:** 전역 상태는 최소화 — 컴포넌트 트리를 넓게 넘나드는 상태만
- 디렉토리 구조 정본은 `CONTEXT.md` §3 (실제 features 11개). 새 feature 추가 시 그 표를 갱신한다

## 6. TypeScript 컨벤션 (구 `typescript.md` 병합)

`any` 금지·Boolean 접두사·이벤트 네이밍은 `CONTEXT.md` F-6 / F-7 / F-8 소유. 아래만 여기 있다.

- `any` 가 불가피하면 **`unknown` + Type Guard** 로 좁힌다
- 상수는 `UPPER_SNAKE_CASE`
- ★**API wire 타입은 손으로 쓰지 않는다.** `apps/web/src/types/api.gen.ts` 생성물에서 import 하고,
  재생성은 `just contracts` (ADR-027, I-20). 구 `typescript.md` 의 「모든 API 응답 타입을 명시적으로 정의」는
  ADR-027 이전의 규칙이라 **폐기됐다**
- **파일명은 kebab-case** (`note-editor.tsx`, `use-media-query.ts`). 실측 98 vs 7 로 kebab 이 사실상의 표준이다.
  ★구 `typescript.md` 의 「컴포넌트 PascalCase / 훅 camelCase」는 코드와 맞지 않아 폐기.
  잔존 PascalCase 7개(`WorkspaceSwitcher.tsx` 등)는 **기존 파일이므로 이번에 개명하지 않는다** — 신규만 kebab

## 7. 반응형

- **Desktop-first** 접근 (기존 코드 기준)
- Breakpoint: `xl:` (≥1280px 기본), `md:` (768px compact), 기본 (mobile)
- 고정 px 대신 CSS 변수 — `globals.css` 의 `--sidebar-width`, `--sidebar-collapsed-width`
  (★구 규칙이 적던 `--rag-panel-width` 는 **실재하지 않는다** — 폐기)
- Mobile: `md:hidden` 으로 데스크톱 전용 요소 숨김
- `useBreakpoint()` 훅(`hooks/use-media-query.ts`)으로 isMobile/isCompact/isDesktop 감지
- Zustand `store/ui.ts`: `sidebarCollapsed`, `isMobile` 상태 관리

## 8. e2e (`apps/web/e2e/`)

- ★신규 page/component 를 만들면 **영향받는 spec 의 selector 도 같은 PR 에서** 갱신한다.
  static review 는 spec selector ↔ 신규 컴포넌트 label 의 cross-file 정합을 못 잡는다 (PR #101 CI fail)
- ★**`data-testid` 를 우선한다.** `getByRole` + regex + `.first()` 는 같은 라벨이 2개일 때
  의도와 다른 DOM 첫 매치를 조용히 집는다
- ★CI e2e 실패 시 **코드 추측 전에 trace.zip 의 page snapshot(`error-context.md`) 을 먼저 읽어라.**
  `gh run download <run-id> --dir /tmp/ci-artifacts` → `find ... -name error-context.md`.
  이 순서를 건너뛰어 헛다리 2회를 짚은 적이 있다 (PR #101 v1/v2)

> 위 3건 = Sprint 24 Wave 2 PR #101 회귀 (2026-05-20)
