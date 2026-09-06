# Kairos Web (Next.js 16)

Kairos 의 사용자 인터페이스. App Router + React 19 + Tailwind v4 + shadcn/ui v4.
OCI 단일 VM 위 컨테이너로 배포된다 ([ADR-028](../../docs/adr/028-oci-selfhosting.md)).

<img src="public/landing/screenshots/screenshot-dashboard.png" alt="대시보드" width="820" />

## 실행

**pnpm 전용이다 — npm / yarn 을 쓰지 않는다.** 명령은 루트 `mise.toml` 이 단일 진입점이다.

```bash
mise run install   # pnpm install --frozen-lockfile
mise run fe-dev    # next dev :3000
mise run fe-test   # vitest
mise run fe-build  # next build (타입 검사 포함)
mise run e2e       # playwright
```

환경변수는 `.env.example` → `.env.local`. **BE 가 떠 있어야 화면이 동작한다.**
Mock 모드가 없다 — `mocks/` 도 `NEXT_PUBLIC_API_MOCK` 도 존재하지 않고, FE 는 항상 실제 BE 를 호출한다.
셋업 전체는 [`docs/development/getting-started.md`](../../docs/development/getting-started.md).

## 구조 (FSD)

```
src/
├── proxy.ts       세션 쿠키 기반 리다이렉트 — Next.js 16 명칭 (middleware.ts 아님)
│                  ★ 인가는 BE 몫이다. 여기서는 하지 않는다
├── app/           라우트 진입점 — Thin Component (RSC 우선)
│   ├── (landing)/ 랜딩 + pricing
│   ├── (auth)/    sign-in / sign-up (Better Auth, ADR-031)
│   ├── (app)/     인증 영역 — dashboard · projects · meetings · notes · inbox
│   │              · memory · search · actions · new · settings
│   │              · admin/recall-metrics — founder 표시 게이트, **유일한 admin 화면 (별도 admin 앱 없음)**
│   ├── api/auth/[...all]/route.ts   Better Auth 핸들러 — 이 앱의 유일한 route handler. JWKS(`/api/auth/jwks`)도 여기서 서빙
│   └── invite/    초대 수락 (그룹 밖 public 라우트)
├── components/
│   ├── ui/        shadcn v4 — 수정 금지 (F-1)
│   ├── layout/    Sidebar · Header · PanelLayout · RAGPanel · BottomNav · CmdK
│   ├── landing/   랜딩 섹션
│   ├── shared/    도메인 횡단 공통 (ItemPromoteModal · ExportButton)
│   └── onboarding/
├── features/      도메인별 비즈니스 레이어 — 각 feature = api.ts + hooks.ts + types.ts + components/
│                  (+ 선택 schemas.ts · store.ts · CONTEXT.md). 17 feature ↔ BE 도메인 매핑은 아래 표
├── hooks/         앱 전역 유틸 훅
├── lib/           api-client · query-client · query-keys · visibility · utils
├── store/         Zustand (전역 UI 상태만)
└── types/         api.gen.ts (생성물, I-22) + 공통 유틸 타입
```

**barrel `index.ts` 를 두지 않는다** (현재 0개, 예외 없음). Next.js 는 barrel import 를 빌드 비용으로
취급하고, feature 경계는 F-9 + eslint `no-restricted-imports` 가 이미 강제한다.
**`server/` 폴더도 없다** — 데이터 페칭은 100% 클라이언트 TanStack Query 다.

`admin/recall-metrics`의 founder 판정은 `NEXT_PUBLIC_FOUNDER_USER_ID`를 비교하는 **FE 표시 게이트**다.
클라이언트 공개 값이므로 인가 경계가 아니며, 실제 `GET .../memory/metrics` API는 workspace `viewer+`를 허용한다.

### features ↔ BE 도메인 매핑

| Feature | 대응 BE 도메인 | 핵심 컴포넌트 |
|---|---|---|
| `auth/` | auth | sign-in / sign-up 폼 (Better Auth 클라이언트) |
| `workspaces/` | workspaces | WorkspaceSwitcher · DangerZone · WorkspaceTypeBadge |
| `members/` | workspaces (member + invite) | invite-manager · member-list |
| `projects/` | projects | project-list · dashboard · ProjectAdminDialogs |
| `meetings/` | meetings | upload · meeting-detail · transcript-viewer |
| `notes/` | notes | note-list · **note-detail** (Tiptap 에디터) · quick-memo |
| `actions/` | actions | action-board |
| `inbox/` | inbox | inbox-list · inbox-item-card · smart-inbox |
| `memory/` | memory | CaptureSheet · RecallResultCard |
| `rag/` | rag | RAGPanel · ask-input · answer-card (SSE) · markdown-message |
| `upload/` | upload | upload-dropzone (presigned URL) · useRecording |
| `integrations/` | integrations | 외부 문서 상세 (Google Drive, ADR-026) |
| `onboarding/` | onboarding | step progression |
| `feedback/` | feedback | feedback-button (dogfooding 위젯) |
| `home/` | 다도메인 조합 | dashboard-suggestions · ActivityFeed |
| `sources/` | 다도메인 조합 | source-viewer |
| `audit/` | `common/audit_router.py` | audit-list — role 변경 / promote trail |

정본: [`CONTEXT.md`](CONTEXT.md) §3 · §5 · 전체 트리는
[`docs/architecture/directory-map.md`](../../docs/architecture/directory-map.md).
레포 전체에서 이 앱이 차지하는 자리(계약 파이프라인 · CI 게이트 · 배포 경로)는
[`docs/architecture/diagrams/repo-structure.html`](../../docs/architecture/diagrams/repo-structure.html) 인터랙티브 다이어그램.

## 상태 관리 3층

섞지 않는다. 어디에 둘지 헷갈리면 **서버에서 온 것은 전부 React Query** 다.

| 종류 | 도구 | 기준 |
|---|---|---|
| Server state | TanStack Query v5 | API 응답. 캐시 키는 `lib/query-keys.ts` 에 모은다 |
| Client global | Zustand | 화면 간 공유되는 **UI 상태만** (패널 열림 등). 서버 데이터 복제 금지 |
| Local | `useState` | 한 컴포넌트 안에서 끝나는 것 |

## ★ 타입

`src/types/api.gen.ts` 는 **OpenAPI 계약 생성물이다 — 손으로 수정하지 않는다.**
wire 타입은 여기서 import 하고, 재생성은 루트에서 `mise run contracts`
([I-22](../../CONTEXT-MAP.md), [ADR-027](../../docs/adr/027-apps-monorepo-and-contract-governance.md) D2).

수기 wire interface 를 새로 쓰면 계약 게이트(`mise run contracts-check`)가 CI 에서 막는다.

## 테스트

| 종류 | 위치 | 명령 |
|---|---|---|
| 단위 (39 파일) | 코드 옆 `__tests__/` | `mise run fe-test` |
| e2e (44 spec) | `e2e/` | `mise run e2e` |

Playwright project 3종:

- **`chromium`** — 로그인 후 본 기능 회귀. `setup`(auth.setup.ts)이 storageState 를 먼저 만든다
- **`public-only`** — `security-headers.spec.ts` 전용. 로그인도 BE 도 필요 없어 CI 에서 단독으로 돈다
  (`mise run fe-security-headers`)
- **`team`** — RBAC 회귀 T1~T23. `team-setup` 이 별도 계정 세트를 준비한다

상세: [`docs/development/testing.md`](../../docs/development/testing.md)

## 규칙

- 스택 함정 (Next 16 / Zod v4 / shadcn v4 / 반응형 / e2e): [`AGENTS.md`](AGENTS.md)
- 불변식 (F-NN) + 디렉터리 + feature 매핑: [`CONTEXT.md`](CONTEXT.md)
- 시각·UI 정본: [`/DESIGN.md`](../../DESIGN.md) — `components/ui/` 수정 금지 (F-1)
