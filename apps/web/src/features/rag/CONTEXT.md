<!-- rag 도메인 (FE) — AI 검색 답변 + SSE 스트리밍 클라이언트 -->

# features/rag CONTEXT (FE)

> 상위: `/apps/web/src/CONTEXT.md` (있다면) · 백엔드 도메인 헌법: `apps/api/src/rag/CONTEXT.md`.

---

## 1. 책임

- 백엔드 `POST /api/v1/workspaces/{wid}/rag/ask` SSE 호출 + 토큰 스트림 누적
- AI 검색 패널(오버레이) UI 상태 (질문 입력 / 답변 표시 / 출처 목록 / 에러)
- 검색 범위(scope) 선택 — workspace / project / source-level

---

## 2. 카피 정책 (Sprint 14 T-4 lock-in)

**사용자 노출 카피에서 "RAG" 약어 사용 금지.**

- 노출 텍스트(JSX text node / `label` / `placeholder` / `aria-label` / 사용자 보이는 에러 메시지) — "RAG" → "AI 검색"
- 코드 식별자(폴더 `rag/`, `RagService`, `useRagStream` 등) — 유지 (개발자 가독성)
- 개발자 주석 / docstring — 유지 (도메인 용어 가독성)

**근거**: Multi-Agent QA(Casual 페르소나) 결과 용어 해독률 37.5%. "RAG"는 일반 사용자에게 비식별 약어. AI는 도메인 외부에서도 보편적으로 통용되며 검색 의도를 직관적으로 전달.

---

## 3. 책임 외

- 검색/생성 알고리즘 자체 (백엔드 `rag/service.py` 책임)
- 권한 검증 (백엔드 `rag/pipeline_service.py` 책임 — ADR-014 옵션 A)
