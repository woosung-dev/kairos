# Sprint 11 세션 시작 프롬프트

> 이 파일을 그대로 복사해서 다음 세션 첫 메시지로 붙여넣기.
> 작성일: 2026-05-12 | 참조: docs/TODO.md, docs/REFACTORING-BACKLOG.md

---

# Sprint 11 세션 — E2E 자동화 + 마이크 녹음 + meetings 리팩토링

## 세션 시작 전 Context Sync (CLAUDE.md §3 순서대로 읽을 것)
1. CONTEXT-MAP.md (헌법 — D-4/D-7~D-10 부채, BL-001/002 백로그)
2. AGENTS.md
3. DESIGN.md
4. backend/src/meetings/CONTEXT.md (BL-001/002 관련)
5. docs/TODO.md (현재 작업 상태)
6. docs/REFACTORING-BACKLOG.md (BL-001/002 상세)

---

## 워크플로우 진입점

docs/TODO.md 진행 결정 트리 기준:
- AD-35 Playwright E2E → "검증 자동화" → **Stage 5 (QA + DevEx)**
- 브라우저 마이크 녹음 → "새 기능" → **Stage 1~3 (brainstorming → plan → implement)**
- BL-001/002 리팩토링 → "기술 부채" → **Stage 4 (deepen-modules 후속)**

---

## Goal 1: AD-35 — Playwright E2E 자동화 suite 구축

### 현황
- Sprint 6 dogfooding에서 8 케이스 수동 통과
- Playwright E2E 환경은 ADR-008에서 스캐폴딩 완료 (test.yml + e2e 잡)
- 실제 테스트 코드 미작성 상태
- Clerk testing mode 계정 미생성 (GitHub E2E_* Secrets 미등록)

### 수행할 것
1. `/qa` Quick tier → 프로덕션 전체 앱 smoke test (Playwright MCP 사용)
   - 인증 → 워크스페이스 → 회의 업로드 → RAG → Source Viewer
   - [1] 클릭 → Source Viewer 풀콘텐츠 렌더 (ADR-008 전체 E2E)
2. V-T2: Playwright E2E 골든패스 2개 코드화
   - `e2e/auth.spec.ts` — 로그인 → 워크스페이스 접근
   - `e2e/meeting-upload.spec.ts` — 오디오 업로드 → status=completed
3. V-T4: schemathesis로 BE API 스키마 검증 (선택)
   - `pytest --co -q tests/` 로 현재 테스트 목록 확인 후 결정

### Generator-Evaluator
- Generator: Playwright E2E 코드 작성
- Evaluator: `/codex review` 8.5/10 합격
- TDD: 테스트 먼저 작성 → 통과 확인

### 완료 기준
- [ ] 실제 m4a 업로드 → STT → Inbox E2E Playwright 코드 (e2e/ 폴더)
- [ ] Source Viewer 풀콘텐츠 렌더 확인
- [ ] CI test.yml e2e 잡 활성화 (또는 활성화 조건 명시)

---

## Goal 2: 브라우저 마이크 직접 녹음 기능

### 현황
- 인터뷰이-01 피드백 2026-05-12: "음성 직접 녹음 기능이 없어 불편"
- `/new` 페이지: 오디오 업로드 탭 + 텍스트 입력 탭만 존재
- 신규 탭: "마이크 녹음" 추가 필요
- 브라우저 Web Audio API + MediaRecorder API 사용

### 수행할 것 (brainstorming 먼저)
1. `/office-hours` 또는 `superpowers:brainstorming` 으로 UX/구현 방향 확정
   - 녹음 → m4a/webm 변환 → 기존 `POST /upload/file` 프록시 활용 가능
   - 실시간 파형 시각화 여부 (DESIGN.md 확인)
2. TDD:
   - FE: `useRecording` 훅 단위 테스트 (mock MediaRecorder)
   - BE: 기존 `POST /upload/file` 엔드포인트 재활용 (추가 개발 최소)
3. 구현:
   - `frontend/src/features/upload/hooks.ts` — `useRecording` 훅 추가
   - `/new` 페이지 — "🎙️ 직접 녹음" 탭 추가

### Generator-Evaluator
- Generator: 브라우저 마이크 녹음 훅 + UI
- Evaluator: `/codex review` 8.5/10
- TDD: mock MediaRecorder로 훅 테스트 → 브라우저 실제 동작 QA

### 완료 기준
- [ ] 마이크 녹음 → 중지 → 파일 생성 → `POST /upload/file` 업로드
- [ ] 기존 E2E 파이프라인(STT → 요약 → Inbox) 동일하게 통과
- [ ] 인터뷰이-01 재확인용 스크린샷

---

## Goal 3: BL-001/002 — meetings pipeline 리팩토링 (선택)

### 현황 (docs/REFACTORING-BACKLOG.md)
- **BL-001**: status commit 단일화 → Sprint 11+ 백로그 (★★★☆☆)
- **BL-002**: process_meeting/capture_text 공통 로직 추출 (★★★☆☆)
- Goal 1/2 완료 후 시간 여유 있을 때 진행

### 수행할 것
1. BL-002 먼저: `_analyze_and_store` private 메서드 추출
   - TDD: 기존 test_pipeline.py 3 테스트 → PASS 유지 필수
   - 360 LOC → ~250 LOC 예상
2. BL-001 (선택): status progress 설계만 (코드 변경 없음, ADR 신규)

### 완료 기준
- [ ] `backend/tests/meetings/test_pipeline.py` 3 테스트 PASS 유지
- [ ] pipeline_service.py LOC 감소 확인
- [ ] `/codex review` 8.5/10

---

## Goal 4: 잔여 소형 docs (Sprint 11 마무리)

### 수행할 것
1. `docs/requirements/prd.md` — Sprint 6/7/8/9/10 phase 표 업데이트 (작음)
2. `docs/requirements/second-brain.md §8` — visibility "개인↔팀 경계" 해소 표기
3. F4 인터뷰이-02~05 섭외 준비 — interview-guide.md 기반 질문 시트 2차 정제

---

## 완료 기준

- [ ] AD-35 E2E: Playwright 코드 2개 + CI 잡 연동
- [ ] 브라우저 마이크 녹음: 실제 동작 확인 (QA)
- [ ] BL-002 (선택): test PASS + LOC 감소
- [ ] prd.md / second-brain.md §8 업데이트
- [ ] 모든 변경 `/ship` 완료

---

## 진행 원칙

- **Generator-Evaluator**: 각 코드/문서 변경 후 Codex CLI `/codex review` 명시 호출
- **TDD**: 코드 변경 시 테스트 먼저, 실패 확인 후 구현
- **워크플로우**: 새 기능(Goal 2)은 `/office-hours` → 플랜 → 구현 순서 준수
- **브라우저**: Playwright MCP 우선 사용 (GStack 헤드리스는 fallback)
- **Git Safety**: commit/push/deploy 단계별 사용자 승인

---

## 참고 파일

| 파일 | 용도 |
|------|------|
| `docs/REFACTORING-BACKLOG.md` | BL-001/002 상세 설계 |
| `backend/src/meetings/pipeline_service.py` | BL-002 대상 파일 |
| `backend/tests/meetings/test_pipeline.py` | BL-002 기준 테스트 |
| `frontend/src/app/(app)/new/page.tsx` | 마이크 녹음 탭 추가 위치 |
| `frontend/src/features/upload/hooks.ts` | useRecording 훅 추가 위치 |
| `docs/requirements/interview-guide.md` | F4 인터뷰이-02~05 준비 |
| `docs/dev-log/015-f4-demand-signals.md` | ADR-015 S5/S6 중간 현황 |

---

## 다음 세션 이후 백로그 (Sprint 12+)

- **F6** Wedge 선정 ADR — F4 인터뷰 5명 이상 완료 후 착수
- **F7** L4 우선화 검토 ADR
- **F2** S1~S4 Demand 시그널 실측 (analytics 도입)
- **BL-001** status progress 테이블 분리 (Sprint 12+)
- **AD-34** FE RBAC 정밀 분기 (`useUser+useMembers` 매칭)
- **D-4** EmbeddingChunk L0 ERD 정리
- **D-7** actions 텍스트 유사도 dedupe
- **D-8** 회의 R2 hash 중복 검출

---

가능한 우리 워크플로우를 따르며 진행해줘. Generator-Evaluator 방식으로 Evaluator는 Codex를 명시적으로 호출해서 검토받을 수 있도록 진행해주고, TDD를 잘 지켜서 해줘!
