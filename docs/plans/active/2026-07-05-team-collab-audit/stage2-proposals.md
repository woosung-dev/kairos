# Stage 2 제안 — 팀 협업 (2026-07-05 team-collab-audit 산출)

> 이번 스프린트에서 구현하지 않고 제안으로만 기록. 우선순위는 팀 협업 가치 기준 추정.

## A. 협업 기능 확장

1. **초대 승인(approval) 단계** — 현재 링크 소지+로그인=즉시 가입. pending 멤버 상태 + owner/admin 승인 큐 도입 시 보안 강화. 사용자 결정으로 이번엔 현행 유지 (2026-07-05).
2. **초대 이메일 발송** — 현재 링크 복사만. Clerk invitation API 또는 자체 SMTP. webhook SKIP(ADR-022) 상태와 정합 검토 필요.
3. **personal→team 승격 마이그레이션** — 의도적 lock-in (Sprint 15) 해제 검토. PLG 전환 퍼널의 핵심 마찰 지점: 개인으로 쌓은 데이터를 팀으로 가져가려면 현재 promote 를 항목별 반복해야 함.
4. **FE 프로젝트 생성 다이얼로그 visibility 셀렉터** — BE 는 이번에 연결됨(W-5 시드). UI 노출은 신규 e2e selector + 명세 갱신 비용 있어 이연.
5. **Promotion review queue (v1.7 로드맵)** — 기존 로드맵 유지.

## B. 인프라/성능

6. **RBAC 분산 캐시 invalidation** — in-process 60s TTL 은 Cloud Run 다중 인스턴스에서 role 강등이 최대 60s 지연. Redis pub/sub 또는 DB 버전 칼럼. GA 전 필수 검토.
7. **hybrid search 병렬화 (PERF-r2-3)** — vector/text 순차 await. 동일 AsyncSession 이라 세션 2개 분리 + SET LOCAL 재설계 필요. 이번에 넣은 `rag.timing` 로그로 search 구간이 유의미하면 진행.
8. **cursor pagination 5도메인 (BUG-S28-PERF-1)** — 데이터량 증가 시.
9. **RAG p95 < 5s (BL-S27e-1)** — `rag.timing` 로그 분포 확보 후 Sentry perf 와 묶어 대응. LLM 구간이 지배적이면 모델/스트리밍 UX 로 해소.
10. **WorkspaceMember soft delete (BL-S27-1) + AdminAccessAudit (BL-S27-3) + Member.last_active_at (BL-065)** — 기존 백로그 유지.

## C. QA 인프라

11. **팀 e2e CI 통합** — T1~T19 를 nightly-e2e.yml 에 추가 (QA 계정 secret 필요). 현재 로컬 수동 전용.
12. **T-UI-1 모바일 햄버거 nav** — 랜딩 페이지 한정 (기능/요금 앵커 2개). 팀 초대 깔때기는 랜딩 nav 미경유 + 앱 내 bottom-nav 존재 확인(2026-07-05 360px 실측) — 우선순위 낮음 유지.

## 관찰 기록 (조치 불필요, 참고)

- private 전환 시 member 의 열려있던 상세는 조용히 /projects 목록으로 리다이렉트 — 존재 은닉 보안 태세와 정합.
- Clerk dev 인스턴스가 모든 페이지에서 `/v1/environment` PATCH 400 을 냄 — 외부 노이즈, 앱 발 console.error 0건.
- dev 모드 페이지 로드(networkidle): dashboard 4.4s / settings 4.9s / projects 2.7s / notes 3.4s (Neon RTT + dev 빌드 기준 참고치).
- 360px 톱바 검색 placeholder 가 좁게 찌그러짐 — 코스메틱, 협업 표면 밖.
