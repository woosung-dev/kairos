<!-- Kairos 프론트엔드 헌법 — Next.js 16 + RSC + FSD + 시안→컴포넌트 흐름 -->

# Frontend CONTEXT

> 루트 헌법: `/CONTEXT-MAP.md` 우선. 이 문서는 Next.js / React / FSD 레이어 규칙.

---

## 1. 책임

- 모든 UI 렌더링과 상호작용 (회의/노트/Inbox/RAG/프로젝트)
- Clerk 인증 (`proxy.ts`로 미들웨어)
- BE API 호출 (React Query) + Mock 데이터 (개발용)
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
├── app/           라우트 진입점 — Thin Component (RSC 우선)
│   ├── (auth)/    Clerk 인증
│   ├── (landing)/ 랜딩 페이지
│   ├── (app)/     인증된 영역 (dashboard, inbox, workspace/[id]/...)
│   └── invite/    초대 수락
├── components/
│   ├── ui/        shadcn v4 — 수정 금지
│   └── layout/    Sidebar, Header, PanelLayout, RAGPanel
├── features/      도메인별 비즈니스 레이어 (실제 11개)
│   ├── inbox/  projects/  meetings/  actions/
│   ├── notes/  (TiptapEditor 포함: components/note-editor.tsx)
│   ├── rag/  members/  workspaces/
│   ├── upload/  sources/  home/
│   └── 각 feature: components/ + api.ts + hooks.ts + schemas.ts + types.ts
├── hooks/         공통 유틸 훅
├── lib/           constants, utils, query-client
├── mocks/         Mock data (개발용)
├── store/         Zustand (전역 UI 상태만)
└── types/         공통 유틸 타입 (UUID, Timestamped)
```

> `editor/` 별도 feature 폴더 없음. TiptapEditor는 `features/notes/components/note-editor.tsx`.

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
| inbox/ | inbox | inbox-list, inbox-item-card, classify-dialog |
| projects/ | projects | project-list, project-detail, create-project-dialog |
| meetings/ | meetings | upload, detail, transcript-viewer |
| actions/ | actions | action-board |
| notes/ | notes | note-list, note-detail, **note-editor** (Tiptap) |
| rag/ | rag | RAGPanel, ask-input, answer-card (SSE) |
| members/ | workspaces (member + invite) | invite-dialog, member-list |
| workspaces/ | workspaces (workspace) | workspace-switcher |
| upload/ | upload | upload-dropzone (presigned URL) |
| sources/ | (다도메인 조합 — 자료 목록 뷰) | source-list |
| home/ | (다도메인 조합 — 대시보드 위젯) | home-dashboard |

> `sources/`, `home/`은 단일 BE 도메인 매핑이 아닌 **다도메인 조합 뷰**. BE 호출은 여러 feature의 api 통과.

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
- 상세 규칙: `.ai/stacks/nextjs/frontend.md` (Sprint 26 부터 `.ai/rules/` 심링크 폐지)
