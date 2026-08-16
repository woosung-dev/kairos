# Better Auth 전환 — 다음 세션 인계

> 그대로 복사해 새 세션에 붙여넣으면 된다.
> 상세 결정은 `docs/adr/031-better-auth-migration.md` 가 정본이다.

---

## 붙여넣을 프롬프트

```
Kairos 의 Clerk → Better Auth 전환을 이어서 진행한다.
정본은 docs/adr/031-better-auth-migration.md, 인계 문서는
docs/plans/active/2026-08-17-better-auth-cutover-handoff.md 다. 둘 다 먼저 읽어라.

지난 세션에서 코드 전환은 끝났고 PR #177 이 CI green 상태로 열려 있다.
남은 것은 (1) 배포 사전 준비 (2) 2단계 배포 (3) 컷오버 +7일 정리 다.

먼저 PR #177 이 아직 열려 있는지, main 이 그 사이 움직였는지 확인하고
현재 상태를 알려준 다음 진행 방향을 제안해줘.
```

---

## 지난 세션에 한 것 (PR #177, 8커밋 / 158파일)

**결정** — ADR-031 D1~D11. 핵심만:

- Better Auth 를 Next.js `/api/auth/[...all]` 에 마운트, `jwt` 플러그인 JWKS 로 FastAPI 가 검증 (Bearer 유지)
- 기각: BFF 전량 프록시(RAG SSE 프록시 재작성 필요) · 세션 쿠키 직접 조회(공식 계약 없음 + `.woosung.dev` 광역 쿠키가 형제 서비스로 샘)
- 서명 = EdDSA/Ed25519 기본값, exp 15분
- **컬럼은 rename 이 아니라 가산** — `auth_user_id` 추가, `clerk_id` 는 nullable 로 완화만. 롤백이 이미지 태그만으로 끝나고, 창업자 레거시 행 식별이 가능해진다
- `AUTH_PROD_HARDENING` 기본 True 로 **재무장** (migrate one-shot 이 config 게이트라 crash-loop 경로가 구조적으로 막힘)
- JWKS URL 을 issuer 에서 분리 → prod 는 내부망 `http://web:3000/api/auth/jwks`
- members 응답에서 외부 인증 ID 제거, FE 권한 판정은 내부 UUID 축으로

**검증 (전부 실측)**

- CI 전부 green: `changes · backend-test · contract-check · frontend-build · e2e · CI Required`
- e2e **32 passed, 11 skipped** — 로그인 폼 → 세션 → JWT → 백엔드 관통이 CI 에서 실제로 돈다
- 로컬: BE 919 passed / FE 164 passed / 계약 drift 0
- alembic 25 리비전을 일회용 pgvector 컨테이너에 실제 적용 + downgrade/재upgrade 멱등 확인
- 프로덕션 standalone 이미지를 띄워 compose 내부망 DB 에 붙여 `/api/auth/jwks` 200 + Ed25519 키 확인
- 창업자 재연결 SQL 을 실제로 실행해 검증 (아래 함정 참조)

**덤으로 고친 것** — `seed_qa_fixtures.py` 의 `owner_clerk_id`(존재한 적 없는 컬럼) · `find_by_email` dead code(비-UNIQUE email + `.one_or_none()`) · 랜딩 카피의 철거된 스택 4종

---

## 남은 것

### 1. 배포 사전 준비 (사용자 작업 · 코드 아님)

- [ ] **Google OAuth 클라이언트 신규 발급** — ★Drive 연동(ADR-026)의 `GOOGLE_OAUTH_CLIENT_ID` 와 **반드시 다른 클라이언트**. 같이 쓰면 로그인이 Drive 의 restricted scope 앱 검증에 딸려 들어가고 시크릿 로테이션이 둘을 동시에 끊는다.
  - redirect URI: `https://kairos.woosung.dev/api/auth/callback/google`, `http://localhost:3000/api/auth/callback/google`
- [ ] **`BETTER_AUTH_SECRET` 생성** — `openssl rand -base64 32`. 서버 `~/kairos/.env`(0600) 에만. **`deploy/oci/build.env` 금지** (`--build-arg` 로 이미지 레이어에 평문으로 박힌다)
- [ ] 서버 `~/kairos/.env` 갱신 — `CLERK_*` 5줄 삭제, `AUTH_*` 4개 + `BETTER_AUTH_*` 3개 + `GOOGLE_CLIENT_*` 2개 추가 (템플릿: `deploy/oci/.env.example`)
- [ ] 로컬 `deploy/oci/build.env` 갱신 — `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` 줄 삭제, `NEXT_PUBLIC_FOUNDER_CLERK_ID` → `NEXT_PUBLIC_FOUNDER_USER_ID`(값은 재가입 후 확정)

### 2. PR #177 머지

머지해도 자동 배포는 없다 (`deploy.yml` 은 ADR-028 로 제거됨). 배포는 전부 수동 `just` 레시피다.

### 3. 2단계 배포 (ADR-031 §배포)

**D-1 · dormant 배포** — Clerk 는 그대로 살아 있고 사용자 영향 0. 목적은 컷오버 당일에 처음 시도하는 것을 없애는 것 (ADR-028 이 스스로 남긴 교훈: 인증 실패와 인프라 실패를 같은 창에서 구분할 수 없다).

```
just deploy-preflight && just deploy-build <TAG-A> && just deploy-ship <TAG-A>
```
수동 스모크 4항목:
- `curl https://kairos.woosung.dev/api/auth/jwks` → `kty:"OKP"`, `crv:"Ed25519"`
- `docker exec kairos-api python -c "import urllib.request;urllib.request.urlopen('http://web:3000/api/auth/jwks').read()"` → 200 (내부망 도달)
- Google 로그인 1회 완주 → `SELECT * FROM auth_account WHERE "providerId"='google'` 1행
- `docker stats` 로 web 메모리 실측 (mem_limit 768m 적정성)

**D-0 · 컷오버** — ⏱ **다운타임 2~4분 + 전원 재가입.**

1. ☐ **`pg_dump -Fc` 로컬 저장** ← 빼먹으면 2층 롤백이 통째로 사라진다 (DB 백업 자동화 BL-OCI-1 미완)
2. ☐ `just deploy-preflight` (진행 중 회의 0 — BackgroundTasks 는 재시도가 없다)
3. ☐ `docker compose stop web api` → 다운타임 시작
4. ☐ `just deploy-ship <TAG-B>` (migrate → web → api)
5. ☐ **`curl .../api/auth/jwks` 1회** — Better Auth 는 키를 lazy 생성한다. 안 하면 첫 로그인 사용자가 JWKS 빈 셋을 맞는다
6. ☐ 창업자 재가입 → **재연결 SQL** (아래 함정)
7. ☐ `just deploy-status` + `/dashboard` 로그인 관통 → 다운타임 종료
8. ☐ **Clerk dev 인스턴스는 삭제하지 않는다** — 롤백 창 7일 유지

> #### ⚠️ 재연결 SQL 함정 2가지 (지난 세션에 실제로 깨뜨려 확인함)
>
> **① 순서가 계약이다.** UPDATE 를 먼저 하면 `ix_users_auth_user_id` UNIQUE 위반으로 통째로 실패한다.
> ```sql
> BEGIN;
>   DELETE FROM workspace_members WHERE user_id = :new_row_id;
>   DELETE FROM workspaces        WHERE owner_id = :new_row_id AND type = 'personal';
>   DELETE FROM users             WHERE id = :new_row_id;
>   UPDATE users SET auth_user_id = :new_auth_id, email = :new_email
>    WHERE clerk_id = :founder_clerk_id;
> COMMIT;
> ```
> **② 실행 직후 `api` 재기동.** `_USER_CACHE`(60초)가 삭제된 행을 들고 있어 그동안 창업자에게 워크스페이스가 비어 보인다 — 마이그레이션 실패로 오인하기 딱 좋다.

**롤백** — 1층: `just deploy-rollback <TAG-A>` 만으로 완결(스키마 가산 전용, RTO 약 2분, 데이터 손실 0). 2층: `pg_dump` 복원. ⚠️ `alembic downgrade` 는 운영에서 실행 금지.

### 4. 컷오버 +7일 (롤백 창 종료)

- [ ] alembic 신규 리비전 — `DROP INDEX ix_users_clerk_id` + `DROP COLUMN users.clerk_id`
- [ ] `apps/api/src/auth/models.py` 에서 `clerk_id` 필드 삭제 + `auth/CONTEXT.md` §3 레거시 주석 정리
- [ ] 서버 `~/kairos/.env` 의 `CLERK_*` 잔여 삭제
- [ ] **Clerk dev 인스턴스 삭제** ← **ADR-031 종료 조건.** 레포가 public 이고 히스토리 675 커밋에 dev secret 이 있다. 키가 무의미해지는 것과 실제로 무효화되는 것은 다르다
- [ ] `docs/TODO.md` 의 T-SEC-CLERK-ROTATE / T-CLEANUP-1 종결, ADR-031 Status 갱신

### 5. 후속 백로그 (별건 · 컷오버와 같은 창에서 하지 말 것)

| 항목 | 메모 |
|---|---|
| **비밀번호 재설정 경로 부재** | 레포에 이메일 발송 인프라 0건. 현재는 사인인 화면에 "Google 로그인 또는 운영자 문의" 안내만. 외부 사용자 확대 전 필수 |
| team e2e 실행 | `E2E_RUN_TEAM=true` — 이번 run 의 11 skipped 에 포함 |
| FE 스크린샷 증거 | `console.error` 0건은 e2e 가 집계해 통과, 스크린샷은 별도 |
| 계약이 raw dict 표면을 못 덮음 | `/users/me`·members 가 `response_model` 없이 dict 반환 → wire 키 변경이 OpenAPI 에 안 잡힌다. BL 등재 |
| CSP `strict-dynamic` (BL-S27e-3) | Clerk·Sentry 도메인이 사라져 진입 장벽이 크게 낮아졌다 |
| `users.email` UNIQUE | 컷오버 후 레거시+재가입 행이 같은 이메일을 가질 수 있다 |
| `auth_user` 삭제가 `users` 로 전파 안 됨 | FK 없음(설계상 소유자 분리). 탈퇴 기능 생기면 2단계 삭제 필요 |
| main dependabot 취약점 104건 | 이번 작업과 무관, 별건 |
