"use client";
// Better Auth JWT 를 클로저로 주입한 ApiClient 를 제공하는 훅 (PR-3 c5 seam / ADR-031)
//
// ★왜 캐시가 필수인가 — Clerk 의 `getToken()` 은 SDK 내부에 캐시가 있어 대개 메모리 반환이었다.
//   Better Auth 에는 동등물이 없다. 토큰은 `GET /api/auth/token` 으로 받는다. 순진하게 매번
//   부르면 대시보드 첫 진입의 5-endpoint fanout 이 그대로 5회의 추가 왕복이 된다 —
//   Sprint 24/28 이 백엔드 캐시로 깎아낸 그 경로를 프론트에서 되돌리는 셈이다.
//
// ★single-flight 도 필수다. 캐시만 있고 in-flight 공유가 없으면 fanout 이 동시에 miss 를 만나
//   5개의 동시 요청을 낸다. 캐시가 있는 척하면서 아무것도 아끼지 못한다.

import { useMemo } from "react";

import { createApiClient, type ApiClient } from "./api-client";

/** 만료 이 시간 전부터는 새로 받는다. 시계 오차 + 네트워크 지연 여유. */
const REFRESH_MARGIN_MS = 60_000;

/** 모듈 스코프 — 훅 인스턴스가 여러 개여도 토큰은 하나다. */
let cachedToken: string | null = null;
let cachedExpiresAtMs = 0;
let inFlight: Promise<string | null> | null = null;

/** JWT payload 의 exp 를 읽는다. 서명 검증은 백엔드 몫이라 여기서는 디코드만 한다. */
function readExpiryMs(token: string): number {
  try {
    const payload = token.split(".")[1];
    if (!payload) return 0;
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    const exp = (JSON.parse(json) as { exp?: number }).exp;
    return typeof exp === "number" ? exp * 1000 : 0;
  } catch {
    // 디코드 실패 = 캐시하지 않음. 다음 호출에서 다시 받는다.
    return 0;
  }
}

async function requestToken(): Promise<string | null> {
  const res = await fetch("/api/auth/token", {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { token?: string };
  return data.token ?? null;
}

async function fetchToken(): Promise<string | null> {
  if (cachedToken && Date.now() < cachedExpiresAtMs - REFRESH_MARGIN_MS) {
    return cachedToken;
  }
  // 이미 누가 받고 있으면 그 약속에 올라탄다 (single-flight).
  if (inFlight) return inFlight;

  inFlight = requestToken()
    .then((token) => {
      if (token) {
        cachedToken = token;
        cachedExpiresAtMs = readExpiryMs(token);
      }
      return token;
    })
    .catch(() => null)
    .finally(() => {
      inFlight = null;
    });

  return inFlight;
}

/** 로그아웃·세션 만료 시 호출한다. 안 하면 최대 15분간 죽은 토큰을 계속 붙인다. */
export function clearAuthTokenCache(): void {
  cachedToken = null;
  cachedExpiresAtMs = 0;
  inFlight = null;
}

export function useApiClient(): ApiClient {
  return useMemo(() => createApiClient(fetchToken), []);
}
