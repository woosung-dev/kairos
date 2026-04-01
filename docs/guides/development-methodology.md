# AI 기반 1인 풀스택 개발 방법론

> 신규 프로젝트에 바로 적용 가능한 8 Stage 프레임워크.
> Stage 1~3은 프로젝트 초반 1회. Stage 4~8은 2주 Sprint로 반복.

---

## 전체 흐름

```
[Stage 1] 기획 → [Stage 2] 아키텍처 → [Stage 3] 디자인
  ↓
[Stage 4] Sprint 계획 → [Stage 5] 구현 → [Stage 6] 검증 → [Stage 7] 배포 → [Stage 8] 학습
  ↓                                                                              ↓
  └──────────────────────── Stage 4로 돌아감 (다음 Sprint) ←──────────────────────┘
```

---

## Stage 1: 기획 — "뭘 만들 것인가?"

**도구:** `/office-hours` (Startup 또는 Builder 모드)

1. 6개 강제 질문: 수요 증거, 현재 해결법, 구체적 사용자, 가장 좁은 쐐기, 관찰, 미래 적합성
2. 전제(Premises) 확인 → 3가지 접근 방안 비교 → 선택
3. 디자인 문서 생성 → `~/.gstack/projects/{slug}/`

**선택적:** `/plan-ceo-review` (스코프 검증), `/autoplan` (3중 자동 리뷰)

**산출물:** 디자인 문서 (문제, 수요 증거, 타겟 유저, 성공 기준)

---

## Stage 2: 아키텍처 — "어떤 구조로?"

**도구:** `/plan-eng-review` + 직접 문서 작성

1. 기술 스택 결정 → `docs/dev-log/001-tech-stack.md` (ADR)
2. 데이터 모델 설계 → `docs/architecture/erd.md` (전체 Phase 고려)
3. API 경계 설계 → `docs/api/endpoints.md` (FE mock API와 1:1 대응)
4. 파이프라인 설계 → `docs/architecture/` (데이터 흐름, 비동기 패턴)
5. `/plan-eng-review` 실행 (아키텍처 건전성 검증)

**핵심:** 아키텍처는 전체 Phase 커버. 실행 계획은 Sprint 직전에만 상세화.

**산출물:** ADR, ERD, API 명세, 아키텍처 문서

---

## Stage 3: 디자인 — "어떻게 보일 것인가?"

**도구:** `/design-consultation` → Stitch MCP → Pencil MCP

1. `/design-consultation` → DESIGN.md (색상, 타이포, 간격, 모션, 분위기)
2. Stitch + MCP → DESIGN.md 임포트 → 5개 화면 동시 생성 → 실시간 수정 반복
3. Pencil MCP → 커스텀 컴포넌트만 정밀 편집 (기존 UI 킷에 없는 것)

**사용 비율:** 일반 화면 80% Stitch 참고, 커스텀 20% Pencil 정밀

**산출물:** DESIGN.md, 화면별 스크린샷, 디자인 토큰

---

## Stage 4: Sprint 계획 — "이번 2주에 뭘 할 것인가?"

**도구:** `brainstorming` → `writing-plans`

1. Vertical Slice 선정 ("FE+BE 관통하는 핵심 흐름은?")
2. `brainstorming` (필수) — 기능 단위 설계 탐색
3. `writing-plans` — 구체적 파일, 순서, 의존성
4. [중간 규모+] 별도 서브에이전트에서 계획 리뷰
5. 병렬화 판단 — 독립 작업은 git worktree로 분리

**산출물:** Sprint 작업 목록 (우선순위 + 예상 시간 + 의존성)

---

## Stage 5: 구현 — "코드 작성"

**도구:** TDD → `/simplify` → `/browse`

1. `test-driven-development` — 테스트 먼저 → Red → Green → Refactor
2. `/simplify` — TDD 잔여물 정리 (코드량 5~15% 감소)
3. `/browse` — FE 변경 시 즉시 브라우저 확인
4. `react-best-practices` / `composition-patterns` — FE 자동 적용

**모델 전략:**

| 작업 | 모델 |
|------|------|
| 아키텍처, 새 기능, 디버깅 | Opus |
| 단순 수정, 문서 | Sonnet |
| 파일 탐색 | Haiku |

**병렬:** 독립 작업은 `using-git-worktrees` + `dispatching-parallel-agents`

---

## Stage 6: 검증 — "제대로 동작하는가?"

**도구:** `/qa` → `/design-review` → `/investigate`

1. `/qa` — Sprint 말 통합 QA (Health score 8+ 목표)
2. `/design-review` — 라이브 UI 비주얼 감사
3. `/investigate` — 버그 시 `/freeze` + 읽기 전용 분석 → 승인 후 수정
4. `/careful` — 파괴적 명령 전 경고

**비동기:** `/qa-only` (리포트만), `/review` (PR 코멘트) — 답변 불필요

---

## Stage 7: 배포 — "사용자에게 전달"

**도구:** `/ship` → `/review` → `/land-and-deploy`

1. `/ship` — 테스트 + 리뷰 + VERSION/CHANGELOG + PR
2. `/review` — 7개 전문 리뷰어 병렬 실행 (자동)
3. `/land-and-deploy` — PR 머지 + CI + 헬스체크 + 카나리
4. `/cso` — 보안 감사 (배포 전 1회)
5. `/benchmark` — 성능 기준선 (성능 민감 기능 후)

---

## Stage 8: 학습 — "뭘 배웠는가?"

**도구:** `lessons.md` → `/retro` → 규칙 승격

1. 실수 즉시 → `.ai/project/lessons.md` 기록
2. Sprint 말 → `/retro` (커밋 분석 + lessons.md 업데이트)
3. 3회 반복 패턴 → `.ai/stacks/` 규칙 승격
4. 정기 감사 → 모델 개선으로 불필요해진 규칙 삭제

**승격 경로:** lessons.md → .ai/project/ → .ai/stacks/ → .ai/common/ → 삭제

---

## 신규 프로젝트 시작 체크리스트

```
□ AGENTS.md 프로젝트 컨텍스트 채우기
□ .ai/rules/ 심링크 설정 (스택에 맞게 교체)
□ /office-hours → 디자인 문서 생성
□ docs/ 구조 생성 (requirements/, architecture/, dev-log/, guides/)
□ ADR-001: 기술 스택 결정
□ ERD 설계 (전체 Phase 고려)
□ API 명세 (FE mock과 1:1 대응)
□ /design-consultation → DESIGN.md
□ Stitch MCP 설정
□ PRD Sprint 분해
□ Sprint 1 시작 → Stage 4~8 반복
```

---

## MCP 관리

| 세션 | 활성 MCP | 비활성 |
|------|---------|--------|
| 코딩 | GitHub만 | 디자인 도구 |
| 디자인 | Pencil + Stitch + GitHub | — |
| 디버깅 | GitHub | 디자인 도구 |

---

## 핵심 원칙

1. **아키텍처는 전체, 실행은 Sprint 단위** — 나중에 DB 스키마 바꾸는 게 가장 비싼 실수
2. **Vertical Slice** — Phase 순서 대신 FE+BE 관통
3. **코드 생성은 Claude Code** — 디자인 도구는 "시각적 결정"에만
4. **brainstorming 필수** — 매 기능 구현 전 설계 탐색
5. **TDD → simplify → browse → qa** — 품질 파이프라인 빠짐없이
6. **lessons.md** — 실수를 자산으로, 3회 반복 시 규칙 승격
