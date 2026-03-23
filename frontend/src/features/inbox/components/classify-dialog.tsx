"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Target,
  Pin,
  BookOpen,
  Archive,
  Check,
  X,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { InboxItem } from "@/features/inbox/types";
import type { ParaItem, ParaCategory } from "@/features/para/types";

const categoryConfig = {
  project: { icon: Target, label: "Project", color: "text-blue-500" },
  area: { icon: Pin, label: "Area", color: "text-amber-500" },
  resource: { icon: BookOpen, label: "Resource", color: "text-green-500" },
  archive: { icon: Archive, label: "Archive", color: "text-zinc-400" },
} as const;

interface ClassifyDialogProps {
  item: InboxItem | null;
  paraItems: ParaItem[];
  isOpen: boolean;
  onClose: () => void;
  onClassify: (inboxItemId: string, paraItemId: string) => void;
  onDismiss: (inboxItemId: string) => void;
  isClassifying: boolean;
}

export function ClassifyDialog({
  item,
  paraItems,
  isOpen,
  onClose,
  onClassify,
  onDismiss,
  isClassifying,
}: ClassifyDialogProps) {
  const [selectedParaId, setSelectedParaId] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<ParaCategory | null>(
    null
  );

  // 다이얼로그 열릴 때 AI 추천으로 초기 선택
  const effectiveSelected =
    selectedParaId ?? item?.aiSuggestedParaId ?? null;

  const filteredItems = filterCategory
    ? paraItems.filter((p) => p.category === filterCategory)
    : paraItems.filter((p) => p.status !== "archived");

  if (!item) return null;

  const handleClassify = () => {
    if (!effectiveSelected) return;
    onClassify(item.id, effectiveSelected);
    setSelectedParaId(null);
    setFilterCategory(null);
  };

  const handleDismiss = () => {
    onDismiss(item.id);
    setSelectedParaId(null);
    setFilterCategory(null);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>PARA 분류</DialogTitle>
          <DialogDescription className="line-clamp-2">
            {item.title}
          </DialogDescription>
        </DialogHeader>

        {/* AI 추천 표시 */}
        {item.aiSuggestedParaType && (
          <div className="flex items-center gap-2 rounded-md border border-blue-500/20 bg-blue-500/5 px-3 py-2">
            <Sparkles className="h-4 w-4 text-blue-500" />
            <span className="text-xs text-muted-foreground">AI 추천:</span>
            <Badge variant="outline" className="text-xs">
              {item.aiSuggestedParaTitle}
            </Badge>
            {item.aiConfidence != null && (
              <span className="text-xs text-muted-foreground">
                ({Math.round(item.aiConfidence * 100)}%)
              </span>
            )}
          </div>
        )}

        {/* 카테고리 필터 */}
        <div className="flex gap-1">
          {(
            Object.entries(categoryConfig) as [
              ParaCategory,
              (typeof categoryConfig)[ParaCategory],
            ][]
          ).map(([cat, cfg]) => {
            const Icon = cfg.icon;
            const isActive = filterCategory === cat;
            return (
              <Button
                key={cat}
                variant={isActive ? "secondary" : "ghost"}
                size="sm"
                className="gap-1.5 text-xs"
                onClick={() =>
                  setFilterCategory(isActive ? null : cat)
                }
              >
                <Icon className={cn("h-3.5 w-3.5", cfg.color)} />
                {cfg.label}
              </Button>
            );
          })}
        </div>

        {/* PARA 아이템 목록 */}
        <ScrollArea className="h-64">
          <div className="flex flex-col gap-1">
            {filteredItems.map((paraItem) => {
              const cfg = categoryConfig[paraItem.category];
              const Icon = cfg.icon;
              const isSelected = effectiveSelected === paraItem.id;

              return (
                <button
                  key={paraItem.id}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm transition-colors",
                    isSelected
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-muted"
                  )}
                  onClick={() => setSelectedParaId(paraItem.id)}
                >
                  <Icon className={cn("h-4 w-4 shrink-0", cfg.color)} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{paraItem.title}</p>
                    {paraItem.description && (
                      <p className="truncate text-xs text-muted-foreground">
                        {paraItem.description}
                      </p>
                    )}
                  </div>
                  {isSelected && (
                    <Check className="h-4 w-4 shrink-0 text-primary" />
                  )}
                </button>
              );
            })}
            {filteredItems.length === 0 && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                해당 카테고리에 아이템이 없습니다.
              </p>
            )}
          </div>
        </ScrollArea>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDismiss}
            disabled={isClassifying}
          >
            <X className="mr-1.5 h-3.5 w-3.5" />
            무시
          </Button>
          <Button
            size="sm"
            onClick={handleClassify}
            disabled={!effectiveSelected || isClassifying}
          >
            <Check className="mr-1.5 h-3.5 w-3.5" />
            {isClassifying ? "분류 중..." : "분류 확정"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
