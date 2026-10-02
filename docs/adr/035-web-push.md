# ADR-035 — 웹 푸시 (회의 처리 완료·실패 → 업로더 본인)

**Status**: Accepted — PR-2 구현 완료, 자동 검증 PASS (EVAL-P2-1 PASS + GEN-P2-2 minor 3건 수정, 2026-10-02). 실푸시 수신 T-PWA-52·53·54 는 오케스트레이터 실브라우저 확인 대기 · iOS T-PWA-55 는 별도
**Date**: 2026-10-02
**Spec**: [`docs/requirements/pwa.md`](../requirements/pwa.md) §5 (PR-2) · 테스트 [`test-matrix.md`](../plans/active/2026-10-02-pwa/test-matrix.md) PR-2
**Invariant**: `apps/api/CONTEXT.md` §5 **B-16** · 도메인 정본 `apps/api/src/push/CONTEXT.md`
**Related**: ADR-034 PWA 설치형 셸 (같은 SW 에 `push`·`notificationclick` 을 더했다) · ADR-014 (크로스 도메인은 오케스트레이터 경유) · ADR-031 (Better Auth — 로그아웃 순서의 전제)

---

## 배경

업로드한 회의는 STT·AI 분석이 BackgroundTask 로 수 분 걸린다 (B-7). 사용자는 결과를 보려고 탭을 열어 두거나
다시 들어와야 했다. PR-2 는 **처리 완료·실패를 업로드한 본인에게 웹 푸시로 알린다** (pwa.md §1 사용자 결정 — 그 밖의
이벤트는 BL-PWA-4).

웹 푸시는 이 앱에서 세 가지 제약과 부딪친다.

- **서버가 사용자가 준 URL 로 POST 한다** — 구독 endpoint 를 그대로 믿으면 SSRF 다 (pwa.md R-6).
- **알림은 잠금화면에 뜨고, 브라우저 알림 권한은 origin 단위다** — 같은 기기를 쓰는 다음 사용자를 구분하지 못한다.
  권한이 남아 있다고 다시 구독하면 다음 사용자가 동의 없이 앞 사용자의 알림을 받는다.
- **발송은 느린 외부 네트워크다** — 파이프라인 DB 세션을 연 채로 기다리면 커넥션 풀을 붙잡는다.

---

## 결정

### D1. 수신자 = 업로더 본인, 그것도 지금 워크스페이스 멤버일 때만

`Meeting.created_by_id` 1명에게만 보낸다. 같은 워크스페이스의 다른 멤버·admin 에게도 보내지 않는다.
조회 세션 안에서 회의를 `workspace_id` 로 읽고(`find_by_id`), 업로더가 **지금도** 그 워크스페이스 멤버인지
`WorkspaceRepository.find_member` 로 확인한다 — 아니면 미발송 (`apps/api/src/meetings/pipeline_service.py:374-389`).
멤버십이 끊긴 사람에게 그 워크스페이스의 회의 id 를 보내지 않는다 (I-9).

### D2. 페이로드 = `{v, kind, meetingId, workspaceId}` 만, 문구·URL 은 SW 가 만든다

- 서버 페이로드 키는 4개뿐이고 직렬화 ≤ 512B 를 넘으면 `PushPayloadTooLargeError` (`apps/api/src/push/service.py:91-109`).
  회의 제목·요약·전사·이름은 넣지 않는다 (게이트 ④) — 잠금화면은 기기 주인이 아닌 사람도 본다.
- 사람이 읽는 문구는 SW 가 `kind` 로 고른다. 클릭 URL 도 SW 가 UUID 정규식을 통과한 id 로 조립하고
  (`/meetings/<uuid>` + `?workspace=<uuid>`), 클릭 시 같은 origin `/meetings/<uuid>`·`/dashboard` 밖이면 `/dashboard` 로 바꾼다
  (`apps/web/src/lib/pwa/push-notification.ts` `parsePushPayload`·`buildPushNotification`·`resolveNotificationTarget`).
  서버 문자열을 URL 로 쓰지 않는다.
- `workspaceId` 는 알림 딥링크의 워크스페이스 전환용이다 (게이트 ⑥, `features/workspaces/hooks.ts:160` `useWorkspaceDeepLink`).

### D3. endpoint = ASCII · `https` · 호스트 allowlist, 삭제는 id 로

API-002 는 Pydantic 검증으로 422 를 낸다 (`apps/api/src/push/schemas.py:103-135`):
**ASCII 만** → 금지 문자(공백·제어문자·역슬래시) 없음 → `https` → userinfo 없음 → 포트 없음/443 → IP 리터럴 아님 →
호스트 allowlist (`fcm.googleapis.com` · `android.googleapis.com` · `.push.services.mozilla.com` · `.push.apple.com` ·
`.notify.windows.com`, 점으로 시작하면 접미사 일치). 길이 ≤ 2048.

- **ASCII 검사를 맨 앞에 둔 이유** (EVAL-P2-1 D1): 실제 푸시 서비스 endpoint 는 전부 ASCII 다. 비ASCII 는 ① IDN 호스트가
  우리 파서와 HTTP 클라이언트(punycode)에서 다르게 해석될 수 있고 ② 2048자 × 3바이트가 btree 인덱스 행 한도를 넘어
  ③ lone surrogate(`\ud800`)는 DB 인코딩에서 실패해 — 422 가 아니라 500 이 됐다. 500 경로는 요청 본문을 로그에 남길 수 있다.
- lone surrogate 는 422 응답 자체도 깨뜨린다 — 오류의 `input` 이 응답 본문으로 돌아가 UTF-8 인코딩에서 실패한다.
  전역 422 핸들러가 그때만 ASCII 이스케이프 JSON 으로 직렬화한다 (`apps/api/src/main.py:113-117` `_AsciiJSONResponse`, `:177`).
  JSON 의미는 같고, 이 경로는 push 외 모든 엔드포인트의 422 에 적용된다.
- API-003 은 endpoint 가 아니라 **id** 로 지운다 — endpoint 는 capability URL 이라 경로·접근 로그에 남기지 않는다.
  없거나 남의 것이어도 204 (존재 여부 오라클 차단).

### D4. 발송 시퀀스 — commit 이후 · 발송 중 DB 세션 0개 · 404/410 정리는 새 세션

```
process_meeting / capture_text
  async with 파이프라인 세션: … update_status(completed|failed) → commit → outcome 기록
  # async with 밖 = 파이프라인 세션 close 완료
  if outcome: _notify_meeting_finished(meeting_id, workspace_id, outcome)      (:281-282, :348-349)

_notify_meeting_finished  (전체 try/except — 어떤 실패도 회의 상태에 영향 0)        (:351-418)
  0. VAPID 미구성 → return                    create_push_dispatcher() is None
  1. 조회 세션: 회의 → 멤버 확인 → 구독을 원시 값(PushTarget)으로 복사           (:374-389)
  2. 조회 세션 close — 이 아래에는 열린 세션이 없다
  3. 발송: aiohttp ClientSession 1개, 구독별 webpush_async                     (:396)
  4. 404·410 이 있을 때만 새 짧은 세션으로 `id AND user_id` 삭제 → commit        (:405-409)
```

- `webpush_async` 인자는 `ttl=86400` · **`timeout=10` 명시** (미지정이면 aiohttp 까지 `None` 이 가서 무제한) ·
  `Urgency: normal` · 호출마다 새 `vapid_claims` dict (`apps/api/src/push/sender.py:72-84`, 근거 pwa.md §5.3).
- 재시도는 없다 (BL-PWA-6). 로그에는 meeting_id·user_id·개수·상태코드·예외 타입명만 남긴다 — endpoint·keys·payload 금지.

### D5. 서비스를 둘로 나눈다 — `PushService`(API) · `PushDispatchService`(발송)

`apps/api/src/push/service.py:1-8` 의 근거 그대로: 발송은 세션이 하나도 없는 구간에서 돌아야 한다.

- `PushService` (`:58`) — API-001~003. 요청 세션의 `PushRepository` 를 쓴다.
- `PushDispatchService` (`:121`) — Repository 를 갖지 않는다. `PushTarget` 원시 값을 받아 보내고 결과를 성공 / 404·410 /
  그 외로 분류만 한다. 조회·정리 세션은 오케스트레이터가 앞뒤로 따로 연다 (B-3).
- `sender.py` 는 pywebpush 호출만 하는 얇은 래퍼(`PushSender` Protocol) — 테스트에서 가짜로 바꾼다.

### D6. 로그아웃 = ①∥② + 3초 상한, 앱 로드 동기화가 2차 방어선

로그아웃하면 그 기기의 푸시가 꺼진다 (게이트 ⑦ — 같은 사용자도 다시 켜야 한다). 구현은
`apps/web/src/features/push/flows.ts:200-210` `disablePushOnDevice`, 호출은 기존 순서 앞
(`apps/web/src/components/layout/header.tsx:171-183` — signOut 뒤에는 `/api/auth/token` 이 401 이라 서버 삭제가 불가능하다).

- **① 표식 id 로 API-003 ∥ ② 로컬 `unsubscribe()`** 를 `Promise.allSettled` 로 함께 시작한다 (요청은 ①이 먼저 나간다).
  전체를 3초 상한(`PUSH_CLEANUP_TIMEOUT_MS`, `:29`)으로 감싸고, 끝나면 ③ 표식 compare-and-delete. throw 하지 않는다.
  ①→② 순차였다면 느린 네트워크(①)가 3초를 다 써서 ②가 돌지 못하고, 로그아웃 뒤에도 이 기기가 푸시를 받는다.
- ①은 SW 등록이 없어도 보낸다 — 같은 로드 안에 kill-switch 로 등록만 사라진 잔여를 지운다. 등록은
  `getRegistration()` 1회로만 얻고 `serviceWorker.ready` 는 기다리지 않는다 (등록 없음이면 영원히 pending, ADR-034 D5).
- 같은 id 의 API-003 이 동기화와 로그아웃에서 겹치면 요청 1회·promise 공유 (`:82-99`).
- **2차 방어선 — 앱 로드 동기화** (`:212-269` `syncPushOnAppLoad`, `hooks.ts:37-56` `usePushAppLoadSync`):
  소유자 표식(`localStorage["kairos:push:v1"]` = `{userId, subscriptionId}`, zod 파싱)이 현재 사용자와 다르거나 없으면
  서버를 부르지 않고 `unsubscribe()` 만 한다 (세션 만료 등 로그아웃 없이 계정이 바뀐 경우). 표식이 일치하면 API-002 를
  다시 보내 브라우저의 endpoint 교체·서버 행 유실을 복구한다 (`pushsubscriptionchange` 대신 — BL-PWA-9).
- 동기화는 **계정당 1회**다 — 모듈 상태 `lastSyncedMeId` (EVAL-P2-1 D3). 로그아웃→다른 계정 로그인은 soft navigation 이라
  JS 수명이 이어지므로 boolean 가드면 새 계정 기준 동기화를 건너뛴다.
- 서버 백스톱: API-002 는 `ON CONFLICT (endpoint)` upsert 라 같은 기기에서 다른 사용자가 구독하면 그 행이 현재 사용자로
  rebind 된다 (`apps/api/src/push/repository.py` `upsert`).

### D7. VAPID 키 교체 — 자동 재구독 없음, 다음 앱 로드에 '꺼짐' 으로 정리

키를 바꾸면 기존 구독은 전부 우리 서명을 받지 못한다. FE 는 구독의 `options.applicationServerKey` 를 API-001 공개키와
비교한다 (`flows.ts:108-121` `matchesCurrentVapidKey`, EVAL-P2-1 D2).

- 앱 로드 동기화: 키가 다르고 표식 일치 → API-003(표식 id) ∥ `unsubscribe()` → 표식 compare-and-delete (`:247-256`).
  표식 불일치·없음 → `unsubscribe()` 만 (기존 분기).
- SCR-002 상태 판정: 키가 다르면 **'꺼짐'** (`:129-148`) — 그 구독으로는 알림이 오지 않으므로 '켜짐' 은 거짓이다.
- 공개키를 모르면(API-001 이 `null` 이거나 실패) 비교를 건너뛴다 — 기존 동작 그대로. 그래서 동기화 훅은 API-001 이
  끝난 뒤(성공·실패 모두)에 돈다.
- 사용자가 토글을 다시 켜면 `enablePush` 가 옛 키 구독을 먼저 끊고 새 키로 구독한다 (`:156-191`).
- 자동 재구독을 하지 않는 이유: 페이지 로드 동안 푸시 구독 상태를 사용자 조작 없이 새로 만드는 경로를 두지 않는다
  (권한 요청·구독 생성은 토글 클릭 안에서만 — pwa.md §5.5). 키 교체는 드문 운영 이벤트이고 토글 1회로 복구된다.

### D8. 403 은 정리하지 않는다 — 404·410 만 행 삭제

`GONE_STATUS_CODES = {404, 410}` (`apps/api/src/push/service.py:33`). 429·5xx·403·413·타임아웃은 행 유지 + warning 1줄.

- 404·410 은 푸시 서비스가 "이 구독은 사라졌다" 고 말하는 신호다. 403 은 대개 **우리 쪽** VAPID 서명·키 문제다
  [가정 — 서비스별 403 의미는 확인하지 않았다]. 설정 실수(잘못된 개인키·subject) 한 번에 403 을 받은 행을 지우면,
  키를 바로잡아도 모든 사용자가 알림을 다시 켜야 한다. 행을 남기면 설정 수정만으로 복구된다.
- 대가: 키 교체 뒤 그 기기에서 앱을 다시 열지 않는 사용자의 옛 행은 발송마다 403 warning 을 남기며 남는다.
  앱을 열면 D7 이 API-003 으로 지운다. 개수 상한·축출은 BL-PWA-14.

### D9. `push_subscriptions` 는 사용자 단위 리소스 (ENT-001)

`workspace_id` 가 없다 — B-2 예외 (FeedbackEntry 와 같은 위치). 대신 Repository 의 모든 조회·삭제에 `user_id` WHERE
(404/410 정리도 `id AND user_id`). `endpoint` UNIQUE + `user_id` FK(`users.id`, ON DELETE CASCADE) + index.
키(`p256dh`·`auth`)를 평문 저장하는 근거: 구독은 우리 VAPID 개인키로 서명한 요청만 받는다 (RFC 8292).
상세: `docs/architecture/erd.md` "ADR-035 웹 푸시 엔티티". 경로는 I-13 예외 `/api/v1/users/me/push-*`.

### D10. 설정 — VAPID 3필드, 런타임 env, warn-only

`VAPID_PUBLIC_KEY` · `VAPID_PRIVATE_KEY`(SecretStr) · `VAPID_SUBJECT` 셋 다 있어야 활성 (`apps/api/src/core/config.py:122-124`).
형식 오류는 warning 만 (부팅 차단 금지, C-18). build.env 가 아니라 api 컨테이너 런타임 env 다 — 공개키는 API-001 로 FE 에
준다 (`NEXT_PUBLIC_*` 빌드 인라인을 피한다, pwa.md C-14). 개인키는 raw 32바이트 base64url 만 정상으로 본다 (PEM 은 BL-PWA-19).
생성 명령은 `apps/api/src/push/CONTEXT.md` §7.

---

## 위험

- **iOS** — 16.4+ 홈 화면 앱에서만 푸시가 된다 (REQ-011 안내). 실기기 확인(T-PWA-55) 전이다.
- **Edge/WNS** — allowlist 문자열만 검증했다. 실제 호스트 형식·발송은 미검증 (BL-PWA-18). 목록 밖이면 422 라 안전 방향으로 실패한다.
- **로그아웃 없이 계정이 바뀐 기기의 잔여 창** (pwa.md R-10) — 다음 사용자가 앱을 열기 전 도착한 알림 1건. 페이로드에 내용이
  없어 노출은 "어떤 회의가 끝났다" 수준이다.
- **실제 로그아웃 e2e 가 없다** — `push.spec.ts` T-PWA-49 는 sign-out 을 stub 한다 (Better Auth rate limit, BL-PWA-15).
  `auth-relogin.spec.ts` 는 셀렉터 불일치로 항상 skip 이다 (BL-PWA-16).

---

## 기각한 대안

**① 워크스페이스 멤버 전체·관리자에게 발송** — 사용자 결정은 업로더 본인뿐이다 (pwa.md §1). 받는 사람이 늘수록 잠금화면 노출과
알림 피로가 커진다.

**② 페이로드에 회의 제목** — 잠금화면·계정 전환 잔여 창에서 내용이 샌다 (게이트 ④).

**③ allowlist 없이 `https` 만 검사** — `https://169.254.169.254/` 같은 내부 주소로 POST 를 보내게 된다 (R-6).

**④ endpoint 로 삭제 (`DELETE ?endpoint=`)** — capability URL 이 경로·접근 로그에 남는다.

**⑤ 하나의 `PushService` 가 조회·발송·정리를 모두** — Repository(세션)를 쥔 채 네트워크를 기다리게 된다 (D4·D5).

**⑥ `asyncio.to_thread` + 동기 pywebpush** — 2.1.0+ 의 `webpush_async`(aiohttp)가 있다 (B-10 100% async).

**⑦ 로그아웃 ①→② 순차** — 느린 ①이 3초 예산을 다 써 ②(로컬 unsubscribe)가 돌지 못한다 (D6).

**⑧ 로그아웃 후 같은 사용자 재로그인 시 자동 재구독** — 알림 권한은 사용자를 구분하지 못해 다음 사용자를 동의 없이 구독시킨다 (게이트 ⑦).

**⑨ 키 교체 시 앱 로드에서 자동 재구독** — D7. 사용자 조작 없는 구독 생성 경로를 두지 않는다.

**⑩ 403 도 행 삭제** — D8. 우리 설정 실수가 전체 구독 삭제로 번진다.

**⑪ SW `pushsubscriptionchange` 처리** — SW 에는 인증 토큰이 없다. 앱 로드 동기화가 대신한다 (BL-PWA-9).

---

## 검증

- BE pytest (`apps/api/tests/push/` · `tests/meetings/test_push_hook.py`): API-001~003·검증(SSRF·비ASCII·lone surrogate·IDN)·
  발송 시퀀스(세션 열림/닫힘 spy)·응답코드별 정리·best-effort·미구성·비멤버·페이로드·sender 인자·마이그레이션.
  전체 1082 passed (EVAL-P2-1, 오케스트레이터 · 기준선 996) → 1086 passed (GEN-P2-2 D1 회귀 4건 추가).
- alembic dry-run: 가산형 — `CREATE TABLE push_subscriptions` 1 + 명시 이름 제약 4 (오케스트레이터 실측).
- 계약: `mise run contracts-check` drift 0 (API-001~003 추가).
- FE vitest: 동기화·로그아웃·키 불일치·계정 전환 재동기화·표식·SW `push`/`notificationclick`·딥링크.
- e2e (오케스트레이터, EVAL-P2-1): public-only 18 pass · chromium 42 pass / 11 skip · `push.spec.ts` 9 ✓.
- 수동: 실푸시 수신 T-PWA-52(완료)·53(실패)·54(계정 전환 미수신)는 **오케스트레이터 실브라우저 확인 대기**. iOS T-PWA-55 는 별도.
- 행별 상태·기대값의 정본은 test-matrix 다.
