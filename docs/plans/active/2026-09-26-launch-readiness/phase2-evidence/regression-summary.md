# Phase 2 회귀 요약 — API 탐침 (2026-09-27)

- 대상: 로컬 BE `localhost:8000/api/v1` (kairos-qa-db :5436) · FE `localhost:3000`. 서버는 재시작하지 않았다.
- 로그: `phase2/probe-regression.log` (QAPROBE 119줄 = 기준 92 + 기준 `#UI` 9 + 신규 14 + 신규 `#UI` 3 + 기대값 변경 1. VERDICT 합: PASS 87 · UI→main 30 · BLOCKED 1 · EXPECTATION-CHANGED 1 · FAIL 0). 스크립트: `phase2/regression/r1~r8*.py`, 헬퍼 `reg.py` (qa.py 를 복사하고 LOG 경로만 바꿈).
- 판정 기준: Phase 1 `probe-results.log` 의 `VERDICT=PASS` 92줄. 기대값은 Phase 1 과 같고, 2026-09-27 결정(U-2/U-4 등)과 부딪히는 곳만 새 기준으로 판정했다.
- 파이프라인·RAG 는 실제 Gemini/OpenAI 를 호출했다. RAG 판정은 전부 `cached=false` 응답으로 했다. R2 업로드는 하지 않았다.

## 1. 합계

| 구분 | PASS | FAIL | BLOCKED | UI→main | EXPECTATION-CHANGED |
|---|---|---|---|---|---|
| §4.2 Phase 1 PASS 재실행 (92) | **79** | **0** | 0 | 13 | 0 |
| └ 섞인 탐침의 UI 부분 (별도 `#UI` 줄) | — | — | — | 9 | — |
| §5 신규 실행 (14) | **8** | **0** | 1 | 5 | — |
| └ 신규 탐침의 UI 부분 (`#UI` 줄) | — | — | — | 3 | — |
| 기대값 변경 기록 | — | — | — | — | 1 (G1-050b) |

- **FAIL 0건.** Gate 0 수정 뒤 Phase 1 PASS 탐침 중 API 로 돌릴 수 있는 79개가 모두 그대로 PASS 다. 볼 권한이 있는 사용자까지 막히는 과잉 차단도 없었다.
- **92줄 중 UI 전용 13개**: SWEEP-owner/admin/member/viewer · WS-CREATE-UI · AUDIO-UPLOAD-UI · G3-020~G3-023 · G3-040 · G2-007 · G1-029.
- **API 와 UI 가 섞인 9개**: API 부분은 PASS 이고 UI 부분만 남았다. G1-014 · G2-048 · G2-057 · G2-061 · G2-062 · G3-047 · G3-048 · SWEEP-outsider · G1-028.
- **§5 신규 결과**
  - PASS 8: G1-006 · G1-012 · G1-081 · G1-054 · G1-058 · G2-015 · G2-030 · G2-043.
  - UI→main 5: G2-012 · G2-036 · G3-018 · G1-082 · G1-084. 여기에 G1-006 · G2-030 · G2-043 의 UI 부분이 더 남았다.
  - BLOCKED 1: G1-086.

## 2. FAIL 목록

없음.

첫 실행에서 G3-007 이 FAIL 로 나왔지만 탐침 쪽 문제였다.
- admin 질문이 member 질문과 끝 한 글자만 달라서 semantic cache 가 적중했고 `cached=true` 가 됐다.
- admin 은 member 가 볼 수 있는 것을 전부 볼 수 있으므로 누출은 아니다. admin 은 note 출처가 있는 정상 답을 받았다.
- 문구를 역할마다 완전히 바꿔 다시 돌렸다. 결과는 member/admin 이 `cached=false` 로 정상 답을 받았고, viewer 는 'Draft 프로젝트는 작성자만 접근 가능합니다.' 오류를 받아 PASS 다. 로그에는 두 번째 실행 결과를 남기고, 첫 실행이 왜 무효인지 GOT 에 적었다.

## 3. BLOCKED

- **G1-086 (lazy seed 첫 호출 경쟁 조건)**
  - 진짜 첫 호출을 재현하려면 새 계정을 가입시켜야 한다. 이 에이전트에서는 계정 생성을 하지 않았다.
  - 대신 기존 newbie 계정으로 12개 동시 호출(`/users/me` · `/workspaces` · `/users/me/onboarding`)을 보냈다. 결과는 전부 200, 500 은 0건이고 User 1행 · personal WS 1개로 그대로다.
  - 새 계정 첫 호출 경쟁은 메인 세션이 사용자 승인을 받고 실행해야 한다.

## 4. 참고 관찰 (회귀 아님 — Gate 1 범위의 알려진 결함)

1. **E1-N1 고아 청크를 우연히 재현 (P2, T-47, Phase 2 범위 밖)**
   - G1-053b 에서 만들고 1초 안에 지운 REG 노트 2개(`b52d8b25…`, `82287404…`)의 청크가 각 2개씩 남았다.
   - 그중 `b52d8b25` 가 viewer 의 RAG 출처로 나왔다 (RAG-LEAK viewer#1). 삭제된 노트가 검색되는 것이다. 다만 원래 Alpha(public) 노트라 권한 누출은 아니다.
   - 원인: `apps/api/src/notes/pipeline_service.py:65` 는 노트 존재를 임베딩 시작 시점에만 확인한다. 그 뒤 `embed_note` 가 OpenAI 호출을 마치고 청크를 넣기 때문에, 그 사이에 삭제가 끝나면 청크가 남는다 (삭제 정리는 `:155`).
   - 청크를 지우려면 DB 를 직접 고쳐야 하므로 남겨 두었다.
2. **RAG 출처 권한 교차 확인**: RAG-LEAK · RAG-CACHE 에서 받은 출처를 전부 질문한 역할로 상세 GET 했다. 모두 200 이었다 (고아 청크 1건 제외). 권한 밖 출처는 없다.
3. **semantic cache 방향성 (C-008 관련, P3)**
   - admin 이 만든 캐시는 member 에게 가지 않았다 (RAG-CACHE-leak, `cached=false`, Delta 없음).
   - 반대로 member 가 만든 캐시는 거의 같은 질문을 한 admin 에게 적중했다 (G3-007 첫 실행). 권한이 큰 사용자가 덜 완전한 답을 받을 수 있다는 C-008 의 성격으로 보인다 [가정].
4. **G1-012**: 서명을 먼저 검증하고 iss 를 나중에 본다 (`apps/api/src/auth/dependencies.py:206` 의 `jwt.decode`).
   - 그래서 iss 만 조작한 토큰과, 서버 kid 를 달고 직접 서명한 토큰은 둘 다 401 '유효하지 않은 토큰입니다' 로 끝난다.
   - InvalidIssuer 분기(`:227-230`, '유효하지 않은 토큰 발급자입니다')를 타려면 서버 비밀키로 서명한 토큰이 있어야 해서 외부에서는 확인할 수 없다.
   - "iss 가 다른 JWT → 401" 이라는 기준은 충족한다.
5. **G1-062b**: 프로젝트 목록은 기본이 active 만이다 (`projects/service.py:121`, baseline 과 같음). 그래서 Phase 1 과 같은 모양으로 비교하려고 status 3종(active·completed·archived) 결과를 합쳐서 판정했다.
6. **PROD-***: 프로덕션에는 익명 GET 만 보냈다. 프로덕션은 아직 수정 전 배포다.

## 5. 기대값 변경 (U-4)

- **G1-050**: 남이 만든 프로젝트에서 viewer 403 · member 403 · admin 200 · owner 200 이다. Phase 1 기대와 부딪히지 않아 PASS.
- **G1-050b (EXPECTATION-CHANGED)**: 프로젝트를 만든 member 는 visibility 를 private 로 바꿔 200, GET 200, 다시 public 으로 200 을 받았다. 새 기준으로 PASS.

## 6. 새로 만든 임시 리소스

**삭제 완료 (API)**

- 임시 WS `REG-ws-953d7c` `261f8522-65c0-48e4-9302-3ce91f4b8f0c`
  - admin/member/viewer/newbie/outsider 가 초대로 들어왔고, 안에 REG 프로젝트 2개가 있었다.
  - owner 가 DELETE 해서 204 를 받았다. WS·멤버·프로젝트가 0/0/0 으로 남은 것이 없다.
- QA Team REG 프로젝트 6개 (g1049-owner, g1048-member, g1052, g1088, g2057-full, g2057-e2): admin DELETE 204. g1048-admin 과 g2057-empty 는 탐침 중에 이미 삭제했다.
- REG 노트 6개: 4개는 cleanup 에서 204, 2개(member own · member2)는 탐침 중에 삭제했다. 이 2개는 고아 청크가 남았다 (§4-1).
- G1-014 용 owner 추가 세션: sign-out 으로 폐기했다. 공유 jar(`jar-owner.txt`) 세션은 그대로 살아 있다 (200).

**비활성화**

- QA Team 초대 `0ae1c56d-d749-4614-802d-18403862fa1e` (G1-030) · `863fc8d7-ec3f-4c86-a744-068534876c96` (G1-036): `is_active=false`, `use_count=0`.

**남아 있음 (삭제 API 없음)**

| 종류 | id | 제목 | 상태 |
|---|---|---|---|
| 회의 | `09b787b2-b5b3-43ab-9fbf-22c023f0c50b` | REG Alpha 스프린트 점검 a5900c (owner) | Alpha 자동 연결, 액션 4 |
| 회의 | `332c46b6-9e78-4b83-9200-a32f4f1c66de` | REG 사내 교육 일정 a5900c (admin) | 링크 0, 인박스 미처리 1 |
| 회의 | `5e738120-342b-418b-b249-a8e62176315a` | REG Outsider 전략 a5900c | Outsider Co, 링크 0, 인박스 미처리 1 |
| 회의 | `0c7229a5-ad4a-4815-9e2b-0a88745a7b76` | REG G2-015 베타 출시 회의 a5900c (member) | Alpha 자동 연결, 액션 3 |
| 회의 | `d87b8591-750e-4e41-be82-8bfc8e6dedab` | REG 주간 1:1 a5900c (member) | 📋 회의록 자동 연결 (conf 0.9) |
| 회의 | `7dde6822-38f0-4f5f-93c2-00cae6919cde` | REG b50 a5900c (member) | G2-048 classify 로 Alpha 연결 |
| 액션 | `31bba3d1-062c-416c-80a1-ba52fa260c3f` · `6d70be98-3175-466d-91b6-40ba21c908fe` · `a3ded847-cdb4-4b67-8a5c-4cabf4c8ef4b` | REG-act-admin/owner/member | Alpha, `todo` |

- 위 회의에서 파생된 인박스 항목과 AI 추출 액션도 남아 있다.
- 이제 Alpha 에는 REG 액션 3개와 REG 회의 3개가 연결되어 있다. 그래서 Alpha 삭제 409 문구에 나오는 액션 수가 Phase 1 과 다를 수 있다.
- RAG 질문으로 semantic cache 항목이 생겼다 (TTL 7일).

## 7. 기존 fixture 상태 (끝난 뒤 SELECT 로 확인)

- QA Team 멤버: owner/admin/member/viewer 4명, 역할은 그대로다. newbie·outsider 는 QA Team 에 없다.
- 프로젝트 visibility/status 는 그대로다: Alpha public/active · Beta draft · Gamma/Delta private · Done completed · Old archived.
- QA-TMP Gamma/Delta 액션은 `todo` 그대로다. G1-067 의 PATCH 가 404 였고 행이 바뀌지 않았다.
- `phase2/fx.env` fixture (F1~F6, IB_*, MEMO) 는 읽기만 했다. G1-081 은 MEMO 를 GET 만 했다.
- 기존 fixture 의 visibility/status 를 바꾼 탐침은 없어서 원복할 것도 없다. G1-050 에서 바꾼 visibility 는 전부 REG 프로젝트였고 public 으로 되돌렸다.
