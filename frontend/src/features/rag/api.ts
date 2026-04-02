import type { RagAskRequest } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const ragKeys = {
  all: ["rag"] as const,
};

export async function askRag(
  token: string,
  wid: string,
  data: RagAskRequest,
): Promise<Response> {
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces/${wid}/rag/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(`RAG 요청 실패: ${res.status}`);
  }

  return res;
}
