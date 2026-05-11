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
    │       └── projects/[projectId]/
    │           ├── meetings/[meetingId]/
    │           ├── notes/
    │           ├── actions/
    │           └── files/
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
    │   ├── projects/
    │   │   ├── components/            # project-list, project-detail, create-project-dialog
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
    ├── projects/                      # 프로젝트 CRUD + MeetingProjectLink + ProjectMember (Sprint 6) + visibility
    ├── meetings/                      # 회의 인제스트, STT, AI 파이프라인 (pipeline_service)
    ├── actions/                       # 액션 아이템
    ├── notes/                         # Tiptap 노트 + pipeline_service (Sprint 6 ADR-014)
    ├── rag/                           # RAG 검색 + Gemini 답변 + pipeline_service (Sprint 6 ADR-014)
    ├── workspaces/                    # Workspace + Member + Invite (default_project_visibility, Sprint 6)
    ├── embeddings/                    # EmbeddingChunk + SemanticCache (cross-domain shared service)
    ├── upload/                        # R2 presigned URL
    ├── services/                      # 외부 wrapper (transcription, ai_processing) — cross-domain shared service
    ├── common/
    │   ├── database.py                # AsyncSession 팩토리
    │   ├── exceptions.py              # 전역 예외 핸들러
    │   ├── r2.py                      # Cloudflare R2 클라이언트
    │   ├── prompts.py                 # Gemini 프롬프트 상수
    │   └── pagination.py
    └── core/
        └── config.py                  # pydantic-settings
```

각 도메인 폴더는 다음 파일로 구성:
`router.py` / `service.py` / `repository.py` / `schemas.py` / `models.py` / `dependencies.py` / `exceptions.py`

**오케스트레이터 (Sprint 6 ADR-014 옵션 A 적용)**: cross-domain 호출 또는 권한 검증 일원화가 필요한 도메인은 추가로 `pipeline_service.py`를 가짐 — 현재 `meetings`, `notes`, `rag` 3 도메인. 진입은 router → pipeline_service → service 위임.
