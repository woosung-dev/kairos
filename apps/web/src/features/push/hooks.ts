"use client";
// 웹 푸시 셸 훅 — API-001 조회 · 앱 로드 동기화 · 로그아웃 정리 (docs/requirements/pwa.md §5.5)
// ★`(app)` 셸(PushSync)과 헤더(로그아웃)가 import 해 모든 인증 라우트의 공용 청크에 실린다.
//   설정 화면 전용 로직(SCR-002 상태·토글)은 `use-push-settings.ts` 에 둔다 (GATE-PR2).
import { useCallback, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

import { useMe } from "@/features/auth/hooks";
import { pushKeys } from "@/lib/query-keys";
import { useApiClient } from "@/lib/use-api-client";

import { fetchPushConfig } from "./api";
import { createBrowserPushDeps, disablePushOnDevice, syncPushOnAppLoad } from "./flows";

export function usePushConfig() {
  const api = useApiClient();
  return useQuery({
    queryKey: pushKeys.config(),
    queryFn: () => fetchPushConfig(api),
    // 서버 env(VAPID)로만 바뀐다 — 세션 동안 사실상 고정
    staleTime: 5 * 60_000,
    retry: false,
  });
}

// 계정당 1회 — 재렌더·라우트 이동·셸 재마운트에는 다시 돌지 않는다 (vercel advanced-init-once).
// boolean 이 아니라 마지막 계정 id 다: 로그아웃→다른 계정 로그인은 soft navigation 이라 JS 수명이
// 이어진다 — 그때 새 계정 기준으로 다시 동기화해야 앞 계정의 구독이 남지 않는다 (EVAL-P2-1 D3).
let lastSyncedMeId: string | null = null;

/**
 * 앱 로드 동기화 (pwa.md §5.5) — `(app)` 셸에 1번 마운트한다. `me` 와 API-001 이 끝난 뒤에 돈다
 * (키 불일치 판정에 공개키가 필요하다). API-001 이 실패하면 키 없이(null) 돈다 — 키 비교만 빠진다.
 */
export function usePushAppLoadSync(): void {
  const api = useApiClient();
  const { data: me } = useMe();
  const meId = me?.id;
  const pushConfig = usePushConfig();
  const isConfigSettled = pushConfig.isSuccess || pushConfig.isError;
  const vapidPublicKey = pushConfig.data?.vapidPublicKey ?? null;

  useEffect(() => {
    if (!meId || !isConfigSettled || lastSyncedMeId === meId) return;
    lastSyncedMeId = meId;
    void syncPushOnAppLoad(api, meId, vapidPublicKey, createBrowserPushDeps());
  }, [api, meId, isConfigSettled, vapidPublicKey]);
}

/**
 * 로그아웃 앞단 정리 — signOut 이전에 await 한다 (이후엔 토큰이 401). 3초 안에 끝나고 throw 하지 않는다.
 * 시작할 때 동기화 가드를 비운다 — 같은 JS 수명에서 **같은 계정**이 다시 로그인했는데 ①·②가 둘 다
 * 실패했으면 남은 구독을 다음 동기화(표식 없음 → unsubscribe)가 끊어야 한다.
 */
export function usePushLogoutCleanup(): () => Promise<void> {
  const api = useApiClient();
  return useCallback(() => {
    lastSyncedMeId = null;
    return disablePushOnDevice(api, createBrowserPushDeps());
  }, [api]);
}
