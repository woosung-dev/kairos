export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** FastAPI RequestValidationError 의 detail 항목 ({ loc, msg, type, ctx }) */
interface ValidationIssue {
  loc?: unknown;
  type?: unknown;
  ctx?: unknown;
}

function isValidationIssue(value: unknown): value is ValidationIssue {
  return typeof value === "object" && value !== null && "loc" in value;
}

/** loc 의 마지막 문자열 요소 = 필드명 ("body"/"query"/"path" 같은 위치 접두어는 건너뛴다). */
function fieldOf(issue: ValidationIssue): string | null {
  if (!Array.isArray(issue.loc)) return null;
  const names = issue.loc.filter(
    (part): part is string =>
      typeof part === "string" && !["body", "query", "path", "header"].includes(part),
  );
  return names.at(-1) ?? null;
}

function limitOf(issue: ValidationIssue, key: "min_length" | "max_length"): number | null {
  if (typeof issue.ctx !== "object" || issue.ctx === null) return null;
  const limit = (issue.ctx as Record<string, unknown>)[key];
  return typeof limit === "number" ? limit : null;
}

/** 422 detail 배열 → 한국어 한 줄. 첫 항목만 말한다 (Pydantic msg 는 영어라 노출하지 않는다). */
function formatValidationIssues(issues: ValidationIssue[]): string {
  const first = issues[0];
  const field = first ? fieldOf(first) : null;
  const hint = field ? ` (${field})` : "";
  if (first?.type === "string_too_short") {
    const min = limitOf(first, "min_length");
    return min !== null ? `최소 ${min}자 이상 입력해 주세요${hint}` : `입력값이 너무 짧습니다${hint}`;
  }
  if (first?.type === "string_too_long") {
    const max = limitOf(first, "max_length");
    return max !== null ? `최대 ${max}자까지 입력할 수 있습니다${hint}` : `입력값이 너무 깁니다${hint}`;
  }
  if (first?.type === "missing") return `필수 입력값이 비어 있습니다${hint}`;
  return `입력값을 확인해 주세요${hint}`;
}

/**
 * BE 오류 본문의 detail → 사용자에게 보일 메시지.
 *
 * ★FastAPI 422 는 detail 이 `{loc,msg,type}` 객체 **배열**이다. 그대로 `new Error(detail)` 에
 *   넘기면 "[object Object]" 가 화면에 뜬다 (C-025). 문자열이 아닌 detail 은 여기서 한국어로 바꾼다.
 */
export function formatErrorDetail(detail: unknown, status: number): string {
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail)) {
    const issues = detail.filter(isValidationIssue);
    if (issues.length > 0) return formatValidationIssues(issues);
  }
  if (status === 422) return "입력값을 확인해 주세요";
  return `요청을 처리하지 못했습니다 (HTTP ${status})`;
}

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
    throw new ApiError(formatErrorDetail(error?.detail, res.status), res.status);
  }

  // 본문 없는 2xx — 204 뿐만이 아니다.
  //
  // ★202 Accepted 는 B-7/I-EXT-3 의 장기 작업 규약이고, 그 중 일부는 본문 없이
  //   `Response(status_code=202)` 만 돌려준다. 204 만 특수 처리하면 그런 응답에서
  //   `res.json()` 이 "Unexpected end of JSON input" 으로 reject 되어, 서버는 정상
  //   접수했는데 FE 의 onSuccess(캐시 무효화)가 통째로 건너뛰어진다. 화면은 "버튼이
  //   아무 일도 안 함" 이 되고 콘솔에는 unhandled error 가 남는다.
  //   OpenAPI 는 빈 본문 202 도 스키마가 있는 것처럼 기록하므로 contracts-check 가
  //   원리적으로 못 잡는 자리다 — 여기서 닫는다.
  if (res.status === 204) {
    return undefined as T;
  }

  // 202 Accepted 는 본문이 없을 수 있다 (B-7/I-EXT-3 의 장기 작업 접수 응답 중
  // 일부는 `Response(status_code=202)` 다). 그 경우 res.json() 이 "Unexpected end
  // of JSON input" 으로 reject 되어, 서버는 정상 접수했는데 FE 의 onSuccess 가
  // 통째로 건너뛰어진다.
  //
  // ★허용을 202 로만 좁힌다. 200 의 빈 본문은 프록시 절단이나 핸들러 버그이므로
  //   조용히 undefined 를 돌려주면 원인에서 멀리 떨어진 곳에서 터진다 — 계속
  //   시끄럽게 실패시킨다. content-length 로 판별하지 않는 이유는 청크 전송
  //   응답에 그 헤더가 없기 때문이다.
  if (res.status === 202) {
    const body = await res.text();
    return (body === "" ? undefined : JSON.parse(body)) as T;
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

/** BE 목록 API 의 `pageSize` 상한 (`Query(..., le=100)`, projects/actions router) — 한 번에 받을 수 있는 최대 건수. */
export const API_PAGE_SIZE_MAX = 100;

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
