# General-User — 30대 PM 첫 인상 (문서 0 read)

> 페르소나: 30대 직장인 PM. 회의 많음. AI 도구 friendly (ChatGPT/Cursor). 5초 룰 엄격. SNS/유튜버 추천 보고 첫 진입.

## 6 시나리오 결과

| # | 시나리오 | 결과 | 측정값 |
|---|---|---|---|
| 1 | landing 5초 첫 인상 | ⚠️ partial | hero 명확 (5초 안에 "AI 회의 정리" 인지). **단 "이미 동작하는 제품입니다" 섹션 screenshot 3건 모두 깨짐 → trust 직격타** |
| 2 | 가입 흐름 (OAuth or email) | 🔴 BLOCKED | Clerk HIBP password breach detection 이 단순 password 영구 차단. dev 인스턴스의 "Development mode" + creative-boxer-79.accounts.dev 도메인 노출 |
| 3 | onboarding tooltip 발화 | ✅ PASS | dashboard 진입 시 "AI 검색은 ⌘K" + CmdK 진입 시 "검색 범위는 현재 워크스페이스 전체입니다" tooltip 정상 (Sprint 22 OBN-04) |
| 4 | 첫 회의 업로드 | ⛔ DOWNSTREAM-FAIL | 업로드 자체 가능 (R2 presigned OK), 단 **AI 처리 실패 = "실패" status 표시 + retry 옵션 없음** = "이게 정말 동작하는 제품인가" 의심 |
| 5 | 첫 RAG query (⌘K) | ⚠️ partial | ⌘K palette 진입 가능. ? 키 = AI 검색 (well-discovered). 단 데이터 0 + AI 실패라 의미 있는 응답 부재 |
| 6 | 12분 안에 "쓰겠다 vs 닫겠다" 결정 | 🔴 닫겠다 | 외부 5명 페르소나 emulation 기준: **12분 안 3+ 이탈 지점** 발생 (production 500 + 가입 마찰 + 회의 처리 실패) |

## 이탈 지점 매핑 (Critical Path)

```
[Landing] ──── 5초 hero OK ──── ✅ proceed
   ↓
[Sign-up CTA] ──── "Development mode" 표시 + dev 도메인 ──── 🚧 hesitation (이탈 risk 30%)
   ↓
[Clerk sign-up form] ──── HIBP password 차단 (약한 pwd 사용 시) ──── 🔴 이탈 1
   ↓
[Production dashboard] ──── 500 errors (현재 production) ──── 🔴 이탈 2 (즉시 닫음)
   ↓
[(localhost equivalent) Dashboard] ──── ✅ 정상 (8.2s 첫 호출 latency)
   ↓
[새 회의 업로드] ──── R2 OK + 202 Accepted ──── ✅ proceed
   ↓
[Meeting detail] ──── 5-10s 대기 → status="실패" ──── 🔴 이탈 3 (핵심 가치 0)
   ↓
[Closes tab]
```

**이탈 지점 = 3건** (production 진입 시) → audit decision policy §5: **이탈 ≥ 3건 → 🔴 BLOCK**

## 평가 점수

| 차원 | 점수 | 근거 |
|---|---|---|
| 직관성 | 5/10 | Hero + CTA 명확, dashboard nav 간결. 단 production fail 로 진행 불가 |
| 이탈 지점 수 | 3 (high) | 가입 마찰 + dashboard 500 + 회의 처리 실패 |
| 유튜버 추천 가치 | 3/10 | 현재 상태로는 추천 시 "동작 안 함" 클레임 risk. P0 fix 후 6/10 가능 |
| 첫 업로드 도달 시간 | N/A | 업로드 자체는 ~3분 가능 (가입 1.5min + workspace 8s + /new 30s + 업로드 1min). **단 결과 확인 = fail** |

## 핵심 Findings

### P0-USER-EXIT (이탈 ≥ 3건, BLOCK trigger)

**증상**: 본 audit policy §5 의 "일반 사용자 이탈 ≥ 3건 → 🔴 BLOCK" 조건 충족. production 의 dashboard 500 + AI pipeline 실패 + dev 도메인 마찰의 누적 효과.

**Verdict**: 외부 5명 모집 → 평균 60-80% 즉시 이탈 예상.

### P0-VALUE-DEAD (핵심 가치 0)

**증상**: 회의 업로드 후 "AI 자동 요약" 가치 = 0. status `실패` + retry 부재.

**Verdict**: Kairos 의 정체성 ("AI가 정리합니다") 가 첫 사용 첫 5분 안에 fail = **value prop unfulfillment** 가장 치명적 finding.

### P1-FIRST-VIEW-DEVMODE (Development mode 표시)

**증상**: Clerk sign-in 페이지 footer "Development mode" + 회원가입 링크 도메인 `creative-boxer-79.accounts.dev`.

**Verdict**: 30대 PM 페르소나가 "이거 정식 서비스인가" 의심 발생. 외부 5명 모집 시 conversion rate ↓.

### P2-POSITIVE-ONBOARDING (긍정 finding)

**증상**: dashboard 진입 시 onboarding tooltip 자연스럽게 발화. ⌘K 진입 시 안내 명확.

**Verdict**: Sprint 22 OBN-04 정상 동작. 본 audit 의 positive evidence.

### P2-INBOX-EMPTY-NO-GUIDE

**증상**: 신규 가입 직후 `/inbox` 진입 = empty state UI 없음. "AI 가 회의 분류한 항목" 이라는 explanation 만으로는 "왜 비어있는지" 안내 부재.

## 외부 5명 진입 결정 input

**자동 verdict**: 🔴 BLOCK — 이탈 지점 3건 + 직관성 5/10 (BLOCK 한계 5/10 경계 + 1 P0 value-dead).

## 사용자 액션 (audit 외)

1. **P0 fix 후 (Cloud Run redeploy + GEMINI_API_KEY) → 재진입 audit 시 직관성 7/10 + 이탈 1건 미만 추정**
2. Production env 의 Clerk Production 인스턴스 발급 (현재 dev) — `Development mode` 표시 제거. 단 ADR-022 SKIP 결정 정합성 검토 필요
3. Meeting 실패 시 retry 버튼 + 명확한 root cause 안내 (P1 follow-up)

## 30대 PM 한 줄 평가

**"hero 는 매력적. 회의 업로드 까지는 OK. 그러나 '자동 요약' 약속이 깨지면 다시 안 옴. P0 fix 가 모든 conversion 의 prerequisite."**
