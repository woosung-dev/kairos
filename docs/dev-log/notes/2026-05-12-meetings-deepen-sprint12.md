# Deepen-modules audit — meetings/ 도메인 (2026-05-12, Sprint 12)
> Sprint 12 Round 3. BL-002 완료 직후 상태 점검. co-change 분석 포함.
> (기존 2026-05-12-meetings-deepen.md는 Sprint 10 audit. 본 파일은 Sprint 12 신규 점검.)

## Phase 1: Module Inventory

| 파일 | LOC | Public Surface | 분류 | 비고 |
|------|-----|----------------|------|------|
| pipeline_service.py | 261 | 1 class, `process_meeting()`, `capture_text()`, `_analyze_and_store()` | ORCHESTRATOR | BL-002 완료 — `_analyze_and_store` 추출됨 |
| service.py | 194 | 1 class, 5 public methods | SHALLOW (facade) | 순수 DTO 변환 + repo 위임 |
| repository.py | 125 | 1 class, 10+ methods | **DEEP** | 복잡 SQL, multi-table join |
| router.py | 109 | 6 route handlers | SHALLOW | HTTP adapter |
| models.py | 48 | 3 SQLModel tables | SCHEMA | — |
| schemas.py | 32 | 4 Pydantic DTOs | SCHEMA | — |
| dependencies.py | 40 | 3 factory functions | ASSEMBLY | DI 조립 |
| exceptions.py | 8 | 1 exception | SCHEMA | — |

meetings CONTEXT.md 확인. M-2, M-6 불변식 코드에서 검증됨.

## Phase 2: Locality & Co-change 분석

### co-change 횟수 (6개월)

| 파일 | 변경 횟수 |
|------|----------|
| pipeline_service.py | 9회 — 핫스팟 |
| dependencies.py | 7회 |
| router.py | 6회 |
| service.py | 5회 |
| models.py | 4회 |

### 주요 co-change 클러스터

1. `pipeline_service.py` + `dependencies.py` + `models.py` — BackgroundTask 세션 수명 버그 수정
2. `models.py` + `pipeline_service.py` + `router.py` + `schemas.py` + `service.py` — Sprint 8 Quick Capture 5파일 동시 변경
3. `dependencies.py` + `service.py` — export 기능 리뷰 반영
4. `router.py` + `service.py` — export API 신설
5. `dependencies.py` + `pipeline_service.py` — pipeline threshold 하드코딩 제거

### co-change 해석

- `pipeline_service.py` ↔ `dependencies.py` 반복 커플링 — DI 구조상 예상됨. pipeline 인터페이스 변경 시 dependencies.py의 factory도 수정 필요. 추가 BL 불필요.
- Sprint 8 5파일 동시 변경 — 새 입력 타입(capture_text) 추가 시 모든 레이어를 건드리는 패턴. BL-002 완료 후 향후 신규 입력 타입은 pipeline에만 `_intake_X` 추가 + router/schema만 신규 추가로 감소 예상.
- `service.py:export_meeting()` — `get_meeting_detail()` 재호출로 JSON 포맷 시 3쿼리 중복. 발견했으나 BL-001과 묶어 처리 결정.

## Phase 3: Grilling Session 결정 로그

- BL-001 (status commit 단일화): 이미 등재됨 (REFACTORING-BACKLOG.md). 재등재 불필요.
- export 중복 쿼리 후보: 사용자 skip 결정. BL-001과 묶어서 sprint 처리 예정.

## Phase 4: 등재 결과

- **신규 BL 없음** — meetings/ 도메인은 BL-001(미실행)로 충분히 커버됨.

## CONTEXT.md 검증

- M-2 (commit 5회) 코드 확인: `pipeline_service.py` 줄 71/86/90/215/222 ✅
- M-6 (임베딩 비차단) 코드 확인: `except Exception` 블록으로 임베딩 실패 시에도 `completed` ✅
- 문서 갱신 불필요.

## Sprint 권고

meetings/ 도메인 다음 작업 우선순위:
1. BL-001 (status commit 단일화) — ★★★☆☆, 단독 sprint
2. export 중복 쿼리 — BL-001 sprint 시 같이 처리 권고
