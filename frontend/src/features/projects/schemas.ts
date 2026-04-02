import { z } from "zod/v4";

export const createProjectSchema = z.object({
  title: z.string().min(1, "프로젝트 이름을 입력하세요"),
  description: z.string().optional(),
  tags: z.array(z.string()).default([]),
});

export type CreateProjectFormData = z.infer<typeof createProjectSchema>;
