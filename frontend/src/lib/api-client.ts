export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * BE API 호출 코어 — createApiClient 전용 내부 경로.
 * token 옵션은 여기서만 처리한다 (외부 노출 금지 — PR-3 c8 복붙 회귀 봉쇄).
 */
async function coreApiFetch<T = unknown>(
  path: string,
  options?: RequestInit & { token?: string }
): Promise<T> {
  const { token, ...fetchOptions } = options ?? {};

  // Sprint 29 R3 (api-multipart): FormData 본문이면 Content-Type 을 직접 지정하지 않는다.
  // 브라우저가 multipart/form-data + boundary 를 자동 설정하므로, 강제 application/json 은
  // 업로드를 깨뜨린다 → memory/upload 헬퍼가 apiClient 를 우회·중복하던 원인. 이제 apiClient
  // 가 multipart 를 지원해 헬퍼 통합 가능.
  const isFormData =
    typeof FormData !== "undefined" && fetchOptions.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  // fetchOptions.headers가 있으면 병합
  if (fetchOptions.headers) {
    const incoming =
      fetchOptions.headers instanceof Headers
        ? Object.fromEntries(fetchOptions.headers.entries())
        : (fetchOptions.headers as Record<string, string>);
    Object.assign(headers, incoming);
  }

  const res = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...fetchOptions,
    headers,
  });

  if (!res.ok) {
    const error = await res
      .json()
      .catch(() => ({ detail: "요청 실패" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  // 204 No Content
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

/**
 * 공개(무토큰) 엔드포인트용 fetch 래퍼 (JSON/FormData/204 처리).
 * 인증이 필요한 호출은 ApiClient(createApiClient/useApiClient) seam 을 사용할 것 —
 * token 을 직접 넘기는 저수준 경로는 의도적으로 제거했다 (PR-3 c8).
 */
export async function apiClient<T = unknown>(
  path: string,
  options?: RequestInit
): Promise<T> {
  return coreApiFetch<T>(path, options);
}

/** 토큰 부재 시 throw — 소비처가 error.message("인증이 필요합니다")를 그대로 렌더한다. */
export class AuthRequiredError extends Error {
  constructor() {
    super("인증이 필요합니다");
    this.name = "AuthRequiredError";
  }
}

/**
 * 인증 토큰이 주입된 API 클라이언트 seam (PR-3 c5).
 * feature api 함수는 token 문자열 대신 이 인터페이스를 받는다.
 */
export interface ApiClient {
  /** apiClient 동작 보존 (JSON/FormData/204 처리) + 토큰 자동 첨부. */
  fetch<T = unknown>(path: string, init?: RequestInit): Promise<T>;
  /** raw Response 반환 — Blob export, SSE 스트림 용. ok 검사는 호출자 책임. */
  fetchRaw(path: string, init?: RequestInit): Promise<Response>;
  /** rag SSE 등 escape hatch. 토큰 null 이면 AuthRequiredError throw. */
  getToken(): Promise<string>;
}

export function createApiClient(
  getToken: () => Promise<string | null>,
): ApiClient {
  const resolveToken = async (): Promise<string> => {
    const token = await getToken();
    if (!token) throw new AuthRequiredError();
    return token;
  };

  return {
    async fetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
      const token = await resolveToken();
      return coreApiFetch<T>(path, { ...init, token });
    },
    async fetchRaw(path: string, init?: RequestInit): Promise<Response> {
      const token = await resolveToken();
      const headers = new Headers(init?.headers);
      headers.set("Authorization", `Bearer ${token}`);
      return fetch(`${API_BASE_URL}/api/v1${path}`, { ...init, headers });
    },
    getToken: resolveToken,
  };
}
