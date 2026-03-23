"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Target,
  Pin,
  BookOpen,
  Archive,
  Plus,
  MoreHorizontal,
  Pencil,
  Trash2,
  FileText,
  Mic,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { useParaItems, useArchiveParaItem } from "../hooks";
import { CreateParaDialog } from "./create-para-dialog";
import { DEFAULT_WORKSPACE_ID } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { ParaCategory, ParaItem } from "@/types/para";

const categoryConfig = {
  project: { icon: Target, label: "Projects", color: "text-blue-500", singular: "Project" },
  area: { icon: Pin, label: "Areas", color: "text-amber-500", singular: "Area" },
  resource: { icon: BookOpen, label: "Resources", color: "text-green-500", singular: "Resource" },
  archive: { icon: Archive, label: "Archives", color: "text-zinc-400", singular: "Archive" },
} as const;

interface ParaItemListProps {
  category: ParaCategory;
}

export function ParaItemList({ category }: ParaItemListProps) {
  const { data: items, isLoading } = useParaItems(
    DEFAULT_WORKSPACE_ID,
    category
  );
  const archiveMutation = useArchiveParaItem();
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const cfg = categoryConfig[category];
  const Icon = cfg.icon;

  const handleArchive = (item: ParaItem) => {
    archiveMutation.mutate(item.id, {
      onSuccess: () => toast.success(`"${item.title}"이(가) Archive로 이동되었습니다`),
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="h-20 animate-pulse bg-muted/30 p-4" />
          </Card>
        ))}
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6 p-6">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Icon className={cn("h-6 w-6", cfg.color)} />
            <div>
              <h1 className="text-2xl font-bold tracking-tight">{cfg.label}</h1>
              <p className="text-sm text-muted-foreground">
                {items?.length ?? 0}개 아이템
              </p>
            </div>
          </div>
          {category !== "archive" && (
            <Button size="sm" onClick={() => setIsCreateOpen(true)}>
              <Plus className="mr-1.5 h-4 w-4" />
              새 {cfg.singular}
            </Button>
          )}
        </div>

        {/* 아이템 목록 */}
        {items && items.length > 0 ? (
          <div className="space-y-2">
            {items.map((item) => (
              <ParaItemCard
                key={item.id}
                item={item}
                onArchive={handleArchive}
              />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <Icon className={cn("h-12 w-12", cfg.color, "opacity-30")} />
              <h3 className="mt-4 text-lg font-semibold">
                아직 {cfg.singular}이(가) 없습니다
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                새 {cfg.singular}을(를) 만들어보세요.
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      <CreateParaDialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        defaultCategory={category}
      />
    </>
  );
}

function ParaItemCard({
  item,
  onArchive,
}: {
  item: ParaItem;
  onArchive: (item: ParaItem) => void;
}) {
  const cfg = categoryConfig[item.category];
  const Icon = cfg.icon;
  const href =
    item.category === "archive"
      ? `/workspace/${item.workspaceId}/archives`
      : `/workspace/${item.workspaceId}/${item.category}s/${item.id}`;

  return (
    <Card className="group transition-colors hover:bg-accent/30">
      <CardContent className="flex items-center gap-4 p-4">
        <div
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-muted",
            cfg.color
          )}
        >
          <Icon className="h-5 w-5" />
        </div>

        <Link href={href} className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-medium">{item.title}</h3>
          {item.description && (
            <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
              {item.description}
            </p>
          )}
          <div className="mt-1.5 flex items-center gap-3 text-xs text-muted-foreground">
            {item.meetingCount > 0 && (
              <span className="flex items-center gap-1">
                <Mic className="h-3 w-3" />
                {item.meetingCount}
              </span>
            )}
            {item.contentCount > 0 && (
              <span className="flex items-center gap-1">
                <FileText className="h-3 w-3" />
                {item.contentCount}
              </span>
            )}
            {item.actionItemCount > 0 && (
              <Badge variant="outline" className="h-5 text-[10px]">
                액션 {item.actionItemCount}
              </Badge>
            )}
          </div>
        </Link>

        {/* 메뉴 */}
        <DropdownMenu>
          <DropdownMenuTrigger
            className="flex h-8 w-8 items-center justify-center rounded-md opacity-0 transition-opacity hover:bg-accent group-hover:opacity-100"
          >
            <MoreHorizontal className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Pencil className="mr-2 h-3.5 w-3.5" />
              편집
            </DropdownMenuItem>
            {item.category !== "archive" && (
              <DropdownMenuItem onClick={() => onArchive(item)}>
                <Archive className="mr-2 h-3.5 w-3.5" />
                Archive로 이동
              </DropdownMenuItem>
            )}
            <DropdownMenuItem className="text-destructive">
              <Trash2 className="mr-2 h-3.5 w-3.5" />
              삭제
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardContent>
    </Card>
  );
}
