# 아키텍처 다이어그램 (archify)

> 코드가 아니라 **레포 근거를 읽고 그린** 다이어그램 3종. 각 노드의 `SRC` 배지가 근거 파일·행이고,
> 사양의 `meta.repository.revision` 이 그 근거를 읽은 커밋이다. 사실이 바뀌면 사양(JSON)을 고치고 다시 렌더한다 —
> HTML/PNG 를 손으로 편집하지 않는다.

| 다이어그램 | 사양 (source of truth) | 인터랙티브 | README 미리보기 |
|---|---|---|---|
| **시스템 아키텍처** — Oracle A1 단일 VM · Cloudflare Tunnel · 컨테이너 5종 · 외부 API 4곳 | [`system-architecture.archify.json`](system-architecture.archify.json) | [`system-architecture.html`](system-architecture.html) | `system-architecture.light.png` · `.dark.png` |
| **데이터 모델** — `kairos-db` 31 테이블 (alembic 26 + Better Auth 5) · 소유권 · `workspace_id` 격리 경계 | [`data-model.archify.json`](data-model.archify.json) | [`data-model.html`](data-model.html) | `data-model.light.png` · `.dark.png` |
| **모노레포 구조** — 앱 2 · 계약 파이프라인 · 게이트(CI = mise) · 배포 경로 | [`repo-structure.archify.json`](repo-structure.archify.json) | [`repo-structure.html`](repo-structure.html) | `repo-structure.light.png` · `.dark.png` |

컬럼 단위 데이터 모델은 [`../erd.md`](../erd.md), 디렉터리 트리 전체는 [`../directory-map.md`](../directory-map.md) 가 정본이다.
이 폴더는 **그 위의 한 단계 추상화**(컨테이너 · 테이블 그룹 · 배포 단위)만 다룬다.

## 보는 법

- HTML 은 의존성 없는 단일 파일이다 (폰트만 Google Fonts 에서 받는다). **클론 후 브라우저로 열면** 패닝·줌, 노드 검색,
  가이드 뷰(우상단 01~04 — 요청 경로 · 인증 · AI 파이프라인 등), 관계 추적, 다크/라이트, PNG/SVG export 가 동작한다.
- GitHub 는 HTML 을 렌더하지 않으므로 루트 README 에는 PNG(라이트/다크 `<picture>`)를 싣는다.
- 클론 없이 보려면 raw.githack CDN 경유 (머지된 `main` 기준, 캐시 없음):
  [system-architecture](https://raw.githack.com/woosung-dev/kairos/main/docs/architecture/diagrams/system-architecture.html) ·
  [data-model](https://raw.githack.com/woosung-dev/kairos/main/docs/architecture/diagrams/data-model.html) ·
  [repo-structure](https://raw.githack.com/woosung-dev/kairos/main/docs/architecture/diagrams/repo-structure.html)
- Viewer 의 고정 UI(버튼 · 범례 기본 문구 · `<html lang>`)는 **영어**다 — archify 가 `ko` 로케일을 지원하지 않아
  authored 텍스트(제목 · 노드 · 라벨 · 카드)만 한국어다.

## 갱신 절차

archify 는 Claude Code 스킬(`~/.claude/skills/archify`)이다. `architecture` 타입, schema v1.

```bash
A=~/.claude/skills/archify/bin/archify.mjs
N=system-architecture   # data-model | repo-structure

node $A validate architecture docs/architecture/diagrams/$N.archify.json --quality showcase --repo-root .
node $A deliver  architecture docs/architecture/diagrams/$N.archify.json docs/architecture/diagrams/$N.html --quality showcase --repo-root .
node $A visual-check docs/architecture/diagrams/$N.html     # Chrome 필요 — 4 뷰포트 containment + 스크린샷
```

**합격 기준** — `deliver` 가 `9/9 showcase · 0 errors · 0 warnings`, `visual-check` 가 1440×900 / 1600×1000 /
1920×1080 / 2048×1320 전부 `containment ok`(첫 화면에 스크롤 없이 들어옴). `visual-check` 가 만드는
`*.visual-check.*` 사이드카는 커밋하지 않는다.

**레이아웃 제약 (실측, 2026-09-04)** — 첫 화면 게이트를 통과하려면:

- 노드 ≤ 12 · 행 ≤ 4 · 가로 ≤ 1300px (뷰어가 1440 폭에서 930px 로 축소하므로 sublabel 9px 이 6px 이상으로 남아야 한다)
- sublabel ≤ 36자, 카드 항목 ≤ 60자(2줄), 제목 1줄. 공백 없는 긴 토큰(`a·b·c·d`)은 카드에서 줄바꿈이 안 돼 넘친다
- 한 노드에서 여러 노드로 fan-out 할 때 라벨은 `labelSegment`/`labelAt` 로 서로 다른 세그먼트에 놓는다
- `--repo-root .` 를 주면 `sources[].path` 가 실제 존재하는지 검증한다 — 파일을 옮기면 사양도 고친다

PNG 는 브라우저에서 HTML 을 열고 **Export → PNG**(라이트) / 테마 전환 후 다시 Export(다크)로 만들거나,
Playwright 로 `svg` + 범례 영역을 2200px 뷰포트에서 클립 캡처한다. 파일명은 `<name>.light.png` / `<name>.dark.png` 로 고정 —
루트 README 가 이 이름을 참조한다.

## 의도적으로 넣지 않은 것

- 12 노드 한도 때문에 데이터 모델은 **테이블 그룹**(대표 + 위성) 단위다. `feedback_entries` 는 `users` 그룹(user-level),
  `promotion_audit`/`item_promotion_audit` 은 `감사` 그룹으로 묶었다. 컬럼·인덱스는 `erd.md`.
- 시스템 아키텍처의 `Cloudflare 엣지` 는 노드가 아니라 `사용자 → cloudflared` 간선 라벨이다 — 컨테이너로 존재하는 것은 `cloudflared` 만이다.
- 모노레포 다이어그램에 `mise → apps/*` 간선(be-*/fe-* task)은 그리지 않았다 — 교차선이 늘어 오히려 읽기 어려워져 카드로 옮겼다.
