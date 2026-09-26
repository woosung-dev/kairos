#!/usr/bin/env node
// 운영자 수동 비밀번호 재설정 SQL 생성기 (체크리스트 0-16)
// 런북: docs/operations/runbooks/manual-password-reset.md
//
// Better Auth 1.6.29 의 credential 해시를 만들고, 그 해시로 auth_account.password 를 바꾸고
// 해당 사용자의 auth_session 을 전부 지우는 SQL 을 **stdout** 으로 낸다. DB 에 직접 붙지 않는다 —
// 출력을 psql 로 흘려보내는 것은 운영자의 몫이다. 사람용 안내는 stderr 로만 쓴다.
//
// 사용:
//   read -rs KAIROS_NEW_PASSWORD && export KAIROS_NEW_PASSWORD
//   node scripts/auth/reset-password.mjs user@example.com | <psql ...>
//   unset KAIROS_NEW_PASSWORD
//
//   printf '%s\n' "$PW" | node scripts/auth/reset-password.mjs user@example.com | <psql ...>   # stdin
//   node scripts/auth/reset-password.mjs --sessions-only user@example.com | <psql ...>        # 세션 폐기만
//
// ★비밀번호는 argv 로 받지 않는다 (셸 히스토리 · ps 에 남는다). env KAIROS_NEW_PASSWORD 또는 파이프 stdin 만.
//   터미널 stdin 은 에코가 켜져 있어 화면에 비밀번호가 보이므로 거부한다.
//
// 해시 형식 — better-auth/dist/crypto/password.mjs 가 쓰는
// @better-auth/utils@0.4.2 dist/password.node.mjs 를 그대로 재현한다 (auth.ts 에 password.hash 오버라이드 없음):
//   salt = randomBytes(16).toString("hex")                   ← 32자 hex **문자열 자체**가 scrypt salt 다
//   key  = scrypt(password.normalize("NFKC"), salt, 64, { N: 16384, r: 16, p: 1, maxmem: 128*N*r*2 })
//   저장 = `${salt}:${key.toString("hex")}`                    → auth_account.password ("providerId" = 'credential')
// 길이 정책 = Better Auth 기본값 (context/create-context.mjs: min 8 / max 128).
//
// 외부 의존성 0 (node:crypto 만). 운영 서버에 node 가 없어도 맥에서 만들어 SQL 만 ssh 로 흘려보낸다.
import { randomBytes, scrypt } from "node:crypto";
import { readFileSync } from "node:fs";

const SCRYPT = { N: 16384, r: 16, p: 1, dkLen: 64 };
const MIN_PASSWORD_LENGTH = 8;
const MAX_PASSWORD_LENGTH = 128;
// SQL 리터럴에 들어가므로 따옴표·백슬래시·달러·세미콜론·공백을 아예 허용하지 않는다.
const EMAIL_PATTERN = /^[^\s@'"\\$;]+@[^\s@'"\\$;]+\.[^\s@'"\\$;]+$/;

function fail(message) {
  process.stderr.write(`❌ ${message}\n`);
  process.exit(1);
}

function hashPassword(password) {
  const salt = randomBytes(16).toString("hex");
  return new Promise((resolve, reject) => {
    scrypt(
      password.normalize("NFKC"),
      salt,
      SCRYPT.dkLen,
      { N: SCRYPT.N, r: SCRYPT.r, p: SCRYPT.p, maxmem: 128 * SCRYPT.N * SCRYPT.r * 2 },
      (err, key) => (err ? reject(err) : resolve(`${salt}:${key.toString("hex")}`)),
    );
  });
}

function readPassword() {
  const fromEnv = process.env.KAIROS_NEW_PASSWORD;
  if (fromEnv !== undefined && fromEnv !== "") return fromEnv;
  if (process.stdin.isTTY) {
    fail("비밀번호가 없다. `read -rs KAIROS_NEW_PASSWORD && export KAIROS_NEW_PASSWORD` 후 다시 실행하거나 파이프로 넣어라 (터미널 직접 입력은 에코되므로 받지 않는다)");
  }
  // 파이프 입력: 끝의 개행 1개만 떼어낸다 (앞뒤 공백은 비밀번호의 일부일 수 있다)
  return readFileSync(0, "utf8").replace(/\r?\n$/, "");
}

const args = process.argv.slice(2);
const sessionsOnly = args[0] === "--sessions-only";
const rest = sessionsOnly ? args.slice(1) : args;
if (rest.length !== 1 || rest[0].startsWith("-")) {
  fail("사용법: reset-password.mjs [--sessions-only] <email>  (비밀번호는 env KAIROS_NEW_PASSWORD 또는 stdin)");
}
const email = rest[0].toLowerCase();
if (!EMAIL_PATTERN.test(email)) fail(`이메일 형식이 아니거나 허용하지 않는 문자가 있다: ${email}`);

const header = [
  `-- Kairos 수동 비밀번호 재설정 (${sessionsOnly ? "세션 폐기만" : "비밀번호 교체 + 세션 폐기"})`,
  `-- 생성 ${new Date().toISOString()} · 대상 ${email}`,
  "-- DO 블록 하나 = 트랜잭션 하나. 조건이 안 맞으면 RAISE EXCEPTION 으로 전부 롤백된다.",
  "\\set ON_ERROR_STOP on",
];

let body;
if (sessionsOnly) {
  body = `DO $kairos_reset$
DECLARE
  v_users int;
  v_user text;
  v_sessions int;
BEGIN
  SELECT count(*) INTO v_users FROM auth_user WHERE lower(email) = '${email}';
  IF v_users <> 1 THEN
    RAISE EXCEPTION 'kairos-reset: auth_user rows for % = % (expected 1) - aborted', '${email}', v_users;
  END IF;
  SELECT id INTO v_user FROM auth_user WHERE lower(email) = '${email}';
  DELETE FROM auth_session WHERE "userId" = v_user;
  GET DIAGNOSTICS v_sessions = ROW_COUNT;
  RAISE NOTICE 'kairos-reset: sessions revoked = % for %', v_sessions, '${email}';
END
$kairos_reset$;`;
} else {
  const password = readPassword();
  // Better Auth 와 같은 기준(UTF-16 code unit 수 = String.length)으로 센다 — sign-up.mjs 의 검사와 동일.
  const length = password.length;
  if (length < MIN_PASSWORD_LENGTH || length > MAX_PASSWORD_LENGTH) {
    fail(`비밀번호 길이는 ${MIN_PASSWORD_LENGTH}~${MAX_PASSWORD_LENGTH}자여야 한다 (받은 길이 ${length})`);
  }
  const hash = await hashPassword(password);
  if (!/^[0-9a-f]{32}:[0-9a-f]{128}$/.test(hash)) fail("해시 형식 검증 실패 (내부 오류)");
  body = `DO $kairos_reset$
DECLARE
  v_users int;
  v_user text;
  v_accounts int;
  v_sessions int;
BEGIN
  SELECT count(*) INTO v_users FROM auth_user WHERE lower(email) = '${email}';
  IF v_users <> 1 THEN
    RAISE EXCEPTION 'kairos-reset: auth_user rows for % = % (expected 1) - aborted', '${email}', v_users;
  END IF;
  SELECT id INTO v_user FROM auth_user WHERE lower(email) = '${email}';
  UPDATE auth_account SET password = '${hash}', "updatedAt" = now()
   WHERE "userId" = v_user AND "providerId" = 'credential';
  GET DIAGNOSTICS v_accounts = ROW_COUNT;
  IF v_accounts <> 1 THEN
    RAISE EXCEPTION 'kairos-reset: credential account rows = % (expected 1) - Google-only account? aborted', v_accounts;
  END IF;
  DELETE FROM auth_session WHERE "userId" = v_user;
  GET DIAGNOSTICS v_sessions = ROW_COUNT;
  RAISE NOTICE 'kairos-reset: password updated = % row, sessions revoked = % for %', v_accounts, v_sessions, '${email}';
END
$kairos_reset$;`;
}

process.stdout.write(`${header.join("\n")}\n${body}\n`);
process.stderr.write(
  `ℹ SQL 을 stdout 으로 냈다 (대상 ${email}). psql 출력의 NOTICE 'kairos-reset: ...' 줄로 결과를 확인한다.\n`,
);
