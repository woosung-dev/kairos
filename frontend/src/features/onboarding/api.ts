// 온보딩 도메인 API — Clerk JWT + workspace 컨텍스트 헤더로 호출
import { apiClient } from "@/lib/api-client";

import { onboardingResponseSchema, type OnboardingResponse } from "./schemas";

export const onboardingKeys = {
  all: ["onboarding"] as const,
  status: (wid: string | null) => [...onboardingKeys.all, "status", wid] as const,
};

export async function fetchOnboarding(
  token: string,
  workspaceId: string,
): Promise<OnboardingResponse> {
  const data = await apiClient<unknown>("/users/me/onboarding", {
    token,
    headers: {
      "X-Workspace-Id": workspaceId,
    },
  });
  return onboardingResponseSchema.parse(data);
}
