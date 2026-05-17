# Power User Report — Sprint 18 → 19 Multi-Agent QA

| 항목 | 값 |
|---|---|
| 검증 시각 | 2026-05-17 KST |
| 페르소나 | Power (smoke) — 파워 유저 |
| 환경 | local (FE :3000 + BE :8000) — Sentinel A 로그인 |
| Cap | 60분 |
| 자동화 | Playwright MCP + Clerk session token → fetch |

## 1. Executive Summary
| 항목 | 결과 |
|---|---|
| 총 결함 카운트 | **7 (Critical 0, High 3, Medium 3, Low 1)** |
| Persona Health Score | **3.4/10** = max(0, 10 - (0×3 + 3×1.5 + 3×0.5 + 1×0.1)) = 10 - 6.1 → 3.9. Cmd+K 시각 단축키 안내 vs 실제 동작 gap 가중 → **3.4** |
| 가장 큰 발견 | Cmd+K command palette UI는 풍부 (검색·이동·생성 3 섹션) 단축키 표 (G I/G P/G N/G S/C) 노출하지만 **실제 시퀀스 단축키 핸들러 미연결** + palette 검색 입력은 필터링 안 됨. Power 사용자에게 "안내는 있으나 실행은 안 됨" 좌절. |

## 2. 결함 상세

| # | 영역 | 결함 | Severity | Confidence | 재현 | 권고 |
|---|---|---|---|---|---|---|
| H-1 | 단축키 | Cmd+K palette 안에 "이동 G I/G P/G N/G S, 생성 C" 단축키 표 노출. **실제 시퀀스 키 미동작**. dashboard에서 G→I 눌러도 /inbox 이동 안 함. C 눌러도 /new 이동 안 함. | High | H | dashboard → Meta+K → Esc → g → i (1초) → URL 미변경 | `useHotkeys('g i', ...)` 또는 `mousetrap` 시퀀스 라이브러리 적용 |
| H-2 | 벌크 작업 | Inbox 16건 — checkbox 0개, "전체 선택" 버튼 없음, 일괄 confirm/dismiss 버튼 없음. Power 사용자가 16건 일일 처리해야 함. | High | H | `/inbox` → `document.querySelectorAll('input[type=checkbox]').length === 0` | 각 카드 좌측 checkbox + 헤더에 "전체 선택" + footer fixed 벌크 액션 바 |
| H-3 | Export UI 누락 | BE API에 `GET /workspaces/{ws}/meetings/{id}/export` + `/notes/{id}/export` 2 endpoint 존재. UI에는 **export 버튼 0개** (notes, dashboard, inbox 어느 곳에도). | High | H | `/notes` → "내보내/export/다운로드" 키워드 검색 0건 vs OpenAPI에 `export` 2 endpoint | note/meeting detail에 "내보내기" 버튼 + 드롭다운 (PDF/Markdown) |
| M-1 | a11y / Command Palette | Cmd+K modal에 `role="dialog"` / `aria-label` 미설정. 스크린리더가 modal 컨텍스트 파악 못함. Esc 닫기는 동작 ✅. | Medium | H | Meta+K → `document.querySelector('.fixed.inset-0.z-50').getAttribute('role')` → null | `<div role="dialog" aria-label="명령 팔레트" aria-modal="true">` 패치 |
| M-2 | Command Palette / 검색 | palette input에 "Inbox" 입력해도 항목 리스트 필터링 안 됨. 단순히 정적 메뉴만 표시. | Medium | H | Meta+K → "Inbox" 타이핑 → 5개 이동/생성 항목 그대로 노출 | `cmdk` lib `Command.Input` + `Command.Empty` 적용 |
| M-3 | API 디스커버리 | `/openapi.json` (root)는 404. `/api/v1/openapi.json` 만 동작 + `/api/v1/docs`도 200. Power 사용자가 root에서 API spec 찾기 어려움. | Medium | H | `curl /openapi.json` → 404 vs `curl /api/v1/openapi.json` → 200 | FastAPI root에서 `/openapi.json` redirect 또는 OpenAPI metadata에 명시 |
| L-1 | API / Quick Capture schema | `POST /meetings/capture` `transcriptText` (camelCase) — Python pyd v2 alias. min_length 50 강제. FE는 `text` 로 호출 가능성. | Low | M | `{"text": "..."}` → 422 vs `{"transcriptText": "..."}` → 202 | API doc에 명확한 예시 추가 |

## 3. 단축키 / 벌크 / Export / API 매트릭스

| 영역 | 시도 | 결과 | 비고 |
|---|---|---|---|
| **Cmd+K (palette open)** | Meta+K | ✅ 동작 (modal open, role 누락) | Casual H-3 정정: palette는 동작했음 |
| **Esc (palette close)** | Esc | ✅ 동작 | |
| **G I (Inbox 이동)** | g → i (1초 내) | ❌ 미동작 | UI 표는 있음, 핸들러 없음 |
| **G P / G N / G S** | g → p/n/s | ❌ 미동작 | 동일 |
| **C (콘텐츠 추가)** | c | ❌ 미동작 | 동일 |
| **? (도움말 / AI 검색)** | ? | ❌ 미동작 | palette 안 "AI 검색 ?" 라벨 있음 |
| **벌크 선택** | `/inbox` 16건 | ❌ checkbox 0 | 16건 일일 클릭만 가능 |
| **export UI** | notes/meetings | ❌ 0 버튼 | 단 API endpoint 2개 존재 |
| **API capture** | POST /meetings/capture (camelCase) | ✅ 202 Accepted | id `0024fd0c-d124-4c7f-b335-feb1b6a28e0d` 생성 |
| **API workspaces list** | GET /workspaces | ✅ 200 + 3 ws | Sentinel A 시드 정상 표시 |
| **Cross-tenant IDOR check** | GET /workspaces/{sentinel_B_id} | ✅ 403 "워크스페이스 멤버가 아닙니다" | **BUG-C01 fix (19eb363) 정상 동작** |
| **OpenAPI 디스커버리** | /api/v1/openapi.json | ✅ 200 (42 endpoints) | root /openapi.json은 404 |

## 4. 산출물
- 스크린샷
  - `power/cmdk-palette.png` (Cmd+K command palette 열린 상태)
- trace zip: Critical 0건 → 미생성
- API 검증 부가 메모:
  - `POST /workspaces/{id}/meetings/capture` 성공 시 reply `{"id", "status": "uploading", "message": "파이프라인이 시작되었습니다"}` — 비동기 처리 패턴 ✅
  - `transcriptText` 필드명 (camelCase via Pydantic alias) — Python 백엔드답지 않은 노출 → 외부 자동화 사용자 혼란
  - BUG-C01 fix는 cross-tenant 403 정상 동작 → 추가 회귀 발견 시 alarm
