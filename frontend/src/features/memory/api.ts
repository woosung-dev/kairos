// Sprint 15 Memory 도메인 API — capture / recall / detail
import { apiClient, API_BASE_URL } from "@/lib/api-client";
import type {
  MemoryCreateResponse,
  MemoryDetail,
  MemoryRecallResult,
} from "./types";

// --- Query Key Factory ---

export const memoryKeys = {
  all: ["memory"] as const,
  detail: (wid: string, mid: string) =>
    [...memoryKeys.all, "detail", wid, mid] as const,
  recall: (wid: string, q: string) =>
    [...memoryKeys.all, "recall", wid, q] as const,
};

// --- 내부 헬퍼: FormData 업로드용 raw fetch ---
// apiClient는 Content-Type: application/json을 강제하므로 multipart를 못 보낸다.
// upload/hooks.ts와 동일한 패턴으로 직접 fetch 호출.
async function postFormData<T>(
  token: string,
  path: string,
  formData: FormData
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) {
    const errBody = await res
      .json()
      .catch(() => ({ detail: "요청 실패" }));
    throw new Error(
      (errBody as { detail?: string }).detail ?? `HTTP ${res.status}`
    );
  }
  return res.json() as Promise<T>;
}

// --- API 함수 ---

/**
 * 텍스트 메모 capture — multipart/form-data text 필드 전송.
 * BE는 202 Accepted + status="processing"으로 즉시 응답한다.
 */
export async function captureText(
  token: string,
  workspaceId: string,
  text: string
): Promise<MemoryCreateResponse> {
  const fd = new FormData();
  fd.append("text", text);
  return postFormData<MemoryCreateResponse>(
    token,
    `/workspaces/${workspaceId}/memory`,
    fd
  );
}

/**
 * 음성 메모 capture — multipart/form-data audio 파일 전송.
 * STT + embedding은 BackgroundTask로 처리, polling으로 상태 확인.
 */
export async function captureVoice(
  token: string,
  workspaceId: string,
  blob: Blob,
  filename: string
): Promise<MemoryCreateResponse> {
  const fd = new FormData();
  fd.append("audio", blob, filename);
  return postFormData<MemoryCreateResponse>(
    token,
    `/workspaces/${workspaceId}/memory`,
    fd
  );
}

/**
 * Memory 단건 상세 조회 (polling용)
 */
export async function getMemory(
  token: string,
  workspaceId: string,
  memoryId: string
): Promise<MemoryDetail> {
  return apiClient<MemoryDetail>(
    `/workspaces/${workspaceId}/memory/${memoryId}`,
    { token }
  );
}

/**
 * Memory recall — vector + keyword hybrid 검색, Top 3 결과 반환.
 */
export async function recallMemory(
  token: string,
  workspaceId: string,
  q: string
): Promise<MemoryRecallResult> {
  const qs = new URLSearchParams({ q });
  return apiClient<MemoryRecallResult>(
    `/workspaces/${workspaceId}/memory/recall?${qs.toString()}`,
    { token }
  );
}

// --- R6 Promote 1-button ---

export interface PromoteMemoryResponse {
  new_memory_id: string;
  audit_id: string;
  status: string;
}

/**
 * Memory promote — 원본 보존 + target team workspace 복제 (ADR-016 AD-41).
 * 202 Accepted + audit_id. embedding 재생성은 백그라운드.
 */
export async function promoteMemory(
  token: string,
  sourceWorkspaceId: string,
  memoryId: string,
  targetWorkspaceId: string
): Promise<PromoteMemoryResponse> {
  return apiClient<PromoteMemoryResponse>(
    `/workspaces/${sourceWorkspaceId}/memory/${memoryId}/promote`,
    {
      token,
      method: "POST",
      body: JSON.stringify({ target_workspace_id: targetWorkspaceId }),
    }
  );
}
