# Integrated Defect Matrix — Sprint 18 → 19 Multi-Agent QA Step 4

| 항목 | 값 |
|---|---|
| 작성 시각 | 2026-05-17 KST |
| 범위 | Curious / Casual / Mobile / Power 4 페르소나 smoke |
| 환경 | local (FE :3000 + BE :8000), Sentinel A 로그인 (E2E 테스트 워크스페이스 자동 매핑) |
| 자동화 | Playwright MCP + axe-core 4.10.0 + curl + Clerk session token fetch |

---

## 1. 결함 카운트 매트릭스 (페르소나 × Severity)

| 페르소나 | Critical | High | Medium | Low | 총계 | Persona Health |
|---|---|---|---|---|---|---|
| **Curious** (40min cap) | 0 | 2 | 4 | 2 | 8 | 5.0 |
| **Casual** (40min cap, 정정 후) | 0 | 2 | 5 | 2 | 9 | 4.0 |
| **Mobile** (60min cap) | 0 | 2 | 3 | 1 | 6 | 4.4 |
| **Power** (60min cap) | 0 | 3 | 3 | 1 | 7 | 3.4 |
| **합계** | **0** | **9** | **15** | **6** | **30** | — |

(Persona Health Score: `max(0, 10 - (C×3 + H×1.5 + M×0.5 + L×0.1))` — 일부는 cross-persona carry-over로 ±0.5~1 가중)

## 2. Composite Score 추정

raw composite (사용자 지정 가중치):
```
raw = Curious×0.20 + Casual×0.15 + Mobile×0.15 + Power×0.15
    = 5.0×0.20 + 4.0×0.15 + 4.4×0.15 + 3.4×0.15
    = 1.00 + 0.60 + 0.66 + 0.51
    = 2.77 / 0.65 (정규화)
    ≈ 4.26 / 10
```

**Guardrail**: P0 (Critical) 발견 0건 → cap 적용 없음.
**Sentinel P0** (별도 보고서 `qa-report.md`) = 10.0/10 → composite 결합 시 +α.

**최종 추정**: 4.3~4.5 / 10. Sprint 18→19 진입 시 **Critical 0 (BUG-C01 완전 fix 확인)**이지만 High 결함 9건 누적 — fix backlog 진입 권장.

## 3. Top 5 Sprint 19 후보 결함 (BUG-CNN / ISSUE-NNN)

| 우선 | 후보 ID | 영역 | 결함 한 줄 | 출처 | 권장 fix 사이즈 |
|---|---|---|---|---|---|
| 1 | **BUG-C02** | 라우팅 / 모바일 primary nav | `/projects` 404 — BottomNav 5개 primary 중 1개 깨짐 + dashboard "빠른 접근" 카드도 깨짐 | Mobile H-1 / Casual H-2 | S (라우트 신설 또는 nav 제거) |
| 2 | **BUG-C03** | 라우팅 | `/meetings` 404 — dashboard "최근 활동" 미팅 data 있지만 list view 없음 | Casual H-1 | M (list view 신설) |
| 3 | **ISSUE-018** | 단축키 / 핸들러 미연결 | Cmd+K palette UI에 시퀀스 단축키 (G I/G P/G N/G S/C) 안내 있지만 실제 핸들러 미연결. "안내 vs 실행" gap. | Power H-1 | S (useHotkeys 시퀀스 추가) |
| 4 | **ISSUE-019** | 벌크 작업 | Inbox 16건 → checkbox 0 / 전체 선택 0 / 벌크 액션 0. Power 사용자 16번 클릭 강제. | Power H-2 | M (선택 상태 + 벌크 confirm/dismiss API 연결) |
| 5 | **BUG-C04** | Export UI 누락 | BE에 `/meetings/{id}/export` + `/notes/{id}/export` 2 endpoint 존재. FE 어디에도 export 버튼 없음. | Power H-3 | S (note/meeting detail에 버튼 + 드롭다운) |

## 4. 그 외 High 결함 (Sprint 20+ 후보)

| ID | 결함 | 출처 |
|---|---|---|
| ISSUE-020 | 랜딩 페이지에 제품 시각자료 (스크린샷·비디오) 0개 | Curious H-1 |
| ISSUE-021 | 워크스페이스 전환 메뉴 클릭 → URL/UI 미변경 | Curious H-2 |
| ISSUE-022 | a11y / 모바일 BottomNav 터치 타겟 36~40px (≤ 44pt 위반) | Mobile H-2 |

## 5. Sentinel P0 (참고)

별도 보고서 `qa-report.md` v2 (2026-05-17 19:20):
- 28/28 PASS (BUG-C01 fix 후)
- RAG visibility 3-layer + Workspace IDOR 회귀 0
- Sentinel Health 10.0/10

본 통합 매트릭스에는 Sentinel 결함이 포함되지 않음 (별 라인 검증).

## 6. 진행 중 [확인 필요] 항목

- **시드 워크스페이스 매핑**: Sentinel A 로그인 후 자동 매핑된 워크스페이스가 "E2E 테스트 워크스페이스" (다른 setup). 시드 fixture `9966a04e-0db3-4d65-a5fe-6c5c4f49901d` (WS-QA-SENTINEL_A-2026-05-17)는 드롭다운 3번째 항목으로 존재. → 시드 단계에서 새 가입 user의 default workspace를 시드 ws로 설정해야 동등 비교 가능. (Curious H-2 부분과 연관)
- **Workspace switch 동작 검증**: 메뉴 클릭으로 워크스페이스 전환이 실제로 fail하는지, UI 시각 피드백만 누락인지 추가 검증 필요. localStorage / cookie 변경 여부 확인 미실행.
- **랜딩 페이지 a11y**: 로그인 상태에서 `/` → `/dashboard` 자동 redirect로 anonymous 랜딩 a11y 측정 못함. logout 후 재측정 권장.
- **3G throttle / 모바일 페이지 로드**: Mobile smoke에서 제외. nightly 검증 권장.

## 7. 산출물 디렉토리 구조

```
docs/dev-log/qa/2026-05-17-multi-agent-qa-sprint18/
├── interested-user-report.md (Curious)
├── general-user-report.md (Casual)
├── mobile-user-report.md (Mobile)
├── power-user-report.md (Power)
├── integrated-defect-matrix.md (본 문서)
├── curious/
│   ├── landing-desktop.png
│   ├── signup.png
│   └── dashboard-firstview.png
├── casual/
│   ├── inbox-empty.png
│   └── memory-search.png
├── mobile/
│   ├── iphone-se-dashboard.png
│   ├── iphone-se-projects-404.png
│   ├── iphone-se-inbox.png
│   ├── pixel7-new-capture.png
│   └── pixel7-recording.png
├── power/
│   └── cmdk-palette.png
├── granola-comparison/
│   └── landing.png
└── traces/ (Critical 0건 → 미생성)
```
