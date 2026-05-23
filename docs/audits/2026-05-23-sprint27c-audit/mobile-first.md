# Mobile-First — 모바일 chrome 사용자 (Pixel 5 viewport)

> 페르소나: 모바일 chrome 사용자. SNS 링크 click → 모바일 첫 진입. 가입 60%+ 모바일 가정.

## 6 시나리오 결과

| # | 시나리오 | 결과 | 비고 |
|---|---|---|---|
| 1 | LCP 측정 (Pixel 5) | ⚠️ partial | landing FCP 3-4s 추정 (production), localhost ~2s. Sprint 24 Wave 2 BUG-MOBILE-005 fix 적용 후 잔여 latency |
| 2 | landing → 가입 모바일 흐름 | 🔴 BLOCKED | Clerk sign-in form 모바일 보기 ok 단 HIBP 차단 issue 동일 |
| 3 | 모바일 회의 업로드 | ✅ partial | file picker 모바일 정상 (file_upload tool 통해 fixture 업로드 verify). 실 모바일에서는 iOS Files / 직접 녹음 권한 분기 추가 검증 필요 |
| 4 | mobile RAG UX (⌘K 대체 = touch) | ⚠️ partial | mobile 상단 헤더에 검색 버튼 존재. ⌘K 키바인딩은 mobile 의미 없음 — UI 버튼이 대안. 단 "AI 검색 ?" 발견 가능성 ↓ |
| 5 | FAB / bottom navigation | ✅ PASS | **mobile bottom nav 5탭 (홈/프로젝트/추가/Inbox/메모) 잘 구현됨** — Desktop 좌측 sidebar 대체. mobile-first 패턴 정합 |
| 6 | keyboard overflow | ⏸ NOT_TESTED | viewport emulation 의 한계 — 실 iOS Safari keyboard 거동 검증은 manual 필요 |

## 평가 점수

| 차원 | 점수 | 근거 |
|---|---|---|
| LCP < 2.5s (Good) | 6/10 | localhost 2s 통과, production 3-4s 추정 (Cold start 영향). Core Web Vitals "Needs Improvement" 영역 |
| 모바일 가입 완료율 (예상) | 4/10 | HIBP 차단 + dev domain 표시 동일. P0-AUTH 동일 |
| 모바일 RAG 직관성 | 6/10 | 검색 버튼 발견 가능. AI 검색 (?) prefix 는 mobile 에서 hint 약함 |
| critical mobile bug 수 | 0 (확인된 한도 내) | bottom nav + 상단 헤더 정상. FAB / dialog overlap 0 |

**평균: 5.3/10**

## 핵심 Findings

### POSITIVE — bottom nav 구현 (P2-positive)

**증상**: Pixel 5 viewport (393x851) 에서 5탭 bottom nav 자동 표시. 좌측 sidebar 자동 hide. 모바일 UX 표준 패턴 정합.

**Verdict**: ✅ 외부 5명 모바일 유입 시 navigation 직관성 OK.

### P1-MOBILE-COLD-START

**증상**: production landing LCP ~3-4s (Cloud Run cold start + Vercel CDN 일부). Core Web Vitals "Good" (<2.5s) 미달.

**Verdict**: SNS 유입 시 ad-blocker / 데이터 차단 환경의 사용자 이탈률 ↑. Sprint 24 BUG-MOBILE-005 fix (JWT cache) 가 partial 해소.

### P0-MOBILE-INHERIT (production 모바일 진입 시 dashboard 500)

**증상**: production 모바일에서도 desktop 과 동일한 P0-1 (dashboard 500) 재현. 모바일 사용자에게 더 치명적 (back 버튼이 SNS feed 로 복귀 = re-entry probability 0).

**Verdict**: Desktop 의 audit verdict 와 동일. P0 fix prerequisite.

### P2-MOBILE-SEARCH-? (AI 검색 prefix hint 부재)

**증상**: 상단 검색 버튼 = ⌘K palette. 단 "AI 검색 = ? 키" hint 가 mobile 에서 발견 가능성 ↓ (키보드 없음).

**Verdict**: mobile 전용 AI 검색 toggle 또는 placeholder 강화 P2.

## 외부 5명 진입 결정 input

**자동 verdict**: 🔴 NOT-READY (Desktop 과 동일 P0 inherit). Mobile 자체 UX 5.3/10 = production 동일 fix 후 6-7/10 가능.

## 사용자 액션 (audit 외, mobile 특화)

1. P0 fix (Cloud Run + GEMINI_API_KEY) — Desktop 과 동일 prerequisite
2. real iOS Safari 1회 manual 진입 verify — viewport emulation 한계 보완
3. SNS 유입 채널 별 OG image / Twitter card 모바일 미리보기 verify (CEO finding P2 동일)

## 모바일 페르소나 한 줄 평가

**"Bottom nav + 상단 검색 = mobile-first design 정합. 단 LCP 3-4s + production 500 = 외부 5명 모바일 유입 시 cold start 갭에서 30-50% 이탈 추정. P0 fix + Cloud Run min instance 1 권고."**
