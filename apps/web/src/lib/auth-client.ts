// Better Auth 클라이언트 (ADR-031 — Clerk 대체)
//
// baseURL 을 지정하지 않으면 현재 origin 을 쓴다. FE 와 auth 핸들러가 같은 Next 앱이므로 그대로 둔다.
"use client";

import { createAuthClient } from "better-auth/react";
import { jwtClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  plugins: [jwtClient()],
});

export const { signIn, signUp, signOut, useSession } = authClient;
