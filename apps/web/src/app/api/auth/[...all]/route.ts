// Better Auth 핸들러 마운트 (ADR-031)
//
// ★이 앱 최초의 route handler 다 (Clerk 시절 src/app/api/** 는 비어 있었다).
// proxy.ts 의 public matcher 가 /api/auth 를 반드시 통과시켜야 한다 — 아니면 로그인 자체가 막힌다.
import { toNextJsHandler } from "better-auth/next-js";

import { auth } from "@/lib/auth";

export const { GET, POST } = toNextJsHandler(auth);
