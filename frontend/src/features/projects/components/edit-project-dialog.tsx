// 프로젝트 편집 다이얼로그 (AD-34 신규)
"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { useUpdateProject } from "../hooks";
import type { Project } from "../types";

const editProjectSchema = z.object({
  title: z.string().min(1, "프로젝트 이름을 입력하세요"),
  description: z.string().optional(),
  status: z.enum(["active", "completed", "archived"]),
  tags: z.string(),
});

type EditProjectFormData = z.infer<typeof editProjectSchema>;

interface EditProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  project: Project;
}

export function EditProjectDialog({
  open,
  onOpenChange,
  workspaceId,
  project,
}: EditProjectDialogProps) {
  const updateProject = useUpdateProject(workspaceId);

  const form = useForm<EditProjectFormData>({
    resolver: zodResolver(editProjectSchema),
    defaultValues: {
      title: project.title,
      description: project.description ?? "",
      status: project.status,
      tags: project.tags.join(", "),
    },
  });

  // 다이얼로그가 열릴 때마다 프로젝트 최신 값으로 리셋
  useEffect(() => {
    if (open) {
      form.reset({
        title: project.title,
        description: project.description ?? "",
        status: project.status,
        tags: project.tags.join(", "),
      });
    }
  }, [open, project, form]);

  const onSubmit = (data: EditProjectFormData) => {
    const tags = data.tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    updateProject.mutate(
      {
        id: project.id,
        data: {
          title: data.title,
          description: data.description || null,
          status: data.status,
          tags,
        },
      },
      {
        onSuccess: () => onOpenChange(false),
        onError: (err) => {
          form.setError("root", {
            message: err instanceof Error ? err.message : "수정에 실패했습니다",
          });
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>프로젝트 편집</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>프로젝트 이름</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="프로젝트 이름" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>설명</FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      placeholder="프로젝트 설명 (선택)"
                      rows={3}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="status"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>상태</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="active">진행 중</SelectItem>
                      <SelectItem value="completed">완료</SelectItem>
                      <SelectItem value="archived">보관</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="tags"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>태그</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="태그1, 태그2, 태그3" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            {form.formState.errors.root && (
              <p className="text-sm text-destructive">
                {form.formState.errors.root.message}
              </p>
            )}
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                취소
              </Button>
              <Button type="submit" disabled={updateProject.isPending}>
                {updateProject.isPending ? "저장 중..." : "저장"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
