"use client";
// 현재 사용자 조회 훅 (ADR-031 — Clerk 의 useUser/useAuth 대체)
//
// ★왜 Better Auth 의 `useSession()` 을 그대로 안 쓰는가 —
//   세션의 user.id 는 `auth_user.id`(외부 인증 ID)이고, 앱 도메인이 쓰는 식별자는
//   `users.id`(내부 UUID)다. 멤버 목록·소유권 비교는 전부 내부 UUID 축이다.
//   세션을 직접 쓰면 그 둘이 섞여, Clerk 시절 `member.clerkId === user.id` 매칭이
//   깨졌던 것과 같은 종류의 결합이 다시 생긴다.

import { useQuery } from "@tanstack/react-query";

import { useApiClient } from "@/lib/use-api-client";

export interface Me {
  /** 내부 UUID — 앱 도메인의 사용자 식별자. 인증 공급자가 바뀌어도 불변이다. */
  id: string;
  /** 외부 인증 ID (Better Auth auth_user.id). 디버깅·지원용이며 권한 판정에 쓰지 않는다. */
  authUserId: string | null;
  displayName: string;
  email: string;
  avatarUrl: string | null;
  onboardingStep: number;
  onboardedAt: string | null;
}

export const meKeys = {
  detail: ["auth", "me"] as const,
};

export function useMe() {
  const api = useApiClient();
  return useQuery({
    queryKey: meKeys.detail,
    queryFn: () => api.fetch<Me>("/users/me"),
    // 로그인 세션 동안 거의 바뀌지 않는다. onboardingStep 갱신은 해당 훅이 직접 무효화한다.
    staleTime: 5 * 60_000,
    retry: false,
  });
}
