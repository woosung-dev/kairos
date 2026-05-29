<!-- QA 정검 → Fix 플레이북 — Sprint 28b/28c 에서 도출한 프로젝트 무관 재사용 절차 -->

# QA 정검 → Fix 플레이북 (재사용용)

> Sprint 28b(정검/발견) + 28c(수정/배포)에서 검증된 절차. 다른 프로젝트에도 그대로 적용 가능하도록 원칙·단계·도구를 분리했다. Kairos 는 worked example.

---

## 0. 5대 철학 (이게 핵심)

1. **Evidence over vibes** — 모든 발견은 `file:line` + 재현(라이브 or 테스트)으로 뒷받침. "그래 보인다"는 발견이 아니다.
2. **Adversarial calibration** — 1차 발견은 과대/오진이 섞인다. 독립 평가자(빈 컨텍스트 LLM·다른 모델)로 **반증(refute)** 을 강제 → false positive 를 걸러야 release-grade.
3. **2-channel 격리** — 파괴적/동시성/만료 검증은 **격리 DB(TestContainers)** 에서 결정적으로, 시각/플로우는 **운영에 최소쓰기** 라이브로. 프로덕션 오염 0.
4. **Bug fix ≠ Design decision** — 색 팔레트·브랜드·카피 통일 같은 건 "버그"가 아니라 "결정". 임의로 바꾸지 말고 분리해 owner 에게.
5. **Assumption 도 검증** — "이렇게 고치면 됨"이라는 spec 의 전제부터 코드로 확인. (예: "seed 가 claims 를 안 읽음" → 실제론 이미 읽고 있었고 원인은 Clerk 토큰 설정이었음.)

---

## Phase 1 — 정검 (Audit / Discovery)

목표: **검증된 버그 백로그**(우선순위·근거·재현 포함) 생성. 코드는 안 고친다.

1. **범위 정의** — 직전 정검이 놓친 사각지대를 명시(예: 시각·UX 품질 / 미실행 플로우 / RBAC 엣지·동시성 / 데이터 상태). "전부"가 아니라 "지난번 안 본 것".
2. **다축 발견 (fan-out)**:
   - 라이브: 헤드리스 브라우저(MCP Playwright)로 라우트 × {light·dark·모바일·태블릿} 매트릭스 스샷 + 실제 기능 플로우 실행 + 멀티 계정 RBAC.
   - 정적: N-lens Workflow(시각/접근성/상태/다크/반응형/gating 등 렌즈별 1 에이전트) → confirmed/refuted 분류.
   - 결정적: 동시성·만료·캐시·페이지네이션·IDOR 은 격리 DB 통합테스트.
3. **Evaluator 패널 (필수)** — 빈 컨텍스트 LLM ×2 + 타 모델(codex 등)로 4축 + 헤드라인 adversarial 반증. **세 평가자가 수렴하는 보정점**만 채택. (28b 에서 대비율 오기·"silent fail" 오진·a11y 클러스터 과대 등 5건 보정 + 미탐 contract 버그 2건 추가 발굴.)
4. **심각도 보정** — P0~P3 + nit. 각 항목에 `상태`(신규/확정/정적/관찰) + 최소 1평가자의 `file:line` 재현. **refuted(버그 아님)도 명시 기록** — 다음 세션 재발견 방지.
5. **산출물** — `report.md`(판정·요약), `bugs.md`(백로그 + `## FIX 적용 현황` 표 + `## 미커버` 범위 한계), `evidence.md`, `screenshots/`, **다음 세션 프롬프트**(같은 깊이로 이어가도록).

## Phase 2 — Fix 실행

목표: 백로그를 **재발견이 아니라** 근거대로 수정·배포.

1. **현재 상태 재검증** — 직전 PR 머지로 **line number 가 이동**한다. 고치기 전 각 파일 **재grep**. (Plan 모드면 Explore 에이전트 3개 병렬로 touch point 전수 확인.)
2. **결정 분리** — 설계종속 항목은 착수 전 `AskUserQuestion` 으로 lock-in(권고안 first). 스코프가 고정돼야 한다.
3. **위험 분류 → 라우팅** — Lite(≤3파일·DB/API/인증 무관) / Standard / Heavy(결제·보안·인증·스키마·외부API). 애매하면 한 단계 위로.
4. **Atomic commit** — fix 1건 = 1 commit(semantic + `Co-Authored-By`). FE polish 묶음 / BE 보안 분리 → 별도 PR.
5. **인접 동종 이슈도 함께** — QA가 1곳만 짚어도 같은 패턴이 N곳이면 전수 수정(예: ⌘K 깨짐 2→4곳, visibility 배지 detail→detail+dashboard).
6. **검증 증거 표준** (완료 주장 = 증거):
   - FE: 라이브 스샷 + `console.error 0`. **단정 가능한 건 computed-style/accessibility-tree 로** (스샷보다 객관적 — 예 `getComputedStyle(kbd).fontFamily`, `button[aria-label].disabled`).
   - BE: pytest 요약 + (스키마 변경 시) alembic dry-run. 무변경이면 "N/A" 명시.
   - 통합테스트로 **정적 단정 → 실증** 전환(예: IDOR "정적 갭" → cross-ws mutation 차단 테스트).
7. **CI 게이트 로컬 재현** — CI 가 막히면(결제한도 등) `.github/workflows` 잡을 로컬에서 그대로 재현(backend pytest / vitest / build+typecheck / e2e public-only) → green 후 `--admin` 머지.
8. **Adversarial self-review** — 외부 리뷰어 불가 시 직접: 변경 함수의 **전 호출부 grep**(시그니처 누락 = 런타임 TypeError) + 위험 경로 trace(예: promote 의 `target_workspace_id` 가 복제 row 의 workspace_id 와 일치 → silent no-op 아님 확인).
9. **Atomic doc update** — 코드 PR 마다 canonical doc 1개 동반(`bugs.md` FIX 현황 등).
10. **Scope discipline** — 보고된 것 + 인접 동종만. 디자인 시스템 결정(팔레트/타이포 스케일)·대형 리팩토링은 별도(이번 세션의 잔여 P3 처럼).

---

## 재사용 체크리스트 (복붙용)

```
[ ] 정검 범위 = 직전 정검 사각지대만 명시
[ ] 라이브(브라우저 매트릭스) + 정적(N-lens) + 결정적(격리DB) 3축
[ ] Evaluator 패널로 반증 → 수렴 보정점만 채택, refuted 도 기록
[ ] report/bugs(+FIX현황/미커버)/evidence/screenshots/다음세션프롬프트
[ ] (fix) 착수 전 재grep — line 이동 가정
[ ] 설계종속 = AskUserQuestion 으로 결정 lock-in
[ ] 위험분류(Lite/Standard/Heavy) → 라우팅
[ ] atomic commit + 인접 동종 전수 + canonical doc 동반
[ ] 검증 = computed-style/a11y-tree/통합테스트 (객관) + console.error 0
[ ] CI 막히면 로컬 게이트 재현 후 --admin
[ ] self-review: 전 호출부 grep + 위험경로 trace
[ ] 디자인/브랜드/대형리팩토링은 분리 (bug ≠ decision)
```

## 도구 매핑 (Kairos 기준 — 타 프로젝트는 등가물로)

| 역할 | 도구 |
|---|---|
| 라이브 브라우저 | MCP Playwright (navigate/snapshot/evaluate/screenshot) |
| 정적 fan-out | Workflow(N-lens) / Explore 에이전트 |
| 결정적 테스트 | pytest + TestContainers (운영 무오염) |
| 독립 평가 | 빈 컨텍스트 LLM ×2 + codex/agy |
| 객관 검증 | `browser_evaluate`(computed style), `browser_snapshot`(a11y tree) |
| 진행 추적 | TaskCreate/TaskUpdate |
