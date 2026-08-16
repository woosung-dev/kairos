<!-- Kairos 프론트엔드 헌법 — Next.js 16 + RSC + FSD + 시안→컴포넌트 흐름 -->

# Frontend CONTEXT

> 루트 헌법: `/CONTEXT-MAP.md` 우선. 이 문서는 Next.js / React / FSD 레이어 규칙.

---

## 1. 책임

- 모든 UI 렌더링과 상호작용 (회의/노트/Inbox/RAG/프로젝트)
- Better Auth 인증 서버 마운트 (`app/api/auth/[...all]`) + 보호 라우트 리다이렉트 (`proxy.ts`) — ADR-031
- BE API 호출 (React Query)
- SSE 스트리밍 수신 (RAG 답변)
- 디자인 시스템(`/DESIGN.md`) 강제

## 2. 비책임

- 비즈니스 로직 (BE 책임)
- AI/임베딩/STT (BE 책임)
- 데이터 영속화 (BE + Postgres)

---

## 3. 디렉토리 (FSD)

```
apps/web/src/
├── proxy.ts       세션 쿠키 기반 리다이렉트 (Next.js 16 명칭 — middleware.ts 아님). 인가는 BE 몫
├── app/           라우트 진입점 — Thin Component (RSC 우선)
│   ├── (landing)/ 랜딩 + pricing
│   ├── (auth)/    자체 sign-in / sign-up 폼 (features/auth)
│   ├── (app)/     인증된 영역 — dashboard · projects · projects/[id] · meetings/[id]
│   │              · notes · notes/[id] · inbox · memory · search · actions · new
│   │              · settings · admin/recall-metrics
│   └── invite/    초대 수락 (그룹 밖 public 라우트)
├── components/
│   ├── ui/        shadcn v4 — 수정 금지 (F-1)
│   ├── layout/    Sidebar, Header, PanelLayout, RAGPanel, BottomNav, CmdK
│   ├── landing/   랜딩 섹션
│   ├── shared/    도메인 횡단 공통 (ItemPromoteModal, ExportButton)
│   └── onboarding/
├── features/      도메인별 비즈니스 레이어 (FSD)
│   ├── actions/  audit/  feedback/  home/  inbox/  integrations/  meetings/
│   ├── members/  memory/  notes/  onboarding/  projects/  rag/  sources/
│   ├── upload/  workspaces/
│   └── 각 feature: api.ts + hooks.ts + types.ts + components/
│                   (+선택 schemas.ts / store.ts / CONTEXT.md)
├── hooks/         앱 전역 유틸 훅
├── lib/           api-client, use-api-client, query-client, query-keys, visibility, utils
├── store/         Zustand (전역 UI 상태만)
└── types/         api.gen.ts (생성물, I-22) + 공통 유틸 타입
```

> features 개수는 여기에 적지 않는다 — 정본은 `/CONTEXT-MAP.md` §4.3 이다.
> **barrel `index.ts` 를 두지 않는다** (현재 0개, 예외 없음). Next.js 는 barrel import 를
> 빌드 비용으로 취급하고, feature 경계는 F-9 + eslint `no-restricted-imports` 가 이미 강제한다.
> **`server/` 폴더도 없다** — 데이터 페칭은 100% 클라이언트 TanStack Query 다.
> **`mocks/` 는 존재하지 않는다** (`NEXT_PUBLIC_API_MOCK` 도 없다). FE 는 항상 실제 BE 를 호출한다.

> `editor/` 별도 feature 폴더 없음. TiptapEditor(useEditor/EditorContent)는
> `features/notes/components/note-detail.tsx` — 옛 `note-editor.tsx` 는 importer 0 dead-code 로 삭제됐다.

---

## 4. 핵심 불변식

| # | 불변식 | 강제 |
|---|---|---|
| F-1 | **`components/ui/` 수정 금지** (shadcn 원본 보존) | code review |
| F-2 | **Thin Component** — `app/` 페이지는 데이터 fetch + feature 컴포넌트 조립만 | 페이지 코드 80줄 이내 가이드 |
| F-3 | **RSC 우선**, 클라이언트 컴포넌트는 인터랙션 필수 시만 | `'use client'` 최소화 |
| F-4 | **상태 분리**: Server State = React Query, Client Global = Zustand, Client Local = useState | `store/`는 UI 상태만 |
| F-5 | **에러 위임**: `Suspense` + `ErrorBoundary` 사용 | feature 경계마다 |
| F-6 | **TypeScript Strict**, `any` 금지 | tsconfig + lint |
| F-7 | **Boolean 접두사**: `is`, `has`, `should` | naming |
| F-8 | **이벤트**: 핸들러는 `handle*`, Props는 `on*` | naming |
| F-9 | **API 호출은 feature 안의 `api.ts`만** — 다른 feature의 api 직접 호출 금지 | code review |
| F-10 | **DESIGN.md 토큰 사용** — Tailwind 임의 색/폰트 금지 | code review |
| F-11 | **API URL 패턴**: `/api/v1/workspaces/{workspaceId}/<resource>` (CONTEXT-MAP I-13). `workspaceId`는 라우트 또는 store에서 획득 | `<feature>/api.ts` |
| F-12 | **SSE 수신 패턴**: RAG 답변은 `EventSource` 또는 `fetch + ReadableStream`으로 chunk 누적 | `features/rag/hooks.ts` |

---

## 5. 도메인 features 책임 (BE 도메인과 매핑)

| Feature | 대응 BE 도메인 | 핵심 컴포넌트 |
|---|---|---|
| actions/ | actions | action-board |
| audit/ | (BE `common/audit_router.py`) | audit-list — role 변경 / promote trail |
| feedback/ | feedback | feedback-button (dogfooding 위젯) |
| home/ | (다도메인 조합 — 대시보드) | dashboard-suggestions, ActivityFeed |
| inbox/ | inbox | inbox-list, inbox-item-card, smart-inbox |
| integrations/ | integrations | 외부 문서 상세 조회 (Google Drive, ADR-026) |
| meetings/ | meetings | upload, meeting-detail, transcript-viewer |
| members/ | workspaces (member + invite) | invite-manager, member-list |
| memory/ | memory | CaptureSheet, RecallResultCard |
| notes/ | notes | note-list, **note-detail** (Tiptap 에디터), quick-memo |
| onboarding/ | onboarding | step progression |
| projects/ | projects | project-list, dashboard/, create-project-dialog, ProjectAdminDialogs |
| rag/ | rag | RAGPanel, ask-input, answer-card (SSE), markdown-message |
| sources/ | (다도메인 조합 — 출처 뷰) | source-viewer |
| upload/ | upload | upload-dropzone (presigned URL), useRecording |
| workspaces/ | workspaces (workspace) | WorkspaceSwitcher, DangerZone, WorkspaceTypeBadge |

> `sources/`, `home/`, `audit/` 는 단일 BE 도메인 매핑이 아닌 **다도메인 조합 뷰**.
> BE ↔ FE 전체 매핑 인덱스: `docs/product/domains/README.md`.

---

## 6. 시안 → 컴포넌트 흐름 (Stage 3 산출 시)

1. `/design-shotgun` 또는 Figma 시안 승인
2. `apps/web/src/features/<domain>/components/` 안에 컴포넌트 생성
3. shadcn 토큰만 사용 (DESIGN.md 참조)
4. RSC 기본, 클라이언트 인터랙션은 child만 `'use client'`
5. 라우트로 시각 확인 → `/design-review`

---

## 7. 환경

- Next.js 16 + React 19, App Router
- pnpm (Yarn/npm 금지)
- Tailwind v4 + shadcn v4
- Zod v4 (schema validation)
- 상세 규칙: [`AGENTS.md`](AGENTS.md) (같은 디렉터리 — `CLAUDE.md` 가 본 파일과 함께 자동 로드, ADR-029)
