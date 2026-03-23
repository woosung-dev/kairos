"use client";

import { FileText, Mic, Paperclip } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { InboxItem } from "@/features/inbox/types";
import { cn } from "@/lib/utils";

const sourceIconMap = {
  meeting: Mic,
  note: FileText,
  attachment: Paperclip,
} as const;

const sourceLabel = {
  meeting: "회의록",
  note: "노트",
  attachment: "첨부파일",
} as const;

const categoryColorMap = {
  project: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  area: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  resource: "bg-green-500/10 text-green-500 border-green-500/20",
  archive: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
} as const;

const categoryLabel = {
  project: "Project",
  area: "Area",
  resource: "Resource",
  archive: "Archive",
} as const;

interface InboxItemCardProps {
  item: InboxItem;
  onClassify: (item: InboxItem) => void;
}

export function InboxItemCard({ item, onClassify }: InboxItemCardProps) {
  const SourceIcon = sourceIconMap[item.sourceType];
  const timeAgo = getTimeAgo(item.createdAt);

  return (
    <Card
      className="cursor-pointer transition-colors hover:bg-accent/30"
      onClick={() => onClassify(item)}
    >
      <CardContent className="flex items-start gap-4 p-4">
        {/* 소스 타입 아이콘 */}
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-muted">
          <SourceIcon className="h-4 w-4 text-muted-foreground" />
        </div>

        {/* 콘텐츠 */}
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className="truncate text-sm font-medium">{item.title}</h3>
            <span className="shrink-0 text-xs text-muted-foreground">
              {timeAgo}
            </span>
          </div>

          {item.summary && (
            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
              {item.summary}
            </p>
          )}

          {/* 태그 영역 */}
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="text-[10px]">
              {sourceLabel[item.sourceType]}
            </Badge>

            {item.aiSuggestedParaType && (
              <Badge
                variant="outline"
                className={cn(
                  "text-[10px]",
                  categoryColorMap[item.aiSuggestedParaType]
                )}
              >
                AI: {categoryLabel[item.aiSuggestedParaType]}
                {item.aiConfidence != null && (
                  <span className="ml-1 opacity-60">
                    {Math.round(item.aiConfidence * 100)}%
                  </span>
                )}
              </Badge>
            )}

            {item.aiSuggestedParaTitle && (
              <span className="truncate text-[10px] text-muted-foreground">
                → {item.aiSuggestedParaTitle}
              </span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function getTimeAgo(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diffMs = now - date;
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHour = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return "방금";
  if (diffMin < 60) return `${diffMin}분 전`;
  if (diffHour < 24) return `${diffHour}시간 전`;
  if (diffDay < 7) return `${diffDay}일 전`;
  return new Date(dateStr).toLocaleDateString("ko-KR");
}
