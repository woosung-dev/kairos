<!-- push 도메인 — 웹 푸시 구독 저장 + 회의 완료·실패 발송 (PWA PR-2) -->

# push CONTEXT

> 상위: `/apps/api/CONTEXT.md` → `/CONTEXT-MAP.md`. 정본 spec: [`docs/requirements/pwa.md`](../../../../docs/requirements/pwa.md) §5 (REQ-007·008·010, API-001~003, ENT-001).

---

## 1. 책임

- 로그인 사용자의 브라우저 푸시 구독(`PushSubscription.toJSON()` 의 endpoint + keys) 저장·삭제
- 클라이언트에 VAPID 공개키와 기능 활성 여부 제공 (API-001)
- 회의 처리 **완료·실패**를 업로더 본인(`Meeting.created_by_id`)에게 발송하는 세션 없는 발송 단계
  (`PushDispatchService`) + pywebpush 래퍼(`sender.py`)

## 2. 비책임

- 발송 시점·수신자 결정과 DB 세션 수명 — 오케스트레이터 `meetings/pipeline_service._notify_meeting_finished` 소관 (B-3)
- 알림 문구 — 서버는 사람이 읽는 문자열을 보내지 않는다. SW 가 `kind` 로 정한다 (pwa.md §5.4)
- 재시도 (BL-PWA-6) · 사용자당 구독 개수 상한 (BL-PWA-14) · 그 외 이벤트 (BL-PWA-4)

---

## 3. 엔티티 (소유)

- **PushSubscription** (`push_subscriptions`, ENT-001)
  - `user_id` (FK `users.id` ON DELETE CASCADE, index) — 내부 users.id
  - `endpoint` (text, **UNIQUE** `uq_push_subscriptions_endpoint`) — 푸시 서비스 capability URL
  - `p256dh` (base64url, 디코드 65바이트 `0x04` 시작) · `auth` (base64url, 디코드 16바이트)
  - `created_at` · `updated_at` (upsert·rebind 마다 갱신)
  - **`workspace_id` 없음** — 사용자 단위 리소스 (FeedbackEntry 와 같은 위치)

---

## 4. 의존 (in/out)

- **in**: `auth.get_current_user` (user_id 서버 강제) · `core.config` (VAPID 3필드)
- **in (오케스트레이터)**: `meetings/pipeline_service.py` 가 지연 import 로 `PushRepository`·`create_push_dispatcher` 사용
- **out**: pywebpush 2.5.0 `webpush_async` (aiohttp) → 푸시 서비스 (FCM · Mozilla autopush · Apple · WNS)
- 타 도메인 repository 를 읽지 않는다 (멤버십·회의 조회는 오케스트레이터가 한다)

---

## 5. 엔드포인트 (모두 Bearer JWT, camelCase I-16)

| ID | 메서드 · 경로 | 응답 |
|---|---|---|
| API-001 | `GET /api/v1/users/me/push-config` | 200 `{isEnabled, vapidPublicKey}` — VAPID 미설정이어도 200 |
| API-002 | `PUT /api/v1/users/me/push-subscriptions` | 200 `{id}` · 422 (검증 실패) |
| API-003 | `DELETE /api/v1/users/me/push-subscriptions/{subscription_id}` | 204 (없음·타인 것도 204) · 422 (UUID 아님) |

- I-13 예외 `/api/v1/users` 안 (auth·onboarding 과 같은 위치, C-16).
- API-002 검증 (Pydantic 422): **ASCII 만** · `https` · 포트 없음/443 · userinfo 없음 · IP 리터럴 아님 · 길이 ≤ 2048 ·
  공백·제어문자·역슬래시 없음 · 호스트 allowlist (`schemas.PUSH_HOST_ALLOWLIST` — 점 없이 정확 일치,
  점으로 시작하면 하위 도메인 접미사 일치). `.notify.windows.com` (Edge/WNS) 은 미검증.
- API-003 은 endpoint 를 URL 에 넣지 않으려고 id 로 지정한다 (접근 로그에 capability URL 이 남지 않게).

---

## 6. 불변식

- **모든 조회·삭제에 `user_id` WHERE** (B-2 `workspace_id` 필터의 대체). 404/410 정리 삭제도 `id AND user_id`.
- upsert = `pg_insert(...).on_conflict_do_update(index_elements=["endpoint"])` + `session.execute` (B-10 G3-keep-dialect, C-19).
  같은 endpoint 면 id 유지 + **현재 사용자로 rebind** (같은 기기의 계정 전환 서버 백스톱). flush 후 IntegrityError catch 금지.
- **endpoint·keys·payload 원문을 로그·응답에 넣지 않는다.** 응답은 `{id}` 뿐, 로그는 meeting_id·user_id·개수·상태코드·예외 타입명만.
  `PushTarget` 의 endpoint·keys 는 `repr` 에서 빠져 있다.
- 페이로드 = `{"v":1,"kind","meetingId","workspaceId"}` 만, 직렬화 ≤ 512B (`build_meeting_payload` 가 넘으면 `PushPayloadTooLargeError`).
  회의 제목·요약·전사·이름 미포함 (게이트 ④).
- `webpush_async` 인자: `ttl=86400` · **`timeout=10` 명시** (미지정 = 무제한) · `headers={"Urgency": "normal"}` ·
  `vapid_claims` 호출마다 새 dict (라이브러리가 aud·exp 를 주입해 변형) · aiohttp `ClientSession` 1개를 한 번의 발송 전체가 공유.
- 발송은 best-effort — 재시도 없음. 404·410 → 행 삭제, 그 외(429·5xx·403·413·타임아웃) → 행 유지 + warning 1줄.
- 발송 구간(네트워크 대기)에는 열린 DB 세션 0개 — `PushDispatchService` 는 Repository 를 갖지 않는다.

---

## 7. 설정 (`core/config.py`, pwa.md §5.7)

| env | 형식 |
|---|---|
| `VAPID_PUBLIC_KEY` | uncompressed P-256 공개키 base64url (65바이트 → 87자) |
| `VAPID_PRIVATE_KEY` | raw P-256 개인키 base64url (32바이트 → 43자), `SecretStr` |
| `VAPID_SUBJECT` | `mailto:…` 또는 `https:…` |

- 셋 다 있어야 활성. 일부만 있거나 형식이 틀리면 **warning 만** (부팅 차단 금지, C-18).
- 런타임 env 다 (build.env 아님). 키를 바꾸면 기존 구독은 전부 무효가 된다 — 자동 재구독은 없다.
  FE 는 다음 앱 로드에서 구독의 `applicationServerKey` 가 API-001 공개키와 다르면 API-003 + 로컬 unsubscribe +
  표식 삭제를 하고 SCR-002 를 '꺼짐'으로 보인다. 사용자가 다시 켜면 새 키로 구독한다 (pwa.md §5.5, ADR-035).
  서버는 옛 키 구독의 발송 403 을 정리하지 않는다 (§6 — 403 은 행 유지).
- 생성 (개인키·공개키 한 쌍, 위 형식 그대로):

```bash
cd apps/api && uv run python -c "import base64;from cryptography.hazmat.primitives.asymmetric import ec;from cryptography.hazmat.primitives import serialization as s;k=ec.generate_private_key(ec.SECP256R1());e=lambda b:base64.urlsafe_b64encode(b).rstrip(b'=').decode();print('VAPID_PRIVATE_KEY='+e(k.private_numbers().private_value.to_bytes(32,'big')));print('VAPID_PUBLIC_KEY='+e(k.public_key().public_bytes(s.Encoding.X962,s.PublicFormat.UncompressedPoint)))"
```

- 이 형식으로 "서명 → 공개키 검증" 왕복을 `tests/push/test_push_sender.py` 가 고정한다.

---

## 8. 별칭 금지

- "구독 / PushSubscription" 고정. "device", "token", "registration" 등 별칭 금지 (registration 은 SW 등록과 혼동).
- 발송 이벤트 = `kind` (`meeting.completed` · `meeting.failed`). "type", "event" 별칭 금지.
