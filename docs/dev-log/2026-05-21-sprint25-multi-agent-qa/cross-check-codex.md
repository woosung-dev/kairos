# Cross-Check — codex review + challenge

> Sprint 25 Multi-Agent QA 통합 보고서 적대적 검증
> 호출: 2026-05-21 (KST), `codex exec` CLI (codex-cli 0.132.0)
> session: cosmic-knitting-island

## Verdict

| 단계 | 결과 |
|------|------|
| review | **FAIL** — 보안 결함과 GTM 결손을 같은 P0 버킷에 넣어 실행 우선순위가 흐려짐 |
| challenge | **partial flip** — S-005 no-flip, TRUST/PRICING P0 → P1로 flip |

## 핵심 review 결과

### 1. BUG-SENTINEL-005 (Critical) — no-flip ✅

> `auth_router`가 `main.py`에 공개 include되고, `/api/v1/users/sync`에 인증도 Svix 검증도 없으며 PoC 200 OK면 "internal-only일 수도 있음"은 반론이 아니라 미입증 가정입니다.

**메인 세션 평가**: 동의. Critical 유지. codex가 `backend/src/main.py:132 app.include_router(auth_router)` 라인을 직접 grep으로 확인하여 공개 routing 입증.

### 2. ★★★ TRUST + ★★★ PRICING P0 → P1로 flip ⚠️

> P0는 `BUG-SENTINEL-005`, `BUG-CASUAL-001`만 남기는 게 합리적입니다. TRUST와 PRICING은 베타에서는 P0가 아니라 P1 또는 "GA launch blocker"입니다. 결제 전환에는 치명적이지만 시스템 보안·데이터 무결성·가입 가능성을 즉시 깨지는 않습니다.

**메인 세션 평가**: **수용**. 베타/Pre-GA 단계의 "치명적 결함"의 정의는 (1) 시스템 보안 (2) 데이터 무결성 (3) 가입 가능성으로 한정하는 것이 합리적. TRUST/PRICING은 GA launch blocker 또는 마케팅 wedge로 분리.

### 3. Composite Score 산식 비판

> Composite 산식은 Sentinel 0.5 자체는 합리적이나, 보안 점수와 마케팅 신뢰 점수를 단일 health로 합치는 건 왜곡입니다. Security/Product/GTM 3개 점수로 분리해야 합니다.

**메인 세션 평가**: **수용**. 단일 Composite은 의사결정 신호 흐림. 3축 분리로 재정규화:

| 축 | 정의 | Sprint 25 산출 |
|---|---|---|
| **Security** | Sentinel S1~S4 (보안/데이터 격리/회귀) | 4.55 / 10 |
| **Product** | Casual U1~U3 (과업 직관성/용어/a11y) + Sentinel S2/S3 일부 | 4.6 / 10 (U1 4.0 + U2 3.3 + U3 6.5 평균) |
| **GTM** | Curious C1~C4 (TTFV/룰/경쟁사) + Casual U4 (디자인) | 7.0 / 10 (Curious 6.17 + ui-ux-pro-max 7.85 평균) |

**해석**: GTM은 비교적 양호하지만 Security/Product가 동시에 5 미만 → 베타 단계에서 시스템 신뢰 확보가 GTM 작업의 선결 조건.

### 4. 누락 회귀 영역 (codex 지적)

| 영역 | 메인 세션 조치 |
|------|----------------|
| 인증 게이트 안쪽 CRUD/RBAC | Sprint 25 Wave 2에 추가 (Playwright + Clerk Prod e2e 인프라 도입 시 동반) |
| Webhook idempotency | BUG-SENTINEL-005 fix 시 동반 (Svix 서명 + idempotency key 검증) |
| 더미 user 데이터 오염 정리 | Phase 4에서 cleanup task로 명시 (Neon SQL DELETE) |
| Upload 이후 R2/DB 정합성 | BUG-SENTINEL-003 fix 시 동반 (size limit + R2 putObject 트랜잭션 정합) |

### 5. Challenge partial flip 반영

| 원래 P0 | flip 후 (codex) | 사용자 결정 정정 (2026-05-21) |
|---------|------------------|--------------------------------|
| BUG-SENTINEL-005 | P0 유지 (Critical) | P0 유지 + **권고를 endpoint 비활성화로 변경** (Clerk webhook SKIP 결정으로 Svix 검증 무의미) |
| BUG-CASUAL-001 (Clerk Prod) | P0 유지 | **Out-of-Sprint** (Clerk Production 발급 SKIP 결정) — 정책 재분류 |
| ★★★ TRUST | P1로 강등 (GA launch blocker) | P1 유지 |
| ★★★ PRICING | P1로 강등 (GA launch blocker) | P1 유지 |

## 최종 조치 항목

1. integrated-defect-matrix.md + integrated-report.html에서 P0 → P1 강등 적용
2. Composite Score를 Security/Product/GTM 3축으로 재정규화
3. Sprint 25 plan Wave 1을 BUG-SENTINEL-005 + BUG-CASUAL-001만으로 압축
4. 누락 회귀 영역 4건을 Sprint 25 Wave 2/3에 명시 등재

## codex 사용 메타

- CLI: codex-cli 0.132.0
- 호출 mode: `codex exec --skip-git-repo-check`
- 사용 토큰: ~25,535
- 실 검증 행위: codex가 직접 `rg`로 `auth.router|include_router|users/sync` grep하여 공개 routing 확인 → "internal-only 가정"을 미입증으로 기각
