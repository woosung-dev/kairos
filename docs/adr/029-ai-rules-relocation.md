# ADR-029: `.ai/` 해체 — 스택 규칙을 디렉터리별 `AGENTS.md` 로 이전

**Status**: Accepted
**Date**: 2026-08-15
**관련**: ADR-027 (apps 레이아웃 · 계약 거버넌스) · ADR-028 (OCI 셀프호스팅 — 본 이전에서 정정한 드리프트의 출처) · ADR-020 (pgvector HNSW halfvec) · `AGENTS.md` §5 · `apps/backend/CONTEXT.md` §5 · `apps/web/CONTEXT.md` §4
**선례**: quant-bridge `docs/decisions/027-nested-agents-md.md` (2026-08-07, 실측 포함)

---

## 1. 배경 — 규칙 정본이 git 밖에 있었다

`.ai/` (14 파일 1,350줄)가 kairos 의 AI 규칙 SSOT 였다. 그런데 `.gitignore:59` 에 `.ai/` 가 있어
**git 이 추적하지 않았다** (`git ls-files .ai` = 0).

그럼에도 tracked 문서·코드 **63곳**이 `.ai/` 를 가리켰다 — 루트 `AGENTS.md`(4) · `CONTEXT-MAP.md` ·
ADR 12개 · `docs/TODO.md` · `apps/{backend,web}/CONTEXT.md` · 그리고 **백엔드 소스 docstring 3곳**.
새 클론 · CI · 타 머신에서는 전부 dangling reference 였고, `.worktreeinclude:26` 의 `.ai` 수동 포함이
그 증상만 덮고 있었다.

이 상태는 이미 한 번 기록됐다 — [ADR-009](009-stage1-retrofit.md) §F10, [ADR-011](011-persona-definition.md)
「`.ai/` 가 의도적 gitignore 라 표 갱신 PR 자체가 불가」. 그때는 우회했고 이번에 해소한다.

### 더 큰 문제 — 안 읽히니까 코드와 어긋난 채 방치됐다

`.ai/stacks/fastapi/backend.md` 343줄은 에이전트가 **작정하고 열어야** 컨텍스트에 들어왔다.
실제로 대부분의 세션에서 안 읽혔고, 그 사이 규칙이 코드와 벌어졌다. 이전 착수 전 실측한 드리프트:

| # | 옛 규칙 | 실제 |
|---|---|---|
| 1 | `session.exec()` **절대 금지** | ★코드 **102회 / 15파일** 사용. Sprint 20 BL-054 로 `CONTEXT.md` **B-10** 이 5카테고리 allowlist 로 **의무화**했다 (I-14 가 B-10 인용) |
| 2 | 배포 = GCP Cloud Run + Docker | ADR-028 로 Oracle A1 + Cloudflare Tunnel, Cloud Run 철거 완료 |
| 3 | DB = PostgreSQL on Neon / 임베딩 절에 halfvec·HNSW 없음 | 2026-08-14 오라클 셀프호스팅(Neon=백업). 실제 `HALFVEC(1536)`+HNSW (I-20/I-21) |
| 4 | R2 = aioboto3 **또는** `run_in_executor` | 코드는 aioboto3 전용 + 공유 client 재사용(PERF-1). executor 예시는 사문화 |
| 5 | 스트리밍 = `StreamingResponse` | **B-14** 「`EventSourceResponse`, `StreamingResponse` 직접 사용 안 함」 |
| 6 | (FE) CSS 변수 `--rag-panel-width` | `globals.css` 에 **존재하지 않음** |
| 7 | (FE) 배포 = Vercel | ADR-028 로 철거 |
| 8 | `from src.core.config import settings` | 그런 심볼 **없음**. `get_settings()` (`@lru_cache`) 뿐 — import 시 ImportError |
| 9 | (TS) 「모든 API 응답 타입을 명시적으로 정의」 | ADR-027 로 `api.gen.ts` 생성물 import, **수기 wire interface 금지** |
| 10 | (TS) 컴포넌트 PascalCase / 훅 camelCase | 실측 **kebab 98 vs Pascal 7**. kebab 이 사실상의 표준 |

★**1번이 이 ADR 의 핵심 논거다.** 규칙만 틀렸고 코드는 이미 맞았다.
정정 없이 자동 로드 경로로 올렸다면 그 순간부터 에이전트가 102곳을 「위반」으로 오판했을 것이다.
**안 읽혀서 사고가 안 났을 뿐**이라는 사실이, 안 읽히는 위치가 왜 위험한지를 보여준다.

---

## 2. 결정

### 2.1 스택 규칙은 그 스택의 디렉터리에 `AGENTS.md` 로 둔다

```
apps/backend/AGENTS.md   # 구 .ai/stacks/fastapi/backend.md (드리프트 정정 후)
apps/backend/CLAUDE.md   # @AGENTS.md + @CONTEXT.md
apps/web/AGENTS.md       # 구 .ai/stacks/nextjs/frontend.md + .ai/common/typescript.md
apps/web/CLAUDE.md       # @AGENTS.md + @CONTEXT.md
```

Claude Code 는 **그 디렉터리의 파일을 읽는 순간** 하위 `CLAUDE.md` 를 로드하고 `@` import 를 따라 편다.
codex 등 다른 에이전트는 `AGENTS.md` 를 직접 읽는다. 실측 근거는 quant-bridge ADR-027 이 2026-08-07 에
확보했으므로 **재검증하지 않고 인용한다**.

★심볼릭 링크가 아니라 `@` import 를 쓴다 (`.worktreeinclude` 가 심볼릭을 스킵, Windows 는 관리자 권한 필요).
기존 `.claude/CLAUDE.md -> ../AGENTS.md` 는 **예외로 유지** — `.worktreeinclude:12` 이
「git 이 추적하는 링크라 워크트리가 알아서 체크아웃한다」고 실측을 남겼다. 루트 `CLAUDE.md` 는 신설하지 않는다.

### 2.2 ★`AGENTS.md` 는 불변식을 재진술하지 않는다

kairos 는 quant-bridge 와 달리 **앱별 `CONTEXT.md` 가 이미 있다** (backend 149줄 B-1~B-15,
web 110줄 F-1~F-12). 그리고 `CONTEXT-MAP.md` 헌법이 `I-14 → B-10` 처럼 그 ID 를 직접 인용한다.
그대로 두면 같은 디렉터리에 규칙 문서가 2개가 되고, 실제로 **B-10 ↔ 구 backend.md §2 가 이미 충돌**했다.

그래서 역할을 규약으로 못박는다:

| 문서 | 소유 |
|---|---|
| `apps/*/CONTEXT.md` | **불변식** (`B-NN` / `F-NN`) + 도메인 모듈 표 + 책임 경계 |
| `apps/*/AGENTS.md` | **코드 스켈레톤 + 스택 함정** + CONTEXT 로 가는 포인터 |

**`B-NN`·`F-NN`·`I-NN` 이 붙은 문장은 `AGENTS.md` 에 복사하지 않는다.** 충돌하면 CONTEXT 가 맞다.
규칙을 추가할 때는 `AGENTS.md` 가 아니라 해당 `CONTEXT.md` 에 새 `B-NN`/`F-NN` 으로 넣는다.
→ 구조적으로 두 정본이 생길 수 없다.

`CLAUDE.md` 가 `@AGENTS.md` + `@CONTEXT.md` **둘 다** import 하는 이유가 이것이다.
불변식이 CONTEXT 에만 있는데 CONTEXT 가 수동 로드면, 자동 로드되는 것은 포인터뿐이라 목적이 반감된다.

### 2.3 `.ai/` 는 삭제한다

| 원본 | 줄 | 처리 |
|---|---|---|
| `stacks/fastapi/backend.md` | 343 | → `apps/backend/AGENTS.md` (드리프트 1~5·8 정정, 불변식은 B-NN 포인터로) |
| `stacks/nextjs/frontend.md` | 149 | → `apps/web/AGENTS.md` (드리프트 6·7 정정) |
| `common/typescript.md` | 28 | → `apps/web/AGENTS.md` §6 (드리프트 9·10 정정) |
| `common/global.md` §2 | ~40 | → 루트 `AGENTS.md` §5 (Atomic Update 라우팅 표 · ID 체계 · TODO 운영) |
| `common/global.md` §4 | ~8 | → `apps/backend/AGENTS.md` §2 (환경변수 NEVER 2줄) |
| `common/global.md` §1·§3·§5 | ~25 | **삭제** — §3 은 `AGENTS.md §6` 과 완전 중복, §1 은 포인터, §5 자기개선 루프는 `.ai/` 경로 전제 |
| `templates/workflow.md` | 80 | **삭제** (사용자 판정 — 옛 내용). 위험도 분류 Lite/Standard/Heavy + MUST/MUST NOT 도 함께 폐기. 루트 `AGENTS.md` §4 는 「검증 증거 표준」만 유지 |
| `project/lessons.md` | 188 | 미승격 6건만 규칙 본문 **인라인 병합** (§3), 나머지 폐기 |
| `stacks/flutter/mobile.md` | 275 | **삭제** — kairos 무관, 참조 0 |
| `project/domain.md` | 19 | **삭제** — 사실상 빈 파일 (승격 0건). `CONTEXT-MAP.md` 가 대체 |
| `integrations/with-gstack.md` · `with-superpowers.md` | 144 | **삭제** — 존재하지 않는 `.ai/rules/` 전제. 스킬 라우팅 SSOT 는 `AGENTS.md` 말미 1줄 |
| `templates/qa-reviewer.md` | 42 | **삭제** — `.claude/agents/` 부재로 어디에도 로드되지 않던 죽은 파일 |
| `templates/lessons-starter.md` · `settings.json.example` | 34 | **삭제** — 빈 템플릿 / 채택된 적 없는 예시 (dart·black 잔재) |

동시 정리:
- `docs/guides/development-methodology.md` (258줄) **삭제** — Sprint 26 에 폐지된 옛 8-Stage 프레임워크.
  `AGENTS.md §4` 의 Plan→Code→Test 와 정면으로 다른 워크플로우를 주장하고 있었다
- `.claude/rules -> ../.ai/rules` **삭제** — untracked + 타깃 부재(dangling)
- `.worktreeinclude` 의 `.ai` 항목 삭제 — 내용이 tracked 가 되어 불필요
- `.gitignore` 의 `.ai/` 줄은 **남긴다** — 재도입 방지용. 「ADR-029 로 해체, 재도입 금지」주석 추가

### 2.4 ADR·dev-log 의 `.ai/` 인용은 고치지 않는다 (tombstone)

ADR 은 그 시점의 결정 기록이다. 특히 [ADR-009](009-stage1-retrofit.md) §F10 과
[ADR-011](011-persona-definition.md) 은 「`.ai/` 가 gitignore 라 PR 불가」가 **결정의 근거 자체**라
경로를 바꾸면 역사 왜곡이다. 본문 무수정, 상단에 참고 1줄만 단다.

---

## 3. lessons 처리 — `docs/lessons.md` 를 만들지 않는다

`.ai/project/lessons.md` 를 `docs/lessons.md` 로 옮기지 않는다. 이유 셋:

1. **강제 수단이 없다.** quant-bridge 의 lessons 는 `docs-audit.sh`·`bl-audit.sh` 가 떠받치지만
   kairos `justfile` 에는 docs recipe 가 0개다. 강제 없는 lessons 파일은 `.ai/project/lessons.md` 의
   재현일 뿐이다 (실제로 마지막 기록 2026-05-20 이후 정지)
2. **살아 있는 정책과 충돌한다.** `docs/README.md:17` 「Sprint 26 부터 dev-log/ 폐지」 +
   구 `workflow.md:15` 「별도 retrospective 파일 작성 금지」
3. **인라인이 더 잘 읽힌다.** 규칙 본문에 넣으면 자동 로드 경로에 올라탄다

미승격 교훈 6건은 규칙 본문에 녹였다:

| 교훈 | 새 위치 |
|---|---|
| pgvector `HalfVector` ≠ `numpy.ndarray` → `to_list()` 폴백 | `apps/backend/AGENTS.md` §7 |
| asyncpg `:name::type` 금지 → `CAST(:name AS type)` | `apps/backend/AGENTS.md` §7 |
| BackgroundTask 에 요청 session 주입 금지 → `session_factory` | `apps/backend/AGENTS.md` §8 |
| 컬럼 **타입 변경**은 2단계 배포의 예외 (operator class 사전 체크) | `apps/backend/AGENTS.md` §9 |
| lifespan 외부 CLI = `init_engine()` + `get_session_factory()` / `PYTHONUNBUFFERED=1` | `apps/backend/AGENTS.md` §10 |
| e2e `data-testid` 우선 · `.first()` 금지 · trace.zip snapshot 먼저 | `apps/web/AGENTS.md` §8 |

나머지는 승격 완료(session_factory 코드 반영 · Atomic Update 매트릭스는 Sprint 26 에 정책 자체가 뒤집힘)
또는 사실 무효(Neon free tier 측정 환경 — ADR-028 로 Neon 은 백업)라 폐기했다.

---

## 4. Consequences

**얻는 것**

- ★**스택 규칙이 자동 로드된다.** `apps/backend/` 파일을 여는 순간 규칙 + 불변식이 함께 들어온다.
  지금까지 대부분의 세션에서 안 읽히던 492줄이 조건부로 항상 로드된다
- ★**codex 등 타 에이전트도 읽는다.** `AGENTS.md` 는 스펙 표준 경로다
- **규칙 정본이 git 안으로 들어온다.** 새 클론·CI·워크트리에서 dangling 이 사라진다
- **드리프트 10건이 정정됐다.** 특히 `session.exec` 은 코드 102곳과 규칙이 정반대였다
- **`.worktreeinclude` 마찰 제거** — 규칙을 수동 복사할 이유가 없어졌다

**치르는 것**

- **파일이 스택당 2개다** (`AGENTS.md` + `CLAUDE.md`). 하나만 옮기면 조용히 안 읽힌다
- **`/compact` 후 재주입되지 않는다.** 압축 뒤 스택 규칙이 필요하면 그 디렉터리 파일을 한 번 더 열어라
- **디렉터리 진입 시 ~490줄이 얹힌다** (AGENTS + CONTEXT). 조건부라 고정비는 아니지만,
  무겁다고 판단되면 `CLAUDE.md` 에서 `@CONTEXT.md` 를 빼고 포인터 1줄로 되돌리는 것이 후퇴 경로다
- ★**§2.2 의 비-재진술 규약을 강제할 게 grep 뿐이다.** quant-bridge 는 `docs-audit.sh` 로 집행하지만
  kairos 엔 docs 게이트가 없다. 누군가 `AGENTS.md` 에 규칙 문장을 쓰면 다시 두 정본이 되고
  이번 이전은 **드리프트를 옮긴 것에 불과**해진다 → `BL-S29-1` 로 `just docs-check` 등재

## 5. 재평가 트리거

⑴ 규칙이 **디렉터리 경계를 넘어야** 할 때 (예: `apps/web/e2e/**` 와 `apps/backend/tests/**` 를 함께 겨냥)
⑵ 하위 `AGENTS.md` 가 루트와 **충돌해야만** 표현되는 규칙이 생길 때
⑶ Claude Code 나 `agents.md` 의 로딩·우선순위 규약이 바뀔 때 (본 ADR 의 사실 근거는 두 도구의 현재 동작에 종속)
⑷ `CONTEXT.md` 동시 import 가 컨텍스트를 유의미하게 압박할 때

---

## 6. Tombstone

| 구 경로 | 새 위치 |
|---|---|
| `.ai/stacks/fastapi/backend.md` | `apps/backend/AGENTS.md` |
| `.ai/stacks/nextjs/frontend.md` | `apps/web/AGENTS.md` |
| `.ai/common/typescript.md` | `apps/web/AGENTS.md` §6 |
| `.ai/common/global.md` | `AGENTS.md` §5 (일부) · `apps/backend/AGENTS.md` §2 (환경변수) · 나머지 삭제 |
| `.ai/templates/workflow.md` | **삭제** (`AGENTS.md` §4 에 검증 증거 표준만 잔존) |
| `.ai/project/lessons.md` | `apps/backend/AGENTS.md` §7~10 · `apps/web/AGENTS.md` §8 (미승격 6건) · 나머지 삭제 |
| `.ai/project/domain.md` | **삭제** (`CONTEXT-MAP.md` 가 대체) |
| `.ai/integrations/with-gstack.md` | **삭제** (`AGENTS.md` 말미 Skill routing) |
| `.ai/integrations/with-superpowers.md` | **삭제** (동상) |
| `.ai/templates/qa-reviewer.md` | **삭제** (gstack `/review`·`/qa` 가 대체) |
| `.ai/templates/lessons-starter.md` | **삭제** |
| `.ai/templates/settings.json.example` | **삭제** |
| `.ai/stacks/flutter/mobile.md` | **삭제** (kairos 무관) |
| `.ai/rules/` (심링크 타깃) | **이미 부재였음** — `.claude/rules` dangling 링크 제거 |
| `docs/guides/development-methodology.md` | **삭제** (옛 8-Stage. 현행은 `AGENTS.md` §4) |

원문 = git history. `.ai/` 는 untracked 였으므로 **git 에 남지 않는다** — 이 표가 유일한 기록이다.
