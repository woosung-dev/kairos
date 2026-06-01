# 트랙 C1 — Playwright 라이브 검토 결과 (2026-06-01)

> 환경: 로컬 풀스택(FE :3000 / BE :8000 / Neon DB), owner `d@e.com`, 워크스페이스 "QA Cycle C Team". 검토 전용 read-only.

## 검증 완료 (PASS)

| 항목 | 결과 |
|------|------|
| 라우트 렌더 | dashboard / inbox / memory / notes / projects / projects[목록] / new / meetings[id] / settings / landing / sign-in 전부 **console errors 0** (Clerk dev-key warning 1건만, 비차단) |
| AI 파이프라인 | 회의 텍스트 capture(`062b2307`) → status=**완료**. 요약 + 핵심결정 2 + 주제 3 + 액션 2(담당자 / 마감일 `6월 8일`→`2026-06-08` 정규화 / 우선순위 "높음") 정확 추출 |
| **GEMINI_API_KEY** | **유효** — backlog `BL-S27c-2`(invalid)는 **stale**. 라이브로 정상 작동 |
| RAG | 벡터검색(소스 2건) + SSE 스트림 답변 + 출처 인용("📎 …회의 2026-06-01") 정상 |
| Inbox 적재 | 회의 → 사이드바 Inbox 배지 "1" 생성 (capture→분류→inbox 파이프라인 동작) |
| Inbox empty state | "📥 처리할 항목이 없습니다 / 회의를 녹음하거나…" **존재** — `BL-S27c-6`은 해소됨 |
| Feedback 모달 | 별점(aria-label) / 텍스트 / 익명 체크 / 제출 가드 / Close — 접근성 라벨 양호 (외부 발송 방지 위해 실제 제출 생략) |
| 모바일(390px) | 가로스크롤 0, BottomNav(fixed) + 햄버거 + 피드백 FAB, 오버플로 없음 |
| Landing | 제품 이미지 3/3 정상 로드(`BL-S27c-3` 로컬 재현 안 됨), AIDA 구조, 가로스크롤 0 |
| Sign-in | Clerk koKR 위젯 정상 |

## 발견 (FINDING)

- **F-LIVE-1 (P1)** RAG 답변 **마크다운 미렌더링**. `frontend/src/features/rag/components/rag-chat.tsx:125` 가 `whiteSpace: "pre-wrap"`(인라인 스타일) + `renderContentWithCitations`가 `[n]` 인용 마커만 파싱. 마크다운 렌더러 의존성 자체 없음(react-markdown/remark/marked 부재) → `###`/`**`/`*` 기호가 화면에 raw 노출. RAG는 핵심 기능이라 가독성 직격. **권고**: react-markdown + remark-gfm 도입 후 citation 마커 통합 렌더(또는 streamdown). 의존성 추가+검증 필요 → 승인 후 별도 수정.
- **F-LIVE-2 (P2)** **초기 렌더 flicker 클러스터**. 워크스페이스 스위처명(fallback "Kairos") / settings 헤더("— · — · 멤버 0") / 사이드바 프로젝트("프로젝트 없음") / inbox 목록이 client fetch 로딩 중 fallback/빈값을 노출 후 데이터 도착 시 갱신. 모두 재현 후 정상화 확인 — 기능 손실 0, 시각 품질 이슈. 근본: 거의 모든 페이지 `'use client'` + client-only fetch + 로딩 skeleton 가드 부재. `BL-S27e-2`(nav flicker)의 확장.
- **F-LIVE-3 (P3)** `/actions` → `/inbox` redirect. actions kanban feature(353줄)에 대한 진입점이 사이드바/대시보드에 없음 → 사실상 미사용 기능. `BL-S27c-7` 관련.
- **F-LIVE-4 (P3)** `/pricing` 이 **로그인 상태에서 `/dashboard`로 redirect** — 로그인 사용자가 가격 페이지 접근 불가.
- **F-LIVE-5 (P3)** 이모지 아이콘 광범위 사용(🎙️📝📎📥🚀💡📋⚙️🔴) vs 사이드바 SVG 혼용 → 아이콘 일관성 / ui-ux `no-emoji-icons`. DESIGN.md 의도 확인 필요.
- **F-LIVE-6 (P3)** sign-in "kairos" 소문자 브랜딩(Clerk application name) — 다른 화면은 "Kairos".

## 외부 조치 (참고)
- Clerk "Development mode" 배지 노출 — Production 인스턴스 발급은 사용자 SKIP 결정(GA 별도 sprint).

## evidence
스크린샷: dashboard-initial / inbox-empty / rag-markdown-raw / mobile-dashboard / landing-full (Playwright MCP output dir).
