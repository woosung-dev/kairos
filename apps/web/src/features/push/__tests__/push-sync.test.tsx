// T-PWA-51 앱 로드 동기화 — 표식 일치 → PUT 정확히 1회 (재렌더·라우트 이동(셸 재마운트)에도 추가 0)
// + 계정 전환 시 재동기화 (EVAL-P2-1 D3) · API-001 공개키 전달 (D2) · API-001 실패 시 키 없이 동기화
// + 로그아웃 정리가 가드를 비운다 (같은 계정 재로그인 시 재동기화, GATE-PR2 경미 6).
// 계정당 1회 가드(lastSyncedMeId)는 모듈 상태라 이 파일의 테스트는 순서대로 이어진다 —
// 테스트마다 아직 동기화하지 않은 계정 id 를 쓴다 (vitest 는 파일마다 모듈을 새로 읽는다).
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ApiClient } from "@/lib/api-client";
import { PushSync } from "../components/push-sync";
import { usePushLogoutCleanup } from "../hooks";
import { PUSH_OWNER_MARKER_KEY } from "../marker";
import { base64UrlToUint8Array } from "../utils";

const ME = "11111111-1111-4111-8111-111111111111";
const OTHER_USER = "22222222-2222-4222-8222-222222222222";
const THIRD_USER = "55555555-5555-4555-8555-555555555555";
const SUBSCRIPTION_ID = "33333333-3333-4333-8333-333333333333";
const VAPID_PUBLIC_KEY =
  "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U";
const STALE_KEY_BYTES = new Uint8Array(65).fill(7);

type FetchFn = (path: string, init?: RequestInit) => Promise<unknown>;

const { fetchMock, meState, configState, deleteState } = vi.hoisted(() => ({
  fetchMock: vi.fn<FetchFn>(),
  meState: { current: undefined as { id: string } | undefined },
  // API-001 응답을 테스트가 정한다 — pending 이면 resolve 를 쥐고 있다
  configState: { respond: (): Promise<unknown> => Promise.resolve(undefined) },
  deleteState: { shouldFail: false },
}));

const api: ApiClient = {
  fetch: <T,>(path: string, init?: RequestInit) => fetchMock(path, init) as Promise<T>,
  fetchRaw: () => Promise.reject(new Error("unused")),
  getToken: () => Promise.resolve("token"),
};

vi.mock("@/lib/use-api-client", () => ({ useApiClient: () => api }));
vi.mock("@/features/auth/hooks", () => ({ useMe: () => ({ data: meState.current }) }));
vi.mock("sonner", () => ({ toast: Object.assign(vi.fn(), { error: vi.fn() }) }));

fetchMock.mockImplementation((path, init) => {
  if (path === "/users/me/push-config") return configState.respond();
  if (init?.method === "PUT") return Promise.resolve({ id: SUBSCRIPTION_ID });
  if (init?.method === "DELETE" && deleteState.shouldFail) return Promise.reject(new Error("offline"));
  return Promise.resolve(undefined);
});

function installRegistrationWithSubscription(keyBytes: Uint8Array) {
  const subscription = {
    options: { applicationServerKey: keyBytes.slice().buffer },
    toJSON: () => ({
      endpoint: "https://fcm.googleapis.com/fcm/send/device-token",
      keys: { p256dh: "p256dh-key", auth: "auth-key" },
    }),
    unsubscribe: vi.fn(() => Promise.resolve(true)),
  };
  const registration = {
    pushManager: {
      getSubscription: () => Promise.resolve(subscription),
      subscribe: vi.fn(),
    },
  };
  Object.defineProperty(navigator, "serviceWorker", {
    value: { getRegistration: () => Promise.resolve(registration) },
    configurable: true,
  });
  return subscription;
}

function setMarker(userId: string) {
  localStorage.setItem(PUSH_OWNER_MARKER_KEY, JSON.stringify({ userId, subscriptionId: SUBSCRIPTION_ID }));
}

function createWrapper() {
  const queryClient = new QueryClient();
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

const callsOf = (method: string) =>
  fetchMock.mock.calls.filter(([, init]) => (init?.method ?? "GET") === method);
const syncCalls = () => callsOf("PUT").length + callsOf("DELETE").length;

afterEach(() => {
  Reflect.deleteProperty(navigator, "serviceWorker");
  localStorage.clear();
  fetchMock.mockClear();
  deleteState.shouldFail = false;
});

describe("T-PWA-51 usePushAppLoadSync", () => {
  it("me·API-001 이 다 온 뒤 PUT 1회 — 재렌더·재마운트에도 추가 0", async () => {
    const subscription = installRegistrationWithSubscription(base64UrlToUint8Array(VAPID_PUBLIC_KEY));
    setMarker(ME);
    let resolveConfig: (value: unknown) => void = () => {};
    configState.respond = () => new Promise((resolve) => (resolveConfig = resolve));
    const Wrapper = createWrapper();

    // me 로딩 중 — 아직 동기화하지 않는다
    const view = render(<PushSync />, { wrapper: Wrapper });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(syncCalls()).toBe(0);

    // me 는 왔지만 API-001 대기 중 — 키 불일치 판정에 공개키가 필요하다
    meState.current = { id: ME };
    view.rerender(<PushSync />);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(syncCalls()).toBe(0);

    resolveConfig({ isEnabled: true, vapidPublicKey: VAPID_PUBLIC_KEY });
    await waitFor(() => expect(callsOf("PUT")).toHaveLength(1));
    expect(callsOf("PUT")[0][0]).toBe("/users/me/push-subscriptions");

    view.rerender(<PushSync />);
    view.unmount();
    render(<PushSync />, { wrapper: Wrapper });
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(callsOf("PUT")).toHaveLength(1);
    expect(callsOf("DELETE")).toHaveLength(0);
    expect(subscription.unsubscribe).not.toHaveBeenCalled();
  });

  it("같은 JS 수명에서 계정이 바뀌면 다시 동기화한다 — API-001 공개키로 옛 키 구독을 정리", async () => {
    const subscription = installRegistrationWithSubscription(STALE_KEY_BYTES);
    setMarker(OTHER_USER);
    configState.respond = () => Promise.resolve({ isEnabled: true, vapidPublicKey: VAPID_PUBLIC_KEY });

    // 로그아웃 → 다른 계정 로그인 (soft navigation — 모듈 상태가 남아 있다)
    meState.current = { id: OTHER_USER };
    render(<PushSync />, { wrapper: createWrapper() });

    await waitFor(() => expect(subscription.unsubscribe).toHaveBeenCalledTimes(1));
    expect(callsOf("DELETE").map(([path]) => path)).toEqual([
      `/users/me/push-subscriptions/${SUBSCRIPTION_ID}`,
    ]);
    expect(callsOf("PUT")).toHaveLength(0);
    await waitFor(() => expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull());
  });

  it("API-001 이 실패해도 동기화한다 — 키 비교만 건너뛴다 (옛 키 구독도 PUT)", async () => {
    const subscription = installRegistrationWithSubscription(STALE_KEY_BYTES);
    setMarker(THIRD_USER);
    configState.respond = () => Promise.reject(new Error("503"));

    meState.current = { id: THIRD_USER };
    render(<PushSync />, { wrapper: createWrapper() });

    await waitFor(() => expect(callsOf("PUT")).toHaveLength(1));
    expect(callsOf("DELETE")).toHaveLength(0);
    expect(subscription.unsubscribe).not.toHaveBeenCalled();
  });

  it("로그아웃 정리가 가드를 비운다 — 같은 계정 재로그인 시 다시 동기화 (①·② 둘 다 실패했던 구독을 끊는다)", async () => {
    // 직전 테스트가 THIRD_USER 로 동기화했다 — 같은 계정이면 가드가 막는다
    const subscription = installRegistrationWithSubscription(base64UrlToUint8Array(VAPID_PUBLIC_KEY));
    setMarker(THIRD_USER);
    configState.respond = () => Promise.resolve({ isEnabled: true, vapidPublicKey: VAPID_PUBLIC_KEY });
    meState.current = { id: THIRD_USER };
    const Wrapper = createWrapper();

    const view = render(<PushSync />, { wrapper: Wrapper });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(syncCalls()).toBe(0);

    // 로그아웃 — ① DELETE 실패 ∥ ② unsubscribe 실패 → 표식만 지워지고 구독은 남는다
    deleteState.shouldFail = true;
    subscription.unsubscribe.mockImplementationOnce(() => Promise.reject(new Error("unsubscribe failed")));
    const { result } = renderHook(() => usePushLogoutCleanup(), { wrapper: Wrapper });
    await act(() => result.current());
    expect(callsOf("DELETE")).toHaveLength(1);
    expect(subscription.unsubscribe).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(PUSH_OWNER_MARKER_KEY)).toBeNull();

    // 같은 계정으로 다시 로그인 — `(app)` 셸이 다시 마운트된다. 표식 없음 → 서버 호출 없이 unsubscribe
    view.unmount();
    render(<PushSync />, { wrapper: Wrapper });
    await waitFor(() => expect(subscription.unsubscribe).toHaveBeenCalledTimes(2));
    expect(callsOf("PUT")).toHaveLength(0);
  });
});
