<!-- Kairos 디렉토리 구조 맵. BE 16 모듈(13 도메인 + common/core/services) + FE 15 features 정합 (2026-07-01 arch-verification fix — feedback 도메인/feature 등재). -->

# 디렉토리 구조 맵

> baseline: `sprint-28/fixes` 머지 직전 (2026-05-26). Sprint 28 BUG-S28-ARCH-3 fix —
> Round A Architecture 측정 결과 FE 7→14 / BE common 5→10 / services chunked 누락
> stale 보강. (2026-07-01 arch-verification: feedback 도메인/feature 반영해 CONTEXT-MAP §4.1/§4.3 + AGENTS.md 를 BE 16 + FE 15 로 재정합.)

## 프론트엔드 (FSD 기반, FE 15 features)

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
    │   ├── ui/                        # shadcn/ui v4 (수정 금지, I-11)
    │   ├── layout/                    # Sidebar, Header, PanelLayout, RAGPanel
    │   └── shared/                    # 도메인 횡단 공통 (Sprint 23 D4)
    │       └── ItemPromoteModal.tsx   # 5 도메인 generic promote modal
    │
    ├── features/                      # FE 15 도메인 features (FSD)
    │   ├── actions/                   # 액션 아이템 list / detail
    │   ├── audit/                     # AdminAccessAudit / role 변경 trail (Sprint 25)
    │   ├── feedback/                  # dogfooding 피드백 위젯 (user-level, BE feedback 도메인 대응)
    │   ├── home/                      # 대시보드 + ActivityFeed + RecommendedQuestions
    │   ├── inbox/                     # Inbox 적재 + 분류 dialog
    │   ├── meetings/                  # 회의 list / upload / detail / retry
    │   ├── members/                   # WorkspaceMember CRUD + invite UI
    │   ├── memory/                    # Sprint 15 Recall-first wedge (capture/recall/promote)
    │   ├── notes/                     # Tiptap 노트 (note-detail 가 유일 에디터, Sprint 29 R3)
    │   ├── onboarding/                # OnboardingTooltip + step progression
    │   ├── projects/                  # 프로젝트 CRUD + ProjectMember + visibility
    │   ├── rag/                       # RAG ⌘K + SSE stream + citation
    │   ├── sources/                   # 출처 인용 (RAG 결과 enriched chunk)
    │   ├── upload/                    # R2 presigned + proxy + MIME validation
    │   └── workspaces/                # Workspace switcher + invite + type badge
    │
    ├── hooks/                         # 공통 유틸리티 훅
    ├── lib/                           # 서드파티 설정, 유틸 (query-client, constants)
    ├── mocks/                         # Mock data (개발용)
    │   └── data/
    ├── store/                         # Zustand 전역 상태
    │   └── ui.ts
    └── types/                         # 공통 유틸 타입 (UUID, Timestamped 등)
        └── index.ts
```

## 백엔드 (도메인 모듈러 구조, BE 16 모듈 = 13 도메인 + common/core/services)

```
backend/
└── src/
    ├── auth/                          # Clerk JWT 검증 + lazy seed + RBAC + User/Member cache (Sprint 28)
    ├── inbox/                         # Inbox 적재 + 분류
    ├── projects/                      # 프로젝트 CRUD + MeetingProjectLink + ProjectMember + visibility (Sprint 6 ADR-014)
    ├── meetings/                      # 회의 인제스트, STT, AI 파이프라인 (pipeline_service)
    ├── actions/                       # 액션 아이템
    ├── feedback/                      # dogfooding 피드백 수집 (user-level, workspace nullable). prefix 예외: /api/v1/feedback
    ├── notes/                         # Tiptap 노트 + pipeline_service (Sprint 6 ADR-014)
    ├── rag/                           # RAG 검색 + Gemini 답변 + pipeline_service (Sprint 6 ADR-014)
    ├── onboarding/                    # User.onboarding_step (0~4) lifecycle — workspaces/projects/meetings/rag 가 hook 호출 (Sprint 22 OBN-02)
    ├── workspaces/                    # Workspace (personal/team, Sprint 15) + Member + Invite (default_project_visibility)
    ├── memory/                        # Sprint 15 Recall-first wedge — MemoryItem capture/distill/recall/promote + admin_router (R2 cleanup cron) + pipeline_service (Sprint 24 BL-006)
    ├── embeddings/                    # EmbeddingChunk + SemanticCache (cross-domain shared service, ADR-014 옵션 A). source_type 'memory' 추가 (Sprint 15)
    ├── upload/                        # R2 presigned URL + proxy + MIME validation
    ├── services/                      # 외부 wrapper (cross-domain shared service)
    │   ├── transcription.py           # Whisper 1hr 이하 단일 호출
    │   ├── chunked_transcription.py   # 1hr 초과 ffmpeg duration probe + 1hr chunk + 5초 overlap + 병렬 Whisper + merge
    │   ├── ai_processing.py           # Gemini distill / summary / RAG stream — Sprint 28 PERF-4 timeout 적용
    │   └── ai_resilience.py           # Sprint 28 PERF-4 — Gemini/Whisper timeout + circuit breaker singleton
    ├── common/
    │   ├── database.py                # AsyncSession 팩토리
    │   ├── exceptions.py              # 전역 예외 핸들러
    │   ├── r2.py                      # Cloudflare R2 클라이언트 (aioboto3)
    │   ├── prompts.py                 # Gemini 프롬프트 상수 + Pydantic V2 schema
    │   ├── pagination.py              # cursor + offset pagination utility
    │   ├── visibility.py              # ★ project visibility 정책 SSOT (2026-07-13) — decide/ORM clause/raw SQL 상수, stateless
    │   ├── audit_repository.py        # ItemPromotionAudit (Sprint 23 D4) — 4 도메인 공통
    │   ├── audit_router.py            # audit 조회 endpoint (admin/owner 전용)
    │   ├── audit_schemas.py           # audit DTO (Pydantic V2)
    │   ├── promote_helpers.py         # 5 도메인 promote 공통 헬퍼 (BL-S27e-F BL-S28-ARCH-1 carry)
    │   └── promote_models.py          # ItemPromotionAudit ORM 모델
    └── core/
        ├── config.py                  # pydantic-settings (Sprint 27e SEC-3/4 + cutover hardening)
        ├── database.py                # init_engine / dispose_engine (S28-ARCH-4 후 이동 권고)
        └── lifespan.py                # FastAPI lifespan (Sentry init conditional)
```

각 도메인 폴더는 다음 파일로 구성:
`router.py` / `service.py` / `repository.py` / `schemas.py` / `models.py` / `dependencies.py` / `exceptions.py`

**오케스트레이터 (Sprint 6 ADR-014 옵션 A 적용)**: cross-domain 호출 또는 권한 검증 일원화가
필요한 도메인은 추가로 `pipeline_service.py`를 가짐 — 현재 `meetings` / `notes` / `rag` /
`memory` 4 도메인 (Sprint 24 Wave 2 BL-006 으로 `memory/pipeline_service.py` 신설).
진입은 router → pipeline_service → service 위임.

**common 의 audit / promote 도메인 분리 권고**: `common/audit_*.py` + `common/promote_*.py`
5 파일은 사실상 audit 도메인 — Sprint 27e BUG-S27e-ARCH-3 + Sprint 28 BUG-S28-ARCH-1 carry.
BL-S27e-F (architecture deepening sprint) 진입 시 `backend/src/audit/` 신설 → BE 17 모듈 권고 (현재 16 — audit 추가 시 17).

**의존성 cycle**: Sprint 28 BUG-S28-ARCH-4 측정 — 11 쌍 양방향 (`core ↔ common` layered
최하위 cycle 포함). runtime 은 lazy import + model-only 회피로 ImportError 0 (Round B verify),
정적 정합은 carry. `common/database.py` → `core/database.py` 이동 권고 (Sprint 29 carry).
