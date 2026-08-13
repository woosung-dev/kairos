// 온보딩 도메인 API — Clerk JWT + workspace 컨텍스트 헤더로 호출
import type { ApiClient } from "@/lib/api-client";

import { onboardingResponseSchema, type OnboardingResponse } from "./schemas";


export async function fetchOnboarding(
  api: ApiClient,
  workspaceId: string,
): Promise<OnboardingResponse> {
  const data = await api.fetch<unknown>("/users/me/onboarding", { headers: {
      "X-Workspace-Id": workspaceId,
    },
  });
  return onboardingResponseSchema.parse(data);
}
