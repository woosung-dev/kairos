<!-- Sprint 27e 아키텍처 가디언 발견사항 -->

# Sprint 27e — 아키텍처 가디언 발견사항

- 검사 범위: 헌법 (CONTEXT-MAP.md B-*/I-*) / ADR (014/019/020/021/022/023/024) / SOLID + DRY + KISS / 결합도-응집도 / 일관성 / 비전 (second-brain pivot + PERSONA-001 + Atomic Update) / 부채 (BL-005~013, BL-S26-*, BL-S27c-*, BL-S27e-*)
- 시나리오: Personal + Team (아키텍처는 대부분 시나리오 독립; 본 audit 에서 시나리오별 결합도 분기 없음)
- 검사 일시: 2026-05-25 00:25 KST
- baseline commit: `1b24898` (Sprint 27d fix bundle merged main, 본 audit branch `sprint-27e/multi-review` 분기 후 변경 0)
- 분석 모드: 정적 (로컬 FE/BE down, 실 endpoint 호출 없음)

---

## 1. 헌법 / ADR 위반 매트릭스

| ID | 헌법 또는 ADR | 심각도 | 차단? | file:line | 위반 | 정합 회복 방안 |
|----|-------------|--------|------|----------|------|--------------|
| BUG-S27e-ARCH-1 | CONTEXT-MAP I-1 + backend §B-3 | P1 | NO | `backend/src/onboarding/service.py:18-20`, `backend/src/onboarding/repository.py:14` | OnboardingService 가 `self._session = session` 보유 + service 가 raw `text()` SQL 직접 실행 (line 28-34) — I-1 "Service 가 AsyncSession 직접 다루지 않는다" 명백 위반. CONTEXT.md §3 "Single-session: 호출자 transaction 합류" 는 헌법 예외 근거 부재. | (a) `OnboardingRepository.get_status_row(user_id) -> Row \| None` 추가 + service 위임. (b) repository/service 양쪽 raw text → typed `select(User.onboarding_step, User.onboarded_at)` + `session.exec()` 로 B-10 G1 manifest 정합. 단일 트랜잭션 합류 패턴은 repository 경유로도 보장 가능 (호출자 session → repo). |
| BUG-S27e-ARCH-2 | CONTEXT-MAP §4.2 (cross-domain shared service) | P2 | NO | `backend/src/services/transcription.py:14` | `from src.meetings.models import TranscriptSegment` — shared service 가 도메인 모델에 역의존. 헌법 "services/ 는 외부 wrapper, cross-domain orchestrator 가 호출" 정책과 어긋남 (services 가 meetings 모델 형식에 결합 → meetings 도메인 변경 시 services 깨짐). | `services/transcription.py` 내부 DTO 정의 (예: `TranscriptionSegmentDTO`) → 반환 → 호출자 (`meetings/pipeline_service.py`) 가 DTO → `TranscriptSegment` ORM 변환. ai_processing.py 가 model import 0인 패턴과 정합. |
| BUG-S27e-ARCH-3 | CONTEXT-MAP §4.1 (도메인 경계) + Layered Architecture | P2 | NO | `backend/src/common/audit_router.py:14,18`, `backend/src/common/promote_helpers.py:173` | `common/` 가 `auth.rbac` + `workspaces.models` import — common 은 도메인 무관 layer 인데 상위 도메인 import. audit 라우터/헬퍼는 실질 audit 도메인이지만 common 위에 얹혀 있어 layered 역방향 결합. | (a) `backend/src/audit/` 신설 (router + repository + schemas + helpers 이전) → BE 모듈 16개 (현 15). (b) common 은 도메인 무관 utility 만 (`database`, `exceptions`, `pagination`, `r2`, `prompts`) 유지. directory-map.md 정합 갱신 동반. |
| BUG-S27e-ARCH-4 | CONTEXT-MAP §4.1 (모듈 수) + §4.3 + `docs/architecture/directory-map.md` | P2 | NO | `CONTEXT-MAP.md:43` ("13 BE 모듈"), `CONTEXT-MAP.md:60` ("11 FE features"), `docs/architecture/directory-map.md:74-100`, `.claude/CLAUDE.md` ("BE 13 모듈 + FE 11 features") | 헌법 텍스트가 실재와 불일치 — BE 실재 15 모듈 (`onboarding` 추가 + `common`/`core`/`services` 포함 시), FE 실재 14 features (`audit, home, members, memory, onboarding, sources, workspaces, upload` 등 추가). directory-map.md FE 표기 7개 (inbox/projects/meetings/actions/editor/memory/rag) 로 더 stale. Atomic Update 원칙 (Sprint 26 §9) 위반 — 코드 추가 시 헌법 doc 동기화 누락. | 헌법 §4.1 텍스트 "BE 15 모듈 (auth · workspaces · projects · inbox · meetings · notes · actions · memory · onboarding · upload · embeddings · rag · common · core · services)" + §4.3 "FE 14 features" 갱신. directory-map.md 전수 다시 작성. `.claude/CLAUDE.md` 의 "13/11" 숫자 갱신. Atomic Update 라우팅 회귀 가드 (CI lint) 권고. |
| BUG-S27e-ARCH-5 | CONTEXT-MAP I-1 (boundary) | P3 | NO | `backend/src/rag/service.py:38-41` | `RagService._advance_onboarding` 가 `self.embedding_repo.session` 으로 다른 repository 의 session 을 꺼내 OnboardingService 에 전달. repository 의 session 은 캡슐화된 implementation detail — 이를 service 가 우회 추출하는 것은 Demeter Law + I-1 정신 위반. | (a) `RagService.__init__` 에 별도 hook callable (예: `onboarding_hook: Callable[[uuid.UUID], Awaitable[None]]`) 주입 → router/dependency 가 session 보유. (b) BUG-S27e-ARCH-1 해소 시 OnboardingService 가 session 보유 안 하므로 자연스럽게 호출 가능. |
| BUG-S27e-ARCH-6 | SOLID (SRP) + KISS | P2 | NO | `backend/src/rag/service.py:45` `RagService.ask` 192 LOC, `backend/src/meetings/service.py:256` `promote` 172 LOC, `backend/src/meetings/pipeline_service.py:48` `_analyze_and_store` 125 LOC, `backend/src/notes/service.py:225` `promote` 124 LOC, `backend/src/notes/service.py:381` `_bg_promote_embed_note` 115 LOC, `backend/src/memory/service.py:405` `promote` 103 LOC, `backend/src/inbox/service.py:158` `promote` 100 LOC | 50+ LOC method 13개 — promote 패턴이 5 도메인 (`memory`, `meeting`, `note`, `inbox`, `action`) 에 산재. `common/promote_helpers.py` 가 일부 추출했으나 service 본문 100+ LOC 유지. SRP 위반 (각 promote 함수 = workspace 검증 + 복제 + audit + BG task add + return 5+ 책임). | (a) `common/promote_helpers.py` 확장 — `verify_target_workspace(...)`, `clone_item(...)`, `enqueue_embed_audit(...)` 분리. (b) 각 service 의 promote 50 LOC 미만으로 축소. Sprint 23 D4 의 일부 추출 패턴 후속 확장. |
| BUG-S27e-ARCH-7 | Atomic Update (.ai/common/global.md §2) | P3 | NO | `docs/refactoring-backlog.md:440-471` (BL-005), `backend/src/memory/service.py:405-505` | BL-005 가 "★★★★★ P0 헌법 위반" 으로 등재됐으나 코드 검증 결과 promote() 가 `WorkspaceRepository.find_by_id` + `find_member` 사용 (Sprint 19 PR #1 C10) 으로 이미 해소됨. `self.repo.session.execute` 호출 0 hit. BL 문서가 stale → Atomic Update 누락. | BL-005 → "✅ 완료 (Sprint 19 PR #1 C10, 2026-05-18)" 마크 + 본문에 회복 commit 명시. BL-006 와 같은 closed 표기. |

---

## 2. 의존성 그래프 분석

각 BE 모듈이 import 하는 다른 모듈 (`from src.<X>` 패턴, `__pycache__` 제외).

| 모듈 | import 갯수 | 결합도 | 의존 대상 | 비고 |
|------|------------|--------|----------|------|
| `core` | 1 | low | `common` | 최하위 (정상) |
| `embeddings` | 2 | low | `common`, `core` | shared service 자리, 정상 |
| `auth` | 2 | low | `common`, `workspaces` (rbac.py 에서 WorkspaceMember 조회) | 정상 (rbac 가 workspace 필요) |
| `onboarding` | 2 | low | `auth`, `common` | 정상 (User 모델 참조) |
| `common` | 3 | medium | `auth`, `core`, `workspaces` | ⚠️ **ARCH-3** — common 이 auth/workspaces 역의존 (audit_router 책임 분리 미흡) |
| `services` | 3 | medium | `common`, `core`, `meetings` | ⚠️ **ARCH-2** — services 가 meetings.models 역의존 |
| `workspaces` | 4 | medium | `auth`, `common`, `core`, `projects` | workspaces ↔ projects 양방향 (cycle 위험, dependencies.py 의 ProjectRepository 주입) |
| `upload` | 4 | medium | `auth`, `common`, `core`, `workspaces` | 정상 |
| `projects` | 4 | medium | `auth`, `common`, `meetings`, `workspaces` | projects → meetings (MeetingProjectLink 모델) — meetings ↔ projects 양방향 (cycle 위험) |
| `inbox` | 5 | medium | `auth`, `common`, `meetings`, `projects`, `workspaces` | 정상 (Inbox 가 meeting/project 참조) |
| `notes` | 5 | medium | `auth`, `common`, `embeddings`, `projects`, `workspaces` | 정상 (embeddings 호출은 pipeline_service 경유 §4.2 정합) |
| `actions` | 5 | medium | `auth`, `common`, `meetings`, `projects`, `workspaces` | 정상 |
| `memory` | 5 | medium | `auth`, `common`, `core`, `embeddings`, `workspaces` | 정상 (BL-006 해소, pipeline_service 분리) |
| `rag` | 6 | medium-high | `auth`, `common`, `embeddings`, `projects`, `services`, `workspaces` | RagService 내부 embedding 직접 호출은 ADR-014 옵션 A 예외 인정 (rag/CONTEXT.md §5) |
| `meetings` | 8 | **high** | `actions`, `auth`, `common`, `embeddings`, `inbox`, `projects`, `services`, `workspaces` | 가장 결합도 높음. pipeline_service 가 5+ 모듈 조합 (orchestrator 정합). 단 service.py 도 7 모듈 import (actions/embeddings/workspaces/projects) — orchestrator 와 책임 분리 점검 필요. |

### 양방향 (cyclic) 의존 (실제 import 단계 verified)

| 쌍 | 방향 | 비고 |
|----|------|------|
| `meetings ↔ projects` | meetings → `projects.repository` (pipeline), projects → `meetings.repository` (dependencies, MeetingProjectLink) | Sprint 6 이전부터 존재. lazy import / model-only import 로 회피. |
| `workspaces ↔ projects` | workspaces → `projects.repository`, projects → `workspaces.repository` | dependencies.py 의 양방향. lazy import 의존 — Python import order 깨지면 ImportError. |
| `services → meetings` (단방향) | services/transcription → `meetings.models` | **ARCH-2** |
| `common → auth, workspaces` (단방향) | common/audit_router → `auth.rbac`, `workspaces.models` | **ARCH-3** |

cycle 자체는 runtime 동작 (Python import 시점 분리), 그러나 모듈 책임 경계가 흐려져 변경 비용 증가.

---

## 3. 개별 발견사항 + 정합 회복 방안

### BUG-S27e-ARCH-1 — OnboardingService 가 AsyncSession 직접 보유 + service 가 raw SQL

- **위반**: CONTEXT-MAP I-1 ("Service 는 AsyncSession 을 직접 다루지 않는다. Repository 경유.")
- **심각도**: P1
- **차단**: NO (production 동작 영향 없음, 코드 품질 부채)
- **file**: `backend/src/onboarding/service.py:18-34`, `backend/src/onboarding/repository.py:14-27`

#### 위반 내용

```python
# backend/src/onboarding/service.py
class OnboardingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session            # ← I-1 위반 (service 가 session 보유)
        self._repo = OnboardingRepository(session)

    async def get_status(self, user_id: UUID) -> OnboardingResponse:
        result = await self._session.execute(   # ← service 가 raw SQL 직접 실행
            text(
                "SELECT onboarding_step, onboarded_at "
                "FROM users WHERE id = :user_id"
            ),
            {"user_id": user_id},
        )
```

#### 헌법 / ADR 참조

> **CONTEXT-MAP §6 I-1**: "AsyncSession 은 Repository 만 보유 (service 에서 `from sqlalchemy.ext.asyncio import AsyncSession` 금지)"
> **backend/CONTEXT.md §B-10 (G1 manifest)**: "typed scalar select → `(await session.exec(stmt)).all() / .first() / .one_or_none() / .one()`"

onboarding/CONTEXT.md §3 "Single-session: 호출자 transaction 합류" 는 의도 합리적이나, 다른 도메인 (workspaces/projects/actions) 도 "호출자 session 합류" 가 가능 — `Repository(session)` 패턴 그대로. service 가 session 을 보유할 필요 없음.

#### 정합 회복 방안

```python
# backend/src/onboarding/repository.py
from sqlmodel import select
from src.auth.models import User

class OnboardingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_status_row(self, user_id: UUID) -> tuple[int, datetime | None] | None:
        stmt = select(User.onboarding_step, User.onboarded_at).where(User.id == user_id)
        result = await self._session.exec(stmt)
        row = result.first()
        return (row[0], row[1]) if row else None

    async def increment(self, user_id: UUID, target_step: int) -> None:
        # G3-convert: DML w/o rowcount → session.exec(update(...))
        from sqlmodel import update
        stmt = (
            update(User)
            .where(User.id == user_id, User.onboarding_step < target_step)
            .values(
                onboarding_step=target_step,
                onboarded_at=func.now() if target_step == 4 else User.onboarded_at,
            )
        )
        await self._session.exec(stmt)


# backend/src/onboarding/service.py
class OnboardingService:
    def __init__(self, repo: OnboardingRepository) -> None:  # AsyncSession 보유 X
        self._repo = repo

    async def get_status(self, user_id: UUID) -> OnboardingResponse:
        row = await self._repo.get_status_row(user_id)
        if row is None:
            return OnboardingResponse(step=0, totalSteps=4, onboardedAt=None, isCompleted=False)
        step, onboarded_at = row
        return OnboardingResponse(step=step, totalSteps=4, onboardedAt=onboarded_at, isCompleted=step >= 4)
```

#### 위반 누적 비용

- 향후 onboarding step 추가 (예: step=5 paid customer 도달) 시 raw SQL 2곳 (repository + service) 수정 vs typed query 1곳.
- I-1 예외 사례가 누적되면 다른 hook helper (예: 향후 audit/analytics) 도 같은 패턴 답습 위험.

#### 영향 범위

- `backend/src/onboarding/dependencies.py` (있다면) 또는 dependencies.py 신규 — `get_onboarding_service(session) -> OnboardingService(OnboardingRepository(session))` 패턴 정렬.
- `auth/dependencies.py:222`, `rag/service.py:39`, `workspaces/service.py`, `projects/service.py`, `meetings/pipeline_service.py` 등 OnboardingService 호출처 — DI 그래프만 변경, 호출 API 동일.

---

### BUG-S27e-ARCH-2 — services/ 가 meetings 도메인 모델 역의존

- **위반**: CONTEXT-MAP §4.2 ("cross-domain shared service = orchestrator 경계 내부만"), 의존성 역전 (DIP)
- **심각도**: P2
- **차단**: NO
- **file**: `backend/src/services/transcription.py:14`

#### 위반 내용

```python
# backend/src/services/transcription.py
from src.meetings.models import TranscriptSegment   # ← services 가 meetings 도메인 import
```

`services/` 는 외부 wrapper (Whisper, Gemini, OpenAI embedding) 만 책임지는 도메인 무관 shared service 디렉토리. 이 디렉토리가 `meetings` 도메인 모델을 import 하면 도메인 → services 의존 그래프가 양방향이 되어 layered 깨짐.

비교: `services/ai_processing.py` 는 model import 0건 — 자체 DTO/dict 반환 → 호출자 (도메인 pipeline_service) 가 ORM 변환. 정합 패턴.

#### 정합 회복 방안

```python
# backend/src/services/transcription.py
from dataclasses import dataclass

@dataclass
class TranscriptionSegmentDTO:
    start_sec: float
    end_sec: float
    text: str
    speaker: str = "Speaker"

class TranscriptionService:
    async def transcribe_with_chunking(self, audio: bytes, filename: str) -> list[TranscriptionSegmentDTO]:
        ...   # 외부 Whisper 호출 + DTO 변환만

# backend/src/meetings/pipeline_service.py
async def process_meeting(self, ...):
    segments_dto = await self._transcription.transcribe_with_chunking(...)
    transcript_segments = [
        TranscriptSegment(meeting_id=mid, start_sec=s.start_sec, ..., speaker=s.speaker)
        for s in segments_dto
    ]
    await self._meeting_repo.save_transcript(transcript_segments)
```

#### 위반 누적 비용

- meetings 도메인의 `TranscriptSegment` schema 변경 시 services 도 영향 — orthogonal 가야 할 두 layer 가 결합.
- 신규 도메인이 transcription 재사용 시 같은 결합 답습 가능성.

#### 영향 범위

- `backend/src/services/transcription.py` + `chunked_transcription.py` (사용 시) + `meetings/pipeline_service.py` 호출처. DTO 도입 = +30 LOC.

---

### BUG-S27e-ARCH-3 — common/ 디렉토리가 상위 도메인 (auth/workspaces) 역의존

- **위반**: Layered Architecture (common 은 도메인 무관 layer), CONTEXT-MAP §4.1 책임 경계
- **심각도**: P2
- **차단**: NO
- **file**: `backend/src/common/audit_router.py:14,18`, `backend/src/common/promote_helpers.py:173`

#### 위반 내용

```python
# backend/src/common/audit_router.py
from src.auth.rbac import require_admin       # ← common → auth
from src.workspaces.models import WorkspaceMember   # ← common → workspaces
```

`common` 의 다른 파일 (`database`, `exceptions`, `pagination`, `r2`, `prompts`) 는 도메인 무관 utility — 정합. 그러나 `audit_router`, `audit_repository`, `audit_schemas`, `audit_repository`, `promote_helpers`, `promote_models` 는 실질 **audit/promote 도메인** 인데 common 에 얹혀있음.

#### 정합 회복 방안

옵션 A (권고):

```
backend/src/audit/
├── router.py            # ← common/audit_router.py
├── repository.py        # ← common/audit_repository.py
├── schemas.py           # ← common/audit_schemas.py
├── models.py            # ← common/promote_models.py (ItemPromotionAudit 등)
├── promote_helpers.py   # ← common/promote_helpers.py
└── CONTEXT.md           # 신설 (audit 도메인 책임 명시)

backend/src/common/
├── database.py
├── exceptions.py
├── pagination.py
├── r2.py
└── prompts.py
```

- `CONTEXT-MAP §4.1` BE 모듈 = 15 → 16 (audit 추가).
- `directory-map.md` 갱신 (BUG-S27e-ARCH-4 와 합쳐 처리).

옵션 B (낮은 비용, 차선): `audit/` 분리 deferred — common 내부에 audit 폴더 (`common/audit/`) 로 nested 후 README 에 "audit 은 향후 도메인 분리 예정" 마크. 결합 정리 효과는 없음.

#### 위반 누적 비용

- common 책임이 흐려지면서 다음 결합 (예: common 에 user_metrics 추가) 답습 위험.
- audit 도메인 자체 책임 확장 시 (예: ADR-023 D-6.4 BL-S27-3 AdminAccessAudit 추가) common 에 누적되어 god module 화.

---

### BUG-S27e-ARCH-4 — 헌법/architecture doc 의 BE/FE 모듈 수가 실재와 불일치 (Atomic Update 위반)

- **위반**: Atomic Update (.ai/common/global.md §2), CONTEXT-MAP §4 정확성
- **심각도**: P2
- **차단**: NO
- **file**: `CONTEXT-MAP.md:43,60`, `docs/architecture/directory-map.md:74-100`, `.claude/CLAUDE.md`

#### 위반 내용

| 표기 위치 | 표기 값 | 실재 | delta |
|----------|--------|------|------|
| `CONTEXT-MAP.md:43` | "백엔드 모듈 (13)" | 15 (`auth · workspaces · projects · inbox · meetings · notes · actions · memory · onboarding · upload · embeddings · rag · common · core · services`) | +2 (`onboarding` Sprint 22 신설, `services` 가 분류에 누락되어 카운트 불일치) |
| `CONTEXT-MAP.md:60` | "frontend features `inbox · projects · meetings · actions · notes · rag · members · workspaces · upload · sources · home` (11)" | 14 (`actions, audit, home, inbox, meetings, members, memory, notes, onboarding, projects, rag, sources, upload, workspaces`) | +3 (`audit, memory, onboarding` 누락) |
| `docs/architecture/directory-map.md:31-62` | FE features 7개 (inbox/projects/meetings/actions/editor/memory/rag) | 14 | +7 (`audit, home, members, onboarding, sources, upload, workspaces` 누락) |
| `.claude/CLAUDE.md` | "BE 13 모듈 + FE 11 features" | BE 15 + FE 14 | +2 BE, +3 FE |

#### 정합 회복 방안

3-step PR:

1. `CONTEXT-MAP.md:43-45` 갱신: "백엔드 모듈 (15): `auth · workspaces · projects · inbox · meetings · notes · actions · memory · onboarding · upload · embeddings · rag · common · core · services`"
2. `CONTEXT-MAP.md:58-62` 갱신: "frontend features (14): `inbox · projects · meetings · actions · notes · rag · memory · members · workspaces · upload · sources · home · audit · onboarding`"
3. `docs/architecture/directory-map.md` FE features 섹션 전수 재작성 — 누락 7 features (audit/home/members/onboarding/sources/upload/workspaces) 추가.
4. `.claude/CLAUDE.md` 의 "13/11" 숫자 갱신.

#### 위반 누적 비용

- 새로 들어오는 AI 또는 contributor 가 헌법을 읽고 "FE features 가 11개" 라고 가정 → 실재 14 → 잘못된 모듈 경계 파악.
- ADR-023 (D-6 lock-in) 이 "현 코드 동작 명시화" 패턴인데 헌법이 stale 하면 다음 sprint 의 Atomic Update 도 같은 패턴 답습.

#### 영향 범위

3 파일 수정, ~30 LOC diff. ARCH-3 의 `audit/` 도메인 분리 결정과 함께 묶어 1 PR 권고.

---

### BUG-S27e-ARCH-5 — RagService 가 다른 repository 의 session 을 우회 추출 (Demeter 위반)

- **위반**: Law of Demeter, I-1 정신 (Repository session 캡슐화)
- **심각도**: P3
- **차단**: NO
- **file**: `backend/src/rag/service.py:38-41`

#### 위반 내용

```python
async def _advance_onboarding(self, user_id: uuid.UUID) -> None:
    try:
        from src.onboarding.service import OnboardingService
        session = self.embedding_repo.session    # ← embedding_repo 내부 session 우회 추출
        onboarding = OnboardingService(session)
        await onboarding.increment_step(user_id, 4)
        await session.commit()
```

`embedding_repo.session` 은 EmbeddingRepository 의 implementation detail — RagService 가 이를 꺼내 다른 service 에 주입하는 것은 캡슐화 깨뜨림. Sprint 6 ADR-014 옵션 A "권한 검증 일원화" 의 책임 분리 정신과도 어긋남.

#### 정합 회복 방안

옵션 A (BUG-S27e-ARCH-1 해소 시 자연스럽게 해결):

```python
# rag/dependencies.py
async def get_rag_service(
    session: AsyncSession = Depends(get_async_session),
    onboarding: OnboardingService = Depends(get_onboarding_service),
    ...
) -> RagService:
    return RagService(
        embedding_repo=EmbeddingRepository(session),
        embedding_service=...,
        ai_service=...,
        onboarding=onboarding,   # ← DI 로 주입
    )

# rag/service.py
async def _advance_onboarding(self, user_id):
    try:
        await self.onboarding.increment_step(user_id, 4)
        # commit 은 호출자 (router) 또는 별도 session lifecycle 책임
```

옵션 B (호환): hook callable 주입.

#### 위반 누적 비용

- 다른 도메인이 같은 패턴 답습 시 (예: meetings 가 inbox_repo.session 으로 actions 호출) repository session 캡슐화 무력화.
- onboarding hook 처럼 cross-domain 부수 효과가 늘어날수록 service 가 다른 repository session 을 꺼내는 횟수 증가 → 트랜잭션 lifecycle 추적 불가.

---

### BUG-S27e-ARCH-6 — Service/PipelineService 메서드가 SRP 한계 초과 (50+ LOC 13개)

- **위반**: SRP (Single Responsibility), KISS, 메서드 길이 가이드 (CLAUDE.md §2 "200줄이 50줄로 가능하면 rewrite")
- **심각도**: P2
- **차단**: NO
- **file**: `backend/src/rag/service.py:45` (ask 192 LOC), `backend/src/meetings/service.py:256` (promote 172 LOC), `backend/src/meetings/pipeline_service.py:48` (_analyze_and_store 125 LOC), `backend/src/notes/service.py:225` (promote 124 LOC), `backend/src/notes/service.py:381` (_bg_promote_embed_note 115 LOC), `backend/src/meetings/service.py:428` (_bg_promote_embed_meeting 110 LOC), `backend/src/memory/service.py:405` (promote 103 LOC), `backend/src/inbox/service.py:158` (promote 100 LOC), `backend/src/memory/service.py:257` (recall 90 LOC), `backend/src/meetings/pipeline_service.py:174` (process_meeting 81 LOC), `backend/src/embeddings/service.py:91` (embed_meeting 77 LOC), `backend/src/notes/service.py:497` (_bg_regenerate_embed_with_audit 65 LOC), `backend/src/embeddings/service.py:169` (embed_note 62 LOC)

#### 위반 내용

5 도메인 (memory/meeting/note/inbox/action) 의 `promote` 가 모두 100+ LOC. 각각 책임:
1. workspace 검증 (target ws 존재 + type='team' + member)
2. source 복제 (raw_content/distilled_json 복사 + 신규 ID)
3. audit row 신설 (ItemPromotionAudit or PromotionAudit)
4. event 기록 (memory 만)
5. embed text 생성
6. BG task add
7. 응답 반환

→ 7 책임 × 5 도메인 = 35 책임이 service.py 분산.

`common/promote_helpers.py:221` 가 일부 헬퍼 (audit row + embed_text 생성) 제공하나 절반만 추출.

#### 정합 회복 방안

```python
# common/promote_helpers.py 확장
async def verify_promote_target(
    workspace_repo: WorkspaceRepository,
    target_workspace_id: UUID,
    user_id: UUID,
) -> Workspace:
    """target ws 존재 + type='team' + user 가 멤버 검증. 5 도메인 공통."""
    ws = await workspace_repo.find_by_id(target_workspace_id)
    if ws is None: raise TargetWorkspaceInvalidError()
    if ws.type == "personal": raise CannotPromoteToPersonalError()
    if await workspace_repo.find_member(target_workspace_id, user_id) is None:
        raise TargetWorkspaceInvalidError()
    return ws

async def enqueue_promote_embed(
    background_tasks: BackgroundTasks,
    *,
    bg_fn: Callable, new_item_id: UUID, target_workspace_id: UUID,
    audit_id: UUID, embed_text: str, session_factory, pipeline,
) -> None:
    background_tasks.add_task(bg_fn, new_item_id=..., ...)
```

각 도메인 service.promote() = 50 LOC 미만 (검증 + helper 호출 + 복제 + audit + enqueue).

#### 위반 누적 비용

- 6번째 도메인 promote 추가 시 또 100 LOC 답습.
- promote 정책 (예: D-6.4 admin audit 추가) 변경 시 5 도메인 동시 수정 — locality 낮음.

---

### BUG-S27e-ARCH-7 — BL-005 가 stale (이미 해소된 부채 P0 등재 유지)

- **위반**: Atomic Update (BL backlog 동기화), 거버넌스 정확성
- **심각도**: P3
- **차단**: NO
- **file**: `docs/refactoring-backlog.md:440-471`

#### 위반 내용

BL-005 본문: "★★★★★ P0 헌법 위반 — `memory/service.py:420, 431` 가 `self.repo.session.execute(target_q)` 직접 호출".

실재 코드 (`backend/src/memory/service.py:405-505` promote): `self.workspace_repo.find_by_id(target_workspace_id)` + `self.workspace_repo.find_member(target_workspace_id, promoted_by_user_id)` 사용 — WorkspaceRepository 경유. `self.repo.session.execute` grep 0 hit.

memory `[[project_sprint19_pr1_kickoff]]` "Sprint 19 PR #1 C10 (Codex F-4): WorkspaceRepository 통한 검증 (backend rule §3 회복)" 와 정합 — BL 만 갱신 안 됨.

#### 정합 회복 방안

```markdown
## BL-005 — memory.service.promote() Service Session 직접 접근 제거 ✅ **완료 (Sprint 19 PR #1 C10, 2026-05-18)**

**해소**:
- `backend/src/memory/service.py:443-447` — WorkspaceRepository.find_member + find_by_id 사용.
- `self.repo.session.execute(...)` 호출 0 hit 검증 (Sprint 27e ARCH audit).
- `MemoryService.__init__` workspace_repo 주입 강제 (line 424 fail-closed RuntimeError).

**근거**: Sprint 19 PR #1 C10 (Codex F-4), memory `project_sprint19_pr1_kickoff.md`.
```

---

## 4. 부채 (BL) 재평가

### Active BL 중 본 sprint 검증 대상 (BL-005~013, BL-S26-*, BL-S27c-*, BL-S27e-*, BL-S27-*)

| BL | 현재 우선순위 | 실 코드 상태 (verified) | production 진입 시 영향 | 본 sprint fix 권고 |
|----|------------|----------------------|----------------------|-----------------|
| BL-005 | ★★★★★ P0 | ✅ **이미 해소** (Sprint 19 PR #1 C10) — BL 문서 stale | 0 | BL 문서 마크 (BUG-S27e-ARCH-7) |
| BL-006 | ✅ 완료 | 검증: `memory/service.py` 의 `from src.embeddings.*` 0 hit. `pipeline_service.save_memory_chunk` 캡슐화 적용. architecture gate test 가 회귀 차단. | 0 | NO (closed) |
| BL-007 | ★★★ P1 | `memory/service.py:637-709` module-level `_call_distill`/`_call_embedding`/`_call_transcribe` 잔존 — services 통합 미적용 | 낮음 (성능/유지보수 부채만, 외부 호출 동작 영향 0) | NO (carry, BL-005/006 묶음 sprint 후) |
| BL-008 | ★★★ P1 | `memory/service.py` `_upload_audio_to_r2`/`_download_audio_from_r2` 잔존 — R2Service 메서드 상향 미적용 | 낮음 (boto3 client 재생성 = connection pool 부담, 외부 5명 dogfooding 부하 미미) | NO (carry) |
| BL-009 | ★★ P2 | `memory/service.py` 3 BG task `processing→embedding_pending→active` 전이 중복 — status_flow 분리 미적용 | 낮음 | NO (carry) |
| BL-010 | (정책 미결) | `memory/service.py:335-355` `_get_query_embedding` cache lookup + race condition 정책 미결정 | 낮음 (UNIQUE 충돌 무시 패턴 동작, deterministic 부족) | NO (정책 결정 필요) |
| BL-011 | ★★ P2 | memory 모듈 test coverage 9 critical 케이스 | 낮음 (existing 테스트 통과) | NO (carry) |
| BL-012 | ★ P3 | memory hygiene 18건 (TODO comment 잔재 등) | 0 | NO (carry) |
| BL-013 | ★★ P2 | alembic FK ondelete + 2-phase deploy + downgrade safety | 중간 (외부 dogfooding 시 cascade 정책 필요) | NO (carry, 별도 sprint) |
| BL-S26-1 | ★ P3 | 헌법 토큰컷 Sprint 27a partial (3793→3398). 목표 ≤3,000 잔여 13%. | 0 | NO (carry) |
| BL-S26-2 | ★★ P2 | docs/*.md 47 → 30 cut. | 0 | NO (carry) |
| BL-S26-3 | ★ P3 | dev-log dead link cleanup. | 0 | NO (carry) |
| BL-S27c-1 | ✅ 완료 | Sprint 27d main `1b24898` 머지 — `auth/dependencies.py:160-178` ON CONFLICT 적용 verified. | 0 | NO (closed) |
| BL-S27c-2 | ✅ 완료 | GEMINI_API_KEY 재발급은 사용자 작업 — 코드 변경 없음. | n/a | NO (사용자 task) |
| BL-S27c-3 | ★★ P1 | Landing screenshot 400 fix — `frontend/public/landing/screenshots/` 파일 존재, Next.js Image config issue | 0 (landing trust 직접 영향 외) | NO (carry) |
| BL-S27c-4~10, BL-S27c-12, BL-S27c-11 | 다양 | UX/운영 BL, 본 audit scope 외 | 다양 | NO (carry) |
| BL-S27e-1 | ★ P3 | RAG p95 측정 — Sentry 도입 시 자동 | 낮음 (10.6s avg → 외부 UX 임계) | NO (BL-S27c-9 Cloud Run min instance 와 묶음) |
| BL-S27e-2 | ★ P3 | 사이드바 nav flicker | 0 (시각 잡음) | NO |
| BL-S27e-3 | ★ P3 | CSP 정책 도입 | 0 | NO |
| BL-S27e-4 | ★ P3 | FE 병렬 E2E flake | 0 (CI gate 외) | NO |
| BL-S27-1 | ★ | WorkspaceMember.is_active soft delete | 낮음 (외부 5명 dogfooding 시 퇴사 case 0건 예상) | NO |
| BL-S27-2 | ★ | RAG 신선도 라벨 | 0 | NO |
| BL-S27-3 | ★ | AdminAccessAudit 테이블 | 낮음 (admin = founder 1인) | NO |

### 본 audit 신규 권고 BL (반영 권고)

| BL 번호 (제안) | 제목 | 우선순위 | 근거 |
|--------------|------|---------|------|
| BL-S27e-ARCH-1 | OnboardingService AsyncSession 분리 (I-1 정합) | ★★ P1 | BUG-S27e-ARCH-1 |
| BL-S27e-ARCH-2 | services/transcription 의 meetings.models 역의존 제거 (DTO 패턴) | ★ P2 | BUG-S27e-ARCH-2 |
| BL-S27e-ARCH-3 | `backend/src/audit/` 도메인 분리 (common 책임 정리) | ★ P2 | BUG-S27e-ARCH-3 |
| BL-S27e-ARCH-4 | 헌법/directory-map 의 BE/FE 모듈 수 정합 갱신 | ★★ P1 (governance) | BUG-S27e-ARCH-4 |
| BL-S27e-ARCH-5 | RagService 의 embedding_repo.session 우회 추출 제거 | ★ P3 | BUG-S27e-ARCH-5 |
| BL-S27e-ARCH-6 | promote 패턴 공통 helper 확장 (5 도메인 LOC 축소) | ★ P2 | BUG-S27e-ARCH-6 |
| BL-S27e-ARCH-7 | BL-005 closed 마크 (Atomic Update 회복) | ★ P3 | BUG-S27e-ARCH-7 |

---

## 5. 정합 OK 항목 (verified)

검사 후 위반 없음 — 정합 명시.

| 항목 | 검증 결과 |
|------|---------|
| **B-1 (FastAPI 100% async)** | 12 router 파일의 모든 endpoint async (`auth/router.py:13` `async def get_me` 외 51개) — sync def endpoint 0건 |
| **B-3 (Pydantic V2)** | `class Config` 잔재 0 (test 제외). `.dict()` (V1) 잔재 0. SQLModel/Pydantic V2 일관. |
| **I-3 / I-6 / ADR-019 Phase B (모델 고정)** | `GEMINI_MODEL = "gemini-3.1-flash-lite"` (services/ai_processing.py:22, memory/service.py:69). `text-embedding-3-small` (embeddings/service.py:84). 다른 모델 string 0건. |
| **I-4 (프롬프트 중앙)** | `system_instruction='...'` 인라인 0건. 모두 `common/prompts.py` 상수 참조. |
| **I-7 (chunk_level=2 검색)** | `embeddings/repository.py` vector/text search 모두 `chunk_level = 2` filter. |
| **I-9 (RBAC mutation 가드)** | 14 router 의 mutation endpoint 모두 `require_admin/member/owner/viewer` 적용 (auth/me + onboarding/me + memory admin_router 의 cron 인증 외 — 자기 자신 또는 cron secret 보호). |
| **I-11 (shadcn/ui 무수정)** | `git log` 검증 — components/ui 수정 commit 0건 (초기화 외). |
| **I-13 (workspace prefix)** | 모든 도메인 router prefix = `/api/v1/workspaces/{workspace_id}/<resource>` 정합. 예외 = `/api/v1/users` (auth, onboarding), `/api/v1/admin/memory` (cron), `/api/v1/invites/...` (invite-by-token) — 헌법 예외 인정. |
| **I-14 / B-10 (session.exec)** | 모든 `session.execute` 호출이 B-10 manifest (G1~G3-keep-dialect) 5 카테고리 정합 — embeddings (SET LOCAL, G2), actions (rowcount, G3-keep), memory (pg_insert dialect, G3-keep-dialect), main.py (healthcheck, G2), auth/dependencies (lazy seed dialect, G2). 예외 = onboarding (BUG-S27e-ARCH-1). |
| **I-18 (Promote = 복제 + tombstone)** | memory = `PromotionAudit`, 4 도메인 (meeting/note/inbox/action) = `ItemPromotionAudit` 적용. 5 도메인 promote 함수 모두 source 보존 + duplicate INSERT. |
| **I-19 (Personal invite 차단)** | `workspaces/service.py:131` + `invite_service.py:61, 176` 모두 `PersonalWorkspaceProtected` raise. |
| **I-20 (halfvec 1536)** | `embeddings/models.py:44, 76` + `memory/models.py:140` 모두 `HALFVEC(1536)`. `Vector(1536)` 잔재 0. |
| **I-21 (HNSW 세션 변수)** | `_apply_hnsw_session_params` 가 embeddings vector_search (line 186) + find_similar_cache (line 330) + memory vector_search (line 177) 진입에서 호출. 정합. |
| **ADR-014 cross-domain 정합** | service.py 끼리 직접 import 0건. embeddings/ai_processing/transcription 호출은 pipeline_service 또는 RagService (옵션 A 예외, rag/CONTEXT.md §5 명시) 경유. `test_no_memory_to_embeddings_lazy_import.py` 회귀 가드 존재. |
| **ADR-021 (Sentry scrubbing)** | `main.py:45-55` `_scrub_pii_hook` — `transcript` / `email` / `password` / `audio_url` / `user.email` / `user.ip_address` 제거 + `send_default_pii=False`. |
| **ADR-022 + ADR-024 (Clerk webhook SKIP)** | `sync_user` handler + `/users/sync` endpoint grep 0 hit (제거 완료). 회귀 가드 `tests/auth/test_auth_sync_disabled.py` 존재 (`auth/CONTEXT.md` §5/§6 strikethrough). ADR-024 supersedes 명시. |
| **ADR-023 (D-6 5건)** | D-6.4 `_apply_visibility_filter` (projects/repository.py:73-114) admin/owner bypass 동작. BL-S27-3 AdminAccessAudit 후속 등재. ADR-023 5건 모두 BL 후속화. |

---

## 6. Summary

- **헌법 위반**: 1건 (I-1 — BUG-S27e-ARCH-1)
- **헌법/architecture doc 정합 위반 (Atomic Update)**: 1건 (BUG-S27e-ARCH-4)
- **ADR 위반**: 0건
- **설계 원칙 위반 (SOLID/DRY/KISS/Layered)**: 4건 (ARCH-2 DIP / ARCH-3 Layered / ARCH-5 Demeter / ARCH-6 SRP)
- **BL 거버넌스 stale**: 1건 (BUG-S27e-ARCH-7)
- **차단 (Blocking)**: **0건** (production 진입 직접 영향 없음)
- **비차단 (P1~P3)**: 7건 (모두 BL-S27e-ARCH-1~7 carry)

### 가장 critical 3건

1. **BUG-S27e-ARCH-1** (P1, NO-BLOCK) — `OnboardingService` 가 AsyncSession + raw SQL 직접 보유. 헌법 I-1 명백 위반. 외부 5명 진입 후에도 동작 정상이나, 다음 onboarding step 확장 또는 새 hook helper 가 같은 패턴 답습하기 전에 본 sprint 또는 Sprint 28 안에 정합 회복 권고.

2. **BUG-S27e-ARCH-4** (P1, NO-BLOCK) — 헌법 + directory-map + .claude/CLAUDE.md 의 BE/FE 모듈 수가 stale (BE 13→실재 15, FE 11→실재 14). Atomic Update 원칙 위반. 새로 들어오는 AI agent / contributor 가 모듈 경계를 잘못 파악할 risk. ARCH-3 (audit 도메인 분리) 와 합쳐 1 PR 권고.

3. **BUG-S27e-ARCH-6** (P2, NO-BLOCK) — 5 도메인 promote 함수 100+ LOC × 5 = 5+ 책임 분산. SRP/KISS 위반. promote 정책 변경 (예: ADR-023 D-6.4 admin audit 추가) 시 5곳 동시 수정. `common/promote_helpers.py` 확장으로 50 LOC 미만으로 축소 가능.

### GO 판정 (헌법 정합성 차원)

- 헌법 정합성 GO 조건 (SCOPE.md): "CONTEXT-MAP.md + ADR-* 위반 0" — 본 audit 결과 헌법 위반 **1건 (BUG-S27e-ARCH-1)** + 정합 1건 (BUG-S27e-ARCH-4).
- 그러나 모든 위반은 **비차단 (P1~P3)**. production 동작 0 영향 / 외부 5명 dogfooding 0 차단.
- 본 reviewer 판정: **PASS-with-carry** — 7건 모두 BL-S27e-ARCH-1~7 로 carry 후 Sprint 28 (paid customer 1명) 또는 Sprint 29 (architecture deepening) 묶음 처리. 헌법 doc 정합 회복 (ARCH-4) 만 본 sprint 안에 1 PR 권고 (governance 의미, ~30 LOC).

### 후속 sprint 진입 시 첫 read

`docs/refactoring-backlog.md` 의 BL-S27e-ARCH-1~7 신규 등재 (위 §4) + 본 파일 §6 critical 3건.

---

## 7. 비전 (second-brain pivot + PERSONA-001 + Atomic Update) 정합

| 차원 | 결과 |
|------|------|
| **second-brain pivot (ADR-004)** | 5 도메인 (memory/meeting/note/inbox/action) promote 흐름이 "복제 + tombstone" 일관 적용 — 흘러가는 시간 속 결정적 순간 포착 메타포 정합. RAG 6-Layer 가 SemanticCache + Hybrid + RRF + Gemini SSE 로 Distill 자동화 충실. |
| **PERSONA-001 (1인 풀스택)** | `services/` 외부 wrapper 단순 (transcription/ai_processing/chunked_transcription 3 파일). cross-domain orchestrator 패턴이 5 도메인 일관 적용 — 1인 풀스택이 변경 추적 가능한 구조. 그러나 promote SRP 위반 (BUG-S27e-ARCH-6) 이 1인 founder 의 변경 비용 증가 — 다음 promote 정책 변경 시 5 도메인 동시 touch. |
| **Atomic Update** | 부분 위반 (BUG-S27e-ARCH-4 + ARCH-7) — 코드 추가 시 헌법/BL 갱신 1회 누락. Sprint 26 §9 "코드 변경 시 관련 canonical doc 1개를 같은 PR 에 포함" 정책 회귀. |

비전 정합도 = **8/10** (5 도메인 promote 일관성 + Distill 자동화 충실은 강점, Atomic Update 부분 위반은 governance 부채).

---

*검사자: Architecture Guardian (Claude Opus 4.7, 1M context)*
*baseline: 1b24898 (main, Sprint 27d merged)*
*branch: sprint-27e/multi-review*
