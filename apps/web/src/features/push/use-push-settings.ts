"use client";
// SCR-002 알림 설정 훅 — 마운트 시 상태 판정, 토글 클릭 때만 켜기(권한 요청)·끄기
// (docs/requirements/pwa.md §5.5 · §5.6). 설정 화면 전용 — 셸 청크에 싣지 않으려고 `hooks.ts` 와 나눴다.
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useMe } from "@/features/auth/hooks";
import { useApiClient } from "@/lib/use-api-client";

import {
  createBrowserPushDeps,
  disablePushOnDevice,
  enablePush,
  resolvePushDeviceState,
  type PushDeviceState,
} from "./flows";
import { readPushEnvironment } from "./utils";

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
