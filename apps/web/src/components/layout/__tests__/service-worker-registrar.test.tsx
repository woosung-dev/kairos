// ServiceWorkerRegistrar — 페이지 로드당 1회 · load 이후 · 모드별 호출 (T-PWA-09·14 의 단위 부분)
// 실제 브라우저 등록·제어는 e2e/tests/pwa.spec.ts (T-PWA-08·09) 가 본다.
import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const register = vi.fn(async () => undefined);
const unregister = vi.fn(async () => true);
const getRegistrations = vi.fn(async () => [{ unregister }]);

function installServiceWorker() {
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: { register, getRegistrations },
  });
  Object.defineProperty(window, "isSecureContext", { configurable: true, value: true });
}

async function loadRegistrar() {
  // 모듈 수준 init-once 가드를 테스트마다 새로 시작한다.
  vi.resetModules();
  const mod = await import("../service-worker-registrar");
  return mod.ServiceWorkerRegistrar;
}

async function flush() {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

beforeEach(() => {
  register.mockClear();
  unregister.mockClear();
  getRegistrations.mockClear();
  installServiceWorker();
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("ServiceWorkerRegistrar", () => {
  it("prod — register 정확히 1회 (재마운트·두 번째 인스턴스에도 추가 0)", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_PWA_SW", "");
    const ServiceWorkerRegistrar = await loadRegistrar();

    const first = render(<ServiceWorkerRegistrar />);
    first.unmount();
    render(<ServiceWorkerRegistrar />);
    render(<ServiceWorkerRegistrar />);
    await flush();

    expect(register).toHaveBeenCalledTimes(1);
    const [scriptUrl, options] = register.mock.calls[0] as unknown as [URL, RegistrationOptions];
    expect(String(scriptUrl)).toContain("sw");
    expect(options).toEqual({ scope: "/", updateViaCache: "none" });
    expect(getRegistrations).not.toHaveBeenCalled();
  });

  it("prod — kill-switch(off) 면 등록 대신 기존 등록 해제", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_PWA_SW", "off");
    const ServiceWorkerRegistrar = await loadRegistrar();

    render(<ServiceWorkerRegistrar />);
    await flush();

    expect(register).not.toHaveBeenCalled();
    expect(unregister).toHaveBeenCalledTimes(1);
  });

  it("dev — 등록 대신 기존 등록 해제", async () => {
    vi.stubEnv("NODE_ENV", "development");
    const ServiceWorkerRegistrar = await loadRegistrar();

    render(<ServiceWorkerRegistrar />);
    await flush();

    expect(register).not.toHaveBeenCalled();
    expect(unregister).toHaveBeenCalledTimes(1);
  });

  it("비보안 컨텍스트 — 아무 호출도 없다", async () => {
    vi.stubEnv("NODE_ENV", "production");
    Object.defineProperty(window, "isSecureContext", { configurable: true, value: false });
    const ServiceWorkerRegistrar = await loadRegistrar();

    render(<ServiceWorkerRegistrar />);
    await flush();

    expect(register).not.toHaveBeenCalled();
    expect(getRegistrations).not.toHaveBeenCalled();
  });

  it("load 전이면 load 이벤트 뒤에 등록한다", async () => {
    vi.stubEnv("NODE_ENV", "production");
    const readyState = vi.spyOn(document, "readyState", "get").mockReturnValue("interactive");
    const ServiceWorkerRegistrar = await loadRegistrar();

    render(<ServiceWorkerRegistrar />);
    await flush();
    expect(register).not.toHaveBeenCalled();

    window.dispatchEvent(new Event("load"));
    await flush();
    expect(register).toHaveBeenCalledTimes(1);
    readyState.mockRestore();
  });
});
