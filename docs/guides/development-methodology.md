# AI 기반 1인 풀스택 개발 방법론 (Gstack + Superpowers)

> 신규 프로젝트에 바로 적용 가능한 8 Stage 프레임워크.
> Stage 1~3은 프로젝트 초반 1회. Stage 4~8은 2주 Sprint로 반복.
>
> 이 문서는 **Gstack + Superpowers** 기준으로 작성되었습니다.
> 도구 없이 사용하려면 `methodology.md` (범용 버전)를 참조하세요.

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

### 완료 기준

- [ ] 디자인 문서에 "성공 기준" 3개 이상 정의됨
- [ ] 타겟 사용자, 핵심 가치 제안, MVP 스코프가 확정됨

---

## Stage 2: 아키텍처 — "어떤 구조로?"

**도구:** `/plan-eng-review` + 직접 문서 작성

1. 기술 스택 결정 → `docs/dev-log/adr/001-tech-stack.md` (ADR)
2. 데이터 모델 설계 → `docs/architecture/erd.md` (전체 Phase 고려)
3. API 경계 설계 → `docs/api/endpoints.md` (FE mock API와 1:1 대응)
4. 파이프라인 설계 → `docs/architecture/` (데이터 흐름, 비동기 패턴)
5. `/plan-eng-review` 실행 (아키텍처 건전성 검증)

**핵심:** 아키텍처는 전체 Phase 커버. 실행 계획은 Sprint 직전에만 상세화.

**산출물:** ADR, ERD, API 명세, 아키텍처 문서

### 완료 기준

- [ ] 기술 스택 ADR 작성 완료
- [ ] ERD가 전체 Phase를 고려하여 설계됨
- [ ] API 명세가 FE mock과 1:1 대응으로 작성됨
- [ ] 엔지니어링 리뷰 통과 (또는 자체 체크리스트 확인)

---

## Stage 3: 디자인 — "어떻게 보일 것인가?"

**도구:** `/design-consultation` → Stitch MCP → Pencil MCP

1. `/design-consultation` → DESIGN.md (색상, 타이포, 간격, 모션, 분위기)
2. Stitch MCP → DESIGN.md 임포트 → 5개 화면 동시 생성 → 실시간 수정 반복
3. Pencil MCP → 커스텀 컴포넌트만 정밀 편집 (기존 UI 킷에 없는 것)

> ⚠️ Stitch MCP(2026.03)와 Pencil MCP는 각각 초기 단계.
> 조합 워크플로우는 커뮤니티에서 아직 대규모 검증 사례가 없으므로
> 실제 적용 시 개별 도구부터 테스트 후 조합할 것.

**사용 비율:** 일반 화면 80% Stitch 참고, 커스텀 20% Pencil 정밀

**산출물:** DESIGN.md, 화면별 스크린샷, 디자인 토큰

### 완료 기준

- [ ] DESIGN.md (색상, 타이포, 간격, 컴포넌트 토큰) 확정
- [ ] 핵심 화면 3개 이상 디자인 완료

---

## Stage 4: Sprint 계획 — "이번 2주에 뭘 할 것인가?"

**도구:** `brainstorming` → `writing-plans`

1. Vertical Slice 선정 ("FE+BE 관통하는 핵심 흐름은?")
2. `brainstorming` (필수) — 기능 단위 설계 탐색
3. `writing-plans` — 구체적 파일, 순서, 의존성
4. [중간 규모+] 별도 서브에이전트에서 계획 리뷰
5. 병렬화 판단 — 독립 작업은 git worktree로 분리

**산출물:** Sprint 작업 목록 (우선순위 + 예상 시간 + 의존성)

### 완료 기준

- [ ] Sprint 작업 목록에 모든 task가 파일 경로 + 검증 기준 포함
- [ ] 병렬 가능 작업과 순차 의존 작업이 구분됨

---

## Stage 5: 구현 — "코드 작성"

**도구:** TDD → `/simplify` → `/browse`

1. `test-driven-development` — 테스트 먼저 → Red → Green → Refactor
2. `/simplify` — TDD 잔여물 정리 (코드량 5~15% 감소)
3. `/browse` — FE 변경 시 즉시 브라우저 확인
4. `react-best-practices` — FE 자동 적용
5. 커밋 자동화 — 슬래시 커맨드로 git add → commit → push → PR 생성을 원커맨드로
   (예: `.claude/commands/commit-push-pr.md`)

> 디자인 시스템을 직접 구축하는 단계에서 composition-patterns 스킬 추가를 검토.

> 출처: Boris Cherny — "하루에 수십 번 쓰는 커맨드.
> 슬래시 커맨드에 인라인 bash로 git status를 사전 계산하면
> 모델과의 불필요한 대화를 줄일 수 있다."

**모델 전략:**

| 작업                      | 모델   |
| ------------------------- | ------ |
| 아키텍처, 새 기능, 디버깅 | Opus   |
| 단순 수정, 문서           | Sonnet |
| 파일 탐색                 | Haiku  |

**병렬:** 독립 작업은 `using-git-worktrees` + `dispatching-parallel-agents`

### 막혔을 때 탈출 패턴

| 증상                           | 대응                                                 |
| ------------------------------ | ---------------------------------------------------- |
| 같은 에러 3회 반복             | `/clear` → 새 세션에서 에러 메시지만 전달하여 재시작 |
| 컨텍스트 70% 이상              | `/compact` (이상적으로는 50%에서 선제 실행)          |
| 접근 방식 자체가 틀린 느낌     | Stage 4로 돌아가서 plan 재작성                       |
| Claude가 관련 없는 파일을 수정 | `/freeze`로 작업 범위 제한                           |
| 세션이 점점 느려짐             | 세션 버리기 — Boris: "10~20% 세션은 버린다"          |

> 세션을 버리는 것도 전략이다. 오염된 컨텍스트에서 계속 작업하는 것보다
> 새 세션에서 깨끗하게 시작하는 게 총 시간이 더 적다.

### 완료 기준

- [ ] 모든 task의 테스트 통과
- [ ] 코드 정리(`/simplify`) 완료
- [ ] FE 변경 시 브라우저 검증 완료

---

## Stage 6: 검증 — "제대로 동작하는가?"

**도구:** `/qa` → `/design-review` → `/investigate`

1. `/qa` — Sprint 말 통합 QA (Health score 8+ 목표)
2. `/design-review` — 라이브 UI 비주얼 감사
3. `/investigate` — 버그 시 `/freeze` + 읽기 전용 분석 → 승인 후 수정
4. `/careful` — 파괴적 명령 전 경고

**비동기:** `/qa-only` (리포트만), `/review` (PR 코멘트) — 답변 불필요

### 완료 기준

- [ ] QA Health score 8+ (또는 자체 기준 통과)
- [ ] CRITICAL 이슈 0개
- [ ] 보안 감사(배포 전) 완료

---

## Stage 7: 배포 — "사용자에게 전달"

**도구:** `/ship` → `/review` → `/land-and-deploy`

1. `/ship` — 테스트 + 리뷰 + VERSION/CHANGELOG + PR
2. `/review` — 7개 전문 리뷰어 병렬 실행 (자동)
3. 배포
   - MVP/소규모: 직접 배포 (카나리 불필요)
   - 프로덕션/다수 사용자: `/land-and-deploy` — PR 머지 + CI + 헬스체크 + 카나리
4. `/cso` — 보안 감사 (배포 전 1회)
5. `/benchmark` — 성능 기준선 (성능 민감 기능 후)

### 완료 기준

- [ ] PR 머지 + 배포 완료
- [ ] 배포 후 헬스체크 통과

---

## Stage 8: 학습 — "뭘 배웠는가?"

**도구:** `lessons.md` → `/retro` → 규칙 승격

1. 실수 즉시 → `.ai/project/lessons.md` 기록
2. Sprint 말 → `/retro` (커밋 분석 + lessons.md 업데이트)
3. 3회 반복 패턴 → `.ai/stacks/` 규칙 승격
4. 정기 감사 → 모델 개선으로 불필요해진 규칙 삭제

**승격 경로:** lessons.md → .ai/project/ → .ai/stacks/ → .ai/common/ → 삭제

### 완료 기준

- [ ] lessons.md 업데이트됨
- [ ] 3회 반복 패턴은 규칙으로 승격됨
- [ ] 불필요해진 기존 규칙 삭제됨

### 다음 Sprint로 전환

Stage 8 완료 후 Stage 4로 돌아갈 때:

1. lessons.md에서 이번 Sprint 교훈 확인
2. `/retro` 산출물의 "개선할 점"을 다음 Sprint 제약조건에 반영
3. 이전 Sprint에서 스킵한 INFO 이슈 중 이번에 처리할 것 선별
4. 이전 Sprint에서 새로 발견된 요구사항이 있으면 Stage 1~2 재방문 검토

---

## 신규 프로젝트 시작 체크리스트

```
□ AGENTS.md 프로젝트 컨텍스트 채우기
□ .ai/rules/ 심링크 설정 (스택에 맞게 교체)
□ /office-hours → 디자인 문서 생성
□ docs/ 구조 생성 (00_project/, 01_requirements/, 04_architecture/ 등 global.md 참조)
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

| 세션   | 활성 MCP                 | 비활성      |
| ------ | ------------------------ | ----------- |
| 코딩   | GitHub만                 | 디자인 도구 |
| 디자인 | Pencil + Stitch + GitHub | —           |
| 디버깅 | GitHub                   | 디자인 도구 |

---

## 핵심 원칙

1. **아키텍처는 전체, 실행은 Sprint 단위** — 나중에 DB 스키마 바꾸는 게 가장 비싼 실수
2. **Vertical Slice** — Phase 순서 대신 FE+BE 관통
3. **코드 생성은 Claude Code** — 디자인 도구는 "시각적 결정"에만
4. **brainstorming 필수** — 매 기능 구현 전 설계 탐색
5. **TDD → simplify → browse → qa** — 품질 파이프라인 빠짐없이
6. **lessons.md** — 실수를 자산으로, 3회 반복 시 규칙 승격
7. **세션을 버리는 것도 전략** — 오염된 컨텍스트에서 고집하기보다 새 세션이 총 시간 적음
8. **도구는 점진적으로** — 필요가 증명될 때까지 추가하지 않는다. 스킬 과적재는 각 스킬의 효과를 희석시킨다
