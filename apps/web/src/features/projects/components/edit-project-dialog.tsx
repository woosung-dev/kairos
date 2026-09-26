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
import type { Project, ProjectStatus } from "../types";

const editProjectSchema = z.object({
  title: z.string().min(1, "프로젝트 이름을 입력하세요"),
  description: z.string().optional(),
  status: z.enum(["active", "completed", "archived"]),
  tags: z.string(),
});

type EditProjectFormData = z.infer<typeof editProjectSchema>;

const STATUS_LABELS: Record<ProjectStatus, string> = {
  active: "진행 중",
  completed: "완료",
  archived: "보관",
};

interface EditProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  project: Project;
  /**
   * admin/owner 여부. BE 는 "보관(archived)" 진입·해제를 admin 이상에게만 허용한다 (C-017).
   * false 면 보관 옵션을 숨기고, 이미 보관된 프로젝트는 상태만 잠근 채 다른 필드를 저장할 수 있다.
   */
  canArchive: boolean;
}

export function EditProjectDialog({
  open,
  onOpenChange,
  workspaceId,
  project,
  canArchive,
}: EditProjectDialogProps) {
  const updateProject = useUpdateProject(workspaceId);
  // 보관 상태의 member 편집 — 상태를 바꾸면 BE 가 403 이므로 잠근다 (현재 값 그대로 보내는 것은 허용).
  const isStatusLocked = !canArchive && project.status === "archived";
  const statusOptions: ProjectStatus[] = canArchive || isStatusLocked
    ? ["active", "completed", "archived"]
    : ["active", "completed"];

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
                  <Select
                    onValueChange={field.onChange}
                    value={field.value}
                    disabled={isStatusLocked}
                  >
                    <FormControl>
                      <SelectTrigger data-testid="edit-project-status">
                        {/* items 미등록 상태에서 base-ui 는 raw 값("active")을 그리므로 라벨로 옮긴다 */}
                        <SelectValue>
                          {(value: ProjectStatus) => STATUS_LABELS[value] ?? value}
                        </SelectValue>
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {statusOptions.map((status) => (
                        <SelectItem key={status} value={status}>
                          {STATUS_LABELS[status]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {isStatusLocked && (
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      보관 해제는 관리자만 할 수 있습니다. 다른 항목은 저장할 수 있어요.
                    </p>
                  )}
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
