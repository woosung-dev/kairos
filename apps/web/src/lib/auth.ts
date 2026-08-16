// Better Auth 서버 설정 (ADR-031 — Clerk 대체)
//
// ★이 모듈은 Next 서버에서만 로드된다. 클라이언트 번들에 들어가면 pg / secret 이 노출된다.
//
// ★env 를 module scope 에서 throw 하지 않는 이유:
//   `next build` 가 route module 을 평가하므로 여기서 던지면 빌드가 죽는다. Clerk 시절 CI 가
//   형식이 맞는 fake key 를 주입해야 했던 원인이 그것이다. 대신 미설정은 런타임 500 으로 드러나고,
//   배포 게이트(`/api/auth/jwks` 200 확인)가 그걸 잡는다.
import { betterAuth } from "better-auth";
import { jwt } from "better-auth/plugins";
import { Pool } from "pg";

const baseURL = process.env.BETTER_AUTH_URL ?? "http://localhost:3000";

export const auth = betterAuth({
  baseURL,
  secret: process.env.BETTER_AUTH_SECRET ?? "",
  // ★node-postgres 형식이다. 백엔드의 `postgresql+asyncpg://` DSN 을 그대로 넣으면 안 된다.
  // ★max 를 명시한다 — pg 기본값(10)을 그대로 두면 로그인 폭주가 db 의 max_connections=50 에서
  //   api(pool 5 + overflow 10)의 몫을 잠식한다. 인증은 짧고 드문 쿼리라 5로 충분하다.
  database: new Pool({
    connectionString: process.env.BETTER_AUTH_DATABASE_URL ?? "",
    max: 5,
  }),
  // 코어 테이블은 단수형(user/session/account/verification)이라 앱 도메인의 `users` 와 헷갈린다.
  // `auth_` 접두사로 고정해 인증 전용 테이블임을 스키마에서 드러낸다 (users.auth_user_id 와 대응).
  user: { modelName: "auth_user" },
  session: { modelName: "auth_session" },
  account: { modelName: "auth_account" },
  verification: { modelName: "auth_verification" },
  emailAndPassword: { enabled: true },
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
    },
  },
  trustedOrigins: [baseURL],
  plugins: [
    jwt({
      schema: { jwks: { modelName: "auth_jwks" } },
      // 기본 payload 는 session.user 전체(createdAt/updatedAt/emailVerified 포함)를 실어 토큰이 커진다.
      // 백엔드(`apps/api/src/auth/dependencies.py`)가 소비하는 것은 sub/name/email 셋뿐이므로 그만 넣는다.
      // sub 는 sign.mjs 가 session.user.id 로 별도 세팅한다.
      jwt: {
        definePayload: ({ user }) => ({
          name: user.name,
          email: user.email,
        }),
      },
    }),
  ],
});
