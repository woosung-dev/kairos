# 아키텍처 다이어그램 (archify)

> 코드가 아니라 **레포 근거를 읽고 그린** 다이어그램 7종. 아키텍처 3종은 각 노드의 `SRC` 배지가 근거 파일·행이고,
> 사양의 `meta.repository.revision` 이 그 근거를 읽은 커밋이다. 흐름 4종(데이터 흐름 · 시퀀스 · 상태 전이 · 워크플로우)은
> archify 가 해당 타입에 `sources` 를 지원하지 않아 근거를 카드·가이드 뷰 문장으로 적었다 (근거 코드 경로는 아래 표).
> 사실이 바뀌면 사양(JSON)을 고치고 다시 렌더한다 — HTML/PNG 를 손으로 편집하지 않는다.
>
> **최근 점검 2026-09-06** — main `884a145` 기준 7종을 코드와 대조했다(소스 앵커 54개 · 컨테이너 한도 · 테이블 26+5 · Whisper 10분×4 · 캐시 0.93/7d · RRF k=60 등).
> 고친 것: `repo-structure` 태그의 테스트 파일 수(pytest 124→125 · vitest 31→39), `auth.ts` 앵커 2개(15행 → `socialProviders` 32행 · `modelName` 27행), 아키텍처 3종 `revision`.
> README 트리오의 같은 숫자도 동기했고, 그 과정에서 PR #187 부터 틀려 있던 "alembic 26 리비전"(실제 25 — 26은 테이블 수)을 정정했다. 흐름 4종은 변경 없음.
> HTML 은 재 deliver(9/9 · visual-check 4 뷰포트 pass). README PNG 는 유지 — architecture `tag` 는 SVG 의 `data-detail="fine"` 텍스트라 기본 read 레벨(LOD)에서 숨겨지므로
> 시각 변화가 없고, 재캡처는 Chromium 빌드 차이로 16px 프레이밍만 바뀌었다. tag 를 바꾼 뒤 PNG 재캡처가 필요한지는 이 LOD 규칙으로 판단한다.

## 아키텍처 3종 (2026-09-04)

| 다이어그램 | 사양 (source of truth) | 인터랙티브 | README 미리보기 |
|---|---|---|---|
| **시스템 아키텍처** — Oracle A1 단일 VM · Cloudflare Tunnel · 컨테이너 5종 · 외부 API 4곳 | [`system-architecture.archify.json`](system-architecture.archify.json) | [`system-architecture.html`](system-architecture.html) | `system-architecture.light.png` · `.dark.png` |
| **데이터 모델** — `kairos-db` 31 테이블 (alembic 26 + Better Auth 5) · 소유권 · `workspace_id` 격리 경계 | [`data-model.archify.json`](data-model.archify.json) | [`data-model.html`](data-model.html) | `data-model.light.png` · `.dark.png` |
| **모노레포 구조** — 앱 2 · 계약 파이프라인 · 게이트(CI = mise) · 배포 경로 | [`repo-structure.archify.json`](repo-structure.archify.json) | [`repo-structure.html`](repo-structure.html) | `repo-structure.light.png` · `.dark.png` |

## 흐름 4종 (2026-09-05)

| 다이어그램 (archify 타입) | 무엇을 그렸나 | 근거 코드 | 사양 · HTML |
|---|---|---|---|
| **AI Distillation 데이터 흐름** (`dataflow`) | 오디오 · 텍스트 · Drive 문서 → R2 · Whisper → Gemini · OpenAI 임베딩 → `kairos-db` 저장 → RAG. Capture / STT / Distill / 저장 / Express 5 스테이지 | `meetings/pipeline_service.py` · `services/transcription.py` · `services/ai_processing.py` · `embeddings/service.py` · `integrations/pipeline_service.py` | [`ai-distillation-dataflow.archify.json`](ai-distillation-dataflow.archify.json) · [`.html`](ai-distillation-dataflow.html) |
| **RAG `/ask` 요청 시퀀스** (`sequence`) | web → api → 인가(JWKS · viewer · visibility) → OpenAI 임베딩 → SemanticCache → 하이브리드 검색(HNSW + pg_trgm → RRF) → Gemini SSE → 캐시 저장 → done. 15 메시지 | `rag/router.py` · `rag/pipeline_service.py` · `rag/service.py:ask` · `auth/dependencies.py` | [`rag-ask-sequence.archify.json`](rag-ask-sequence.archify.json) · [`.html`](rag-ask-sequence.html) |
| **회의 상태 전이** (`lifecycle`) | `meetings.status` uploading → transcribing → analyzing → (임계값 판정) → completed, 텍스트 캡처 지름길, InboxItem 대기, failed 터미널 | `meetings/models.py:24` · `meetings/pipeline_service.py:process_meeting · capture_text · _analyze_and_store` · `mise.toml deploy-preflight` | [`meeting-status-lifecycle.archify.json`](meeting-status-lifecycle.archify.json) · [`.html`](meeting-status-lifecycle.html) |
| **배포 워크플로우** (`workflow` v2) | PR → CI 4 잡 → `deploy-preflight` → `deploy-build` → `deploy-ship`(compose sync → save \| ssh \| load → up -d) → verify-env · gc · /ready, 머지 차단 · `deploy-rollback` 예외 레인 | `.github/workflows/test.yml` · `mise.toml [tasks.deploy-*]` · `deploy/oci/README.md` · ADR-028 D7/D9 | [`deploy-workflow.archify.json`](deploy-workflow.archify.json) · [`.html`](deploy-workflow.html) |

README 미리보기 PNG 는 7종 모두 `<name>.light.png` / `<name>.dark.png` 로 같은 폴더에 있다.
컬럼 단위 데이터 모델은 [`../erd.md`](../erd.md), 디렉터리 트리 전체는 [`../directory-map.md`](../directory-map.md),
파이프라인 서술은 [`../ai-pipeline.md`](../ai-pipeline.md) · [`../rag-pipeline.md`](../rag-pipeline.md) 가 정본이다.
이 폴더는 **그 위의 한 단계 추상화**(컨테이너 · 테이블 그룹 · 배포 단위 · 흐름의 순서)만 다룬다.

## 보는 법

- HTML 은 의존성 없는 단일 파일이다 (폰트만 Google Fonts 에서 받는다). **클론 후 브라우저로 열면** 패닝·줌, 노드 검색,
  가이드 뷰(우상단 01~04), 관계 추적, 다크/라이트, PNG/SVG export 가 동작한다.
- GitHub 는 HTML 을 렌더하지 않으므로 루트 README 에는 PNG(라이트/다크 `<picture>`)를 싣는다.
- 클론 없이 보려면 raw.githack CDN 경유 (머지된 `main` 기준, 캐시 없음):
  [system-architecture](https://raw.githack.com/woosung-dev/kairos/main/docs/architecture/diagrams/system-architecture.html) ·
  [data-model](https://raw.githack.com/woosung-dev/kairos/main/docs/architecture/diagrams/data-model.html) ·
  [repo-structure](https://raw.githack.com/woosung-dev/kairos/main/docs/architecture/diagrams/repo-structure.html) ·
  [ai-distillation-dataflow](https://raw.githack.com/woosung-dev/kairos/main/docs/architecture/diagrams/ai-distillation-dataflow.html) ·
  [rag-ask-sequence](https://raw.githack.com/woosung-dev/kairos/main/docs/architecture/diagrams/rag-ask-sequence.html) ·
  [meeting-status-lifecycle](https://raw.githack.com/woosung-dev/kairos/main/docs/architecture/diagrams/meeting-status-lifecycle.html) ·
  [deploy-workflow](https://raw.githack.com/woosung-dev/kairos/main/docs/architecture/diagrams/deploy-workflow.html)
- Viewer 의 고정 UI(버튼 · 범례 기본 문구 · `<html lang>`)는 **영어**다 — archify 가 `ko` 로케일을 지원하지 않아
  authored 텍스트(제목 · 노드 · 라벨 · 카드)만 한국어다.

## 갱신 절차

archify 는 Claude Code 스킬(`~/.claude/skills/archify`)이다. 타입은 파일명 접미로 알 수 있다
(`architecture` 3종 = schema v1 · `dataflow` · `sequence` · `lifecycle` = v1 · `workflow` = v2).

```bash
A=~/.claude/skills/archify/bin/archify.mjs
T=architecture            # dataflow | sequence | lifecycle | workflow
N=system-architecture     # data-model | repo-structure | ai-distillation-dataflow | rag-ask-sequence | meeting-status-lifecycle | deploy-workflow

node $A validate $T docs/architecture/diagrams/$N.archify.json --quality showcase --repo-root .   # --repo-root 는 architecture 만 의미 있음
node $A deliver  $T docs/architecture/diagrams/$N.archify.json docs/architecture/diagrams/$N.html --quality showcase --repo-root .
node $A visual-check docs/architecture/diagrams/$N.html     # Chrome 필요 — 4 뷰포트 containment + 스크린샷
node docs/architecture/diagrams/capture-png.mjs $N          # README 용 light/dark PNG 재생성 (apps/web 의 Playwright 사용)
```

**합격 기준** — `deliver` 가 `9/9 showcase · 0 errors · 0 warnings`, `visual-check` 가 1440×900 / 1600×1000 /
1920×1080 / 2048×1320 전부 `containment ok`(첫 화면에 스크롤 없이 들어옴). `visual-check` 가 만드는
`*.visual-check.*` 사이드카는 커밋하지 않는다. 스크린샷(`*.visual-check.1440x900.light.png`)은 삭제 전에 **눈으로** 본다 —
라벨이 레인 제목을 가로지르거나 간선이 캔버스 밖으로 도는 결함은 검증기가 잡지 않는다 (2026-09-05 lifecycle · workflow 에서 실측).

**첫 화면 게이트의 실제 메커니즘 (2026-09-05 실측, `assets/template.html` 뷰어)** — 뷰어는 viewBox 가로/세로 비 ≥ **1.55** 일 때만
읽기 폭을 뷰포트 높이에 맞춰 줄이고(최소 960px, 그래서 1440 폭에서 다이어그램이 ~930px 로 보인다), 그 아래 비율이면 폭을 전부
써서 세로로 넘친다. 헤더 + 가이드 뷰 + 카드(3장 × 2~3항목)가 ~380px 를 차지하므로 다이어그램에 남는 높이는 ~500px 다. 따라서:

- **비율 ≥ 1.9** 가 목표 (3장 × 3항목 카드 기준). 카드를 3장 × 2항목으로 줄이면 ~1.8 까지 내려간다. 제목은 **1줄** (2줄이면 ~30px 잃는다)
- **텍스트 하한** — 1440 폭에서 노드 보조 텍스트가 6px 이상이어야 한다 (`composition/desktop-readability`). 축소율이 930 / viewBox 폭이므로
  `dataflow` 노드 sublabel(폭에 맞춰 줄어드는 폰트)은 ≤ ~20자, `sequence` 참가자 sublabel 과 `lifecycle` 상태 sublabel 은 **7px 고정**이라
  viewBox 폭 ≤ 1085 여야 한다 — 시퀀스는 sublabel 을 빼고 폭 1290 을 썼다
- `dataflow` — 스테이지 x 는 100 + 215·stage 로 고정(5 스테이지 = 폭 1068). 행 간격 114 는 `yOffset` 으로 100 까지 좁힐 수 있다 (4행 = 높이 560).
  `toSide: top/bottom` 은 auto 라우팅이 지키지 않으므로 `via` 로 마지막 점의 x 를 노드 중심에 맞춘다
- `lifecycle` — 밴드 3개(main 126 / event 278 / `terminal` 450)가 고정이고 아래 "Outcomes" 밴드는 terminal 레인이 없어도 그려진다.
  상태 하단 ≤ 높이 − 122 라 3 밴드면 높이 ≥ 632. 기본 top-channel(y = 102)은 레인 제목과 겹치므로 `channelY: 116` + `labelDy: 13`
- `workflow` v2 — 같은 `col` 이라도 레인이 다르면 x 가 갈릴 수 있다. 레인을 건너는 간선은 top/bottom 포트로 잇고, 한 노드의 같은 면을 두 간선이
  쓰면 포트 분산으로 7px 미세 세그먼트가 생겨 `explicit-pin-conflict` 가 난다 — 면을 나누거나 라벨을 빼서 직선을 만든다
- architecture 3종 (2026-09-04 실측) — 노드 ≤ 12 · 행 ≤ 4 · 가로 ≤ 1300px · sublabel ≤ 36자 · 카드 항목 ≤ 60자(2줄). fan-out 라벨은 `labelSegment`/`labelAt` 로 분산.
  `--repo-root .` 를 주면 `sources[].path` 실재를 검증한다 — 파일을 옮기면 사양도 고친다

## 의도적으로 넣지 않은 것

- 12 노드 한도 때문에 데이터 모델은 **테이블 그룹**(대표 + 위성) 단위다. `feedback_entries` 는 `users` 그룹(user-level),
  `promotion_audit`/`item_promotion_audit` 은 `감사` 그룹으로 묶었다. 컬럼·인덱스는 `erd.md`.
- 시스템 아키텍처의 `Cloudflare 엣지` 는 노드가 아니라 `사용자 → cloudflared` 간선 라벨이다 — 컨테이너로 존재하는 것은 `cloudflared` 만이다.
- 모노레포 다이어그램에 `mise → apps/*` 간선(be-*/fe-* task)은 그리지 않았다 — 교차선이 늘어 오히려 읽기 어려워져 카드로 옮겼다.
- 데이터 흐름에 `MeetingPipelineService` 오케스트레이터 노드는 없다 — 모든 간선의 허브가 돼 별 모양이 되므로, 호출 순서는 카드와 상태 전이 다이어그램이 맡는다.
- 시퀀스에서 임베딩 반환 · 캐시 MISS 반환은 요청 화살표 하나에 접었다 (15 메시지 × 28px 가 첫 화면 한계). HIT 경로는 라벨 괄호와 카드로만 적었다.
- 상태 전이에 `InboxItem 대기 → completed` 화살표는 없다 — InboxItem 은 항상 생성되고 회의는 같은 트랜잭션에서 completed 라, 대기가 회의 완료를 막는 것처럼 읽히는 간선을 뺐다.
- 데이터 흐름에 `회의 · 요약 · 액션 → RAG /ask` 간선은 없다 — RAG 는 meetings 테이블을 읽지 않고 chunk `metadata_json.title` 을 인용한다.
- 상태 전이의 `failed` 는 재시도 전이가 없다 — 코드에 없는 "재시도" 화살표를 그리지 않았다 (사용자 재업로드가 복구 경로).
- 배포 워크플로우의 `deploy-status`(`/ready`) 는 `verify-env · deploy-gc` 와 한 노드로 접었다 — 같은 열의 별도 노드는 `compose up -d` → `검증` 간선과 교차했다.
