"use client";
// 피드백 제출 mutation 훅
import { useApiClient } from "@/lib/use-api-client";
import { useMutation } from "@tanstack/react-query";

import { postFeedback } from "./api";
import type { FeedbackInput } from "./types";

export function useSubmitFeedback() {
  const api = useApiClient();
  return useMutation({
    mutationFn: (input: FeedbackInput) => postFeedback(api, input),
  });
}
