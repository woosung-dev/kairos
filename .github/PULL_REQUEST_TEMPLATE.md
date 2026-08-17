## 무엇을 · 왜

<!-- 1~3줄 -->

## Atomic Update (AGENTS.md §5)

갱신한 canonical doc **1개**를 적는다. 해당 없으면 Lite 예외 사유를 적는다.

- [ ] canonical doc: `...`
- [ ] 또는 **no doc impact** — 사유: <!-- typo / 3파일 이하 버그fix / 외부 시그니처·용어 무변경 리팩토링 -->

<details><summary>라우팅 표</summary>

| 변경 유형 | canonical doc |
|---|---|
| 엔티티/모델 (`models.py`) | `docs/architecture/erd.md` |
| API endpoint (`router.py`) | `contracts/` 재생성 (`mise run contracts`) + 도메인 `CONTEXT.md` |
| 도메인 경계·불변식 | `CONTEXT-MAP.md` |
| 파이프라인·아키텍처 | `docs/architecture/*.md` |
| 의사결정 (대형) | `docs/adr/NNN-*.md` |
| 부채·후속 작업 | `docs/REFACTORING-BACKLOG.md` |
| 개발 원칙 | `AGENTS.md` |

</details>

## 로컬 게이트

> 푸쉬 전 사전 확인. 최종 판정은 CI(`ci-required`)가 한다 — CI 가 red 면 아래 체크와 무관하게 차단이다.
> clean tree 에서 돌린다 (`contracts-check` 가 `git diff --exit-code` 라 더러운 트리에서 오탐한다).

- [ ] `mise run ci-local` 통과 (또는 CI green 으로 갈음)

```
<!-- 출력 요약 (pytest N passed / vitest / build / contracts drift 0) -->
```

## 검증 증거 (AGENTS.md §4)

해당하는 것만 체크한다.

- [ ] **BE 변경** — pytest 결과 요약 + `alembic upgrade` dry-run 출력
- [ ] **FE 변경** — 스크린샷 1장 + `console.error` **0건** (앱 집계: 앱 코드 `console.error` + `pageerror` + 앱 BE `/api/v1/*` 4xx/5xx)
- [ ] **API 시그니처 변경** — `mise run contracts-check` + Playwright smoke **양쪽** 통과 (한쪽만 통과 시 차단)
- [ ] **RBAC/visibility 변경** — team e2e (`--project=team --workers=1`) 통과

## 배포 영향

- [ ] 마이그레이션 포함 — 컬럼 삭제/타입 변경이면 2단계 배포 여부 명시 (`docs/development/migrations.md`)
- [ ] `NEXT_PUBLIC_*` 변경 — 빌드타임 인라인이므로 **FE 이미지 재빌드 필요**
- [ ] 배포 전 `mise run deploy-preflight` 필요 (진행 중 회의 0 확인)
- [ ] 배포 영향 없음

## 롤백

<!-- 되돌리는 방법. 마이그레이션이 있으면 스키마는 되돌아가지 않는다는 점을 명시. -->

## 관련

<!-- ADR-NNN / BL-NNN / 이슈 -->
