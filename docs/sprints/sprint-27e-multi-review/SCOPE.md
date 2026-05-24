# Sprint 27e — 4-Reviewer Multi-Agent Audit (production 진입 직전)

> Sprint 27d (3-세션 product/UX audit GO 8.02/10, PR #108 main merged `1b24898`) 후속 **기술 deep audit**. 보안/성능/테스트커버리지/아키텍처 4 전문 리뷰어 시각으로 production 배포 *전* 최종 검증 루프.
>
> 결정 anchor: `docs/sprints/sprint-27e-multi-review/session-inputs/main.txt`

---

## 왜 본 sprint

Sprint 27d 는 product/UX 시각 (QA-Function / QA-EdgeCase / CTO / CEO / 일반사용자 / Solo-Personal). **기술 깊이 부족**:

- 보안: IDOR + upload mime 만 검증. SQL injection / XSS / 인증 결함 / OWASP top 10 전수 audit 미실시
- 성능: RAG latency 만 측정 (10.6s avg). 알고리즘 / DB 쿼리 N+1 / 캐싱 기회 / sync blocking / 리소스 누수 전수 audit 미실시
- 테스트 커버리지: pytest 469 PASS / vitest 56 PASS 합계만. **에지 케이스 / 통합 테스트 / 신규 기능 가드** 갭 미정량
- 아키텍처: 헌법 (CONTEXT-MAP.md) 정합 부분 검증. **ACM 패턴 / 설계 원칙 / 결합도-응집도 / 일관성** 전수 audit 미실시

→ production 배포 (Cloud Run BE + Vercel FE) 또는 외부 5명 dogfooding *전* 본 4 reviewer audit 추가.

---

## 검증 범위 — 개인 + 팀 2 시나리오

### Scenario A: Personal workspace (1인)

- **사용자**: founder (d@e.com) 단일 Personal workspace `e968c95f-4bbe-4f12-9468-2741c047e142`
- **흐름**: 회의 업로드 → AI 요약 → 노트 작성 → ⌘K 검색 → Action item 처리 → Inbox 분류
- **권한 model**: visibility = personal (본인만)
- **risk**: solo founder 의 1인 데이터 무결성, single-user 가정 위배 시 회귀

### Scenario B: Team workspace (다인)

- **사용자**: founder + (가상의) 멤버 2명 시뮬레이션 (Personal workspace 의 SENTINEL A/B 또는 신규 invite flow)
- **워크스페이스**: Team `7f9f446d-9b7f-4ae7-aa9b-ac861fb81b11` "QA Cycle C Team"
- **흐름**: 워크스페이스 초대 → role 부여 → 공유 회의 업로드 → cross-member RAG → visibility 분기 (public / draft / private)
- **권한 model**: WorkspaceMember role (owner / admin / member) + project visibility (public / draft / private)
- **risk**: cross-tenant leak, IDOR, role escalation, visibility 분기 race

각 reviewer 는 **두 시나리오 모두** 검증. 시나리오별 결함은 별도 표시.

---

## 4 Reviewer 정의

각 reviewer 는 `agents/` 하위의 standalone definition 참조:

| Reviewer | 파일 | 핵심 관심사 |
|----------|------|------------|
| 보안 전문가 | `agents/security-reviewer.md` | OWASP top 10 / SQLi / XSS / 인증 / 안전 X 구성 |
| 성능 분석가 | `agents/performance-analyst.md` | 알고리즘 / DB N+1 / 캐싱 / sync blocking / 리소스 누수 |
| 테스트 커버리지 리뷰어 | `agents/test-coverage-reviewer.md` | 신규 기능 / 에지 / 품질 / 통합 / 추가 권고 |
| 아키텍처 가디언 | `agents/architecture-guardian.md` | ACM 패턴 / 설계 원칙 / 결합도-응집도 / 헌법 정합 |

---

## GO 조건 (4/4 충족 시 production 진입 unlocked)

| 조건 | 기준 | 측정 |
|------|------|------|
| **차단 (Blocking) 결함** | **0건** | 4 reviewer 통합 보고서의 Blocking 표시 결함 |
| OWASP top 10 carry | ≤ 3건 (각 P2 이하) | 보안 reviewer 결과 |
| 성능 critical path p95 | RAG ≤ 15s / API ≤ 500ms / 회의 처리 ≤ 60s | 성능 reviewer 측정 (실 환경) |
| 테스트 커버리지 | 신규 기능 cover ≥ 80% / 통합 테스트 핵심 흐름 100% | 테스트 reviewer 정량 |
| 헌법 정합성 | CONTEXT-MAP.md + ADR-* 위반 0 | 아키텍처 reviewer 결과 |

**NEEDS-FIX**: 차단 결함 1건 이상 → 본 sprint 안에서 fix → 통합 보고서 갱신 → 재평가 → GO 또는 NEEDS-FIX.

**NO-GO**: 차단 결함 fix 시도 후에도 잔존 → production 진입 보류 → Sprint 28 으로 carry + 사용자 결정.

---

## 통합 보고서 형식

`integrated-report.md` (sprint 종료 시 산출):

### 1. Executive Summary (1 페이지)

- 4 reviewer 종합 verdict + GO/NEEDS-FIX/NO-GO 한 줄
- 차단 결함 갯수 + 비차단 결함 갯수
- 가장 critical 한 finding 3건 강조 (file:line + 권장 fix + 영향도)

### 2. 4 reviewer 별 매트릭스

| ID | reviewer | 심각도 | 차단? | file:line | 발견 사항 | 권장 fix |
|----|----------|--------|------|----------|----------|---------|
| BUG-S27e-SEC-1 | 보안 | P0 | YES | backend/src/X:Y | ... | ... |

### 3. GitHub PR comment 형식 출력

`pr-comment.md` — 직접 PR 에 붙여넣을 수 있는 형식 (file/line 인용 + suggested change):

```markdown
### 🔴 BUG-S27e-SEC-1 — SQL injection on `/X` (Blocking)

**file**: `backend/src/X.py:42`
**reviewer**: 보안 전문가
**OWASP**: A03:2021 Injection

```python
# 현 코드
query = f"SELECT * FROM users WHERE name = '{name}'"  # ❌
```

**권장 fix**:

```python
query = select(User).where(User.name == name)  # ✅
```

**영향도**: 인증된 모든 사용자가 SQL injection 가능.
```

### 4. 충돌 해결 + 중복 병합

- 같은 결함을 여러 reviewer 가 다른 시각으로 발견 시 → 단일 ID 통합 + 모든 시각 인용
- reviewer 간 충돌 (보안 우선 vs 성능 우선) → 본 sprint 정책: **보안 > 아키텍처 > 테스트 > 성능** 우선순위로 해결

### 5. 차단 vs 비차단 분류

- **Blocking** (P0/P1): production 진입 전 fix 필수. red 마크.
- **Non-blocking** (P2/P3): BL carry 가능. yellow 마크. Sprint 28+ 처리.

---

## 산출물 (sprint 종료 시)

| 파일 | 내용 |
|------|------|
| `integrated-report.md` | 4 reviewer 통합 + 충돌 해결 + 우선순위 |
| `pr-comment.md` | GitHub PR 직접 첨부용 형식 |
| `security-findings.md` | 보안 reviewer 원본 발견사항 |
| `performance-findings.md` | 성능 reviewer 원본 |
| `test-coverage-findings.md` | 테스트 reviewer 원본 |
| `architecture-findings.md` | 아키텍처 reviewer 원본 |
| `report.html` | 시각화 (Sprint 27d report.html style 차용) |
| `screenshots/` | reviewer 들이 캡처한 증거 (선택) |

---

## 실행 방식

`session-inputs/main.txt` 가 새 세션의 entry. 새 세션은:

1. **환경 검증** (FE/BE health + git log + sprint 27d main HEAD `1b24898` 확인)
2. **4 sub-agent 순차/병렬 spawn** (Agent tool):
   - 각 agent 는 `agents/{name}.md` 의 검사 항목 + 출력 형식 따름
   - Personal + Team 2 시나리오 모두 검증
   - e2e MCP Playwright 적극 활용 (보안 = IDOR fetch / 성능 = page-load timing / 테스트 = e2e gap)
3. **통합 보고서** 작성 (위 형식)
4. **Blocking 결함** 존재 시 사용자 결정 (fix vs carry) → fix 진행
5. **GO 판정** 시 PR 생성 또는 main 직접 commit (사용자 정책)
6. **종료 보고** + Sprint 28 진입 신호

---

## 정책 SKIP / Carry-over

- production 환경 audit (실 Cloud Run): 본 sprint 도 SKIP (Sprint 27c-d 와 동일). dev 환경에서 코드 audit + dev 환경 e2e.
- Sentry: 사용자 정책 SKIP 유지 (ADR-022). 단 본 audit 에서 "Sentry 없이도 외부 5명 진입 가능한지" 자체 평가 1건 추가 (보안 reviewer).
- Clerk Production 키: SKIP 유지. dev key 운영 정합성만 검증.
