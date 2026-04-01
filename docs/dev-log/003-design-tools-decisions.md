# ADR-003: 디자인 도구 선정 — Stitch + Pencil + gstack 조합

**날짜:** 2026-04-01
**상태:** 확정

---

## 결정

디자이너 없이 1인 개발 환경에서, **Google Stitch(생성) + Pencil MCP(편집) + gstack /design-review(QA)** 조합을 채택한다. 총 비용 $0/월.

---

## 배경

### 문제
- 디자인팀 없이 1인 개발 — "어떻게 보여야 하는지" 결정이 병목
- 기존 프론트엔드(Next.js 16 + shadcn/ui v4 + Tailwind v4) 56개 TSX 파일 존재
- 디자인 도구가 코드 생성까지 하면 Claude Code 스킬 체인과 충돌

### 평가 기준 (가중치)
- MCP 통합 품질 (25%) — Claude Code와 직접 연결
- 시각적 디자인 결정력 (25%) — "어떻게 보여야 하는지" 판단 지원
- 비용 (20%) — 1인 개발자 기준
- 디자인 시스템 정의 (15%) — 색상/타이포/간격 체계
- Kairos 스택 호환성 (15%) — Next.js + shadcn + Tailwind + 다크모드

---

## 검토한 도구 (8개)

| 도구 | MCP | 시각적 결정 | 비용/월 | 디자인 시스템 | 스택 호환 | 총점 |
|------|:---:|:---:|------|:---:|:---:|:---:|
| **Google Stitch** | ★★★★★ | ★★★★★ | $0 (550회) | ★★★★☆ | ★★★★☆ | **9.2** |
| **Pencil** | ★★★★★ | ★★★★☆ | $0 (무제한) | ★★★★★ | ★★★★★ | **9.0** |
| **Figma** | ★★★★★ | ★★★★★ | $0(6회)~$25 | ★★★★★ | ★★★☆☆ | **7.8** |
| **v0.dev** | ★★★★☆ | ★★★★☆ | $0($5분)~$20 | ★★☆☆☆ | ★★★★★ | **7.2** |
| **Framer** | ★★★☆☆ | ★★★★☆ | $0~$15 | ★★★★☆ | ★★☆☆☆ | **5.8** |
| **Relume** | ★★☆☆☆ | ★★★☆☆ | $0~$49 | ★★☆☆☆ | ★★★☆☆ | **4.5** |
| Galileo AI | Google Stitch로 합병 | — | — | — | — | — |
| gstack 디자인 스킬 | 내장 | ★★★★☆ | $0 | ★★★★★ | ★★★★★ | **8.5** |

---

## 채택 조합과 역할

### Google Stitch + MCP (생성)

| 항목 | 내용 |
|------|------|
| MCP | `stitch-mcp` — `build_site`, `get_screen_code`, `get_screen_image` |
| 무료 | 550회/월 (Standard 350 + Pro 200) |
| 핵심 가치 | 텍스트 → 5개 화면 동시 생성, DESIGN.md 내보내기 |
| 결과물 | HTML + Tailwind CSS, 스크린샷(PNG), DESIGN.md |

### Pencil MCP (편집)

| 항목 | 내용 |
|------|------|
| MCP | 로컬 자동 시작, 15개 API (양방향 읽기/쓰기) |
| 무료 | 무제한 (로컬 앱) |
| 핵심 가치 | 캔버스에서 정밀 편집, 디자인 토큰 시스템, shadcn UI 킷 내장 |
| 결과물 | 디자인 토큰 + 레이어 구조 + 스크린샷 |

### gstack /design-consultation + /design-review (시스템 + QA)

| 항목 | 내용 |
|------|------|
| /design-consultation | DESIGN.md 생성 (브랜드 키트 정의) |
| /design-review | 라이브 사이트 비주얼 QA (before/after 비교) |
| 무료 | gstack 내장 |

### 역할 분리

```
생성 (Stitch) → "전체 화면을 빠르게 탐색/비교"
편집 (Pencil) → "선택한 방향을 세밀 조정"
시스템 (/design-consultation) → "디자인 철학/토큰/모션 정의"
QA (/design-review) → "구현 후 시각적 품질 보증"
```

---

## 디자인 워크플로우 (5단계)

```
Step 1: /design-consultation → DESIGN.md (브랜드 키트)
  → 색상, 타이포, 간격, 모션, 분위기 확정
  → Stitch에 브랜드 키트로 임포트 (결과물 품질의 핵심)

Step 2: Stitch + MCP → 화면 생성
  → DESIGN.md 토큰 임포트 → 5개 화면 동시 생성
  → 음성/텍스트 실시간 수정 반복

Step 3: Pencil MCP → 정밀 편집 (커스텀 컴포넌트만)
  → RAG 채팅 버블, 트랜스크립트 타임라인 등
  → 일반 화면은 Stitch 결과물로 충분

Step 4: Stitch/Pencil MCP → Claude Code → brainstorming → TDD
  → 스크린샷 + HTML을 "참고 자료"로 사용
  → 기존 shadcn 컴포넌트를 재활용하면서 구현

Step 5: /design-review → 비주얼 QA
  → 구현 결과가 디자인과 일치하는지 확인
```

### 사용 비율 전략

| 화면 유형 | 비율 | 도구 | 이유 |
|-----------|------|------|------|
| 일반 화면 (CRUD, 목록, 상세) | 80% | Stitch 참고 | shadcn 컴포넌트 조합으로 충분 |
| 커스텀 컴포넌트 | 20% | Pencil 상세 | 기존 UI 킷에 없는 고유 컴포넌트 |

### 이유

기존 shadcn/ui 컴포넌트가 있는 프로젝트에서, Pencil의 상세 사양을 받아서 맞추면 shadcn과 충돌 가능. 시각적 목표(스크린샷 + DESIGN.md)를 참고해서 기존 도구로 조합하는 게 빠르고 일관적.

---

## 기각 도구와 이유

| 도구 | 기각 이유 |
|------|----------|
| **Figma** | 무료 6회/월, Dev seat $25/월. 디자인팀이 있으면 1위지만 1인 개발에서는 비용 대비 효과 부족 |
| **v0.dev** | 코드 생성은 Claude Code가 더 잘함. 무료 20회. Stitch(550회) 대비 장점 없음 |
| **Framer** | 자체 배포 플랫폼, Next.js 프로젝트와 분리됨 |
| **Relume** | 공식 MCP 없음, $49/월, 와이어프레임 특화 |

---

## 비용

| 도구 | 월 비용 |
|------|---------|
| Google Stitch | $0 (550회/월, Google Labs 기간) |
| Pencil | $0 (로컬 앱, Max 요금에 포함) |
| gstack 디자인 스킬 | $0 (내장) |
| **합계** | **$0/월** |

> Stitch는 Q4 2026 유료화 예정. 유료화 시 Figma 대비 30-50% 저렴할 것으로 전망.
> Pencil은 Claude Code Max 요금($100~200/월)에 MCP 토큰이 포함됨.

---

## 참조

- Stitch MCP: https://github.com/davideast/stitch-mcp
- Stitch 공식 MCP 문서: https://stitch.withgoogle.com/docs/mcp/setup/
- Pencil 문서: https://docs.pencil.dev/getting-started/ai-integration
- Figma MCP 가이드: https://help.figma.com/hc/en-us/articles/32132100833559
- Design-to-Code Codelab: https://codelabs.developers.google.com/design-to-code-with-antigravity-stitch
