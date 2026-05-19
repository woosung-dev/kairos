// 온보딩 도메인 Zod 스키마 — BE GET /api/v1/users/me/onboarding 응답 검증
import { z } from "zod/v4";

export const onboardingResponseSchema = z.object({
  step: z.number().int().min(0).max(4),
  totalSteps: z.literal(4),
  // Codex 2차 finding P2: FastAPI naive DateTime 은 Z suffix 없이 serialize 되어
  // .datetime() validator 가 ZodError → 검증 relax 로 회피. BE timezone-aware 전환 시 복원 CO.
  onboardedAt: z.string().nullable(),
  isCompleted: z.boolean(),
});

export type OnboardingResponse = z.infer<typeof onboardingResponseSchema>;
