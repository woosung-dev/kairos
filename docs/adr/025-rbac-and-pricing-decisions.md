# ADR-025 — RBAC 권한 모델 + 가격 thesis 결정 (Sprint 5)

**Status**: Accepted (권한 모델 — 구현 완료) / Proposed (가격 thesis — 최종 lock-in 이연)
**Date**: 2026-04-04 (결정) · 2026-06-23 (ADR 등재 — git history 복원)
**Sprint**: 5 (RBAC + 초대 시스템)
**관련**: ADR-014 (권한 검증 위치) · ADR-016 (Personal↔Team IA + ProjectMember) · ADR-024 (§후속 "ADR-025 pricing 결정" forward-ref 가 본 ADR)

## Context

Sprint 5 (2026-04-04) 에서 RBAC 권한 모델과 가격 모델을 함께 결정했다. 당시 설계 spec(`docs/superpowers/specs/2026-04-04-sprint5-rbac-design.md`)은 이 결정을 "ADR-007"로 등재할 예정이라 표기했으나, ADR-007 번호는 이후 LLM Knowledge Base 인사이트(`007-llm-knowledge-base-insight.md`)로 확정되며 **RBAC/가격 결정은 정식 ADR 없이 spec 에만 남았다.**

2026-06-23 cleanup(`5c7dc4b`)이 `docs/superpowers/` 트리를 삭제하면서 결정 근거(5안 비교·기각 사유·가격 thesis)가 canonical 에서 사라졌고, git history 포렌식으로 손실이 확인되어 본 ADR 로 distill 복원한다. 결과(4-role)는 코드·헌법에 살아있었으나 **"왜 그 모델을 골랐는가"는 어디에도 없었다.**

## Decision

### 1. 권한 모델 — 방안 2 (RBAC + ProjectMembership) 채택, 단계적 ship

5안 가중 비교:

| 방안 | 설명 | 점수 | 판정 |
|------|------|:---:|------|
| 1. 단순 RBAC | 워크스페이스 레벨만 | 44 | MVP 최소 |
| **2. RBAC + ProjectMembership** | 워크스페이스 + 프로젝트 공개 범위 | **53** | **채택** |
| 3. ReBAC (Zanzibar) | 관계 기반 세밀 권한 | 46 | 과잉 설계 → 기각 |
| 4. ABAC/PBAC | 정책 기반 속성 권한 | 41 | 과잉 설계 → 기각 |
| 5. Creator 기반 (Coda식) | 생성자만 과금 | 42 | Kairos 가치 불일치 → 기각 |

- **기각 근거**: ReBAC/ABAC 는 1인 founder + 소규모 팀 단계에 과잉 설계. Creator-과금(Coda식)은 "팀의 세컨드 브레인" 가치(모두가 기여·열람)와 불일치.
- **단계적 ship**: Sprint 5 = 워크스페이스 레벨 4-role RBAC, Sprint 6+ = ProjectMember 확장(project visibility `public`/`draft`/`private`). 현재 둘 다 구현 완료 (ADR-014 권한 검증 위치 + ADR-016 Personal↔Team IA 정합).

### 2. 4단계 역할 위계

| 역할 | 레벨 | 권한 요약 |
|------|:---:|------|
| Owner | 4 | 전체 관리(워크스페이스 삭제·역할 변경·모든 CRUD) |
| Admin | 3 | 멤버 초대/제거·모든 콘텐츠 CRUD·프로젝트 Archive |
| Member | 2 | 본인 콘텐츠 CRUD·타인 콘텐츠 읽기·RAG 질문 |
| Viewer | 1 | 읽기 전용·RAG 질문만 |

> canonical 구현 = `backend/src/auth/rbac.py` + CONTEXT-MAP §6 I-9 (RBAC 불변식). 위 표는 결정 당시 요약.

### 3. 가격 thesis — per-seat + AI 사용량 캡 (Proposed, 미확정)

| 플랜 | 가격 | 멤버 | 회의/월 | RAG/유저/월 | 저장 |
|------|------|:---:|:---:|:---:|:---:|
| Free | $0 | 5명 | 5건 | 50회 | 1GB |
| Pro | $10/user | 무제한 | 30건 | 300회 | 50GB |
| Business | $20/user | 무제한 | 100건 | 1,000회 | 500GB |
| Enterprise | 커스텀 | 무제한 | 무제한 | 무제한 | 무제한 |

- **비용 근거**: RAG 질문 1건 ~$0.0005 (무시 수준), 회의 인제스트 1건(30분) ~$0.18 (Whisper 가 핵심 원가). 모든 유료 시나리오에서 **89%+ 마진**. RAG 횟수 제한은 비용 방어가 아닌 **인지적 업셀 장치**.
- **최종 lock-in 이연**: 가격 인프라(결제 연동·사용량 추적)는 Sprint 5 범위 밖. 정식 가격 결정은 ADR-024 종료 기준(**paid customer 1명**) 도달 시점으로 이연. (PRD §7 의 `$19 flat 포지셔닝`과는 별개 thesis 이므로 정식 결정 시 정합 필요.)

### 4. 결제 PG 전략 (방향만)

3단계 확장: ① 포트원+토스(한국)/PayPal → ② Stripe Atlas(PMF 후) → ③ 세금계산서·Invoice+Wire(scale). 코드는 PG-agnostic `PaymentProvider` 추상화로 설계해 Provider 클래스만 교체.

## Consequences

- **즉시 효과**: RBAC 결정 추적성 회복 — ReBAC/ABAC/Coda 기각 근거가 미래 재논의(예: enterprise 보안 요구) 시 grep 가능.
- **가격**: thesis 단계. Stripe/사용량 추적 미구현 (의도적). 정식 결정 = 별도(본 ADR 의 §3 supersede 또는 후속 ADR).
- **ADR 위생**: ADR-024 §후속의 "ADR-025 pricing 결정" forward-ref 해소. ADR-007 번호 혼선(spec 의 잠정 라벨)도 본 Context 로 명시.

## References

- 원문 (git history, 복원 아님): `git show 5c7dc4b^:docs/superpowers/specs/2026-04-04-sprint5-rbac-design.md`
- ADR-014 (Service-to-Service 경계 / 권한 검증 위치) · ADR-016 (Personal↔Team IA + ProjectMember) · ADR-024 (GA readiness, pricing forward-ref)
- CONTEXT-MAP §6 I-9 (RBAC 불변식) · `backend/src/auth/rbac.py`
