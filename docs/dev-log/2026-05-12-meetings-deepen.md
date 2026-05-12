# Deepen-modules audit — backend/src/meetings

> 날짜: 2026-05-12
> 진행: Sprint 10 세션

---

## Phase 1 결과

| 모듈 | LOC | Public Surface | 분류 | 비고 |
|------|-----|---------------|------|------|
| `pipeline_service.py` | 360 | 2 메서드 | **Deep** ✅ | 단순 인터페이스, 풍부한 구현 |
| `service.py` | 194 | 6 메서드 | **Moderate** | CRUD + 변환 로직 혼재 |
| `repository.py` | 125 | N 메서드 | **Moderate-Deep** | DB 접근 전담 ✅ |
| `router.py` | 109 | 6 엔드포인트 | **Thin** (정상) | HTTP 전달자 |
| `dependencies.py` | 40 | 3 함수 | **Thin** (정상) | Depends 조립 |

**I-1 검증:** `pipeline_service.py`가 `AsyncSession`을 import하지만 `async_sessionmaker[AsyncSession]` 타입 힌트 전용 — 실제 세션 보유 없음. **위반 없음.**

---

## Phase 2 결과

| 패턴 | 심각도 | 파일 | Risk |
|------|--------|------|------|
| process_meeting / capture_text 중복 | 🟡 | `pipeline_service.py` | 유지보수 부담, LOC 낭비 |
| D-9 status commit 8회 | 🟡 | `pipeline_service.py` | I-2 원칙 불일치 (허용 결정) |
| co-change 집중 (pipeline_service 8회) | 관찰 | `pipeline_service.py` | 정상 — 파이프라인 변경이 단일 파일에 집중 |

---

## Phase 3 결정 로그

- **후보 A (D-9 헌법 예외 명시):** ★★★★★ 승인
  - CONTEXT-MAP.md I-2에 예외 조항 + 부분 커밋 상태 모델 명시
  - D-9 항목을 "허용 결정 + Sprint 11+ 개선 BL-001"로 업데이트
  
- **후보 B (중복 제거):** ★★★☆☆ 승인 → Sprint 11+ BL-002 등재
  - `_analyze_and_store` private 메서드 추출 방향 합의
  - 현재 sprint에서 즉시 수정 안 함 (파이프라인 핵심, test harness 보강 후)

---

## Phase 4 등재

- **BL-001** — meetings 파이프라인 status commit 단일화 (★★★☆☆, Sprint 11+)
- **BL-002** — process_meeting / capture_text 공통 로직 추출 (★★★☆☆, Sprint 11+, BL-001과 묶음)

→ `docs/REFACTORING-BACKLOG.md`

---

## Sprint 권고

BL-001 + BL-002는 Sprint 11+에 묶음 처리. F4 외부 인터뷰 완료 후 제품 안정화가 우선.

## LESSON 후보

`LESSON-001 후보 (deepen-modules 2026-05-12): pipeline_service.py 처럼 두 진입점(파일 업로드 / 텍스트 입력)이 같은 분석 단계를 공유할 때, STT/입력 전후를 명확히 분리하는 _analyze private 메서드 패턴을 처음부터 적용할 것.`

## 다음 audit 권고

- `backend/src/rag` — RAG 6-Layer 구조 (RagPipelineService 도입 후 레이어 정합)
- `backend/src/actions` — orphan ActionItem D-10 해소 시점
