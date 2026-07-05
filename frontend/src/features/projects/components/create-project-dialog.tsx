// 프로젝트 생성 다이얼로그 — Sprint 24 Wave 2 T-PROJ-LIST (BUG-CASUAL-001) /projects 페이지 신설과 함께 도입
"use client";

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
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AlertTriangle } from "lucide-react";
import { VISIBILITY_DESCRIPTIONS, VISIBILITY_LABELS } from "@/lib/visibility";
import { useCreateProject } from "../hooks";

// "default" = visibility 미전송 → BE 가 멤버의 default_project_visibility(W-5 시드),
// 그것도 없으면 public 으로 결정 (projects/router.py 폴백 체인 보존)
const VISIBILITY_OPTIONS = ["default", "public", "draft", "private"] as const;

const createProjectSchema = z.object({
  title: z.string().min(1, "프로젝트 이름을 입력하세요"),
  description: z.string().optional(),
  tags: z.string(),
  visibility: z.enum(VISIBILITY_OPTIONS),
});

type CreateProjectFormData = z.infer<typeof createProjectSchema>;

interface CreateProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
}

export function CreateProjectDialog({
  open,
  onOpenChange,
  workspaceId,
}: CreateProjectDialogProps) {
  const createProject = useCreateProject(workspaceId);

  const form = useForm<CreateProjectFormData>({
    resolver: zodResolver(createProjectSchema),
    defaultValues: { title: "", description: "", tags: "", visibility: "default" },
  });

  const selectedVisibility = form.watch("visibility");

  const onSubmit = (data: CreateProjectFormData) => {
    const tags = data.tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    createProject.mutate(
      {
        title: data.title,
        description: data.description || null,
        tags,
        ...(data.visibility !== "default" && { visibility: data.visibility }),
      },
      {
        onSuccess: () => {
          form.reset();
          onOpenChange(false);
        },
        onError: (err) => {
          form.setError("root", {
            message: err instanceof Error ? err.message : "생성에 실패했습니다",
          });
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>새 프로젝트</DialogTitle>
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
                    <Input
                      {...field}
                      placeholder="예: 신규 기능 기획"
                      autoFocus
                    />
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
            <FormField
              control={form.control}
              name="visibility"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>공개 범위</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger
                        className="w-full"
                        aria-label="공개 범위 선택"
                        data-testid="create-project-visibility"
                      >
                        <SelectValue>
                          {field.value === "default"
                            ? "워크스페이스 기본값"
                            : VISIBILITY_LABELS[field.value]}
                        </SelectValue>
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem
                        value="default"
                        data-testid="create-project-visibility-default"
                      >
                        워크스페이스 기본값 — 초대 시 설정된 공개 범위 (없으면 공개)
                      </SelectItem>
                      {(["public", "draft", "private"] as const).map((opt) => (
                        <SelectItem
                          key={opt}
                          value={opt}
                          data-testid={`create-project-visibility-${opt}`}
                        >
                          {VISIBILITY_LABELS[opt]} — {VISIBILITY_DESCRIPTIONS[opt]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            {selectedVisibility === "private" && (
              <div
                className="p-3 text-xs rounded flex items-start gap-1.5"
                data-testid="create-project-private-warning"
                style={{
                  background: "rgba(251,191,36,0.1)",
                  borderLeft: "3px solid var(--warning)",
                  color: "var(--text-secondary)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                <AlertTriangle
                  className="w-4 h-4 shrink-0 mt-0.5"
                  style={{ color: "var(--warning)" }}
                />
                <span>
                  비공개 프로젝트는 명시적 멤버 + admin/owner만 접근하고 AI 검색에서
                  제외됩니다. 생성자는 자동으로 멤버에 추가됩니다.
                </span>
              </div>
            )}
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
              <Button type="submit" disabled={createProject.isPending}>
                {createProject.isPending ? "생성 중..." : "생성"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
