# ADR-002: 실행 전략 — Vertical Slice Sprint 채택

**날짜:** 2026-03-31
**상태:** 확정
**참고:** 본 ADR 이 인용하는 `.ai/*` 경로는 2026-08-15 [ADR-029](029-ai-rules-relocation.md) 로 이전·삭제됐다. 본문은 당시 기록이라 수정하지 않는다.

---

## 결정

Phase 1→2→3→4 순차 진행 대신, **Vertical Slice Sprint** 방식을 채택한다.
핵심 가치 흐름("회의 업로드 → AI 요약 → Inbox")을 FE+BE 동시 관통시켜
2주 단위 Sprint로 점진적 확장한다.

---

## 배경

### 문제
- Phase 1(FE만) → Phase 2(BE만) 순차 진행 시 mock data 기간이 길어지고,
  실제 API 연결 시점에 대량 재작업 발생 위험
- Phase별 체크리스트가 추상적이어서 매 세션 시작 시 "다음에 뭐하지?" 반복
- 1인 개발 환경에서 FE↔BE 간 계약 불일치를 조기 발견하려면 빨리 연결해야 함

### 검토한 방안 (5가지)

| 방안 | 핵심 | 추천도 | 채택 |
|------|------|--------|:---:|
| Vertical Slice Sprint | FE+BE 관통, 2주 Sprint | ★★★★★ | **O** |
| Autoplan Pipeline | 3중 리뷰 후 실행 | ★★★★☆ | 부분 채택 |
| Documentation-First | 전체 문서 선행 | ★★★☆☆ | X |
| Sprint + Async Review | 코드 먼저, MR 비동기 리뷰 | ★★★☆☆ | X |
| Parallel Worktree Blitz | 3 에이전트 동시 투입 | ★★☆☆☆ | X |

### 채택 이유

1. **YC "Narrowest Wedge" 원칙**: 가장 작은 가치 단위를 먼저 증명
2. **AI 해커톤 우승 패턴**: End-to-End 데모를 최단 시간에 만들고 확장
3. **Mock data 탈출**: FE↔BE 계약을 Sprint 1에서 바로 검증
4. **1인 개발 최적화**: git worktree로 FE/BE 병렬 진행 가능

### 기각 이유

- **Documentation-First**: 동작하는 코드 없이 문서만 늘어나는 "Analysis Paralysis" 위험.
  1인 개발에서는 코드가 곧 검증.
- **Parallel Worktree Blitz**: FE+BE 통합 개발에서 에이전트 간 소통 없이 3개 동시 진행하면
  API 스키마 불일치 → 머지 충돌 비용이 병렬화 이점을 상쇄.

---

## 계획 전략: Option C — 아키텍처는 전체, 실행은 Sprint 단위

**날짜:** 2026-04-01 확정

### 검토한 방안

| Option | 핵심 | 채택 |
|--------|------|:---:|
| A. 전체 Phase 계획 후 실행 | Phase 1~4 모두 Sprint 수준까지 상세화 후 순차 실행 | X |
| B. Phase N 완전 실행 후 N+1 계획 | 현재 Phase만 상세, 완료 후 다음 계획 | X |
| **C. 아키텍처는 전체, 실행은 Sprint** | 아키텍처 문서는 전체 커버, 실행 계획은 당면 Sprint만 | **O** |

### 채택 이유

- **A의 문제:** Phase 3-4 계획은 Phase 1-2 실행 후 바뀔 수밖에 없음. 실행 전 계획은 가정일 뿐. 시간 낭비.
- **B의 문제:** 아키텍처 레벨 의존성을 못 잡음. Phase 1에서 DB 스키마를 잘못 잡으면 Phase 3 RAG에서 재작업.
- **C의 장점:** 아키텍처(ERD, API 경계, RAG 파이프라인)는 이미 docs/에 전체가 커버됨. 실행 계획만 Sprint 직전에 상세화하면 낭비 없이 의존성도 잡힘.

### 적용

- Phase N 완료 후 `/office-hours` + `brainstorming`으로 N+1 방향 재검증
- Sprint 시작 시 `superpowers:writing-plans`로 해당 Sprint만 상세화

---

## 실행 구조

```
Phase 0 (문서): API 명세 + 백엔드 셋업 가이드 (~3일)
  ↓
Sprint 1: 회의 → AI 요약 (FE+BE 관통) (2주)
  ↓
Sprint 2: Inbox + PARA + 액션 (2주)
  ↓
Sprint 3: RAG + 노트 (2주)
  ↓
Sprint 4: Auth + 배포 + QA (2주)
  ↓
MVP 완료 → 내부 팀 5명 배포
```

### 도구 활용 흐름 (매 기능 구현 시)

```
/office-hours (Sprint 전략)
  → brainstorming (기능 단위 설계)
  → writing-plans (파일/순서 결정)
  → [중간 규모+] 계획 리뷰 (별도 세션/서브에이전트에서 검증)
  → test-driven-development (테스트 먼저)
  → /simplify (코드 정리 — TDD 잔여물 제거)
  → /browse (FE 변경 시 즉시 브라우저 확인)
  → /qa + /ship (통합 검증 + 배포)
```

### 계획 리뷰 원칙 (Dual-Claude 변형)

계획을 작성하는 것과 검증하는 것은 다른 인지 모드. 같은 세션에서 계획+리뷰를 하면
자기가 쓴 계획의 문제를 잘 못 찾음. **분리된 컨텍스트**에서 리뷰해야 함.

| 작업 규모 | 계획 리뷰 방법 |
|-----------|--------------|
| 대규모 (새 Sprint, 아키텍처 변경) | `/autoplan` (CEO+Design+Eng 3중 리뷰) |
| 중규모 (새 기능, 새 도메인) | `writing-plans` 후 **별도 서브에이전트**에서 "스태프 엔지니어로서 이 계획을 리뷰해줘" |
| 소규모 (버그 수정, 단순 변경) | 리뷰 생략 가능 — brainstorming → TDD 직행 |

> 출처: Boris Cherny (Dual-Claude Plan Review) — "가장 큰 실수는 Claude가 계획 없이 바로 코딩하게 하는 것."
> 우리 환경에서는 gstack `/autoplan`과 서브에이전트 리뷰가 이 역할을 대신함.

### 모델 전환 전략

| 작업 유형 | 모델 | 이유 |
|-----------|------|------|
| 아키텍처 결정, 새 기능, 복잡한 디버깅 | Opus | 교정 비용 제거 — 한 번에 맞추는 게 총 시간 더 적음 |
| Plan Mode 계획 작성, 코드 리뷰 | Opus | 깊은 추론 필요 |
| 단순 수정, 문서 작성, 커밋/PR | Sonnet | 빠른 속도로 충분 |
| 파일 탐색, 간단한 질문 | Haiku | 최소 비용 |

> 출처: Boris Cherny — "느리지만 교정 비용이 없어서 결국 더 빠르다."
> 빠른 모델로 생성→에러 수정 반복보다, 느린 모델로 한 번에 맞추는 게 총 시간이 적음.

### Simplify 단계 (TDD 후 코드 정리)

TDD로 "테스트 통과"에 집중하면 불필요한 추상화, 중복 로직, 과도한 타입이 쌓인다.
구현 완료 후, PR 전에 별도 subagent(`/simplify`)로 코드를 정리한다.

```
TDD 완료 → /simplify 실행
  → 불필요한 useCallback/useMemo 제거
  → 중복 에러 핸들링 합침
  → 삭제 가능한 줄 삭제
  → 총 코드량 5~15% 감소
```

> 출처: Boris Cherny spec→draft→simplify→verify 파이프라인.
> "검증 루프를 주면 최종 결과물의 품질이 2~3배 올라간다."

### 개발 중 브라우저 테스트

Sprint 말 /qa만으로는 UI 버그가 누적된다. FE 컴포넌트 완성 시마다 `/browse`로 즉시 확인.

```
FE 컴포넌트 구현 → /browse로 즉시 확인 (개발 중, 수시)
Sprint 말 → /qa로 통합 QA (전체 플로우)
```

### MCP 컨텍스트 관리

MCP를 항상 전부 로드하면 컨텍스트 윈도우를 낭비한다.

| 세션 유형 | 활성 MCP | 비활성 |
|-----------|---------|--------|
| 코딩 세션 | GitHub만 | pencil, 기타 |
| 디자인 세션 | pencil + GitHub | 기타 |
| 디버깅 세션 | GitHub + Sentry(추후) | pencil |

> 출처: Affaan Mustafa — "MCP를 한꺼번에 다 켜면 200K 윈도우가 70K로 줄어든다."

### 안전 가드레일 (/careful + /freeze + /investigate)

에이전트에게 속도만 주고 브레이크를 안 주면 사고난다.

| 스킬 | 용도 | 시점 |
|------|------|------|
| `/careful` | 파괴적 명령 전 경고 (`rm -rf`, `DROP TABLE`, `force-push`) | 민감한 작업 시 |
| `/freeze` | 특정 디렉토리 외 수정 금지 | 디버깅 시 — 관련 없는 코드 수정 방지 |
| `/investigate` | 읽기만 하면서 원인 분석, 수정 제안 후 승인 | STT/Claude 파이프라인 디버깅 |

**특히 중요한 시나리오:**
```
STT 파이프라인 간헐적 에러 → /investigate
  → [Freeze] backend/meetings/ 이외 수정 금지
  → [분석] Whisper API timeout 미처리 발견
  → [제안] tenacity 재시도 + 동적 timeout
  → 사용자 승인 후 수정 적용
```

Claude가 버그 원인과 무관한 코드를 "고쳐놓는" 건 흔한 문제. `/freeze`가 이를 방지.

### lessons.md 적극 활용

`.ai/project/lessons.md`를 빈 템플릿으로 두지 않고 적극 기록한다.

- **기록 시점:** 실수 발생, 예상치 못한 동작, 삽질 종료 시
- **승격 기준:** 동일 패턴 3회 반복 → `.ai/stacks/` 규칙으로 승격
- **Sprint 회고:** 매 Sprint 말 `/retro` 실행 시 lessons.md 업데이트

> 출처: Boris Cherny — "실수할 때마다 CLAUDE.md를 업데이트해서 다시는 그 실수를 하지 마."
> ETH Zürich 연구: 개발자가 작성한 컨텍스트 파일은 AI 자동 생성보다 성공률 4% 향상.

---

## 리스크와 대응

| 리스크 | 대응 |
|--------|------|
| Sprint 1에서 BE 스캐폴딩이 예상보다 오래 걸림 | Phase 0에서 backend-scaffolding.md를 먼저 작성하여 의사결정 선행 |
| FE↔BE API 불일치 | Phase 0에서 endpoints.md 확정, FE mock API와 1:1 대조 |
| Sprint 전환 시 품질 하락 | 매 Sprint 말 /qa 실행, Health score 8+ 미달 시 Sprint 연장 |
| Whisper/Claude API 비용 초과 | Sprint 1에서 실제 비용 측정 후 Semantic Cache 도입 시점 앞당김 |
| TDD 코드 품질 저하 | /simplify 단계 필수 적용 — PR 전 코드 정리 |
| UI 버그 누적 | FE 변경마다 /browse 즉시 확인, Sprint 말 /qa는 통합용 |

---

## 참조

- PRD Sprint 분해: `docs/requirements/prd.md` §5
- API 명세 초안: `~/.gstack/projects/kairos/woosung-main-design-20260331-215834.md`
- RAG 파이프라인 설계: `docs/architecture/rag-pipeline.md`
- 고급 워크플로우 패턴 원본: Boris Cherny(VentureBeat, InfoQ), Garry Tan(gstack), Affaan Mustafa(Anthropic 해커톤)
