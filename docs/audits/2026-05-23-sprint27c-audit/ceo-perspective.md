# CEO — Product-Market + GTM lens

> 페르소나: YC partner Garry Tan 톤. demand reality + 6 forcing question lens. "이거 누가 쓰나" 1문장 forcing question.

## 평가 5축 (각 10점)

### 1. 차별점 명확성 (Notion AI / ChatGPT memory vs Kairos) — 6/10

**Positive**:
- Hero "AI가 정리합니다. 당신은 결정만 하세요." 가 명확한 가치 promise
- CODE 파이프라인 4단계 (Capture → Organize → Distill → Express) — Tiago Forte 차용으로 framework recognition
- "Notion은 정리해야 합니다. Kairos는 정리됩니다." (PRD §7-Marketing) = 강력한 differentiator
- L1~L4 distill 4 level visualization = depth 표현
- "WITHOUT vs WITH KAIROS" 비교 카드 (회의록 어디에 + 결정 기억 + 신입 온보딩) = pain-point matching

**Negative**:
- **ChatGPT (auto memory) vs Notion AI (in-context) vs Kairos** 비교 부재 — landing 어디에도 "왜 ChatGPT memory 가 부족한가" 명시 안 됨. 2026년 시점 ChatGPT memory 가 사용자 default 가능
- "한국팀을 위한" 강조 = market scope 명확. 단 글로벌 SaaS 와의 차별 약함
- L4 조직 인사이트 = 미구현 상태인데 landing 에 strong claim ("조직이 같은 실수를 반복하지 않는다") — 외부 5명에게 over-promise risk

### 2. value prop 5초 룰 — 5/10 — 🟡

**관찰**: landing 진입 첫 5초:
- 1초: "AI가 정리합니다. 당신은 결정만 하세요." (hero)
- 3초: "Capture → Organize → Distill → Express" + "한국팀의 회의, 노트, 자료" (CODE 라벨)
- 5초: "5분 안에 시작 · 베타 무료 · 신용카드 불필요" + 무료로 시작하기 CTA

**Positive**: 명확한 hero + CTA. 5초 안에 "회의 자동화" 인지 가능.

**Negative**:
- **"이미 동작하는 제품입니다" 섹션의 screenshot 3건 모두 깨짐** (`screenshot-dashboard.png` + `meeting-summary.png` + `rag-answer.png` 400). 5초 룰을 통과한 후 사용자가 살펴보는 순간 "목업이 아닙니다" 라는 글자 옆에 깨진 이미지 = **trust 직격타** = P0 ship-blocker 후보 (CEO + General-User 합의)
- 95% / 12x / 24h stats 은 [확인 필요] 라벨 부재 = PRD §2.3 의 [가설] 라벨 정합성 위반
- "조직 인사이트" claim 미구현 상태로 노출 = over-promise

### 3. pricing 신뢰 — 7/10

**Positive**:
- "베타 무료 · 신용카드 불필요" 명시
- pricing 페이지 진입 가능 (`/pricing`)
- Open dev-log 정책 (footer + ADR transparent)

**Negative**:
- pricing 페이지 자체 audit 미실행 (시간 부족 — `/pricing` navigate 미수행)
- paid plan 가격 안내 없음 (베타 무료 후 어떤 가격) → SNS 공유 시 "그래서 얼마인데" 답 부재
- ADR-025 pricing 결정 미실행 (Sprint 28+ 이후)

### 4. SNS 공유성 — 4/10

**Positive**:
- "Built with Clerk · Neon · Cloudflare R2 · Google Cloud · Vercel" footer = builder credibility
- 한국어 + 영어 잘 섞임 (CODE / Capture 등은 영어 유지)

**Negative**:
- **OG tag / Twitter card meta** 별도 verify 안 했지만 추정으로 stock generic 일 가능성
- 외부 5명 모집 시 SNS 공유에서 "Twitter card preview" / "LinkedIn share image" 매력 unknown
- broken screenshot 3건이 OG image 까지 영향 가능성 (예: page screenshot 자동 OG generator 사용 시)
- founder 신뢰 — LinkedIn / GitHub / Twitter handle 노출 없음 (`Built with...` 만)

### 5. 투자의향 (YC partner 본능) — 5/10

**6 Forcing Questions (YC Office Hours)**:

1. **demand reality** — 외부 user 0명. 22 sprint 동안 dogfooding 1명 (founder 본인). [확인 필요]
2. **status quo** — Granola (회의만) / Otter (회의만) / Mem (노트) / Notion AI (인-도큐먼트). Kairos 의 wedge = "input 자유 + auto-distill"
3. **desperate specificity** — 한국팀, 회의 많음. 단 "데일리 정리 1시간 → 0 시간" claim 의 ground truth 부재
4. **narrowest wedge** — W1 (회의 요약·액션 추출, PRD §2). 단 dogfooding 미수행으로 wedge validation 0
5. **observation** — Sprint 6 dogfooding 1명 + Sprint 27a D-6 grill = 내부 evidence. 외부 evidence 0
6. **future-fit** — Phase 4 L4 (조직 인사이트) 가 차별점이나 미구현. ChatGPT memory + Notion AI 도 비슷 방향

**투자 입장**:
- product-market fit 신호 0 (외부 user 0)
- builder quality 7/10 (CTO 평가) = bet-on-founder OK
- 본 audit 의 **외부 5명 dogfooding 시도 = right next step** — 단 audit P0 fix 후 진입 필수

**verdict**: Convert 안 함. seed 단계 (외부 5명 dogfooding 결과 보고) 만 fund-able.

## 종합 점수

| 항목 | 점수 |
|---|---|
| 차별점 명확성 | 6/10 |
| value prop 5초 룰 | 5/10 — 🟡 broken screenshot 이 trust 직격 |
| pricing 신뢰 | 7/10 |
| SNS 공유성 | 4/10 |
| 투자의향 | 5/10 |

**평균: 5.4/10**

## 외부 5명 진입 결정 input

**자동 verdict**: 🟡 PARTIAL — **차별점 6/10 (BLOCK 한계 5/10 위)**, 단 "이미 동작하는 제품입니다" 섹션의 broken screenshot 3건이 trust loss 직격타 = SNS 유입 사용자 첫 인상에서 NOT-PROFESSIONAL 인상 가능.

## 시급 fix 3 권고 (audit 외)

1. **landing screenshot 3건 fix** (10분) — `frontend/public/landing/screenshots/` 파일 자체는 존재 (`ls` verify 완료) → Next.js Image config / format issue. local + production 동일 400 = source code bug. 즉시 fix
2. **paid plan 가격 안내 추가** (30분) — pricing 페이지에 "베타 후 가격 $X/month 예상" 1줄. SNS 공유 시 conversion 가능성 ↑
3. **OG image / Twitter card meta verify** (15분) — `next-seo` 또는 metadata API 로 SNS 공유 preview 명시. 외부 5명 모집 채널 (Twitter/LinkedIn/Discord) 신뢰도 ↑

## YC partner 한 줄 forcing question

**"외부 5명 dogfooding 진입 결정 = 더 미루지 마라. 22 sprint skip 패턴 = 외부 시그널 회피 = product validation 0. P0 audit fix 후 즉시 진입. 결과 분기 = pivot OR paid customer base."**
