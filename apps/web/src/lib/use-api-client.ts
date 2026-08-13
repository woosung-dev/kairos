"use client";
// Clerk getToken 을 클로저로 주입한 ApiClient 를 제공하는 훅 (PR-3 c5 seam)

import { useMemo } from "react";
import { useAuth } from "@clerk/nextjs";
import { createApiClient, type ApiClient } from "./api-client";

export function useApiClient(): ApiClient {
  const { getToken } = useAuth();
  return useMemo(() => createApiClient(() => getToken()), [getToken]);
}
