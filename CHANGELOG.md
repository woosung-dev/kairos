# Changelog

All notable changes to Kairos are documented here.

---

## [0.1.1.0] - 2026-05-15

### Fixed
- **`/notes` 메모 저장 BE 연결** (ISSUE-005) — `quick-memo.tsx` 가 `MOCK_PROJECTS` / `INITIAL_MEMOS` 하드코딩 + `setMemos()` 로컬 state-only "save" 였음. 저장 후 reload 시 노트 사라지던 P1 회귀 해결. `useNotes` / `useCreateNote` / `useProjects` 사용 + tiptap 호환 doc 변환.
- **`/invite/[code]` HTTP 500** (ISSUE-008) — `QueryProvider` 가 `(app)/layout.tsx` 안에만 위치해 (app) 그룹 외부 라우트 (/invite, /sign-in 등) 에서 React Query hook 호출 시 "No QueryClient set" crash. `QueryProvider` + `Toaster` 를 root layout 으로 이동.
- **`/projects/[id]` ErrorBoundary 발동** (ISSUE-009) — `ProjectDashboard` 가 `projectLoading` early return 한 뒤 `useRecentItems` 호출. React hooks 규칙 위반 ("Rendered more hooks than during the previous render"). `useRecentItems` 와 데이터 풀기를 early return 이전으로 이동.

### Documentation
- `docs/dev-log/sprints/2026-05-15-sprint17-qa-verification.md` 신설 — Sprint 17 Exhaustive QA 결과 + 성공 조건 C1~C6 표 + Fix 결과.
- `docs/REFACTORING-BACKLOG.md` — BL-034 ~ BL-039 등재 (asyncpg pool · workspace 중복 · sidebar perf · Satoshi FOIT · invite cache · settings 403 UX).
- `docs/TODO.md` — Sprint 17 Completed + Next Actions.

---

## [0.1.0.2] - 2026-05-12

### Refactored
- `MeetingPipelineService._analyze_and_store` private 메서드 추출 — `process_meeting`과 `capture_text`의 공통 분석 블록(요약→액션→Inbox→자동확정→임베딩→완료) 통합
- `pipeline_service.py` 361 → 261 LOC (28% 감소)

### Tests
- `capture_text` 경로 테스트 추가 — 텍스트 캡처 파이프라인 골든패스 검증 (STT 미호출, 분석→완료 상태 전이)

---

## [0.1.0.1] - 2026-05-12

### Added
- E2E Playwright 골든패스 2개: 인증 리다이렉트 테스트(`auth.spec.ts`) + 미팅 업로드→STT→요약 완료 흐름 테스트(`meeting-upload.spec.ts`)
- 한국어 TTS 오디오 fixture (`test.m4a`, 78KB) — Playwright 파일 업로드 E2E 테스트용
- `.github/workflows/test.yml` E2E 잡 활성화 방법 가이드 주석 추가

### Fixed
- `useMeetingDetail` 훅 폴링 로직 개선: 네트워크 오류 발생 시 폴링이 영구 중단되던 버그 수정 — 이제 완료/실패 상태에서만 폴링을 중단함

### Changed
- 미팅 상세 페이지(`meeting-detail.tsx`)가 STT 처리 중 상태 배지를 자동으로 업데이트하도록 개선 — `refetchInterval` 추가

---

## [0.1.0] - 2026-05-12

Initial baseline: Sprint 1~11 PR1 완료 상태 기준
