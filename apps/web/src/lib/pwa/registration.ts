// SW 등록 모드 결정 + 실행 순수 로직 (docs/requirements/pwa.md §4.4·§4.5) — registrar 와 vitest 가 같이 쓴다.
//
// | 모드       | 언제                                              | 동작                      |
// |------------|---------------------------------------------------|---------------------------|
// | skip       | serviceWorker 미지원 · 비보안 컨텍스트(운영 http)  | 아무것도 안 함             |
// | unregister | dev 빌드 · `NEXT_PUBLIC_PWA_SW=off` (kill-switch)  | 이 origin 의 등록 전부 해제 |
// | register   | prod 기본                                         | sw.js 등록 (scope `/`)     |
//
// ★dev 에서 해제하는 이유: 같은 origin 에서 한 번이라도 prod 빌드를 띄웠다면 그 SW 가
//   dev 내비게이션을 계속 가로챈다. 비용은 getRegistrations() 1회다.

export type ServiceWorkerMode = "skip" | "unregister" | "register";

export interface ServiceWorkerEnvironment {
  readonly nodeEnv: string | undefined;
  readonly killFlag: string | undefined;
  readonly hasServiceWorker: boolean;
  readonly isSecureContext: boolean;
}

export const KILL_SWITCH_VALUE = "off";

export function resolveServiceWorkerMode(env: ServiceWorkerEnvironment): ServiceWorkerMode {
  if (!env.hasServiceWorker || !env.isSecureContext) return "skip";
  if (env.nodeEnv !== "production") return "unregister";
  if (env.killFlag === KILL_SWITCH_VALUE) return "unregister";
  return "register";
}

export interface RegistrationLike {
  unregister(): Promise<boolean>;
}

export interface ServiceWorkerModeDeps {
  readonly getRegistrations: () => Promise<readonly RegistrationLike[]>;
  /**
   * ★결과를 역참조하지 않는다 — Playwright `serviceWorkers: 'block'` 은 register 를
   *   `undefined` 로 resolve 하는 함수로 바꾼다 (pwa.md C-26).
   */
  readonly register: () => Promise<unknown>;
  readonly warn: (message: string, error: unknown) => void;
}

/** 실패는 warn 1줄로 끝낸다 — SW 는 앱 기능과 무관하고, error 는 증거 표준(console.error 0)을 깬다. */
export async function applyServiceWorkerMode(
  mode: ServiceWorkerMode,
  deps: ServiceWorkerModeDeps
): Promise<void> {
  if (mode === "skip") return;
  try {
    if (mode === "unregister") {
      const registrations = await deps.getRegistrations();
      await Promise.all(registrations.map((registration) => registration.unregister()));
      return;
    }
    await deps.register();
  } catch (error) {
    deps.warn(`[pwa] service worker ${mode} 실패`, error);
  }
}

export interface LoadTarget {
  readonly readyState: DocumentReadyState;
  addEventListener(type: "load", listener: () => void, options: { once: true }): void;
}

/**
 * `load` 이후에 실행한다 — hydration·LCP 와 네트워크·CPU 를 다투지 않게 (pwa.md §4.4).
 * 리스너를 cleanup 에서 지우지 않는다: root layout 은 내리지 않고, dev StrictMode 의
 * effect 재실행이 init-once 가드와 만나면 지운 리스너가 다시 붙지 않는다.
 */
export function runAfterLoad(
  documentTarget: Pick<LoadTarget, "readyState">,
  windowTarget: Pick<LoadTarget, "addEventListener">,
  task: () => void
): void {
  if (documentTarget.readyState === "complete") {
    task();
    return;
  }
  windowTarget.addEventListener("load", task, { once: true });
}
