# agy-deferred-scenarios — DEFERRED 시나리오 3건 검증 결과

Opus 1차 audit에서 검증 보류(DEFERRED)되었던 3개 시나리오에 대해 Playwright E2E 시나리오 및 소스 분석을 통해 심층 보강 검증을 수행하였습니다.

## 검증 결과 요약

| ID | 시나리오 | 검증 방법 및 대상 | 결과 | 상세 사유 |
| :--- | :--- | :--- | :--- | :--- |
| **E3** | **Cross-tenant private RAG leak** | `qa-sentinel-p0.spec.ts` (P0-1.10, P0-1.11, P0-1.12) | **PASS** | Sentinel A가 RAG 조회 시 Sentinel B의 private note/chunk가 단 한 건도 인용되지 않음을 확인 (0 leak) |
| **E5** | **Project visibility 분기** | `qa-sentinel-p0.spec.ts` (P0-1.1 ~ P0-1.6) | **PASS** | public/draft/private 프로젝트에 따라 RAG 검색 결과가 올바르게 필터링 및 권한 분기됨을 증명 |
| **E7** | **localStorage workspace drift** | `auth-relogin.spec.ts` + 대시보드 fallback 로직 분석 | **PASS** | 로그아웃 후 재로그인 시 stale workspace ID로 호출하더라도 대시보드 진입 시 primary workspace로 자동 fallback & 갱신됨을 검증 |

---

## 시나리오별 상세 결과

### E3. Cross-tenant private RAG leak (멀티테넌시 격리)
- **검증 상세**:
  - `SENTINEL_A` (Workspace A) 와 `SENTINEL_B` (Workspace B) 계정으로 각각 세션을 생성.
  - `SENTINEL_B`가 소유한 Workspace B 내의 private project 에 노트를 작성하고 임베딩 생성.
  - `SENTINEL_A`가 글로벌 RAG 검색 및 Workspace A 내부 RAG 검색을 통해 질의를 수행했을 때, Workspace B의 데이터가 노출되는지 여부 측정.
- **결과**: `P0-1.11` (B의 cross-tenant 청크가 A에게 절대로 노출되지 않음) 케이스 통과. RAG citation 결과에 B의 note_id 및 chunk_id가 0건 인용되어 완벽한 차단이 확인됨.

### E5. Project visibility 분기 (public / draft / private)
- **검증 상세**:
  - 프로젝트의 세 가지 visibility 모드(`public`, `draft`, `private`)를 3-layer 권한 모델에 매핑하여 RAG 질의 검증.
- **결과**:
  - `P0-1.1` (ProjectMember인 Admin의 public 프로젝트 조회) -> 정상 인용 (**PASS**)
  - `P0-1.2` (ProjectMember인 Admin의 private 프로젝트 조회) -> 정상 인용 (**PASS** - Admin 우회 권한 작동)
  - `P0-1.3` (비멤버 유저의 타 프로젝트 RAG 질의) -> **403/404 차단** (**PASS**)
  - `P0-1.6` (비멤버 유저의 draft 프로젝트 RAG 질의) -> **403/404 차단** (**PASS**)
  - `P0-1.12` (타 테넌트의 project_id로 RAG 질의 IDOR 시도) -> **403/404 차단** (**PASS**)

### E7. localStorage workspace drift (로그아웃 후 재로그인 시 Drift 복구)
- **검증 상세**:
  - 유저 A가 로그아웃 후 유저 B로 재로그인했을 때, localStorage `kairos-workspace`에 남아 있는 유저 A의 stale `activeWorkspaceId`로 API가 잘못 호출되는 상황 시뮬레이션.
- **결과**:
  - `frontend/src/app/(app)/dashboard/page.tsx` 의 auto-fallback 로직이 정상 작동함.
  - 불러온 `workspaces` 목록에 localStorage의 `activeWorkspaceId`가 없을 경우, 첫 번째 워크스페이스 ID(`workspaces[0].id`)로 강제 fallback하며 `setActiveWorkspaceId`를 호출해 즉각 갱신 및 상태를 일치시킴.
  - stale ID로 백엔드에 요청이 가더라도 백엔드 `require_member` 데코레이터에서 정상적으로 403 차단되어 자원 노출을 원천 방어함.
