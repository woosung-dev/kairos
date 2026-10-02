"use client";
// 웹 푸시 훅 — API-001 조회 · SCR-002 상태·토글 · 앱 로드 동기화 · 로그아웃 정리
// (docs/requirements/pwa.md §5.5 · §5.6)
import { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { useMe } from "@/features/auth/hooks";
import { pushKeys } from "@/lib/query-keys";
import { useApiClient } from "@/lib/use-api-client";

import { fetchPushConfig } from "./api";
import {
  createBrowserPushDeps,
  disablePushOnDevice,
  enablePush,
  resolvePushDeviceState,
  syncPushOnAppLoad,
  type PushDeviceState,
} from "./flows";
import { readPushEnvironment } from "./utils";

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

/** 로그아웃 앞단 정리 — signOut 이전에 await 한다 (이후엔 토큰이 401). 3초 안에 끝나고 throw 하지 않는다. */
export function usePushLogoutCleanup(): () => Promise<void> {
  const api = useApiClient();
  return useCallback(() => disablePushOnDevice(api, createBrowserPushDeps()), [api]);
}

export type PushSettingsState = "loading" | PushDeviceState;

/** SCR-002 — 마운트 시 상태 판정, 토글 클릭 때만 켜기(권한 요청)·끄기. */
export function usePushSettings(vapidPublicKey: string | null) {
  const api = useApiClient();
  const { data: me } = useMe();
  const meId = me?.id;
  const [state, setState] = useState<PushSettingsState>("loading");
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    if (!meId) return;
    let isActive = true;
    const deps = createBrowserPushDeps();
    const evaluate = () => {
      const env = readPushEnvironment();
      void resolvePushDeviceState(meId, vapidPublicKey, env, deps).then((next) => {
        if (!isActive) return;
        setState(next);
        // 등록 없음 — prod 첫 방문은 registrar 가 load 뒤 등록하고 claim 하면 controllerchange 가 온다.
        // dev·kill-switch 에선 오지 않아 '사용 불가' 로 남는다 (pwa.md §5.6).
        if (next === "unavailable" && env.hasServiceWorker) {
          navigator.serviceWorker.addEventListener("controllerchange", evaluate, { once: true });
        }
      });
    };
    evaluate();
    return () => {
      isActive = false;
      if ("serviceWorker" in navigator) {
        navigator.serviceWorker.removeEventListener("controllerchange", evaluate);
      }
    };
  }, [meId, vapidPublicKey]);

  const handleToggle = async () => {
    if (!meId || isBusy || (state !== "on" && state !== "off")) return;
    setIsBusy(true);
    try {
      const deps = createBrowserPushDeps();
      if (state === "on") {
        // 끄기는 실패해도 UI 를 끈다 (best-effort, pwa.md §5.5)
        await disablePushOnDevice(api, deps);
        setState("off");
        return;
      }
      if (!vapidPublicKey) throw new Error("VAPID public key is missing");
      const outcome = await enablePush(api, { meId, vapidPublicKey }, deps);
      setState(outcome === "dismissed" ? "off" : outcome);
    } catch {
      // 상태를 바꾸지 않았으므로 토글은 이전 값 그대로다 (원복)
      toast.error("알림 설정을 바꾸지 못했어요. 잠시 후 다시 시도해 주세요.");
    } finally {
      setIsBusy(false);
    }
  };

  return { state, isBusy, handleToggle };
}
