# Phase 2 재테스트 리스트 — Gate 0 수정 검증

> **Phase 1** = 정검 (2026-09-26, [`report.md`](report.md)) · **Phase 2** = Gate 0 수정 → 이 리스트로 재테스트 → §7 양식으로 결과 보고.
> 확인하는 것은 두 가지다.
> 1. 이번 정검에서 FAIL 이던 항목이 수정 뒤 전부 PASS 인가 (§1~§3, §6)
> 2. PASS 였던 항목이 수정 때문에 깨지지 않았나. 특히 가시성 필터를 넓게 걸어 **볼 권한이 있는 사용자까지 막는 과잉 차단** (§4.1)
>
> 사용법: 결과 칸에 `PASS` / `FAIL` / `BLOCKED(사유)` 와 증거 경로(스크린샷·로그)를 적는다.
> 판정 원칙은 Phase 1 과 같다. UI 에서 숨겨지는지와 API 가 거부하는지를 **둘 다** 본다. FAIL 은 Evaluator 가 코드로 다시 확인한 뒤 확정한다.
>
> 예상 시간 (Claude): 준비 30분 · §1 2h · §2 1h · §4 1.5h (스크립트 재실행) · §5 1h · §6 1h · Evaluator 1h = **약 8h**. 사용자는 §3 운영 항목 약 1h.

---

## 0. 준비

| # | 할 일 | 확인 |
|---|---|---|
| 0.1 | **Phase 1 하네스 확인** — 계정 비밀번호·fixture id·`qa.py` 는 세션 임시 폴더(`/private/tmp/...`)에 있어 재부팅하면 사라진다. 사라졌으면 fixture id 는 DB 에서 제목으로 조회하고, 계정 비밀번호는 로컬 DB 에서만 재설정한다 | 6개 역할 로그인 성공 |
| 0.2 | 로컬 DB `kairos-qa-db` (:5436) 재사용. 계정 6개와 fixture 가 그대로 있다. **Neon 접속 금지** | `pg_isready -h 127.0.0.1 -p 5436` |
| 0.3 | 수정 브랜치에서 `alembic upgrade head` → BE uvicorn :8000 → FE `pnpm build && pnpm start` :3000 (report §2 기준선과 같은 방식) | `/api/v1/ready` 가 db ok |
| 0.4 | 브라우저는 반드시 `localhost:3000` 으로 접속한다 (`127.0.0.1` 은 origin·issuer 가 맞지 않아 실패) | owner 로그인 → `/dashboard` console.error 0 |
| 0.5 | 수정 커밋 SHA 를 §7 에 적고, 아래 Phase 2 fixture 를 만든다 | 각 id 기록 |

**기존 fixture** (QA Team)

| 이름 | 성격 | 볼 수 있는 사람 |
|---|---|---|
| Alpha | public 프로젝트 | 전원 |
| Beta | draft (member 작성) | member · admin · owner |
| Gamma | private, 프로젝트 멤버 = admin · member | admin · member · owner |
| Delta | private, 프로젝트 멤버 = admin | admin · owner |
| Done / Old | completed / archived | 전원 |

그 밖에 outsider 소유의 "Outsider Co" (다른 테넌트) 와 newbie (개인 WS 만 있음) 가 있다.

**Phase 2 에서 새로 만들 fixture** — 수정 *뒤에* 만든 데이터와 수정 *전에* 만든 데이터를 둘 다 검사해야 한다.

| id | 만드는 법 | 용도 |
|---|---|---|
| F-1 | admin 이 "코드명 은빛여우" 텍스트 캡처 → 완료 후 Gamma 에 **수동 연결** | 수정 후 생성 · 수동 연결 경로 |
| F-2 | admin 이 "코드명 청록고래" 텍스트 캡처 → 인박스에서 Gamma 로 **확정** | 인박스 확정 경로 |
| F-3 | admin 이 텍스트 캡처 → **Delta 에만** 연결 | member 가 볼 수 없는 회의 |
| F-4 | admin 이 텍스트 캡처 → Alpha 와 Gamma **둘 다** 연결 | 과잉 차단 대조군 |
| F-5 | Phase 1 의 Gamma 연결 회의 ("블루펭귄") | **수정 전 생성 데이터** (백필 검증) |
| F-6 | member 가 텍스트 캡처 → 인박스에서 "무시" (링크 0개) | 과잉 차단 대조군 |

RAG 질문은 매번 문구를 바꿔 `cached=false` 인 응답으로만 판정한다 (7일 semantic cache 때문).

---

## 1. Gate 0-A — 권한 누수 (전부 PASS 여야 Gate 0 통과)

| T | 결함 | 역할 | 절차 | 수정 후 기대 | Phase 1 실측 | 결과 |
|---|---|---|---|---|---|---|
| T-01 | C-014 | viewer | F-1 주제로 `POST /rag/ask` | 답과 출처에 F-1 없음 | 출처에 회의, 답에 "10월 20일" | |
| T-02 | C-014 | viewer | F-2 주제로 질문 | 답과 출처에 F-2 없음 | (같은 원인) | |
| T-03 | C-014 | viewer | F-5 주제로 질문 | 답과 출처에 F-5 없음 — 기존 데이터도 가려진다 | 노출 | |
| T-04 | C-014 | member | F-1 주제로 질문 | 출처에 F-1 **있음** (Gamma 멤버라서) | — | |
| T-05 | C-015 | viewer | `GET /inbox` · `?isProcessed=true` · UI `/inbox` | F-1 · F-2 · F-5 항목 0 | Gamma 요약 원문 수신 | |
| T-06 | C-015 | member | T-05 와 같은 요청 | Gamma 항목 보임 | — | |
| T-07 | C-016 | viewer | `GET /action-items` · UI `/actions` | F-1 · F-5 에서 추출된 액션 0 | Gamma 회의 액션 2건 | |
| T-08 | C-016 | member | T-07 과 같은 요청 | 보임 | — | |
| T-09 | C-018 | member | F-3 을 Alpha 에 `POST /meetings/{F-3}/projects` | 404. 이어서 viewer `GET /meetings/{F-3}` 도 404 | 201 → viewer 200 (전문 공개) | |
| T-10 | C-018 | member | `DELETE /meetings/{F-3}/projects/{Delta}` | 404. admin 으로 보면 링크 유지 | 204, 링크 삭제 | |
| T-11 | C-018 | member | 자기가 보는 Alpha 회의를 Delta 에 POST | 404 (대상 프로젝트도 볼 수 있어야 함) | 미측정 | |
| T-12 | C-018 | member | 인박스 classify 로 Delta 지정 | 404, 항목은 미처리로 남음 | 미측정 | |
| T-13 | C-018 대조 | member | 볼 수 있는 회의 ↔ 볼 수 있는 프로젝트 POST / DELETE | 201 / 204 (정상 경로 유지) | 201 / 204 | |
| T-14 | C-017 | member | `PATCH /projects/{Delta}` `{"description":"x"}` | 404. admin GET 으로 값이 그대로인지 확인 | 200, 저장됨 | |
| T-15 | C-017 | member | `PATCH /projects/{Delta}` `{}` | 404 (메타데이터 미노출) | 200 + 본문 | |
| T-16 | C-017 | member | `PATCH /projects/{Alpha}` `{"status":"archived"}` | 403 (보관은 admin 전용) | 200 (`/archive` 우회) | |
| T-17 | C-017 | admin | `PATCH /projects/{Alpha}` `{"status":"zzz"}` | 422 | 200, 저장됨 | |
| T-18 | C-020 | viewer · member · owner | **(a) 작성자 전용 (2026-09-27 결정)**: `GET /memory/recall?q=치과` · `GET /memory/{admin 메모 id}` · 같은 주제로 `POST /rag/ask` | recall 0건 · 상세 404 · RAG 출처에 memory 0. 작성자 admin 은 보임. owner 도 우회 없음 | 원문 노출 | |
| T-18b | C-020 | — | ~~(b) 팀 공유로 결정한 경우~~ — **폐기** (2026-09-27 결정 (a)). ID 는 재사용하지 않는다 | — | — | N/A |
| T-18c | U-4 | member | member 가 만든 Beta 에 `PATCH {"visibility":"private"}` → 다시 `public`. 이어서 owner 가 만든 Alpha 에 `PATCH {"visibility":"private"}` | Beta 200 (전환 뒤에도 member 가 Beta GET 200) · Alpha 403. UI 편집 다이얼로그에서도 같은 결과 | (결정 전 규칙: 둘 다 403) | |
| T-19 | C-002 | admin | 기존 프로젝트와 무관한 새 주제로 캡처 (새 프로젝트 제안이 나올 때까지 최대 3회) | 신뢰도와 무관하게 `/inbox` 에 남음 (`isProcessed=false`) | 인박스에서 사라지고 미연결 | |
| T-20 | C-002 | member | 회의 상세의 프로젝트 연결 UI 로 Alpha 연결 | POST 201, 상세에 Alpha 표시 | 연결 UI 없음 (FE 가 PUT 전송) | |
| T-21 | C-023 | member | `POST /meetings` 에 존재하지 않는 fileKey → failed 까지 폴링 → `GET /meetings/{id}` | `errorMessage` 에 `r2.cloudflarestorage` · `X-Amz` 0건 | 서명 URL 전체 노출 | |
| T-22 | C-023 | admin | Phase 1 에서 생긴 failed 회의 GET | T-21 과 같음 (기존 행 정리 확인) | 노출 | |
| T-23 | 0-7 | — | `apps/web` 에서 `node -e "console.log(require('next/package.json').version)"` · `pnpm build` | 16.3.3 이상, 빌드 성공 | 16.2.11 | |

## 2. Gate 0-B — 초대 → 첫 사용

| T | 결함 | 역할 | 절차 | 수정 후 기대 | Phase 1 실측 | 결과 |
|---|---|---|---|---|---|---|
| T-24 | C-001 | 기존 계정 | 스토리지를 비운 브라우저 → 로그인 → 새 팀 초대 수락. 가장 오래된 / 중간 / 최신 WS 순서로 3회 | 3회 모두 수락한 팀에 착지 | 가장 오래된 WS 에 착지 | |
| T-25 | C-001 대조 | 같은 계정 | 앱을 쓰던 브라우저에서 수락 | 수락한 팀 | 수락한 팀 (PASS) | |
| T-26 | E2-X01 | 계정 없음 | 초대 링크 → "가입하고 참여" → 가입 → 자동 복귀 → 참여 | 초대한 팀에 착지까지 끊김 없음 | 가입 뒤 초대 페이지로 못 돌아옴 | |
| T-27 | E2-X01 | anon | `/sign-in?callbackURL=/invite/<code>` 에서 가입 링크 클릭 | 가입 URL 에 callbackURL 유지 | 버려짐 | |
| T-28 | C-024 | anon | 이미 있는 이메일로 가입 | "이미 가입된 이메일입니다" | 영어 원문 | |
| T-29 | C-025 | member | `/new` 텍스트 캡처에 😀×25 | 버튼 비활성 또는 읽을 수 있는 한국어 오류 | "[object Object]" | |
| T-30 | C-025 | member | 수정 PR 이 목록화한 다른 422 화면 1곳 | 읽을 수 있는 문구 | 같은 증상 (약 4~5곳) | |

## 3. Gate 0-C — 운영 (명령 결과로 판정)

| T | 체크리스트 | 담당 | 명령 / 방법 | 기대 | 결과 |
|---|---|---|---|---|---|
| T-31 | 0-11 백업 | Claude | 최신 덤프를 새 컨테이너에 복원 → 주요 테이블 row count 비교 | 원본과 일치 | |
| T-32 | 0-12 r2-cleanup | Claude | dry-run 삭제 목록을 `meetings.file_key` 와 대조 | 참조 중인 원본 0건 | |
| T-33 | 0-13 HTTPS | 사용자 | `curl -sI http://kairos.woosung.dev/` · `curl -sI https://kairos.woosung.dev/ \| grep -i strict-transport` (api 호스트도 같이) | 301 · 1줄 | |
| T-34 | 0-14 배포 | Claude | `curl -s -o /dev/null -w '%{http_code}\n' https://kairos-api.woosung.dev/api/v1/workspaces/00000000-0000-0000-0000-000000000000/integrations/google-drive/documents` · FE 응답 헤더 | 401 (405 아님) · `content-security-policy-report-only` 있음 | |
| T-35 | 0-15 Google | 사용자 | 등록 안 한 계정 / 등록한 계정으로 Google 로그인 | 차단 / 성공 | |
| T-36 | 0-16 비밀번호 분실 | 사용자 | runbook 대로 테스트 계정 비밀번호 재설정 | 새 비밀번호로 로그인 | |
| T-37 | 0-17 Clerk | 사용자 | Clerk 대시보드 · 서버에서 `grep -c CLERK ~/kairos/.env` | 인스턴스 없음 · 0 | |
| T-38 | 0-18 nightly | 사용자 | `gh workflow run nightly-e2e.yml --repo woosung-dev/kairos` → `gh run list --workflow nightly-e2e.yml --repo woosung-dev/kairos --limit 1` | success | |
| T-39 | 0-19 main 보호 | 사용자 | `gh api repos/woosung-dev/kairos/rulesets` | 빈 배열이 아님 | |
| T-40 | 0-20 stuck 회의 | 사용자 | `mise run deploy-preflight` | 0 | |

---

## 4. 회귀 — Phase 1 PASS 유지

### 4.1 과잉 차단 대조군 (가장 중요 — 수정의 부작용을 잡는다)

회의 가시성 규칙: **링크가 0개면 전원 공개, 접근 가능한 링크가 1개라도 있으면 공개.** 파생 데이터(RAG 청크·인박스·액션)도 이 규칙과 결과가 같아야 한다.

| R | 역할 | 대상 | 기대 (상세 · RAG · 인박스 · 액션 모두) | 결과 |
|---|---|---|---|---|
| R-01 | viewer | F-6 (링크 0개) | 보임 | |
| R-02 | viewer | F-4 (Alpha + Gamma) | 보임 (접근 가능한 링크가 1개 있음) | |
| R-03 | viewer | Phase 1 의 Alpha 연결 회의 | 보임 | |
| R-04 | admin · owner | F-1 ~ F-6 전부 | 보임 | |

### 4.2 Phase 1 PASS 재실행

기준은 [`probe-results.log`](probe-results.log) 에서 `VERDICT=PASS` 가 들어간 줄 **전부** 다 (92줄 — 형식 예외 2줄 포함). 같은 기대값으로 다시 돌린다. 아래 표는 묶음 안내다.

| 묶음 | 탐침 ID | 결과 |
|---|---|---|
| 인증·토큰 | G1-003 · G1-007 · G1-008 · G1-010 · G1-011 · G1-013 · G1-014 | |
| 테넌트 격리 | G1-026 · G1-072 ~ G1-080 · G1-092 · SWEEP-outsider · RAG-xtenant | |
| 역할 게이트 | G1-021 · G1-024 · G1-042 ~ G1-053 · G1-055 · G1-056 · G1-059 · G1-060 · G3-047. **G1-050 기대값 정정**: member 403 은 *남이 만든* 프로젝트에만 해당한다 (작성자 member 는 200 — T-18c) | |
| 프로젝트·노트·회의 가시성 | G1-062 ~ G1-067 · G1-071 · G1-088 · G1-093 | |
| RAG | RAG-LEAK-private-note · RAG-CACHE-leak · G1-069 · G1-078 · G3-003 · G3-007 · G3-011 | |
| 초대 검증 | G1-030 ~ G1-039 · G1-044 | |
| 파이프라인·콘텐츠 | AUDIO-UPLOAD-UI · TEXT-CAPTURE-API · CLASSIFY-public · G2-007 · G2-048 · G2-057 · G2-062 | |
| 화면 sweep | SWEEP-owner · admin · member · viewer (23 라우트) · G3-040 (375px) — console.error 0 | |
| 워크스페이스 전환 | WS-CREATE-UI · G1-028 · G1-029 | |
| 단축키·팔레트 | G3-020 ~ G3-023 | |

---

## 5. Phase 1 에서 실행하지 못한 P0/P1 시나리오

[`generator-scenarios.json`](generator-scenarios.json) 의 P0/P1 중 탐침 로그에 ID 가 없는 것은 32개다. 그중 18개는 이름이 다른 탐침이 이미 덮었다 (§5.3). 남은 14개를 Phase 2 에서 처음 실행한다.

### 5.1 미실행 (8)

| ID | 역할 | 확인할 것 | 결과 |
|---|---|---|---|
| G1-006 | anon | 가짜 세션 쿠키를 넣으면 페이지 틀은 떠도 `/api/v1` 호출은 전부 401 | |
| G1-012 | member | iss 가 다른 JWT → 401 | |
| G1-081 | outsider | QA Team 메모 id 로 memory 상세 → 403/404 | |
| G2-012 | member | 오디오 회의 상태 전이. 관측한 status 가 {uploading, transcribing, analyzing, completed} 안에 있음 | |
| G2-015 | member | 추출 정확도: 결정 2 · 액션 3 · 마감일 3개. 합성 음성은 발화 일부가 빠지므로(Phase 1 관찰) **같은 스크립트를 텍스트 캡처로 넣어** 판정한다 | |
| G2-030 | member | 회의 export md/json 다운로드, `format=pdf` → 422 | |
| G2-036 | member | 빠른 메모: 빈 입력 검증 문구, 성공 토스트, 목록 상단 반영 | |
| G3-018 | member | 한글 조합 중 Enter → 요청 1회, 마지막 글자 포함 | |

### 5.2 부분 실행 (6) — 빠진 부분만 실행

| ID | Phase 1 에서 본 것 | 남은 것 | 결과 |
|---|---|---|---|
| G1-054 | viewer 캡처 403 | member·admin·owner 202, 본문 길이 경계 422 | |
| G1-058 | 역할별 RAG 응답 | 질문 길이 2~500자 경계 422 | |
| G1-082 | 탭 노출·폴백 | general 탭의 owner 전용 폼 | |
| G1-084 | owner 렌더 · admin 거부 | member·viewer 화면 문구 | |
| G1-086 | newbie 개인 WS 생성 | 첫 호출 동시 요청에서 500 없음 | |
| G2-043 | viewer 의 Gamma 노트 상세 404 | `embedding-status` 404 | |

### 5.3 다른 탐침이 덮은 18개 (재실행 불필요)

G1-016 · G1-017 · G1-018 → AUTH-RATELIMIT / G1-068 · G3-002 → RAG-LEAK-private-note / G1-070 → G1-065 · G1-066 (export 포함) /
G2-017 → CLASSIFY-public / G2-066 → G1-076 / G3-001 → C-014 (G2-021) / G3-004 → RAG-CACHE 역순 실험 / G3-006 → G1-069 /
G3-008 → G1-078 / G3-026 · G3-028 → G1-061 / G3-050 · G3-051 · G3-053 · G3-054 → PROD-* 탐침

---

## 6. Gate 0 밖 결함 (P2 7 · P3 9) — Phase 2 에 포함할 때만 실행

> **2026-09-27 Phase 2 에서는 제외** (사용자 결정 U-5: 범위 = Gate 0 §0~§5). Gate 1 작업 때 실행한다.

수정 범위에 넣은 항목만 실행한다. 원래 재현 절차는 [`report.md`](report.md) §4 에 있다.

| T | 결함 | 역할 | 절차 | 수정 후 기대 | 결과 |
|---|---|---|---|---|---|
| T-41 | C-003 | admin | Gamma 주제로 캡처 | 분류 후보에 요청자가 볼 수 있는 active 프로젝트가 들어가 Gamma 가 추천됨. archived/completed 는 제외 | |
| T-42 | C-004 | member | `/new` 에서 프로젝트를 고르고 캡처 | 생성 즉시 연결 (링크 0개로 공개되는 구간 없음) | |
| T-43 | C-019 | viewer | `GET /projects/{Gamma}/members` | 404 (프로젝트 GET 과 같음) | |
| T-44 | C-022 | member | 같은 질문을 `sourceType=note` → `meeting` 순서로 | 두 번째가 cached=false, 출처 type 이 meeting | |
| T-45 | C-026 | member | 노트 편집 → 250ms 안에 다른 노트로 이동 → 재진입 | 편집 내용 유지 (PATCH 1회) | |
| T-46 | C-027 | member | 인박스 확정 → "되돌리기" | 서버 링크도 해제됨 (회의 상세에서 확인). 또는 버튼 제거 | |
| T-47 | E1-N1 | member | 노트 생성 1초 안에 삭제 × 3회 → 10초 대기 | 해당 source_id 청크 0, RAG 출처에 없음 | |
| T-48 | C-006 | viewer | private 회의 URL 직접 진입 | "접근 권한 없음" 계열 문구, 404 재시도 0회 | |
| T-49 | C-007 | member | `/settings?tab=audit` | 탭 하나가 선택된 상태로 폴백 | |
| T-50 | C-008 | viewer → member | viewer 가 먼저 질문 → member 가 같은 질문 | member 가 cached=false 이거나 권한별 캐시 키 사용 | |
| T-51 | C-009 | — | `auth.ts` 의 `advanced.ipAddress` 설정 · 프로덕션 `docker logs` 에서 "could not determine a client IP" | 설정 있음 · 0건 | |
| T-52 | C-010 | newbie | 첫 방문 `/new` | 툴팁 1회 표시 (또는 정의 제거) | |
| T-53 | C-012 | anon | `curl -sI https://kairos.woosung.dev/robots.txt` | 200 | |
| T-54 | C-013 | anon | `curl -sI https://kairos.woosung.dev/` | `x-powered-by` 없음 · CSP 헤더 있음 | |
| T-55 | C-021 | viewer | `GET /memory/metrics` | 403 (FE 의 founder 전용과 일치) | |
| T-56 | C-028 | member | 같은 회의를 두 번 promote | 사본 1개 (두 번째는 409 또는 기존 사본 반환) | |

---

## 7. 결과 보고 양식

```
# Phase 2 재테스트 결과 — YYYY-MM-DD
- 기준 코드: <branch> @ <SHA>   (Phase 1: main 1d2eac0)
- 실행: Claude 메인 / Evaluator: E-n (fresh context) / codex (P0·P1 교차검증)
- 합계: §1 __/24 (T-18b 제외, T-18c 포함) · §2 __/7 · §3 __/10 · §4.1 __/4 · §4.2 __/92 · §5 __/14 · §6 __/16 (포함한 것만)
- Gate 0 판정: GO / NO-GO
  조건: §1 · §2 · §3 · §4.1 전부 PASS, §4.2 FAIL 0
- FAIL: T-ID | 기대 | 실측 | 증거 경로 | Evaluator 판정
- BLOCKED: T-ID | 사유
- 새 결함: 임시 ID | 등급 | 재현 절차 | 증거 | Evaluator 판정
```
