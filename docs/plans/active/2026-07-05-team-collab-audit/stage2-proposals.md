# Stage 2 제안 — 팀 협업 (2026-07-05 team-collab-audit 산출)

> 이번 스프린트에서 구현하지 않고 제안으로만 기록. 우선순위는 팀 협업 가치 기준 추정.

## 처리 현황 (2026-07-05 재평가 세션, 실측 기반 — branch `sprint/stage2-followup`)

| # | 항목 | 처리 |
|---|---|---|
| 1 | 초대 승인 단계 | **제외** — 사용자 기결정(현행 유지) |
| 2 | 초대 이메일 발송 | **제외** — 이메일/Clerk invitation 코드 0건, ADR-022/024 webhook SKIP 상태라 Clerk Production 컷오버 세션에 묶음 |
| 3 | personal→team 승격 | **이연** — 의도적 lock-in(I-19) 유지, 외부 PLG 신호 후. 중간 단계 후보 = bulk promote |
| 4 | FE visibility 셀렉터 | ✅ **구현** — create-project-dialog Select(기본 옵션="워크스페이스 기본값"=미전송, W-5 폴백 보존) + e2e T20 3케이스. 멤버 시드 prefill 은 BE 3계층 변경이라 후속 후보 |
| 5 | Promotion review queue | **이연** — v1.7 로드맵 유지 |
| 6 | RBAC 분산 캐시 | ✅ **경량안 구현** — Redis/DB버전 비교 후 기각(비용표는 세션 플랜 참조). admin/owner 게이트 캐시 bypass + TTL 60→15s. cross-instance 파괴 연산 창 0, 읽기 stale ≤15s (auth/CONTEXT.md §5.1) |
| 7 | hybrid search 병렬화 | ❌ **실측 기각** — vector/text 분리 계측 후 n=20: 이득 p50=198ms < 판정선. PERF-r2-3 종결, 신규 레버 PERF-r2-6/7 등재 |
| 8 | cursor pagination | **이연** — 데이터량 소, audit 도메인 cursor 레퍼런스 존재 확인 |
| 9 | RAG p95<5s | 📊 **실측 확보** — n=20 분포로 BL-S27e-1 갱신. llm 비중 44%로 "LLM 지배" 반증, 레버 재서열화 |
| 10 | soft delete + audit + last_active | **이연** — 백로그 P3 유지 |
| 11 | 팀 e2e CI 통합 | ✅ **구현** — nightly-e2e.yml team step(T1~T20, workers=1) + trace artifact 분리. **사용자 작업**: GitHub secrets 4개(`QA_LOCAL_OWNER_EMAIL/PASSWORD`, `QA_LOCAL_MEMBER_EMAIL/PASSWORD`) 등록 후 workflow_dispatch 1회 실증 |
| 12 | T-UI-1 햄버거 | **이연** — 기능 손실 0 재확인 |

> 부수 발견·수정: BUG-CACHE-DETACHED-EXPIRED — User/Member in-process 캐시가 live ORM 인스턴스를 보관, expire+detach 시 전 요청 500 연쇄 (PR #135 members JOIN 이후 발현). 캐시 get 자가치유 가드 + 회귀 테스트 2건.

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
