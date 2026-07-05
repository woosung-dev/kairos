# 팀 협업 전수 점검 스프린트 — 체크리스트

> plan.md 의 실행 체크리스트. 완료 시 체크. 2026-07-05 시작.

## Phase 0 — 환경 기동
- [x] 작업 브랜치 `sprint/team-collab-audit` 생성
- [x] backend/.env CORS_ORIGINS 에 :3003 포함 확인
- [x] frontend/.env.local QA_LOCAL_* 계정 존재 확인
- [x] BE 기동 (:8000, --reload 금지) + /api/v1/ready 200
- [x] FE 기동 (:3003) + 렌더 확인
- [x] d@e.com / a@e.com 로그인 가능 확인 (team.setup 로그인 성공)

## Phase 1 — 자동화 회귀 베이스라인
- [x] BE pytest 핵심 도메인 green (125 pass)
- [x] BE pytest 전체 green (622 pass)
- [x] FE 단위 테스트 green (71 pass)
- [x] 팀 e2e T1~T18 green (27 pass, 8.2m)

## Phase 2 — 수동 멀티유저 dogfooding (8 시나리오)
- [x] S1 풀 워크프로세스 + S1b danger zone UI 삭제 (스크린샷 9장)
- [x] S2 동시 편집 반영 (S1/S3 스윕에서 owner 변경→member 즉시 반영 확인)
- [x] S3 visibility 전환 (목록 제거 + 상세는 목록 리다이렉트 — 존재 은닉 정합)
- [x] S4 viewer 강등 UI 게이팅 (사이드바 write 항목 제거 확인)
- [x] S5 무효 초대/빈 상태/로딩 (스크린샷)
- [x] S6 반응형 360px × 라이트/다크 (4탭·danger zone·invite 페이지 정상)
- [x] S7 RAG 팀 컨텍스트 (T5/T15 e2e 커버로 갈음 — 인용·private 미누수)
- [x] S8 로드 시간 기록 (dev: dashboard 4.4s/settings 4.9s/projects 2.7s/notes 3.4s)

## Phase 3 — 기능 갭
- [x] 3a. dead code `add_member(email)` 제거 + CONTEXT.md 드리프트 정정 (PR-1)
- [x] 3b. default_project_visibility 연결: alembic + accept 복사 + create 적용 + 테스트 (PR-2)
- [x] 3c. 워크스페이스 삭제: BE DELETE + cascade + FE danger zone + 테스트 (PR-3)

## Phase 4 — 성능 6건 (PR-4)
- [x] 측정: SSE 커넥션 점유 결정적 회귀 테스트(red-green) + rag.timing 로그
- [x] ① RAG SSE 스트리밍 전 commit (스트리밍 중 checkedout 1→0)
- [x] ② 멤버 목록 N+1 → 단일 JOIN
- [x] ③ AI client 모듈 싱글턴 (ctor identity 캐시)
- [x] ④ refetchOnWindowFocus 전역 false
- [x] ⑤ pool env 설정화 (기본 유지 — ① 이 주 원인 제거, 상향은 Neon 한도 확인 후)
- [x] ⑥ R2 공유 client + 싱글턴 + main lifespan close
- [x] 백로그 갱신 (PERF-5/9/tiptap/PARALLEL-API 종결 + 신규 2건 RESOLVED 기록)

## Phase 5 — 디자인 fix (PR-5)
- [x] 에러 상태 2건 + 재시도 버튼
- [x] 초대 페이지 네트워크 에러 분기 분리 + 재시도
- [x] aria-label 3건 + Select 의미론 전환(DropdownMenu→Select)
- [x] 색 토큰 드리프트 → var(--error)/var(--success)/destructive
- [x] 폰트 토큰 우회 → var(--font-mono)/var(--font-display)
- [x] role raw 노출 라벨 매핑 (invite 페이지·초대 목록 뱃지·Select 트리거)
- [x] 스크린샷 검증 20장 (scratchpad/dogfood)

## Phase 6 — 마감
- [x] QA 발견 버그 즉시 수정 (Select raw 노출·을(를) 문구·team.setup 초대 누적 90→1) — 별도 PR-6 큐 없음
- [x] 전체 회귀 (BE 632 pass · FE 71+build · 팀 e2e T1~T19 29/29 pass 8.1m)
- [x] codex cross-review (P1 3/P2 4 — 수용 3건 반영: item_promotion_audit cascade 누락 적발·완전성 테스트·권한표면 focus refetch. 반박 4건 근거 기록)
- [x] Stage 2 제안 문서화 (stage2-proposals.md) + REFACTORING-BACKLOG 갱신
- [ ] PR 커밋/푸쉬 (각각 사용자 승인)
