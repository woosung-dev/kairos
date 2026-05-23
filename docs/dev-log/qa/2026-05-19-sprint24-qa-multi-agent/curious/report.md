# Curious Day 2 — 신규 사용자 시각 보고서

> 페르소나: AI 회의/지식 관리 도구 도입 검토 중인 시니어 PM. 사전 지식 0.
> Granola/Notion AI 경험 있음.

## 시작/종료/소요
- 시작: 2026-05-19 14:08 UTC (KST 23:08)
- 종료: 2026-05-19 14:17 UTC
- 소요: ~9분 (60-90분 cap 내, 미션 핵심만 우선 집행)
- 도구: Playwright MCP only (코드 수정 0, git diff CLEAN)

## 환경 / 자격증명
- Kairos FE :3000 / BE :8000
- Clerk 가입: `qa-curious-1779199763+clerk_test@example.com` (Clerk test mode `+clerk_test` 이메일 = 코드 `424242` 자동 통과)
- 차단 1: `@kairos-test.local` 도메인 거부 → `+clerk_test@example.com` 해소
- 차단 2: Granola/Notion AI 외부 OAuth → 가입 흐름 불가, **landing 시각 평가로 대체** (MISSION fallback)

---

## 5초 / 30초 / 1분 룰 결과

### SCN-CUR-FIRST-5 (5초 룰) — **FAIL**
- 본 것: "Kairos" / "팀의 세컨드 브레인" / "회의, 노트, 자료가 쌓일수록 조직이 똑똑해집니다" / 시작하기·로그인
- 자기보고: "컨셉 한 줄은 있지만 demo/스크린샷/사회적 증거 없음. Granola는 'back-to-back 미팅' 페르소나 매칭이 즉시 되는데, Kairos는 추상적 가치만 한 줄."
- 평가: FAIL — 가치 명확성은 OK지만 5초 안에 Granola/Notion AI와 다른 점 0
- evidence: `curious-01-landing-5s.png`

### SCN-CUR-FIRST-30 (30초 룰) — **FAIL**
- 발견: Landing이 **viewport 1개 분량 (1271px)**. Features/Pricing/Social proof/How-it-works 섹션 0개. footer도 없음.
- 자기보고: "30초 후에도 '이 도구가 뭘 어떻게 해주는지' 모름. 가입 의향 3/10."

### SCN-CUR-FIRST-60 (1분 룰) — **Maybe (커리어 호기심)**
- 자기보고: "Granola가 명확한 우위. 1분만에 Kairos 선택할 이유 없음. 한국어 UI 때문에 '한국 팀이라면?' 호기심 정도. **Maybe — 더 보고 결정**."

---

## 가입 마찰 (SCN-CUR-FRICTION) — 점수 **6/10**
- 필드 수: 이메일 + 비밀번호 = 2개 (최소화 OK)
- OAuth: Apple + Google (2개)
- ToS / Privacy 링크: **명시 없음** (-2)
- 한국어 일관성: 비밀번호 placeholder "Create a password" — 한국어 화면에 영어 잔재 (-1)
- "Development mode" 배지 노출 (정보용)
- 이메일 검증: `.local` 도메인 거부 — 일반 사용자 좌절 (Clerk 한계, Kairos 책임 X)
- Email verification 코드 단계 — 표준이지만 +1 마찰

마찰 포인트:
1. ToS / Privacy Policy 링크 부재 (도입 결정 차단 요인)
2. Korean/English mixed copy ("Create a password")
3. Development mode 배지 (배포 환경 한정 — 무시)
4. Clerk verification 코드 단계 (표준)

---

## TTFV (NORTH STAR) — **255.5초 / 4분 16초**

| 단계 | T (epoch ms) | ISO | 누적 (sec) | 비고 |
|---|---|---|---|---|
| 시작하기 클릭 (signup 시작) | 1779199763824 | 2026-05-19T14:09:23.824Z | 0.0 | T0 |
| Dashboard 도착 (가입 완료) | 1779199892526 | 2026-05-19T14:11:32.526Z | **128.7** | Clerk + workspace seed |
| AI 분석 시작 클릭 | 1779199936279 | 2026-05-19T14:12:16.279Z | 172.5 | +43.8s (회의 추가 + 텍스트 입력) |
| AI 요약 visible | 1779200019364 | 2026-05-19T14:13:39.364Z | **255.5** | T1 (NORTH STAR) |

세부:
- Clerk 가입 = **128.7초** (전체 50%)
- Dashboard → 회의 추가 → 텍스트 입력 → AI 분석 클릭 = **43.8초**
- AI 처리 (Gemini, 500자 input) = **83.1초**

답답한 지점:
1. Clerk verification 코드 단계 — +30s
2. Dashboard에서 "다음 뭐 해야?" 명시 없음. onboarding tour 0
3. **Onboarding step 1~4 (Sprint 22 OBN-01~04) 실제 화면에 발화되지 않음** → dashboard로 직진
4. AI 처리 83초 — 진행도 0%

---

## 핵심 가치 검증 (SCN-CUR-VALUE) — **7/10**

AI 요약 본 후:
- 요약 품질: 회의 본문(500자) → 3문장 정확 요약. **good**
- 핵심 결정사항: 2개 자동 추출. **good**
- 주제 태그: 4개. **good**
- 액션 아이템: 3개 + 담당자 + 마감일 + 우선순위. **strong** — Granola 강점 영역 동급

🚨 **버그 발견 (P0 Critical)**: 액션 아이템 마감일이 **2024-07-25 / 2024-07-22 / 2024-07-12 표시**. 회의 본문은 "7월 X일" (연도 없음). 현재 2026년 5월인데 AI가 **2024년**으로 hallucinate → 과거 -2년.
- PM 시각: "이 도구 신뢰할 수 있나? 액션 아이템 마감일이 2년 지난 날짜로 자동 생성되는 거면 회의 끝나고 안 보게 됨."

**RAG /ask** (연속):
- 질문: "결제 출시일이 언제로 조정됐어?"
- 응답: "조정된 출시일: 7월 29일 (기존 7월 15일에서 변경) 📎 [소스 1] Q3 OKR 리뷰 회의 (2026-05-19)"
- **소스 인용 + 클릭 가능 출처 + 정확 응답** — Notion AI 대비 강점

🚨 **버그 발견 (P1 High)**: dashboard 추천 질문 ("최근 회의에서 결정된 사항은?") 직접 클릭 → **응답 없이 button만 active 표시** (UX bug). ⌘K command palette로만 동작. 신규 사용자 혼란.

evidence: `curious-04-rag-answer.png`

---

## 도입 결정 요인 — 점수 **4/10**

| 요인 | Kairos | 비고 |
|---|---|---|
| 가격 | ❌ 명시 없음 | Pricing/billing 페이지 0 |
| 보안/Privacy | ❌ ToS/Privacy 링크 0 | landing/settings/sign-up 어디에도 |
| 팀 기능 | ⚠️ 부분 | settings에 "워크스페이스 멤버" 있음 |
| Export | ✅ Markdown/JSON | PDF 없음. **유일한 강점** |
| 신뢰 신호 | ❌ 회사정보·약관·후기·보안인증 0 | Clerk "Secured by Clerk" 배지 1개만 |

차단 요인: 가격·약관·신뢰 신호 부재. B2B SaaS PM이 evaluation 단계에서 자동 탈락.

---

## 도입 결정 (최종)

- **Kairos**: **Maybe → No** (한국어 UI + RAG 인용 매력. 그러나 가격/약관/신뢰 0 + AI hallucinate + dead-click 차단)
- **Granola**: **Yes** (Series C 신뢰 + use case 명시 + $0 free tier + 명확한 problem statement. macOS-only)
- **둘 중 하나만**: **Granola** (evaluation deck 올리기 용이)

**자기보고**: "Kairos가 Granola를 대체할 수 있는가?" → **현재 상태로는 아니다**. 3개 wedge (RAG /ask + 소스 인용 + 한국어 native)는 명확하지만 landing 5초/30초 안에 *증거*로 보이지 않음. **Sprint 24+에서 결정적 30초 wedge 증명 못하면 사용자 acquisition 차단** (gemini F2 직면).

---

## 종료 검증
- `git diff --exit-code`: **CLEAN**
- §19 코드 수정 금지 PASS / §19-4 PII redact / §20 Critical STOP 발견 0 (액션 hallucinate는 P0이지만 STOP 조건 아님)
- 산출물: 8 스크린샷 (`curious-01-landing-5s.png` ~ `curious-08-notion-ai.png`)
