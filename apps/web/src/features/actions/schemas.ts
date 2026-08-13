import { z } from "zod/v4";

export const createActionItemSchema = z.object({
  title: z.string().min(1, "제목을 입력하세요"),
  description: z.string().optional(),
  priority: z.enum(["high", "medium", "low"]).default("medium"),
  dueDate: z.string().optional(),
  projectId: z.string().optional(),
});

export type CreateActionItemFormData = z.infer<typeof createActionItemSchema>;

export const updateActionItemSchema = z.object({
  title: z.string().min(1, "제목을 입력하세요").optional(),
  description: z.string().nullable().optional(),
  priority: z.enum(["high", "medium", "low"]).optional(),
  status: z.enum(["todo", "in_progress", "done", "cancelled"]).optional(),
  dueDate: z.string().nullable().optional(),
  projectId: z.string().nullable().optional(),
});

export type UpdateActionItemFormData = z.infer<typeof updateActionItemSchema>;
