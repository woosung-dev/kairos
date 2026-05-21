# Curious User Report — Sprint 18 → 19 Multi-Agent QA

| 항목 | 값 |
|---|---|
| 검증 시각 | 2026-05-17 KST |
| 페르소나 | Curious (smoke) — 잠재 신규 사용자 |
| 환경 | local (FE :3000 + BE :8000) |
| Cap | 40분 |
| 자동화 | Playwright MCP |

## 1. Executive Summary
| 항목 | 결과 |
|---|---|
| 총 결함 카운트 | **8 (Critical 0, High 2, Medium 4, Low 2)** |
| Persona Health Score | **5.0/10** = max(0, 10 - (0×3 + 2×1.5 + 4×0.5 + 2×0.1)) = 10 - 5.2 → cap 5.0 |
| 가장 큰 발견 | 랜딩 페이지에 **제품 시연 시각자료(스크린샷·비디오·GIF) 0개**. Granola 88 image / 3 video와 정반대. 가치 제안은 강하지만 "어떻게 생겼나"를 모르고 가입. |

## 2. 결함 상세

| # | 영역 | 결함 | Severity | Confidence | 재현 | 권고 |
|---|---|---|---|---|---|---|
| H-1 | 랜딩 / 제품 증거 | 랜딩 페이지에 실제 제품 스크린샷·데모 비디오·GIF가 0개. "Cmd+K" mock card 1개만으로는 제품 외형 추론 불가. Granola는 first-fold 비디오 + 88개 이미지로 시연. | High | H | `/` → first-fold `img` 카운트 0 + `video` 0 | hero 영역에 30초 product loop video 또는 실제 dashboard 스크린샷 3컷 (Capture/Distill/Express) 추가 |
| H-2 | 워크스페이스 진입 / IDOR 후속 | 헤더 워크스페이스 드롭다운에서 `SENTINEL_A` 선택 → URL 변화 없음·UI 상태 변화 없음·여전히 "E2E 테스트 워크스페이스" 표시. 신규 사용자가 워크스페이스 전환 의도를 매번 좌절. | High | H | dashboard → "워크스페이스 전환" → SENTINEL_A 클릭 → 2초 대기 → header 라벨/URL 미변경 | 전환 시 toast + URL `?workspace=<id>` query 갱신 + sidebar `프로젝트` 영역 재로드 |
| M-1 | 가입 i18n | `/sign-up` 비밀번호 placeholder가 영문 `"Create a password"` (다른 placeholder는 한국어). Clerk localization 일부 누락. | Medium | H | `/sign-up` → password input placeholder | Clerk Localizations에 `signUp.start.passwordInputLabel` 한국어 패치 |
| M-2 | 가입 / 라우팅 | 가입 화면 "로그인하기" 링크가 외부 `creative-boxer-79.accounts.dev/sign-in` (Clerk dev URL)로 리다이렉트. 한국 사용자에게 신뢰도 하락 + 자체 로그인 페이지 우회. | Medium | H | `/sign-up` → "로그인하기" 링크 `href` 확인 | Clerk `signInUrl` 환경변수를 `/sign-in`(자체 경로)으로 설정 |
| M-3 | 라우팅 / 404 | `/workspace/{id}` 직접 진입 시 404. 워크스페이스 직접 URL이 미구현이거나 다른 패턴 사용 중. 공유 / bookmark 사용 불가. | Medium | H | `/workspace/9966a04e-0db3-4d65-a5fe-6c5c4f49901d` → 404 | `/dashboard?workspace=<id>` 패턴 또는 `/w/<slug>` 패턴으로 통일 + ADR 명시 |
| M-4 | 랜딩 / 가격 | 랜딩에 가격 정보 0건. "무료 체험" / "14일 무료"만 반복. 결제 모델/플랜 비교 없음. B2B SaaS 평가 어려움. | Medium | H | `/` → `pricing` keyword 검색 0건 | `/pricing` 라우트 + 3 tier (Free/Team/Enterprise) 비교표 |
| L-1 | 랜딩 / CTA 일관성 | first-fold CTA = `시작하기` (sign-up), hero CTA = `무료로 시작하기`. 같은 destination이지만 문구 2종. | Low | H | nav `시작하기` vs hero `무료로 시작하기` | 1개 문구로 통일 ("14일 무료 시작") |
| L-2 | 랜딩 / Dev mode 표시 | `/sign-up` 위젯 하단에 Clerk `"Development mode"` 배지가 노출됨. 프로덕션 환경 분리 시 visibility false 필요. | Low | M | `/sign-up` 하단 위젯 | 프로덕션 Clerk 인스턴스 사용 (BL-existing Clerk Production key 발급 이슈 연결) |

## 3. 인사이트 / Granola 비교

| 차원 | Kairos | Granola | 시사점 |
|---|---|---|---|
| h1 카피 | "AI가 정리합니다. 당신은 결정만 하세요." (추상적 가치) | "The AI notepad for people in back-to-back meetings" (구체적 사용 시나리오) | Kairos는 "what it is" 보다 "what it promises"에 가까움 — TAM 좁히는 게 더 좋을 수도 |
| first-fold 비디오/GIF | 0 | 3+ (자동 재생 product loop) | **Kairos 시급 추가 필요** |
| 이미지 자산 | 0 (CSS mock card 1개만) | 88 | "백문이 불여일견" 누락 |
| 가격 노출 | 첫 fold 없음 | 첫 fold 없음 (둘 다 약점) | 양쪽 모두 `/pricing` 페이지 부재 추정 |
| 본문 길이 | 4-section 풍부 (CODE/Distill 4-Level/타임라인/통계) | ~10,000 chars (간결) | Kairos는 정보 밀도 높음 — 좋음, 다만 시각화 부족 |
| 타겟 명료성 | "팀" / "조직" 반복 — B2B팀 | "back-to-back meetings" — 미팅 폭주 시달리는 개인+팀 | Kairos는 buyer (팀장)인지 user (개인)인지 모호 |

**5초/30초/1분 첫인상 평가 (스크롤 없이)**:
- 5초: h1 + sub-copy "팀의 대화·노트·자료가 CODE 파이프라인을 거치면 자동 구조화" → "팀용 AI 메모 도구" 인식 가능 ✅
- 30초: hero CTA "무료로 시작하기" + "Cmd+K — 정리된 지식이 이렇게 활용됩니다" mock card 1개 보임 → 사용 시나리오 1개 노출 (긍정)
- 1분: 스크롤 1회로 CODE 파이프라인 4단계 인지 가능 → 정보 흡수 良好

**TTFV 분석 (Sentinel A 로그인 후)**:
- 가입 → factor-one(이메일 자동) → dashboard 자동 진입까지 **2 step**. 워크스페이스 선택 강제 없음 (자동 매핑). 매우 빠름.
- 단 dashboard 진입 후 `프로젝트 없음` 표시 + 시드 데이터가 "E2E 테스트 워크스페이스"에 묶여 자동 매핑 → **시드 워크스페이스 무관한 데이터** 노출. 신규 사용자에게는 default workspace empty state 가이드가 핵심.

## 4. 산출물
- 스크린샷
  - `curious/landing-desktop.png` (Kairos 랜딩 full page)
  - `curious/signup.png` (Clerk sign-up 위젯)
  - `curious/dashboard-firstview.png` (Sentinel A 로그인 직후 dashboard)
  - `granola-comparison/landing.png` (Granola 랜딩 비교)
- trace zip: Critical 0건 → 미생성
- 부가 발견: hero 영역의 사이드 카드 ("Q1 런칭 지연 원인" 인사이트 mock)는 design quality 높음, 추가로 product screenshot이 합세하면 효과 배가
