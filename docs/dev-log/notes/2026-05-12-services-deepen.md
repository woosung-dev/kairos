# Deepen-modules audit — services/ 도메인 (2026-05-12)
> Sprint 12 Round 2. co-change 분석 포함 재실행.

## Phase 1: Module Inventory

| 파일 | LOC | Public Surface | 분류 | 비고 |
|------|-----|----------------|------|------|
| transcription.py | 142 | 1 class, `transcribe()`, `download_audio()` | **DEEP** | ffmpeg, Whisper, 포맷 변환, 에러 복구 집중 |
| ai_processing.py | 107 | 1 class, 3 public methods | SHALLOW (adapter) | Gemini 호출 전담 — thin adapter |

services/ 도메인에 CONTEXT.md 없음 (외부 SDK adapter 레이어라 도메인 언어 없음).

## Phase 2: Locality & Co-change 분석

### co-change 횟수 (6개월)

| 파일 | 변경 횟수 |
|------|----------|
| ai_processing.py | 5회 |
| transcription.py | 3회 |

### co-change 클러스터 (cross-domain)

```
[feat: AI 파이프라인 — 액션 추출 + 프로젝트 연결 프롬프트 추가] => common, services
[feat: Claude → Gemini AI 모델 전환]                            => common, core, services
[fix: RAG 파이프라인 버그 2건 — SQL 캐스트 + Gemini 스트리밍]     => embeddings, services
```

→ `ai_processing.py` 5회 변경 중 3회가 `common/prompts.py` 와 동시 변경.

### 근본 원인 분석

`common/prompts.py`에 Gemini 응답 JSON 스키마가 프롬프트 텍스트 안에 문자열로만 존재.
`ai_processing.py`는 `parse_json_response(response.text)` 결과를 타입 검증 없이 반환.
`pipeline_service.py`는 `actions_data.get("actionItems", [])` 같은 문자열 키 접근에 의존.

**Silent failure scenario:**
1. `prompts.py`에서 `"key_decisions"` → `"decisions"` 로 리네임
2. Gemini 응답: `{"decisions": [...]}`
3. `parse_json_response()` 성공
4. `pipeline_service.py`의 `summary_data.get("key_decisions", [])` → `[]` (조용히 빈 값)
5. Meeting 저장됨, 에러 없음, 사용자는 결정사항이 없다고 봄

co-change 3회가 반복된 이유: 프롬프트 바꿀 때마다 키 이름 일치 여부를 수동 확인해온 패턴.

## Phase 3: Grilling Session 결정 로그

1차 세션 (코드 분석만):
- "공통 호출 패턴 추출" (BL-004 후보) → 사용자 거부 ("어려운것 같다, 다른 방안")
- 코드 직접 읽은 후 재분석: ai_processing.py는 thin adapter, 추출 불필요 결정

2차 세션 (CONTEXT.md + co-change 재분석):
- `ai_processing.py` ↔ `common/prompts.py` co-change 패턴 발견
- `common/prompts.py` 직접 읽어 implicit JSON schema 확인
- `pipeline_service.py` dict 키 접근 패턴 확인 (silent failure 위험)
- **새 BL-004 후보 제안: LLM 응답 계약 명시화** → 사용자 승인

## Phase 4: 등재 결과

- **BL-004** 등재 완료 (`docs/REFACTORING-BACKLOG.md`)
  - 영향 파일: `common/prompts.py` + `services/ai_processing.py`
  - 우선순위: ★★★☆☆ / Risk: 🟢

## 교훈 (LESSON 후보)

LESSON-001 후보 (2026-05-12): 코드 구조 분석만으로 "thin adapter" 결론 냈다가 co-change 분석에서 implicit contract 발견. LLM 응답을 untyped dict로 반환하는 패턴은 co-change 없이는 발견 어려움 — co-change 분석은 코드 inspection의 보완재.

## Sprint 권고

BL-003과 묶어서 처리 권고. 둘 다 서비스 레이어 안전성 (N+1 배치화 + 타입 검증) 방향.
