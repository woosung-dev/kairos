"use client";

// ADR-026 D5 — Google Picker 2-토큰 모델.
//
// 서버 토큰(refresh token)과 브라우저 토큰(access token)은 **같은 client_id** 를
// 쓰되 완전히 분리된다. `drive.file` 은 앱+파일 단위 grant 라, 브라우저가 같은
// client_id 로 Picker 를 열고 사용자가 파일을 고르면 그 grant 가 해당 OAuth
// client 에 기록되고, 서버가 자기 refresh token 으로 그 파일을 읽는다.
// 따라서 client_id 동일성은 이 설계의 필수 불변식이다.
//
// ★강제 규칙 (위반 시 설계가 무너진다)
//   - 브라우저 access token 을 localStorage / sessionStorage / cookie /
//     Zustand persist 에 저장하지 않는다. **메모리 변수만** 쓴다.
//   - 브라우저 access token 을 Kairos 백엔드로 보내지 않는다. import 요청 본문에는
//     Picker 가 돌려준 fileId[] 와 최소 메타데이터만 넣는다.
//   - 토큰 획득에 실패하면 서버 상태 변화는 0 이다 — Picker 를 못 열 뿐,
//     connection·sync run·문서의 부분 상태를 만들지 않는다.

import { useCallback, useEffect, useRef, useState } from "react";

const GIS_SRC = "https://accounts.google.com/gsi/client";
const GAPI_SRC = "https://apis.google.com/js/api.js";
const DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file";
const GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document";

// ★모듈 스코프가 아니라 호출 시점에 읽는다. Next 는 `process.env.NEXT_PUBLIC_*`
//   전체 멤버 표현식을 위치와 무관하게 정적 치환하므로 번들 동작은 같고,
//   테스트가 값을 주입할 수 있게 된다.
function readPickerConfig(): { clientId: string; apiKey: string } {
  return {
    clientId: process.env.NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID ?? "",
    apiKey: process.env.NEXT_PUBLIC_GOOGLE_PICKER_API_KEY ?? "",
  };
}

export interface PickedDriveFile {
  id: string;
  name: string;
}

interface TokenResponse {
  access_token?: string;
  error?: string;
}

interface TokenClient {
  requestAccessToken: (overrides?: { prompt?: string }) => void;
}

interface PickerBuilder {
  addView: (view: unknown) => PickerBuilder;
  setOAuthToken: (token: string) => PickerBuilder;
  setDeveloperKey: (key: string) => PickerBuilder;
  setCallback: (callback: (data: PickerCallbackData) => void) => PickerBuilder;
  setTitle: (title: string) => PickerBuilder;
  build: () => { setVisible: (visible: boolean) => void };
}

interface PickerCallbackData {
  action: string;
  docs?: { id: string; name: string }[];
}

interface DocsView {
  setIncludeFolders: (include: boolean) => DocsView;
  setMimeTypes: (mimeTypes: string) => DocsView;
  setSelectFolderEnabled: (enabled: boolean) => DocsView;
}

interface GoogleGlobal {
  accounts: {
    oauth2: {
      initTokenClient: (config: {
        client_id: string;
        scope: string;
        callback: (response: TokenResponse) => void;
        error_callback?: (error: { type?: string }) => void;
      }) => TokenClient;
    };
  };
  picker: {
    PickerBuilder: new () => PickerBuilder;
    DocsView: new (viewId?: unknown) => DocsView;
    ViewId: { DOCUMENTS: unknown };
    Action: { PICKED: string; CANCEL: string };
  };
}

interface GapiGlobal {
  load: (name: string, callback: () => void) => void;
}

declare global {
  interface Window {
    google?: GoogleGlobal;
    gapi?: GapiGlobal;
  }
}

/** 같은 스크립트를 두 번 넣지 않도록 모듈 스코프에 in-flight 를 공유한다. */
const scriptPromises = new Map<string, Promise<void>>();

function loadScript(src: string): Promise<void> {
  const existing = scriptPromises.get(src);
  if (existing) return existing;

  const promise = new Promise<void>((resolve, reject) => {
    const element = document.createElement("script");
    element.src = src;
    element.async = true;
    element.onload = () => resolve();
    element.onerror = () => {
      // 실패한 promise 를 캐시에 남기면 영구히 재시도가 막힌다.
      scriptPromises.delete(src);
      reject(new Error(`스크립트를 불러오지 못했습니다: ${src}`));
    };
    document.head.appendChild(element);
  });
  scriptPromises.set(src, promise);
  return promise;
}

function loadPickerApi(): Promise<void> {
  return loadScript(GAPI_SRC).then(
    () =>
      new Promise<void>((resolve, reject) => {
        const gapi = window.gapi;
        if (!gapi) {
          reject(new Error("Google API 로더를 사용할 수 없습니다"));
          return;
        }
        gapi.load("picker", () => resolve());
      }),
  );
}

export interface UseGooglePickerResult {
  /** Picker 를 열고 선택된 Google Docs 를 돌려준다. 취소하면 빈 배열. */
  open: () => Promise<PickedDriveFile[]>;
  /** 빌드에 client_id / API key 가 주입됐는가. */
  isConfigured: boolean;
  isOpening: boolean;
  error: string | null;
}

export function useGooglePicker(): UseGooglePickerResult {
  // ★메모리 전용. 어떤 영속 저장소에도 쓰지 않는다 (ADR-026 D5).
  const accessTokenRef = useRef<string | null>(null);
  const tokenClientRef = useRef<TokenClient | null>(null);
  const [isOpening, setIsOpening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { clientId, apiKey } = readPickerConfig();
  const isConfigured = clientId !== "" && apiKey !== "";

  useEffect(() => {
    // 언마운트 시 토큰을 지운다 — 페이지를 떠난 뒤 메모리에 남길 이유가 없다.
    return () => {
      accessTokenRef.current = null;
    };
  }, []);

  const requestAccessToken = useCallback(async (): Promise<string> => {
    if (accessTokenRef.current) return accessTokenRef.current;

    await loadScript(GIS_SRC);
    const google = window.google;
    if (!google) throw new Error("Google Identity 스크립트를 사용할 수 없습니다");

    return new Promise<string>((resolve, reject) => {
      tokenClientRef.current = google.accounts.oauth2.initTokenClient({
        client_id: clientId,
        scope: DRIVE_FILE_SCOPE,
        callback: (response) => {
          if (!response.access_token) {
            reject(new Error("Google 액세스 토큰을 받지 못했습니다"));
            return;
          }
          accessTokenRef.current = response.access_token;
          resolve(response.access_token);
        },
        error_callback: () => {
          reject(new Error("Google 인증 창이 닫혔습니다"));
        },
      });
      tokenClientRef.current.requestAccessToken();
    });
  }, [clientId]);

  const open = useCallback(async (): Promise<PickedDriveFile[]> => {
    if (!isConfigured) {
      setError("Google Picker 설정이 빌드에 주입되지 않았습니다");
      return [];
    }
    setError(null);
    setIsOpening(true);
    try {
      // 토큰 실패 시 여기서 끝난다 — 서버로는 아무것도 보내지 않았다.
      const accessToken = await requestAccessToken();
      await loadPickerApi();
      const google = window.google;
      if (!google) throw new Error("Google Picker 를 사용할 수 없습니다");

      return await new Promise<PickedDriveFile[]>((resolve) => {
        // v0 는 Google Docs 만 지원한다 (ADR-026 D4). 폴더 선택은 열지 않는다 —
        // 열어두면 UI 는 고를 수 있는데 BE 가 전부 failed 로 돌려준다.
        const view = new google.picker.DocsView(google.picker.ViewId.DOCUMENTS)
          .setIncludeFolders(false)
          .setSelectFolderEnabled(false)
          .setMimeTypes(GOOGLE_DOC_MIME_TYPE);

        new google.picker.PickerBuilder()
          .addView(view)
          .setOAuthToken(accessToken)
          .setDeveloperKey(apiKey)
          .setTitle("팀 지식으로 가져올 Google Docs 선택")
          .setCallback((data) => {
            if (data.action === google.picker.Action.PICKED) {
              resolve(
                (data.docs ?? []).map((doc) => ({ id: doc.id, name: doc.name })),
              );
            } else if (data.action === google.picker.Action.CANCEL) {
              resolve([]);
            }
          })
          .build()
          .setVisible(true);
      });
    } catch (caught) {
      // 토큰 만료·취소 뒤 재시도가 죽은 토큰을 재사용하지 않도록 비운다.
      accessTokenRef.current = null;
      setError(caught instanceof Error ? caught.message : "Picker 를 열 수 없습니다");
      return [];
    } finally {
      setIsOpening(false);
    }
  }, [apiKey, isConfigured, requestAccessToken]);

  return { open, isConfigured, isOpening, error };
}
