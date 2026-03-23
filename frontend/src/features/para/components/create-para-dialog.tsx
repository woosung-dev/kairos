"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useCreateParaItem } from "../hooks";
import { createParaItemSchema, type CreateParaItemInput } from "../schemas";
import { DEFAULT_WORKSPACE_ID } from "@/lib/constants";
import type { ParaCategory } from "@/features/para/types";

interface CreateParaDialogProps {
  isOpen: boolean;
  onClose: () => void;
  defaultCategory?: ParaCategory;
}

export function CreateParaDialog({
  isOpen,
  onClose,
  defaultCategory = "project",
}: CreateParaDialogProps) {
  const createMutation = useCreateParaItem();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateParaItemInput>({
    resolver: zodResolver(createParaItemSchema),
    defaultValues: {
      category: defaultCategory,
      title: "",
      description: "",
    },
  });

  const onSubmit = (data: CreateParaItemInput) => {
    createMutation.mutate(
      {
        workspaceId: DEFAULT_WORKSPACE_ID,
        category: data.category,
        title: data.title,
        description: data.description,
      },
      {
        onSuccess: () => {
          toast.success("아이템이 생성되었습니다");
          reset();
          onClose();
        },
        onError: () => {
          toast.error("생성에 실패했습니다");
        },
      }
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>새 아이템 만들기</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* 카테고리 선택 */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">카테고리</label>
            <select
              {...register("category")}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="project">Project</option>
              <option value="area">Area</option>
              <option value="resource">Resource</option>
            </select>
          </div>

          {/* 제목 */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">제목</label>
            <input
              {...register("title")}
              placeholder="아이템 제목을 입력하세요"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              autoFocus
            />
            {errors.title && (
              <p className="text-xs text-destructive">{errors.title.message}</p>
            )}
          </div>

          {/* 설명 */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">설명 (선택)</label>
            <textarea
              {...register("description")}
              placeholder="아이템에 대한 설명을 입력하세요"
              rows={3}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
            {errors.description && (
              <p className="text-xs text-destructive">
                {errors.description.message}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "생성 중..." : "생성"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
