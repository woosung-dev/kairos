# 디렉토리 구조 맵

## 프론트엔드 (FSD 기반)

```
frontend/
├── proxy.ts                           # Clerk 인증 미들웨어 (Next.js 16)
└── src/
    ├── app/                           # 라우트 진입점 (Thin Component)
    │   ├── (auth)/                    # Clerk 인증
    │   │   ├── sign-in/[[...sign-in]]/
    │   │   └── sign-up/[[...sign-up]]/
    │   ├── dashboard/
    │   ├── inbox/
    │   ├── weekly-review/
    │   └── workspace/[workspaceId]/
    │       ├── projects/[paraId]/
    │       │   ├── meetings/[meetingId]/
    │       │   ├── notes/
    │       │   ├── actions/
    │       │   ├── files/
    │       │   └── ask/               # RAG 채팅
    │       ├── areas/[paraId]/
    │       ├── resources/[paraId]/
    │       └── archives/
    │
    ├── components/                    # 도메인 무관 공통 UI
    │   ├── ui/                        # shadcn/ui v4 (수정 금지)
    │   └── layout/                    # Sidebar, Header, PanelLayout, RAGPanel
    │
    ├── features/                      # 도메인별 비즈니스 레이어
    │   ├── inbox/
    │   │   ├── components/            # inbox-list, inbox-item-card, classify-dialog
    │   │   ├── api.ts
    │   │   ├── hooks.ts
    │   │   ├── schemas.ts
    │   │   └── types.ts
    │   ├── para/
    │   │   ├── components/            # para-item-list, para-detail, create-para-dialog
    │   │   ├── api.ts
    │   │   ├── hooks.ts
    │   │   ├── schemas.ts
    │   │   └── types.ts
    │   ├── meetings/
    │   │   ├── components/
    │   │   ├── api.ts
    │   │   ├── hooks.ts
    │   │   └── types.ts
    │   ├── actions/
    │   │   ├── components/
    │   │   ├── api.ts
    │   │   ├── hooks.ts
    │   │   └── types.ts
    │   ├── editor/
    │   │   └── components/            # TiptapEditor
    │   └── rag/
    │       ├── components/
    │       ├── api.ts
    │       └── hooks.ts
    │
    ├── hooks/                         # 공통 유틸리티 훅
    ├── lib/                           # 서드파티 설정, 유틸 (constants, utils, query-client)
    ├── mocks/                         # Mock data (개발용)
    │   └── data/
    ├── store/                         # Zustand 전역 상태
    │   └── ui.ts
    └── types/                         # 공통 유틸 타입만 (UUID, Timestamped 등)
        └── index.ts
```

## 백엔드 (도메인 모듈러 구조)

```
backend/
└── src/
    ├── auth/                          # Clerk JWT 검증
    ├── inbox/                         # Inbox 적재 + 분류
    ├── projects/                      # 프로젝트 CRUD + N:M 링크 + 태그
    ├── meetings/                      # 회의 인제스트, STT, AI 파이프라인
    ├── actions/                       # 액션 아이템
    ├── notes/                         # Tiptap 노트
    ├── rag/                           # RAG 검색 + Claude 답변
    ├── common/
    │   ├── database.py                # AsyncSession 팩토리
    │   ├── exceptions.py              # 전역 예외 핸들러
    │   ├── r2.py                      # Cloudflare R2 클라이언트
    │   └── pagination.py
    └── core/
        └── config.py                  # pydantic-settings
```

각 도메인 폴더는 다음 파일로 구성:
`router.py` / `service.py` / `repository.py` / `schemas.py` / `models.py` / `dependencies.py` / `exceptions.py`
