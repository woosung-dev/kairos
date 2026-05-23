# CTO — 아키텍처 + 운영 lens

> 페르소나: solo hacker @levelsio 톤. 1인 운영 가능 여부 우선. 시리즈 A CTO 또는 FAANG senior 의 over-engineering 편향 X.

## 평가 5축 (각 10점)

### 1. 아키텍처 sealed (Phase 0~3 완료도) — 7/10

**Positive**:
- CONTEXT-MAP.md 헌법 21개 불변식 (I-1~I-21) 명시 + code-level 강제 (test_no_memory_to_embeddings_lazy_import.py 등 architecture test)
- 13 BE 도메인 + 11 FE features 경계 명확 (ADR-014 service boundary)
- Sprint 24 Wave 2 BL-052/053/054 cleanup 완료 (PR #92/93/95): SQLAlchemy → SQLModel + AsyncSession Level 3 + session.exec migration. 큰 부채 해소
- ADR-019 Phase B (Gemini swap, 003908a) + ADR-020 (pgvector HNSW halfvec) 완료 = AI stack 최신화
- Promotion 5도메인 lock-in (ADR-016 + Sprint 23 D4, 헌법 I-18)

**Negative**:
- L3/L4 (조직 인사이트) 미구현 = PRD §5 Phase 4 prerequisite 미달
- Phase 4 외부 5명 dogfooding 전체 미실행 (22 sprint, 22-week-skip 패턴)

### 2. 운영 readiness — 3/10 — 🔴 BLOCK

**Critical**:
- **Production BE health 자주 timeout** — audit 중 200 OK (~65ms) ↔ timeout (10s+) 반복. Cloud Run instance instability or cold start aggressive scaling. 외부 5명 동시 진입 시 SLA 깨짐
- **Production deploy stale 가능성** — `/workspaces` 500 (localhost 같은 code 는 200) → main HEAD `eb13a42` Cloud Run revision 미적용. ADR-022 SKIP 결정의 lazy seed 의존도 ↑ 인데 그 코드도 stale 추정
- **GEMINI_API_KEY invalid** (`.env` 또는 Cloud Run secret) — 회의 업로드 → AI pipeline 전체 폭발. Sprint 27a (ADR-019 Phase B) 후 검증 부재
- Sentry SDK 통합 ADR-021 (PR #97) ✅ — 단 alert 채널 (Slack/email) 사용자 확인 필요

**P0-OPS BLOCK 적용** (CTO 보안 baseline < 5 + 운영 readiness < 3 정책 trigger 직전): 운영 readiness 3/10 = critical 1건 BLOCK trigger 한계선. 외부 5명 진입 보류 input.

### 3. BL 부채 합리성 (1인 운영 부담) — 4/10

**측정**:
- `docs/REFACTORING-BACKLOG.md`: 87 BL/D items, 67 starred (active 추정), 21 closed marker
- 21 ADRs (4 가 Sprint 27a 시점 = 0-24 numbering 일부 missing/superseded)

**문제**:
- BL 부채 67건 active = 1인 founder 가 외부 5명 진입 + paid customer 추진 + BL fix 병행 어려움
- 만약 외부 5명 dogfooding 시 신규 P1/P2 5-15건 생성 추정 → 80+ active BL
- Sprint cycle 1주 hard cap = BL fix 우선순위 끝없음
- **Sprint 26 거버넌스 경량화** (228 files -18,194 net, PR #104) 가 정답이었으나 (memory `project_sprint26_glittery_tulip_done`), code 부채 자체는 그대로

**Positive**: BL 카테고리화 (P0/P1/P2) 명확. Atomic Update Sprint 26 매트릭스 폐지로 1인 fit ↑.

### 4. 보안 baseline — 7/10

**Positive**:
- Sprint 19 PR #1+#2 multitenancy I-9 정합 (composite FK + workspace_id WHERE 강제 + service _verify_secondary_fks)
- ADR-022 sync_user endpoint 비활성화 + 회귀 가드 (`test_auth_sync_disabled.py`) 정상 — Sprint 27c verify 통과
- Clerk JWT 검증 (PyJWKClient + cache TTL ≤ token exp) 정합 (Sprint 24 Codex F-1 fix)
- Secret 은 `SecretStr` + `.get_secret_value()` (I-15)
- production endpoint 401/403 거부 정확 (fake bearer token 차단 verify)

**Negative**:
- Clerk dev 인스턴스만 사용 (Production 미발급) — ADR-022 결정 정합 단, "Development mode" 표기 + creative-boxer-79.accounts.dev 도메인 production 노출 = 외부 사용자 trust ↓
- Real IDOR (다른 user valid token) 미검증 — Account #2 login 미시도
- Cloud Run secret rotation 정책 부재 (memory archeology 에서 보이지 않음)
- GEMINI_API_KEY 가 invalid = secret 관리 process 의 첫 실패 case

### 5. "내가 인수하겠나" — 7/10

**1인 founder 입장**:
- 코드 가독성 OK — 한국어 주석 + Sprint 별 fix archeology (memory linking)
- Test coverage = backend 452 PASS (Sprint 25 시점), FE 56 vitest. CI 통과 한 안전 baseline
- 22 sprint archeology (memory 30+ entries) 가 onboarding cost = 6-8h 이상 (높음)
- 1인 founder 가 22 sprint 동안 1명 dogfooding (PERSONA-001) 외 0 명 시그널 → 인수자가 PMF 확인 어려움
- Sprint 26 거버넌스 경량화 = "정상화" 단계로 받아들임 (positive)

**FAANG senior 입장**: 7/10 → 5/10 (다양한 patterns + over-engineering 우려). 본 audit 는 solo hacker lens 우선.

## 종합 Verdict

| 항목 | 점수 | 비고 |
|---|---|---|
| 아키텍처 sealed | 7/10 | 헌법 + 21 불변식 + cleanup sprints 정합 |
| **운영 readiness** | **3/10** | 🔴 **BLOCK trigger** — production instability + deploy stale + GEMINI_API_KEY |
| BL 부채 | 4/10 | 67 active = 1인 부담 |
| 보안 baseline | 7/10 | composite FK + sentinel pass + Clerk JWT |
| 인수의향 | 7/10 | 코드 OK, PMF 미증명 |

**평균: 5.6/10**

## 외부 5명 진입 결정 input

**자동 verdict**: 🔴 NOT-READY — **운영 readiness 3/10 (BLOCK 한계)** + P0 production deploy stale + P0 GEMINI_API_KEY invalid. 외부 5명 입장 시 dashboard broken + 회의 업로드 후 자동 요약 0 = 핵심 가치 0.

## 사용자 액션 권고 (audit 외, 우선순위)

1. **Cloud Run main HEAD `eb13a42` redeploy** (15분) — production deploy stale 즉시 해소
2. **GEMINI_API_KEY 재발급 + Cloud Run secret 동기화** (10분) — AI pipeline 회복
3. **production health check baseline 측정** (1h) — Cloud Run min instance 1 권고 (cold start 회피 추가 cost USD ~$10-15/month). 또는 CDN 헬스체크 + alert 설정
4. **Real IDOR test 1회** (15분) — Account #2 live cross-workspace 시도
5. Sprint 28 진입 전 BL 부채 stop 정책 — paid customer 1명 우선

## 인수의향 결론 (1인 hacker 입장)

코드 quality 7/10 ≥ "인수 가능". 단 **PMF 미증명 + 22 sprint 외부 시그널 0** = 인수 후 product pivot risk 큼. paid customer 1명 도달 후 인수 가치 명확.
