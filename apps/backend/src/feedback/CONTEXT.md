<!-- feedback 도메인 — dogfooding 사용자 피드백 수집 (Sprint 28 Wave 1) -->

# feedback CONTEXT

> 상위: `/apps/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- 로그인 사용자의 인앱 피드백(자유 텍스트 + 1-5 별점 + 익명 옵션) 수집·저장
- 작성 컨텍스트 메타(활성 workspace_id, 페이지 URL, user agent) 함께 보존
- 신규 피드백을 Slack incoming webhook 으로 best-effort 알림 (BackgroundTask)

## 2. 비책임

- 피드백 분석/대시보드 (W1-T3 `/admin/dogfooding-stats` — 후속 PR)
- 알림 채널 보장 (Slack 미설정 시 no-op, 저장은 항상 성공)
- 워크스페이스 RBAC (user-level 도메인 — 로그인만 요구)

---

## 3. 엔티티 (소유)

- **FeedbackEntry** (`feedback_entries`)
  - `user_id` (FK users, 서버 강제 — 클라이언트 입력 비신뢰)
  - `workspace_id` (FK workspaces, **nullable** — 작성 시점 활성 컨텍스트, 없을 수 있음)
  - `rating` (1-5, nullable), `body` (text)
  - `is_anonymous` (Slack 표기만 익명, user_id 는 internal 보존)
  - `page_url`, `user_agent` (재현/디버깅 메타)
  - `created_at`

---

## 4. 의존 (in/out)

- **in**: `auth.get_current_user` (user_id + display_name)
- **out**: `common/notifications.send_slack_message` (best-effort)
- 타 도메인 repository 읽기 없음 (workspace_id 는 메타로만 저장, 멤버십 검증 안 함)

---

## 5. 엔드포인트

- `POST /api/v1/feedback` — user-level (워크스페이스 비종속, 헌법 I-13 예외).
  - body: `body`(필수) · `rating`(1-5) · `isAnonymous` · `workspaceId` · `pageUrl`
  - `user_agent` 는 서버가 요청 헤더에서 추출 (클라이언트 미전송)
  - 201 + `{id, status: "received", createdAt}`

---

## 6. 불변식

- user_id 는 `get_current_user` 로 서버에서 강제 — 요청 body 의 user 정보 신뢰 안 함.
- workspace_id 는 인가 경계가 아니라 메타 컨텍스트 — 멤버십 미검증(저위험: 본인 피드백).
- Slack 전송 실패는 삼킴(best-effort) — 피드백 저장(DB)이 source of truth.
- 환경변수 `SLACK_FEEDBACK_WEBHOOK_URL` 미설정 시 알림 no-op (Sentry SKIP 정책 정합).

---

## 7. 별칭 금지

- "피드백 / FeedbackEntry" 고정. "review", "survey", "report" 등 별칭 금지.
- 별점 = `rating` (1-5). "score", "stars" 등 코드 네이밍 별칭 금지.
