// 피드백 BE API 호출
import { apiClient } from "@/lib/api-client";
import type { FeedbackInput, FeedbackResult } from "./types";

export async function postFeedback(
  token: string,
  input: FeedbackInput,
): Promise<FeedbackResult> {
  return apiClient<FeedbackResult>("/feedback", {
    token,
    method: "POST",
    body: JSON.stringify(input),
  });
}
