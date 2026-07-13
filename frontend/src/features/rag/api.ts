// RAG ask SSE 스트림 API — raw Response 가 필요해 ApiClient.fetchRaw 사용
import type { ApiClient } from "@/lib/api-client";
import type { RagAskRequest } from "./types";


export async function askRag(
  api: ApiClient,
  wid: string,
  data: RagAskRequest,
): Promise<Response> {
  const res = await api.fetchRaw(`/workspaces/${wid}/rag/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(`AI 검색 요청 실패: ${res.status}`);
  }

  return res;
}
