// 피드백 BE API 호출
import type { ApiClient } from "@/lib/api-client";
import type { FeedbackInput, FeedbackResult } from "./types";

export async function postFeedback(
  api: ApiClient,
  input: FeedbackInput,
): Promise<FeedbackResult> {
  return api.fetch<FeedbackResult>("/feedback", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
