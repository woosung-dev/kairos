# 런북: 비밀번호 수동 재설정 (클로즈드 베타)

> 체크리스트 0-16 · 제품 결정: 발송 인프라(이메일)가 생기기 전까지는 **운영자가 수동으로** 재설정한다.
> 도구: [`scripts/auth/reset-password.mjs`](../../../scripts/auth/reset-password.mjs) — SQL 을 만들기만 하고 DB 에 붙지 않는다.

**대상**: 이메일/비밀번호로 가입한 사용자. Google 로그인 사용자는 대상이 아니다 — Google 로 로그인하라고 안내한다
(스크립트도 credential 계정이 없으면 아무것도 바꾸지 않고 실패한다).

## 어디에 무엇이 있나 (Better Auth 1.6.29 소스로 확인)

| 항목 | 값 | 근거 |
|---|---|---|
| 해시 저장 위치 | `auth_account.password` (`"providerId" = 'credential'`, 사용자당 1행) | `alembic/versions/c1a7e0b5d3f2_*.py`, `better-auth/dist/api/routes/sign-up.mjs` |
| 해시 알고리즘 | scrypt N=16384 r=16 p=1 dkLen=64, 비밀번호 NFKC 정규화, 저장 `saltHex:keyHex` | `@better-auth/utils@0.4.2 dist/password.node.mjs` (`auth.ts` 에 오버라이드 없음) |
| 길이 정책 | 8~128자 (기본값) | `better-auth/dist/context/create-context.mjs` |
| 세션 | `auth_session` 행 (cookieCache 미사용 → 행을 지우면 즉시 로그아웃) | `auth.ts`, `api/routes/session.mjs` |
| API 토큰 | 이미 발급된 JWT 는 **최대 15분** 더 유효 (백엔드는 서명·만료만 검증) | `better-auth/dist/plugins/jwt/sign.mjs` 기본 `15m` |

## 1. 본인 확인 — 통과 못 하면 여기서 멈춘다

1. 요청이 **가입 이메일 주소**에서 왔는지 본다. 다른 주소·다른 채널이면 가입 이메일로 되물어 확인한다.
2. 운영자가 이미 알고 있는 연락처(초대 때 쓴 메신저·전화)로 **역으로** 연락해 요청 사실을 확인한다.
3. 계정 존재와 로그인 방식을 확인한다 (읽기 전용):

   ```bash
   printf "SELECT u.email, a.\"providerId\", u.\"createdAt\" FROM auth_user u JOIN auth_account a ON a.\"userId\" = u.id WHERE lower(u.email) = lower('user@example.com');" \
     | ssh oci-tokyo 'bash -lc "docker exec -i kairos-db psql -U kairos -d kairos -tA"'
   ```

4. 날짜·요청 채널·확인 방법을 **비공개 메모**에 남긴다 (공개 레포에 쓰지 않는다).

## 2. 임시 비밀번호 만들기 (맥, 레포 루트)

```bash
export KAIROS_NEW_PASSWORD="$(openssl rand -base64 18)"   # 24자 무작위. 히스토리엔 이 명령 문자열만 남는다
printf '%s\n' "$KAIROS_NEW_PASSWORD"                      # 사용자에게 전달할 값 — 화면에서 한 번만 본다
```

비밀번호는 argv 로 넘기지 않는다 — 스크립트는 env `KAIROS_NEW_PASSWORD` 또는 파이프 stdin 으로만 받는다.
사용자가 정한 값을 써야 하면 `read -rs KAIROS_NEW_PASSWORD && export KAIROS_NEW_PASSWORD` 로 에코 없이 입력한다.

## 3. 적용 — 비밀번호 교체 + 그 사용자의 세션 전부 폐기 (한 트랜잭션)

```bash
node scripts/auth/reset-password.mjs user@example.com \
  | ssh oci-tokyo 'bash -lc "docker exec -i kairos-db psql -U kairos -d kairos -v ON_ERROR_STOP=1"'
unset KAIROS_NEW_PASSWORD
```

- 성공: `NOTICE:  kairos-reset: password updated = 1 row, sessions revoked = N for user@example.com` + exit 0
- 실패(exit 3, **아무것도 안 바뀜**): `auth_user rows ... = 0` (이메일 오타) · `credential account rows = 0` (Google 전용 계정)
- 계정 탈취가 의심돼 **세션만** 끊을 때: `node scripts/auth/reset-password.mjs --sessions-only user@example.com | ssh ...` (같은 파이프)

## 4. 사용자에게 알리기

요청이 온 채널과 **다른** 확인된 채널로 보낸다 (예: 요청=이메일 → 비밀번호=메신저).

> Kairos 비밀번호를 재설정했습니다. 임시 비밀번호: `<값>`
> 기존에 로그인돼 있던 기기는 모두 로그아웃됐습니다. 새 비밀번호로 로그인한 뒤 비밀번호 관리자에 저장해 주세요.
> 본인이 요청하지 않았다면 바로 알려 주세요.

⚠ 앱에는 아직 비밀번호 변경 화면이 없다 — 임시 비밀번호가 그대로 계속 쓰인다. 그래서 길고 무작위인 값을 쓴다.

## 5. 확인

사용자가 로그인했다고 알려 오면 새 세션이 생겼는지 본다:

```bash
printf "SELECT count(*) FROM auth_session s JOIN auth_user u ON u.id = s.\"userId\" WHERE lower(u.email) = lower('user@example.com') AND s.\"createdAt\" > now() - interval '1 hour';" \
  | ssh oci-tokyo 'bash -lc "docker exec -i kairos-db psql -U kairos -d kairos -tA"'
```

## 로컬 리허설 (운영 전에 한 번)

로컬 QA 스택(`kairos-qa-db` 127.0.0.1:5436 · db `kairos_qa`)의 테스트 계정으로 같은 절차를 돌린다.

```bash
export KAIROS_NEW_PASSWORD="$(openssl rand -base64 18)"
node scripts/auth/reset-password.mjs qa-member@kairos.test \
  | docker exec -i kairos-qa-db psql -U kairos -d kairos_qa -v ON_ERROR_STOP=1
# → 로컬 웹에서 새 비밀번호 로그인 성공 · 옛 비밀번호 실패 · 기존 브라우저 세션 로그아웃 확인
unset KAIROS_NEW_PASSWORD
```

2026-09-27 에 QA 덤프를 복원한 **임시 컨테이너**에서 SQL 을 검증했다: 대상 1명만 해시 교체 + 세션 3건 폐기,
저장된 해시를 Better Auth `verifyPassword` 가 새 비밀번호로 `true` · 틀린 비밀번호로 `false` 판정,
Google 전용 계정·없는 이메일은 exit 3 으로 롤백, 다른 사용자 세션 불변.
