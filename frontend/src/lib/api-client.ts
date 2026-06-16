export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * BE API 호출용 fetch 래퍼.
 * Clerk JWT를 token 옵션으로 전달하면 Authorization 헤더를 자동 첨부한다.
 */
export async function apiClient<T = unknown>(
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
