<!-- Kairos 디렉토리 구조 맵. BE 17 모듈(14 도메인 + common/core/services, 2026-07-30 문서 기준) + FE features 정합 (2026-07-31 기준 16). -->

# 디렉토리 구조 맵

> baseline: `sprint-28/fixes` 머지 직전 (2026-05-26). Sprint 28 BUG-S28-ARCH-3 fix —
> Round A Architecture 측정 결과 FE 7→14 / BE common 5→10 / services chunked 누락
> stale 보강. (2026-07-01 arch-verification: feedback 도메인/feature 반영해 CONTEXT-MAP §4.1/§4.3 + AGENTS.md 를 BE 16 + FE 15 로 재정합.)
>
> 2026-07-30: ADR-026의 `integrations` 구현 예정 도메인을 CONTEXT-MAP §4.1 및 AGENTS.md와 정합해 BE 17 모듈 = 14 도메인 + common/core/services로 갱신했다.
>
> 2026-07-31: `integrations` 도메인 구현 완료(ADR-026 Wave 3). FE 에 `features/integrations/`(외부 문서 상세 조회 API·hooks)를 추가했다.
>
> 2026-08-13: ADR-027 App-first 재구성 — `backend/` → `apps/backend/`, `frontend/` → `apps/web/`.
> 배포 단위(앱)를 최상위 경계로 삼는다. 같은 날 후속 PR 로 `contracts/`(OpenAPI 계약) +
> 루트 `justfile` + CI change-detection(`test.yml`) 신설 (ADR-027 D2~D4).
>
> 2026-08-16: ADR-030 — `apps/backend/` → `apps/api/`. 같은 라운드에서 `docs/guides/` 를
> `docs/development/` + `docs/operations/` 로 해체하고 `docs/product/` · `docs/archive/` 를 신설했다.
> **2026-08-16 이전 문서의 `apps/backend/` 는 `apps/api/` 로 읽는다** (ADR-030 D2).

## 최상위 레이아웃 (2026-08-16, ADR-030)

```
kairos/
├── apps/
│   ├── api/                           # FastAPI (OCI 컨테이너 배포 단위, ADR-028/030)
│   └── web/                           # Next.js (OCI 컨테이너 배포 단위, ADR-028)
├── contracts/                         # OpenAPI 계약 생성물 (ADR-027 D2) — `just contracts` 재생성, 수정 금지
├── deploy/oci/                        # ★ 서버 운영 정본 — compose + build.env + README(런북)
├── docs/                              # canonical docs (development, operations, architecture, adr, product)
├── scripts/                           # 레포 공통 스크립트 (verify-prod.sh)
├── justfile                           # 단일 명령 진입점 (ADR-027 D3). `just ci-local` = 로컬 머지 게이트
├── AGENTS.md · CONTEXT-MAP.md · DESIGN.md   # 규칙 / 헌법 / 디자인 (ADR-029)
└── .github/                           # workflows(test, nightly-e2e, r2-cleanup) + PR·Issue 템플릿 + dependabot
```

각 앱은 `AGENTS.md`(스택 함정) + `CONTEXT.md`(불변식 B-NN / F-NN) + `CLAUDE.md`(둘을 `@` import)
를 갖는다 (ADR-029).

**배포 워크플로는 없다.** 배포는 CI 가 아니라 로컬 `justfile` → SSH(`truewords-oracle`) →
`docker save | ssh docker load` → compose up 이다 (ADR-028, 레지스트리 미사용).

규칙: 독립 실행·배포되면 `apps/`, 언어를 넘는 계약이면 `contracts/`, 라이브러리 공유 패키지(`packages/`)는
동일 언어 소비자 2개가 생길 때만 신설 (ADR-027 D5).

## 프론트엔드 (FSD 기반, FE features — 2026-07-31 기준 16)

```
apps/web/
├── proxy.ts                           # 세션 쿠키 리다이렉트 (Next.js 16 명칭). 인가는 BE 몫
└── src/
    ├── app/                           # 라우트 진입점 (Thin Component). route group 3개
    │   ├── (landing)/                 # 랜딩
    │   │   ├── page.tsx               #   "/"
    │   │   └── pricing/
    │   ├── (auth)/                    # 자체 sign-in / sign-up 폼
    │   │   ├── sign-in/[[...sign-in]]/
    │   │   └── sign-up/[[...sign-up]]/
    │   ├── (app)/                     # 인증된 앱 영역 (layout/loading/error 보유)
    │   │   ├── dashboard/  inbox/  notes/  notes/[id]/
    │   │   ├── projects/   projects/[id]/  meetings/[id]/
    │   │   ├── memory/  search/  actions/  new/  settings/
    │   │   └── admin/recall-metrics/  # 유일한 admin 화면 (별도 앱 아님)
    │   └── invite/[code]/             # 그룹 밖 public 라우트
    │
    ├── components/                    # 도메인 무관 공통 UI
    │   ├── ui/                        # shadcn/ui v4 (수정 금지, I-11)
    │   ├── layout/                    # Sidebar, Header, PanelLayout, RAGPanel, BottomNav, CmdK
    │   ├── landing/                   # 랜딩 섹션
    │   ├── onboarding/                # OnboardingTooltip
    │   └── shared/                    # 도메인 횡단 공통 (Sprint 23 D4)
    │       └── ItemPromoteModal.tsx   # 5 도메인 generic promote modal
    │
    ├── features/                      # FE 도메인 features (FSD, 2026-07-31 기준 16)
    │   ├── actions/                   # 액션 아이템 list / detail
    │   ├── audit/                     # AdminAccessAudit / role 변경 trail (Sprint 25)
    │   ├── feedback/                  # dogfooding 피드백 위젯 (user-level, BE feedback 도메인 대응)
    │   ├── home/                      # 대시보드 + ActivityFeed + RecommendedQuestions
    │   ├── inbox/                     # Inbox 적재 + 분류 dialog
    │   ├── integrations/              # 외부 문서 상세 조회 (Google Drive)
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
    │   ├── api-client.ts              # ★ ApiClient seam (2026-07-13) — createApiClient(getToken), 토큰 주입 SSOT
    │   ├── use-api-client.ts          # useApiClient() — JWT 캐시 + single-flight 주입 훅
    │   └── query-keys.ts              # ★ queryKey factory 레지스트리 (2026-07-13) — cross-feature key import 금지 (eslint no-restricted-imports)
    ├── store/                         # Zustand 전역 상태
    │   └── ui.ts
    └── types/
        ├── api.gen.ts                 # ★ 계약 생성물 (openapi-typescript, I-22) — 수기 수정 금지
        └── index.ts                   # 공통 유틸 타입 (UUID, Timestamped 등)
```

단위 테스트는 코드 옆 `__tests__/`, e2e 는 `apps/web/e2e/` (`chromium` / `public-only` / `team` project).
**`mocks/` 와 `NEXT_PUBLIC_API_MOCK` 은 존재하지 않는다** — FE 는 항상 실제 BE 를 호출한다
(2026-08-16 정정: 3개 문서가 없는 디렉터리를 안내하고 있었다).
**barrel `index.ts` 는 두지 않는다** (현재 0개). `server/` 폴더도 없다 — 100% 클라이언트 TanStack Query.

## 백엔드 (도메인 모듈러 구조, BE 17 모듈 = 14 도메인 + common/core/services — 2026-07-31 기준)

```
apps/api/
└── src/
    ├── auth/                          # Bearer JWT 검증 + lazy seed + RBAC + User/Member cache (Sprint 28)
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
    ├── integrations/                  # ADR-026 — Google OAuth 연결·선택 외부 파일/ExternalDocument·sync 상태·외부 소스 생명주기 (PR #143 구현 완료)
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
        └── lifespan.py                # FastAPI lifespan — common/database.py 의 init/dispose_engine 호출
```

> ★ **`core/database.py` 는 존재하지 않는다.** engine 은 `common/database.py` 가 소유한다.
> 아래 "의존성 cycle" 절의 `core/database.py` 이동 권고는 **미실행 상태**다 (2026-08-16 실측).

> ★ `src/integrations/` 는 **ADR-026 외부 소스 도메인**(Google Drive 연결·ExternalDocument)이다.
> 일반 모노레포 권고안이 말하는 `integrations/`(외부 SDK 어댑터 레이어)와 이름은 같고 역할이 다르다 —
> Kairos 에서 SDK 래퍼는 `src/services/` 가 담당한다.

각 도메인 폴더는 다음 파일로 구성:
`router.py` / `service.py` / `repository.py` / `schemas.py` / `models.py` / `dependencies.py` / `exceptions.py`

**오케스트레이터 (Sprint 6 ADR-014 옵션 A 적용)**: cross-domain 호출 또는 권한 검증 일원화가
필요한 도메인은 추가로 `pipeline_service.py`를 가짐 — 현재 `meetings` / `notes` / `rag` /
`memory` 4 도메인 (Sprint 24 Wave 2 BL-006 으로 `memory/pipeline_service.py` 신설).
진입은 router → pipeline_service → service 위임.

**common 의 audit / promote 도메인 분리 권고**: `common/audit_*.py` + `common/promote_*.py`
5 파일은 사실상 audit 도메인 — Sprint 27e BUG-S27e-ARCH-3 + Sprint 28 BUG-S28-ARCH-1 carry.
BL-S27e-F (architecture deepening sprint) 진입 시 `apps/api/src/audit/` 신설 권고 (2026-07-30 문서 기준 BE 17 — `audit` 추가 시 18).

**의존성 cycle**: Sprint 28 BUG-S28-ARCH-4 측정 — 11 쌍 양방향 (`core ↔ common` layered
최하위 cycle 포함). runtime 은 lazy import + model-only 회피로 ImportError 0 (Round B verify),
정적 정합은 carry. `common/database.py` → `core/database.py` 이동 권고 (Sprint 29 carry).
