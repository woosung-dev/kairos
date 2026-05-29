"use client";
// 피드백 제출 mutation 훅
import { useAuth } from "@clerk/nextjs";
import { useMutation } from "@tanstack/react-query";

import { postFeedback } from "./api";
import type { FeedbackInput } from "./types";

export function useSubmitFeedback() {
  const { getToken } = useAuth();
  return useMutation({
    mutationFn: async (input: FeedbackInput) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      return postFeedback(token, input);
    },
  });
}
