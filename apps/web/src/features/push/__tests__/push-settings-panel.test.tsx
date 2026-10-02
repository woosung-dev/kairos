// T-PWA-56 iOS 안내 표시 (렌더) + SCR-002 상태·토글 — 권한 요청은 토글 클릭에서만 (pwa.md §5.5 · §5.6)
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ApiClient } from "@/lib/api-client";
import { PushSettingsPanel } from "../components/push-settings-panel";
import { PUSH_OWNER_MARKER_KEY } from "../marker";

const ME = "11111111-1111-4111-8111-111111111111";
const SUBSCRIPTION_ID = "33333333-3333-4333-8333-333333333333";
const VAPID_PUBLIC_KEY =
  "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U";
const IPHONE_UA =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1";
const DESKTOP_UA =
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36";

const { fetchMock, toastError } = vi.hoisted(() => ({
  fetchMock: vi.fn<(path: string, init?: RequestInit) => Promise<unknown>>(() =>
    Promise.resolve(undefined),
  ),
  toastError: vi.fn(),
}));

const api: ApiClient = {
  fetch: <T,>(path: string, init?: RequestInit) => fetchMock(path, init) as Promise<T>,
  fetchRaw: () => Promise.reject(new Error("unused")),
  getToken: () => Promise.resolve("token"),
};

vi.mock("@/lib/use-api-client", () => ({ useApiClient: () => api }));
vi.mock("@/features/auth/hooks", () => ({ useMe: () => ({ data: { id: ME } }) }));
vi.mock("sonner", () => ({ toast: Object.assign(vi.fn(), { error: toastError }) }));

const requestPermission = vi.fn(() => Promise.resolve<NotificationPermission>("granted"));

function stubNotification(permission: NotificationPermission) {
  vi.stubGlobal(
    "Notification",
    class {
      static permission = permission;
      static requestPermission = requestPermission;
    },
  );
}

function setUserAgent(userAgent: string, platform: string, maxTouchPoints: number) {
  Object.defineProperty(navigator, "userAgent", { value: userAgent, configurable: true });
  Object.defineProperty(navigator, "platform", { value: platform, configurable: true });
  Object.defineProperty(navigator, "maxTouchPoints", { value: maxTouchPoints, configurable: true });
}

function installRegistration(hasRegistration: boolean) {
  let current: { toJSON(): PushSubscriptionJSON } | null = null;
  const subscribe = vi.fn(() => {
    current = {
      toJSON: () => ({
        endpoint: "https://fcm.googleapis.com/fcm/send/device-token",
        keys: { p256dh: "p256dh-key", auth: "auth-key" },
      }),
    };
    return Promise.resolve({ ...current, options: { applicationServerKey: null }, unsubscribe: vi.fn() });
  });
  const registration = {
    pushManager: { getSubscription: () => Promise.resolve(current), subscribe },
  };
  Object.defineProperty(navigator, "serviceWorker", {
    value: {
      getRegistration: () => Promise.resolve(hasRegistration ? registration : undefined),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    },
    configurable: true,
  });
  return { subscribe };
}

function status() {
  return screen.getByTestId("push-status");
}

beforeEach(() => {
  setUserAgent(DESKTOP_UA, "Linux x86_64", 0);
  vi.stubGlobal("PushManager", class {});
  Object.defineProperty(window, "isSecureContext", { value: true, configurable: true });
  stubNotification("default");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  for (const key of ["serviceWorker", "userAgent", "platform", "maxTouchPoints"]) {
    Reflect.deleteProperty(navigator, key);
  }
  Reflect.deleteProperty(window, "isSecureContext");
  localStorage.clear();
});

describe("T-PWA-56 iOS 설치 안내 렌더", () => {
  it("iPhone UA + 비standalone → ios-install-hint 표시 · 토글 disabled", async () => {
    setUserAgent(IPHONE_UA, "iPhone", 5);
    installRegistration(true);
    render(<PushSettingsPanel vapidPublicKey={VAPID_PUBLIC_KEY} />);
    expect(await screen.findByTestId("ios-install-hint")).toBeInTheDocument();
    expect(status()).toHaveAttribute("data-state", "ios-install");
    expect(screen.getByTestId("push-toggle")).toBeDisabled();
  });

  it("데스크톱 → 안내 미표시", async () => {
    installRegistration(true);
    render(<PushSettingsPanel vapidPublicKey={VAPID_PUBLIC_KEY} />);
    await waitFor(() => expect(status()).toHaveAttribute("data-state", "off"));
    expect(screen.queryByTestId("ios-install-hint")).not.toBeInTheDocument();
  });
});

describe("SCR-002 상태 · 토글", () => {
  it("SW 등록 없음 → '사용 불가' · 토글 disabled · 권한 요청 0", async () => {
    installRegistration(false);
    render(<PushSettingsPanel vapidPublicKey={VAPID_PUBLIC_KEY} />);
    await waitFor(() => expect(status()).toHaveAttribute("data-state", "unavailable"));
    expect(status()).toHaveTextContent("이 브라우저·환경에서는 알림을 켤 수 없어요");
    expect(screen.getByTestId("push-toggle")).toBeDisabled();
    expect(requestPermission).not.toHaveBeenCalled();
  });

  it("권한 denied → 안내 문구 · 토글 disabled", async () => {
    stubNotification("denied");
    installRegistration(true);
    render(<PushSettingsPanel vapidPublicKey={VAPID_PUBLIC_KEY} />);
    await waitFor(() => expect(status()).toHaveAttribute("data-state", "denied"));
    expect(status()).toHaveTextContent("브라우저 설정에서 이 사이트의 알림을 허용해 주세요");
    expect(screen.getByTestId("push-toggle")).toBeDisabled();
  });

  it("마운트 시 권한 요청 0 → 토글 클릭 때만 요청 · PUT · 표식 저장 · 켜짐", async () => {
    fetchMock.mockResolvedValue({ id: SUBSCRIPTION_ID });
    const { subscribe } = installRegistration(true);
    render(<PushSettingsPanel vapidPublicKey={VAPID_PUBLIC_KEY} />);
    await waitFor(() => expect(status()).toHaveAttribute("data-state", "off"));
    expect(requestPermission).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId("push-toggle"));

    await waitFor(() => expect(status()).toHaveAttribute("data-state", "on"));
    expect(requestPermission).toHaveBeenCalledTimes(1);
    expect(subscribe).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("push-toggle")).toHaveAttribute("aria-checked", "true");
    expect(JSON.parse(localStorage.getItem(PUSH_OWNER_MARKER_KEY) ?? "null")).toEqual({
      userId: ME,
      subscriptionId: SUBSCRIPTION_ID,
    });
  });

  it("켜기 실패 → 토스트 · 토글은 꺼짐 그대로", async () => {
    fetchMock.mockRejectedValue(new Error("500"));
    installRegistration(true);
    render(<PushSettingsPanel vapidPublicKey={VAPID_PUBLIC_KEY} />);
    await waitFor(() => expect(status()).toHaveAttribute("data-state", "off"));

    fireEvent.click(screen.getByTestId("push-toggle"));

    await waitFor(() => expect(toastError).toHaveBeenCalledTimes(1));
    expect(status()).toHaveAttribute("data-state", "off");
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();
  });
});
