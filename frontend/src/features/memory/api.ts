// Sprint 15 Memory 도메인 API — capture / recall / detail
import type { ApiClient } from "@/lib/api-client";
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

// --- API 함수 ---
// Sprint 29 R3 (api-multipart): api.fetch 가 FormData 본문을 지원하므로 전용 postFormData
// 헬퍼 제거 — multipart 도 api.fetch 단일 경로로 통합(에러 처리·base URL 일관).

/**
 * 텍스트 메모 capture — multipart/form-data text 필드 전송.
 * BE는 202 Accepted + status="processing"으로 즉시 응답한다.
 */
export async function captureText(
  api: ApiClient,
  workspaceId: string,
  text: string
): Promise<MemoryCreateResponse> {
  const fd = new FormData();
  fd.append("text", text);
  return api.fetch<MemoryCreateResponse>(
    `/workspaces/${workspaceId}/memory`,
    { method: "POST", body: fd }
  );
}

/**
 * 음성 메모 capture — multipart/form-data audio 파일 전송.
 * STT + embedding은 BackgroundTask로 처리, polling으로 상태 확인.
 */
export async function captureVoice(
  api: ApiClient,
  workspaceId: string,
  blob: Blob,
  filename: string
): Promise<MemoryCreateResponse> {
  const fd = new FormData();
  fd.append("audio", blob, filename);
  return api.fetch<MemoryCreateResponse>(
    `/workspaces/${workspaceId}/memory`,
    { method: "POST", body: fd }
  );
}

/**
 * Memory 단건 상세 조회 (polling용)
 */
export async function getMemory(
  api: ApiClient,
  workspaceId: string,
  memoryId: string
): Promise<MemoryDetail> {
  return api.fetch<MemoryDetail>(
    `/workspaces/${workspaceId}/memory/${memoryId}`);
}

/**
 * Memory recall — vector + keyword hybrid 검색, Top 3 결과 반환.
 */
export async function recallMemory(
  api: ApiClient,
  workspaceId: string,
  q: string
): Promise<MemoryRecallResult> {
  const qs = new URLSearchParams({ q });
  return api.fetch<MemoryRecallResult>(
    `/workspaces/${workspaceId}/memory/recall?${qs.toString()}`);
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
  api: ApiClient,
  sourceWorkspaceId: string,
  memoryId: string,
  targetWorkspaceId: string
): Promise<PromoteMemoryResponse> {
  return api.fetch<PromoteMemoryResponse>(
    `/workspaces/${sourceWorkspaceId}/memory/${memoryId}/promote`,
    { method: "POST",
      body: JSON.stringify({ target_workspace_id: targetWorkspaceId }),
    }
  );
}
