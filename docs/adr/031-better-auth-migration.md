# ADR-031 — Clerk → Better Auth 자체 호스팅 인증 전환

**Status**: Accepted
**Date**: 2026-08-16
**Supersedes**: [ADR-022](022-clerk-webhook-skip.md) (Clerk webhook SKIP) · [ADR-024](024-ga-readiness.md) (Clerk Production 컷오버 부분)
**Amends**: [ADR-028](028-oci-selfhosting.md) D3 / D5

---

## 배경

Kairos 는 인증만 외부 SaaS(Clerk)에 남아 있었고, 그 상태가 세 가지 문제를 만들었다.

1. **보안 부채가 실재한다.** 레포가 2026-08-16 public 으로 전환됐는데 git 히스토리 675 커밋에 Clerk dev secret 이 남아 있다. `docs/TODO.md` 에 "전환 완료로 키가 무의미해지는 것과 실제로 무효화되는 것은 다르다 — 인스턴스 삭제까지가 종료 조건" 으로 이미 등재돼 있었다.
2. **ADR-022 ↔ ADR-024 가 미결로 얽혀 있었다.** 022 는 "024 가 supersede", 024 는 "미실행". 어느 ADR 도 현재 상태(dev Clerk 인스턴스로 prod 운영 + `CLERK_PROD_HARDENING=false` + audience 검증 skip)를 기술하지 못했다. Clerk Production 컷오버가 커스텀 도메인·신규 키·사용자 마이그레이션 전체를 요구해 계속 미뤄졌기 때문이다.
3. **ADR-028 셀프호스팅 방향과 어긋난다.** 컴퓨트·DB 는 OCI 로 가져왔는데 신원만 외부에 남았다.

---

## 결정

### D1. 로그인 수단 = Google OAuth + 이메일/비밀번호

현행 UX 승계 + 외부 메일 인프라 없이도 쓸 수 있는 경로 확보.

**★Google OAuth 클라이언트는 Drive 연동(ADR-026)의 것과 반드시 분리한다.**
Drive 스코프는 Google 의 restricted scope 라 앱 검증 대상이다. 로그인을 같은 클라이언트에 얹으면 **로그인 자체가 그 검증 블라스트 반경에 들어가고**, 시크릿 로테이션이 로그인과 Drive 를 동시에 끊는다. 같은 GCP 프로젝트 안에 클라이언트를 따로 만든다.

| 용도 | env | redirect URI |
|---|---|---|
| 로그인 (web 컨테이너) | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | `{BETTER_AUTH_URL}/api/auth/callback/google` |
| Drive 연동 (api 컨테이너) | `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | `/api/v1/integrations/google-drive/callback` |

### D2. 기존 계정 전량 폐기 + 재가입. 단 창업자 행은 수기 재연결

CSV 마이그레이션 스크립트의 버그 리스크가 이득보다 크다. 실사용 계정이 dogfood 위주다.

**다만 그대로 두면 창업자 본인의 도그푸딩 데이터가 고아가 된다.** 재가입하면 새 `users` 행이 생기고, 기존 workspaces/meetings/notes/projects 는 옛 `users.id` 를 FK 로 물고 있기 때문이다. `clerk_id` 를 컷오버 시점에 남겨두면(D7) "누가 누구였는지" 를 식별해 한 트랜잭션으로 되돌릴 수 있다.

```sql
-- ★순서가 계약이다. UPDATE 를 먼저 하면 ix_users_auth_user_id UNIQUE 위반으로 통째로 실패한다.
--   (2026-08-16 로컬 실측에서 실제로 이 순서 오류로 깨졌다.)
BEGIN;
  DELETE FROM workspace_members WHERE user_id = :new_row_id;
  DELETE FROM workspaces        WHERE owner_id = :new_row_id AND type = 'personal';
  DELETE FROM users             WHERE id = :new_row_id;
  UPDATE users SET auth_user_id = :new_auth_id, email = :new_email
   WHERE clerk_id = :founder_clerk_id;
COMMIT;
```

**★실행 직후 `api` 컨테이너를 재기동한다.** `_USER_CACHE`(60초 TTL)가 삭제된 행을 들고 있어, 그동안 창업자에게 워크스페이스가 비어 보인다 — 마이그레이션 실패로 오인하기 딱 좋은 상태다.

### D3. Better Auth 를 Next.js 에 마운트 + jwt 플러그인 JWKS → FastAPI 가 검증

Better Auth 는 TypeScript 전용 라이브러리다. 제작자의 공식 답변(better-auth#301)이 "비-TS 백엔드는 JWT 플러그인 + REST 로 붙이라" 이고, Python 클라이언트 제공 계획은 없다.

- `apps/web/src/app/api/auth/[...all]/route.ts` 가 `toNextJsHandler(auth)` 로 마운트
- `jwt()` 플러그인이 `/api/auth/jwks` 로 공개키를, `/api/auth/token` 으로 JWT 를 노출
- FastAPI 는 기존 `PyJWKClient` 구조를 그대로 유지한 채 URL·issuer·클레임만 교체

**기각한 대안 2개:**

- **BFF 전량 프록시** — IETF OAuth BCP(draft-ietf-oauth-browser-based-apps)가 권장하는 최고 보안 패턴이지만, 같은 문서가 "frontend and API running on a common domain" 구성을 명시적으로 범위 밖에 둔다. 결정적 결격은 SSE 다: 비-Node 백엔드 프록시 실사례가 "streaming connections require significantly enhanced proxy logic" 을 3대 단점으로 꼽는데, Kairos 는 RAG 스트리밍이 핵심 경로다.
- **세션 쿠키를 FastAPI 가 직접 조회** — 공식 지원이 없다. 커뮤니티가 Better Auth 내부 소스를 역공학한 HMAC 코드(better-auth#2685, #4352)가 유일한 레퍼런스이며, 이는 API 계약이 아니라 구현 세부라 마이너 버전 업에 조용히 깨진다. 또한 같은 OCI 호스트에 quantbridge·truewords 가 공존하므로 `.woosung.dev` 광역 쿠키는 세션을 형제 서비스로 흘린다.

### D4. 스키마 소유권 = alembic 단독

Better Auth CLI 는 `generate` 로 SQL 산출만 하고, 적용은 alembic 리비전이 한다. 마이그레이션 주체가 둘이면 배포 파이프라인이 갈라진다. 기존 `migrate` one-shot 컨테이너 런북이 그대로 유지된다.

테이블 5개는 `modelName` 으로 `auth_` 접두사를 강제한다 — `user` 는 PostgreSQL 예약어라 psql 수기 쿼리에서 따옴표가 필요하고, 무엇보다 기존 `users` 와 한 글자 차이라 오독 사고가 확정적이다.

**컬럼 네이밍은 Better Auth 를 따른다** (`"emailVerified"`, `"userId"` camelCase). 이 테이블들은 Better Auth 런타임이 소유하고 우리 코드는 조회하지 않는다. snake_case 로 뒤집으려면 모든 필드에 `fields` 매핑이 필요하고 그게 버전 업마다 드리프트 원인이 된다.

### D5. JWT 만료 = Better Auth 기본 15분

**수용한 비용**: 발급된 JWT 는 취소할 수 없다. 로그아웃·멤버 제거 후에도 **최대 15분 + 백엔드 캐시 60초** 동안 인증이 유효하다. Clerk 의 60초 토큰이 이 문제를 실질적으로 가려주고 있었다.

**영향 범위가 좁은 이유**: role/권한은 JWT 에 없고 매 요청 DB 에서 읽는다. 강등 반영은 기존 `_MEMBER_CACHE`(15초) 속도 그대로다. 15분은 *세션 폐기* 반영에만 영향한다.

완화: FE 는 로그아웃 시 토큰 메모리 캐시를 즉시 비운다(`clearAuthTokenCache`). 파괴적 라우트는 이미 `require_member_fresh` 로 DB fresh 조회를 강제한다.

### D6. 서명 알고리즘 = EdDSA / Ed25519 (Better Auth 기본값)

PyJWT 2.12.1 이 EdDSA 를 완전 지원함을 **실측 확인**했다 — `get_default_algorithms()` 에 `EdDSA` 포함, `PyJWK.from_dict` 가 `kty:"OKP"` + `crv:"Ed25519"` 를 `Ed25519PublicKey` 로 파싱.

라이브러리 기본값에서 벗어나면 업그레이드마다 그 경로가 테스트됐는지 스스로 확인해야 한다. 부수 이득으로 서명이 64B(RS256 은 256B)라 2 OCPU VM 에서 매 요청 헤더 비용이 줄고 검증도 빠르다.

`AUTH_JWT_ALGORITHMS` 를 env 로 두어 ES256/RS256 폴백이 env 한 줄로 가능하다. `tests/auth/conftest.py` 가 3종을 매번 파라미터화 검증하므로 되돌릴 수 있는 결정으로 유지된다.

**⚠ 되돌리기 비용**: `auth_jwks` 에 키가 생성된 뒤 알고리즘을 바꾸면 `DELETE FROM auth_jwks` 가 동반되고, 그 순간 미만료 JWT 전량 무효 + 전 사용자 재로그인이다.

### D7. 컬럼 전략 = 가산 후 2단계 삭제

`users.clerk_id` 를 `auth_user_id` 로 **rename 하지 않는다.** 신규 컬럼을 추가하고 `clerk_id` 는 nullable 로 완화만 한 뒤, 컷오버 +7일에 별도 리비전으로 DROP 한다 (`docs/development/migrations.md` 2단계 배포 규약).

**얻는 것**: 리비전이 100% 가산/완화형이라 **구 api 이미지가 새 스키마 위에서 그대로 동작한다** → 롤백이 `just deploy-rollback`(이미지 태그) 만으로 완결된다. RTO 약 2분, 스키마 무손상, 데이터 손실 0. rename 했다면 역방향 리비전을 새로 작성해 앞으로 적용해야 했다.

부수 이득: D2 의 창업자 재연결이 가능해진다.

**NULL distinct 전제 실측 확인** — `ix_users_auth_user_id` 는 partial 이 아닌 UNIQUE 인덱스라 Postgres 가 NULL 을 서로 distinct 로 본다. `auth_user_id IS NULL` 인 레거시 행이 여러 개여도 충돌하지 않고, `ON CONFLICT (auth_user_id) DO NOTHING` 의 race-safe lazy seed 도 그대로 성립한다.

### D8. `auth_*` 테이블과 `users` 의 소유권 분리 (불변식)

| 저장소 | 소유 프로세스 | 내용 |
|---|---|---|
| `auth_user` / `auth_session` / `auth_account` / `auth_verification` / `auth_jwks` | **Next.js (web 컨테이너)** | 신원 · 자격증명 · 세션 · 서명키 |
| `users` + 모든 도메인 테이블 | **FastAPI (api 컨테이너)** | 도메인 프로필 · 소유권 |
| 조인 키 | `JWT.sub` = `auth_user.id` = `users.auth_user_id` | |

- **FastAPI 는 `auth_*` 를 읽지도 쓰지도 않는다.** JWT 서명 검증만으로 신원을 신뢰한다.
- **Next.js 는 도메인 테이블을 읽지도 쓰지도 않는다.**
- DDL 소유권은 alembic 단독(D4).

Better Auth 를 기존 `users` 에 매핑하는 안은 기각했다. `users.id` 는 UUID PK 인데 Better Auth 기본 id 는 TEXT 이고, 무엇보다 **`users` 행 생성 주체가 FastAPI 의 race-safe lazy seed 와 Better Auth 두 곳이 되어** `ON CONFLICT` 경합이 두 프로세스에 걸친다.

**남는 위험**: `auth_user` 삭제가 `users` 로 전파되지 않는다(FK 없음). 탈퇴 기능이 생기면 2단계 삭제가 필요하다 → 백로그.

### D9. `AUTH_PROD_HARDENING` 기본값 = `True` (재무장)

ADR-024 가 미뤄온 하드닝을 이 전환에서 함께 끝낸다. Better Auth 는 우리가 발급자를 소유하므로 "prod 인데 dev 발급자" 라는 모순 자체가 사라졌다.

**부팅 차단형 validator 를 다시 켜도 안전한 구조적 근거**: 2026-06-23~30 인시던트의 실체는 "부팅 차단" 이 아니라 `api` 의 `restart: unless-stopped` 와 결합한 **무한 재시작 루프**였다. 지금은 `migrate` one-shot 이 `alembic/env.py` 에서 `get_settings()` 를 먼저 호출하고 `api` 가 `depends_on: {migrate: service_completed_successfully}` 로 게이트되므로, config 가 잘못되면 migrate 가 죽고 api 는 아예 재생성되지 않는다. 구 컨테이너가 계속 서비스한다.

dev 판정 기준은 Clerk 호스트명 substring → **loopback 주소**(`localhost`/`127.0.0.1`/`[::1]`)로 교체했다.

### D10. JWKS URL 을 issuer 에서 분리, 내부망 경로 사용

이전에는 `dependencies.py` 가 `issuer + "/.well-known/jwks.json"` 으로 조립해 둘이 하드 결합돼 있었다. 분리하면:

```
AUTH_JWT_ISSUER=https://kairos.woosung.dev      # 토큰 iss/aud 와 대조 (공개 URL)
AUTH_JWKS_URL=http://web:3000/api/auth/jwks     # 공개키 fetch (compose 내부망)
```

공개 URL 로 fetch 하면 api → Cloudflare Edge → Tunnel → web 으로 나갔다 들어오고, **Cloudflare 장애/설정 변경이 곧 인증 장애가 된다.** 내부망을 쓰면 그 결합이 사라진다.

### D11. members 응답에서 외부 인증 ID 제거

`GET /workspaces/{id}/members` 응답의 `clerkId` 를 rename 하지 않고 **삭제**했다. FE 의 role 판정이 `member.clerkId === user.id` 문자열 매칭으로 벤더 ID 에 묶여 있었고, 그게 이번 전환에서 가장 크게 터진 지점이다. `userId`(내부 UUID)가 이미 응답에 있었으므로 추가 BE 작업은 0이다. rename 했다면 다음 전환에서 같은 곳이 또 터진다.

---

## 인프라 영향 (ADR-028 개정)

- **ADR-028 D3 "R2 · Clerk · Gemini · OpenAI · Sentry 는 유지"** → Clerk 는 제거된다.
- **ADR-028 D5 / `deploy/oci/README.md` / `docs/operations/deployment.md` 의 "API 의 문은 Clerk JWT 다"** → "API 의 문은 Better Auth 가 발급한 JWT 다. JWKS 는 내부망에서 가져온다" 로 대체. ADR-028 본문은 역사 기록이라 수정하지 않고 여기서 선언한다.
- **`web` 컨테이너가 처음으로 DB 클라이언트가 된다.** 이전에는 `CLERK_SECRET_KEY` 하나만 받고 DB 를 몰랐다. 따라오는 것:
  - `depends_on: {db: healthy, migrate: completed}` 필수. 먼저 뜨면 첫 로그인이 `relation "auth_user" does not exist` 다.
  - 커넥션 예산 — `db` 는 `max_connections=50`, `api` 가 최대 15. `auth.ts` 의 Pool 에 `max: 5` 를 명시해 무제한 기본값을 막는다.
  - `mem_limit` 512m → 768m. scrypt 비밀번호 해싱은 의도적으로 메모리를 쓰는 연산이다.
  - **장애 모드 확장**: 이제 DB 가 죽으면 로그인도 안 된다 (전에는 로그인 페이지는 떴다).
- **빌드 인자에서 인증이 사라진다.** `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` 삭제, `NEXT_PUBLIC_FOUNDER_CLERK_ID` → `NEXT_PUBLIC_FOUNDER_USER_ID`(내부 UUID). 내부 UUID 는 인증 공급자가 또 바뀌어도 불변이라 이 빌드 인자가 다시 재빌드 사유가 되지 않는다.
- **CI 의 fake key 트릭이 단순해진다.** Clerk 은 `pk_test_` + base64(`host$`) 형식 검증을 통과해야 했다. Better Auth 는 32자 이상 아무 문자열이면 된다.

---

## ADR-022 / ADR-024 정리

두 ADR 본문은 **수정하지 않는다** (역사 기록). 여기서 supersede 관계만 선언한다.

- **ADR-022 (Clerk webhook SKIP)**: Better Auth 에는 webhook 개념 자체가 없어 결정의 대상이 소멸했다. 파생 산출물 정리 — `tests/auth/test_auth_sync_disabled.py` 삭제(회귀 가드의 대상이 사라짐, `/users/me` 라우트 가드는 `test_auth_api.py` 가 이미 커버), `apps/api/src/auth/CONTEXT.md` §5 의 "Clerk webhook endpoint 부재" 불변식 삭제, `docs/REFACTORING-BACKLOG.md` 의 sync 재도입 Svix 가드 BL 무효(진입 조건이 "Clerk Production 발급" 이라 영구 도달 불가).
- **ADR-024 (GA readiness)**: **Clerk Production 인스턴스 발급 + Svix webhook 등록 2개 항목만 무효화**한다. **ADR-024 의 GA 종료 기준(외부 5명 중 3명 2주 반복 사용 / 지불 의사 1명)은 유효하게 승계한다** — 통째로 supersede 하면 살아 있는 GA 기준까지 같이 죽는다.

---

## 이번 범위에서 제외한 갭

ADR-028 의 형식을 따라 명시한다. 여기 적히지 않으면 사용자가 막힌 뒤에야 발견된다.

1. **비밀번호 재설정 / 이메일 인증이 없다.** 레포에 SMTP·Resend·SES 어느 것도 없다(grep 확인). D1 이 이메일/비밀번호를 채택했지만 "비밀번호를 잊었습니다" 경로가 존재하지 않는다. 도그푸딩 규모(<10명)에서는 창업자가 SQL 로 수동 처리하고, 사인인 화면에 "Google 로그인을 쓰시거나 운영자에게 문의" 안내를 노출한다. 메일 인프라 도입은 컷오버와 같은 창에서 하지 않는다.
2. **Google 로그인 경로는 E2E 미커버.** Google 이 자동화 브라우저를 탐지하고 reCAPTCHA/2FA 가 비결정적으로 끼어든다. E2E 는 이메일/비밀번호 전용이고, Google 경로는 수동 스모크 체크리스트 상시 항목으로 둔다.
3. **E2E CI 게이트 활성화(`vars.E2E_ENABLED`)** — 별건. 지금은 로컬 `pnpm e2e` 전량 통과가 머지 조건이다.
4. **CSP `strict-dynamic`(BL-S27e-3)** — Clerk 도메인이 사라져 조건은 개선됐으나 별건.
5. **`users.email` UNIQUE 제약** — 컷오버 후 레거시 행과 재가입 행이 같은 이메일을 가질 수 있다. `find_by_email` 은 호출자 0건 dead code 였으므로 이번에 삭제했다(부활 시 `.first()` + 명시 정렬로 새로 만든다).

---

## 종료 조건

**Clerk dev 인스턴스 삭제.** (`docs/TODO.md`) 전환 배포만으로는 끝이 아니다 — 레포가 public 이고 히스토리에 dev secret 이 남아 있어, 키가 무의미해지는 것과 실제로 무효화되는 것은 다르다.

**단 컷오버 +7일까지는 삭제하지 않는다.** 그 7일이 D7 롤백 창이다(구 이미지가 Clerk 로 돌아갈 수 있어야 한다). PR-D(`clerk_id` DROP)와 같은 시점에 실행한다.
