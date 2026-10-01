// T-PWA-14 — SW 등록 모드 결정 + 실행 (docs/requirements/pwa.md §4.4·§4.5)
import { describe, expect, it, vi } from "vitest";
import {
  applyServiceWorkerMode,
  resolveServiceWorkerMode,
  runAfterLoad,
  type ServiceWorkerEnvironment,
} from "../registration";

const PROD: ServiceWorkerEnvironment = {
  nodeEnv: "production",
  killFlag: undefined,
  hasServiceWorker: true,
  isSecureContext: true,
};

describe("resolveServiceWorkerMode", () => {
  it("prod 기본 → register", () => {
    expect(resolveServiceWorkerMode(PROD)).toBe("register");
    expect(resolveServiceWorkerMode({ ...PROD, killFlag: "" })).toBe("register");
  });

  it("prod + NEXT_PUBLIC_PWA_SW=off → unregister (kill-switch)", () => {
    expect(resolveServiceWorkerMode({ ...PROD, killFlag: "off" })).toBe("unregister");
  });

  it("dev·test 빌드 → unregister", () => {
    expect(resolveServiceWorkerMode({ ...PROD, nodeEnv: "development" })).toBe("unregister");
    expect(resolveServiceWorkerMode({ ...PROD, nodeEnv: "test" })).toBe("unregister");
    expect(resolveServiceWorkerMode({ ...PROD, nodeEnv: undefined })).toBe("unregister");
  });

  it("serviceWorker 미지원 또는 비보안 컨텍스트 → skip (dev·kill 보다 우선)", () => {
    expect(resolveServiceWorkerMode({ ...PROD, hasServiceWorker: false })).toBe("skip");
    expect(resolveServiceWorkerMode({ ...PROD, isSecureContext: false })).toBe("skip");
    expect(
      resolveServiceWorkerMode({ ...PROD, nodeEnv: "development", isSecureContext: false })
    ).toBe("skip");
  });
});

function makeDeps() {
  const unregisterA = vi.fn(async () => true);
  const unregisterB = vi.fn(async () => true);
  return {
    unregisterA,
    unregisterB,
    deps: {
      getRegistrations: vi.fn(async () => [{ unregister: unregisterA }, { unregister: unregisterB }]),
      register: vi.fn(async () => undefined),
      warn: vi.fn(),
    },
  };
}

describe("applyServiceWorkerMode", () => {
  it("skip → register·getRegistrations 호출 0", async () => {
    const { deps } = makeDeps();
    await applyServiceWorkerMode("skip", deps);
    expect(deps.register).not.toHaveBeenCalled();
    expect(deps.getRegistrations).not.toHaveBeenCalled();
  });

  it("unregister → 등록 전부 해제, register 0", async () => {
    const { deps, unregisterA, unregisterB } = makeDeps();
    await applyServiceWorkerMode("unregister", deps);
    expect(unregisterA).toHaveBeenCalledTimes(1);
    expect(unregisterB).toHaveBeenCalledTimes(1);
    expect(deps.register).not.toHaveBeenCalled();
  });

  it("register → register 1회, 결과가 undefined 여도 실패하지 않는다 (Playwright block, C-26)", async () => {
    const { deps } = makeDeps();
    await applyServiceWorkerMode("register", deps);
    expect(deps.register).toHaveBeenCalledTimes(1);
    expect(deps.getRegistrations).not.toHaveBeenCalled();
    expect(deps.warn).not.toHaveBeenCalled();
  });

  it("실패는 warn 1줄로 끝나고 throw 하지 않는다", async () => {
    const { deps } = makeDeps();
    const error = new Error("SecurityError");
    deps.register.mockRejectedValueOnce(error);
    await expect(applyServiceWorkerMode("register", deps)).resolves.toBeUndefined();
    expect(deps.warn).toHaveBeenCalledTimes(1);
    expect(deps.warn).toHaveBeenCalledWith(expect.stringContaining("register"), error);
  });
});

describe("runAfterLoad", () => {
  it("이미 complete 면 즉시 실행, 리스너 0", () => {
    const task = vi.fn();
    const addEventListener = vi.fn();
    runAfterLoad({ readyState: "complete" }, { addEventListener }, task);
    expect(task).toHaveBeenCalledTimes(1);
    expect(addEventListener).not.toHaveBeenCalled();
  });

  it("아직이면 load 1회 리스너 뒤 실행", () => {
    const task = vi.fn();
    const addEventListener = vi.fn();
    runAfterLoad({ readyState: "interactive" }, { addEventListener }, task);
    expect(task).not.toHaveBeenCalled();
    expect(addEventListener).toHaveBeenCalledWith("load", task, { once: true });
  });
});
