"use client";

// SW 등록·해제 (docs/requirements/pwa.md REQ-004·REQ-005). 아무것도 렌더하지 않는다.
//
// ★`navigator.serviceWorker.register(...)` 호출부는 레포 전체에서 여기 1곳이고, URL·옵션은
//   리터럴이다 — Next 가 이 정적 패턴을 보고 `lib/pwa/sw.ts` 를 worker 로 빌드한다 (pwa.md C-3).
//   그래서 호출을 모드 분기 **밖** 모듈 함수로 둔다: kill-switch 빌드에서도 이 참조가 살아 있어
//   sw.js 가 같은 URL 로 산출된다 — 브라우저의 업데이트 확인이 404 소음을 내지 않는다 (C-25).
//   SW 코드는 모든 빌드에서 같고(빌드 플래그를 못 읽는다, C-28), 해제는 아래 unregister 모드만 한다.
import { useEffect } from "react";
import {
  applyServiceWorkerMode,
  resolveServiceWorkerMode,
  runAfterLoad,
} from "@/lib/pwa/registration";

function registerServiceWorker(): Promise<unknown> {
  return navigator.serviceWorker.register(new URL("../../lib/pwa/sw.ts", import.meta.url), {
    scope: "/",
    updateViaCache: "none",
  });
}

function getServiceWorkerRegistrations() {
  return navigator.serviceWorker.getRegistrations();
}

function warnServiceWorkerFailure(message: string, error: unknown): void {
  console.warn(message, error);
}

// 페이지 로드당 1회 — root layout 이 다시 마운트되거나 dev StrictMode 가 effect 를 두 번
// 돌려도 등록을 반복하지 않는다 (vercel advanced-init-once).
let hasStarted = false;

export function ServiceWorkerRegistrar() {
  useEffect(() => {
    if (hasStarted) return;
    hasStarted = true;

    const mode = resolveServiceWorkerMode({
      nodeEnv: process.env.NODE_ENV,
      killFlag: process.env.NEXT_PUBLIC_PWA_SW,
      hasServiceWorker: "serviceWorker" in navigator,
      isSecureContext: window.isSecureContext,
    });
    if (mode === "skip") return;

    runAfterLoad(document, window, () => {
      void applyServiceWorkerMode(mode, {
        getRegistrations: getServiceWorkerRegistrations,
        register: registerServiceWorker,
        warn: warnServiceWorkerFailure,
      });
    });
  }, []);

  return null;
}
