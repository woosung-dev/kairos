// 온보딩 도메인 Zod 스키마 — BE GET /api/v1/users/me/onboarding 응답 검증
import { z } from "zod/v4";

export const onboardingResponseSchema = z.object({
  step: z.number().int().min(0).max(4),
  totalSteps: z.literal(4),
  onboardedAt: z.string().datetime().nullable(),
  isCompleted: z.boolean(),
});

export type OnboardingResponse = z.infer<typeof onboardingResponseSchema>;
