import { z } from "zod/v4";

export const createParaItemSchema = z.object({
  title: z
    .string()
    .min(1, "제목을 입력해주세요")
    .max(200, "제목은 200자 이내로 입력해주세요"),
  description: z
    .string()
    .max(1000, "설명은 1000자 이내로 입력해주세요")
    .optional(),
  category: z.enum(["project", "area", "resource", "archive"]),
});

export type CreateParaItemInput = z.infer<typeof createParaItemSchema>;

export const updateParaItemSchema = z.object({
  title: z
    .string()
    .min(1, "제목을 입력해주세요")
    .max(200, "제목은 200자 이내로 입력해주세요")
    .optional(),
  description: z
    .string()
    .max(1000, "설명은 1000자 이내로 입력해주세요")
    .optional(),
});

export type UpdateParaItemInput = z.infer<typeof updateParaItemSchema>;
