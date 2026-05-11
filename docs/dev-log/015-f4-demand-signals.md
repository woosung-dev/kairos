# ADR-015 F4 수요 신호 관찰 기록

> 상태: **draft**
> 작성일: 2026-05-12
> 관련: ADR-009 §F4, ADR-010 AD-8, ADR-011 §4-b

---

## 컨텍스트

ADR-009 §F4는 외부 인터뷰 5-10명을 통해 S5/S6 수요 신호를 측정한다.
`docs/requirements/interview-guide.md`(Sprint 7 T-DOC-1, c2e5198)의 7필드 우회 질문을 사용.

### 측정 배경

Sprint 8 E2E 검증 완료 후(2026-05-12), 프로덕션이 충분히 안정적이라고 판단.
외부 인터뷰이에게 프로덕션 URL(https://kairos-zeta-ebon.vercel.app)을 공유하여
실제 사용 경험 기반 수요 신호를 측정한다.

---

## 측정 계획

| 항목 | 내용 |
|------|------|
| 인터뷰 목표 | 5-10명 외부 인터뷰이 |
| 1차 목표 | 1-2명 (킥오프) |
| 프로덕션 URL | https://kairos-zeta-ebon.vercel.app |
| 가이드 문서 | `docs/requirements/interview-guide.md` |
| 결과 기록 | `docs/requirements/interview-results.md` |

---

## S5/S6 임계값 정의

### S5 — "통합 도구로 대체 어려움" 응답률

| 구분 | 기준 |
|------|------|
| 목표 | ≥60% |
| 측정 시점 | 외부 인터뷰 5-10명 완료 후 |
| PASS 트리거 | ADR-010 thesis PASS → F6 Wedge 선정 ADR 진입 |
| FAIL 트리거 | ADR-010 thesis 조정 검토 필요 |

### S6 — 페르소나-Wedge 분화

| 구분 | 기준 |
|------|------|
| 목표 | 1순위 Wedge ≥2개 분화 |
| 현재 가설 | W3(2명) + W1(1명) = 2개 분화 (ADR-011 §4-c 충족 가설) |
| PASS 트리거 | 현재 가설 유지 → PERSONA-002/003 interview-confirmed 업그레이드 가능 |
| FAIL 트리거 | ADR-011 §4-c Wedge 재정의 ADR 신규 |

---

## 관찰 일정

| 단계 | 일정 | 상태 |
|------|------|------|
| 1차 인터뷰 (1-2명) | 2026-05-XX | 대기 중 |
| 중간 집계 | 1차 완료 후 | 대기 중 |
| 전체 완료 (5-10명) | 2026-XX-XX | 대기 중 |

---

## 자의 결정 라벨

- **AD-15-1**: 1차 1-2명 킥오프 후 임계값 예비 검토 진행 (전체 완료 전 방향 조정 가능)
- **AD-15-2**: PERSONA-002/003 `[가설]` → `interview-confirmed` 전환은 F4 완료 후에만 결정

---

## 결과 (인터뷰 완료 후 업데이트)

→ `docs/requirements/interview-results.md` 참조

**최종 판정:**
- [ ] S5 PASS / FAIL
- [ ] S6 PASS / FAIL
- [ ] 후속 ADR 트리거 결정
