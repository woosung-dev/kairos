# Sprint 17 QA-Fix Loop (2026-05-16)

> Sprint 17 QA 후속 — `/loop` 동적 모드로 `qa-fix` 통합 브랜치 + sub-branch 패턴 시도.

## 워크플로우

```
                   ┌────────────────────┐
                   │       main         │  ← 최종 stable
                   └─────────▲──────────┘
                             │ PR (batched)
                   ┌─────────┴──────────┐
                   │      qa-fix        │  ← long-lived integration
                   └──────▲────▲────▲───┘
                          │    │    │  PR (sub-branch → qa-fix, auto-merge on CI pass)
            ┌─────────────┘    │    └────────────┐
            │                  │                 │
    qa-fix-c1-record-e2e  qa-fix-loop-...   qa-fix-...
```

장점:
- **main 보호**: 다수 작은 PR 이 main 을 흔들지 않음
- **CI 통과 자동 머지**: `gh pr merge --auto --squash` 또는 GitHub 자동 머지
- **루프 진행**: 작업 단위마다 sub-branch → 자동 머지 → 다음 작업 즉시 시작

단점:
- qa-fix 가 main 보다 뒤처질 수 있음 (main 신규 머지 PR 발생 시 sync 필요)
- 최종 qa-fix → main PR 은 다수 commit 누적 → 대형 PR (squash 또는 stack 권장)

## 본 세션 (2026-05-16) 진행 사항

### 직전 세션 (2026-05-15) 카리오버

| BL/ISSUE | 상태 | PR |
|---|---|---|
| ISSUE-005 /notes mock | merged | #40 |
| ISSUE-008 /invite 500 | merged | #40 |
| ISSUE-009 /projects[id] hooks | merged | #40 |
| BL-034 asyncpg pool | merged | #41 |
| BL-038 invite optimistic | merged | #42 |
| BL-039 member 403 UX | merged | #42 |
| BL-035 workspace switcher #N | merged | #43 |
| BL-037 Satoshi Fontshare | closed | #44 (user 거절) |

### 본 루프 (qa-fix 패턴 도입 후)

| 작업 | PR | base | 상태 |
|---|---|---|---|
| BL-036 perf indexes | #45 | main | OPEN (e2e pending) |
| ISSUE-040 RAG visibility filter | #46 | main | OPEN (CI fix push 후 재실행 중) |
| C.1 record state machine spec | #47 | **qa-fix** | **merged 자동** |
| 본 doc (loop progress) | #(생성됨) | **qa-fix** | pending |

### 잔여 (큐)

1. **BL-041 cache leak** — `find_similar_cache` 가 admin 캐시를 비-멤버 hit 시 leak. PR #46 머지 후 진행 (visibility filter 로직 재사용).
2. **ADR-014 backend regression test** — pytest 로 vector_search 의 visibility filter 검증. PR #46 머지 후 qa-fix sync.
3. **C.3b RAG private deep verification** — content seed + 임베딩 후 RAG hit/miss 검증 e2e.

## 헌법 정합 (atomic doc update §2)

본 PR (qa-fix sub-branch) 은 docs/dev-log/ 만 추가 (코드 변경 0). atomic update matrix 요건 없음.

## 다음 단계

PR #45 + #46 머지 → qa-fix 가 main sync → BL-041 + ADR-014 regression test sub-branch 시작.

루프는 `/loop` 동적 모드 — 사용자 명시 중단 또는 모든 잔여 작업 완료 시 종료.
