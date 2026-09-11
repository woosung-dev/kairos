// ADR-026 D5 — Picker 브라우저 토큰이 영속 저장소로 새지 않는지 고정한다.
//
// 이 테스트가 죽으면 2-토큰 모델이 깨진 것이다. 브라우저 access token 은 메모리
// 변수에만 있어야 하며 localStorage / sessionStorage / cookie 어디에도 남으면 안 된다.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useGooglePicker } from "../use-google-picker";

const ACCESS_TOKEN = "ya29-browser-access-token";

interface TokenClientConfig {
  callback: (response: { access_token?: string }) => void;
}

let localSetSpy: ReturnType<typeof vi.spyOn>;
let sessionSetSpy: ReturnType<typeof vi.spyOn>;
let cookieWrites: string[];

function installGoogleGlobals(pickedDocs: { id: string; name: string }[]) {
  let capturedCallback: ((data: unknown) => void) | null = null;

  const builder = {
    addView: () => builder,
    setOAuthToken: () => builder,
    setDeveloperKey: () => builder,
    setTitle: () => builder,
    setCallback: (callback: (data: unknown) => void) => {
      capturedCallback = callback;
      return builder;
    },
    build: () => ({
      setVisible: () => {
        capturedCallback?.({ action: "picked", docs: pickedDocs });
      },
    }),
  };

  const docsView = {
    setIncludeFolders: () => docsView,
    setSelectFolderEnabled: () => docsView,
    setMimeTypes: () => docsView,
  };

  window.google = {
    accounts: {
      oauth2: {
        initTokenClient: (config: TokenClientConfig) => ({
          requestAccessToken: () => config.callback({ access_token: ACCESS_TOKEN }),
        }),
      },
    },
    picker: {
      PickerBuilder: function PickerBuilder() {
        return builder;
      } as unknown as new () => typeof builder,
      DocsView: function DocsView() {
        return docsView;
      } as unknown as new () => typeof docsView,
      ViewId: { DOCUMENTS: "documents" },
      Action: { PICKED: "picked", CANCEL: "cancel" },
    },
  } as unknown as Window["google"];

  window.gapi = { load: (_name: string, callback: () => void) => callback() };
}

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID", "test-client-id.apps.googleusercontent.com");
  vi.stubEnv("NEXT_PUBLIC_GOOGLE_PICKER_API_KEY", "test-picker-api-key");

  // 스크립트 태그는 jsdom 에서 네트워크를 타지 않는다 — 삽입 즉시 onload 를 부른다.
  vi.spyOn(document.head, "appendChild").mockImplementation(((node: Node) => {
    const element = node as HTMLScriptElement;
    queueMicrotask(() => element.onload?.(new Event("load")));
    return node;
  }) as typeof document.head.appendChild);

  localSetSpy = vi.spyOn(Storage.prototype, "setItem");
  sessionSetSpy = vi.spyOn(window.sessionStorage.__proto__, "setItem");
  cookieWrites = [];
  Object.defineProperty(document, "cookie", {
    configurable: true,
    get: () => "",
    set: (value: string) => {
      cookieWrites.push(value);
    },
  });
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
  delete window.google;
  delete window.gapi;
});

describe("useGooglePicker", () => {
  it("선택된 Google Docs 를 돌려주면서 토큰을 어떤 저장소에도 쓰지 않는다", async () => {
    installGoogleGlobals([{ id: "file-a", name: "전략 문서" }]);
    const { result } = renderHook(() => useGooglePicker());

    let picked: { id: string; name: string }[] = [];
    await act(async () => {
      picked = await result.current.open();
    });

    expect(picked).toEqual([{ id: "file-a", name: "전략 문서" }]);

    // ★핵심 단언 — 토큰이 영속 저장소에 닿지 않았다.
    const persistedValues = [
      ...localSetSpy.mock.calls.flat(),
      ...sessionSetSpy.mock.calls.flat(),
      ...cookieWrites,
    ].join("|");
    expect(persistedValues).not.toContain(ACCESS_TOKEN);
    expect(cookieWrites).toEqual([]);
  });

  it("취소하면 빈 배열을 돌려준다 — 서버로 아무것도 보내지 않는다", async () => {
    installGoogleGlobals([]);
    const google = window.google!;
    const originalBuilder = google.picker.PickerBuilder;
    google.picker.PickerBuilder = function PickerBuilder() {
      const builder = {
        addView: () => builder,
        setOAuthToken: () => builder,
        setDeveloperKey: () => builder,
        setTitle: () => builder,
        setCallback: (callback: (data: unknown) => void) => {
          queueMicrotask(() => callback({ action: "cancel" }));
          return builder;
        },
        build: () => ({ setVisible: () => undefined }),
      };
      return builder;
    } as unknown as typeof originalBuilder;

    const { result } = renderHook(() => useGooglePicker());
    let picked: { id: string; name: string }[] = [{ id: "stale", name: "stale" }];
    await act(async () => {
      picked = await result.current.open();
    });

    expect(picked).toEqual([]);
  });

  it("토큰 획득에 실패하면 빈 배열 + 에러 — 서버 상태 변화는 0이다", async () => {
    installGoogleGlobals([]);
    window.google!.accounts.oauth2.initTokenClient = (
      config: TokenClientConfig,
    ) => ({
      // access_token 없이 콜백 → 획득 실패 경로
      requestAccessToken: () => config.callback({}),
    });

    const { result } = renderHook(() => useGooglePicker());
    let picked: { id: string; name: string }[] = [{ id: "stale", name: "stale" }];
    await act(async () => {
      picked = await result.current.open();
    });

    expect(picked).toEqual([]);
    expect(result.current.error).not.toBeNull();
  });
});
