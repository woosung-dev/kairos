"use client";

import {
  Target,
  Pin,
  BookOpen,
  Archive,
  Mic,
  FileText,
  CheckSquare,
  Paperclip,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useParaItem } from "../hooks";
import { cn } from "@/lib/utils";
import type { UUID } from "@/types";

const categoryConfig = {
  project: { icon: Target, color: "text-blue-500" },
  area: { icon: Pin, color: "text-amber-500" },
  resource: { icon: BookOpen, color: "text-green-500" },
  archive: { icon: Archive, color: "text-zinc-400" },
} as const;

interface ParaDetailProps {
  paraId: UUID;
}

export function ParaDetail({ paraId }: ParaDetailProps) {
  const { data: item, isLoading } = useParaItem(paraId);

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        <div className="h-4 w-96 animate-pulse rounded bg-muted" />
      </div>
    );
  }

  if (!item) {
    return (
      <div className="flex items-center justify-center p-12 text-muted-foreground">
        아이템을 찾을 수 없습니다.
      </div>
    );
  }

  const cfg = categoryConfig[item.category];
  const Icon = cfg.icon;

  return (
    <div className="space-y-6 p-6">
      {/* 헤더 */}
      <div className="flex items-start gap-4">
        <div
          className={cn(
            "flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-muted",
            cfg.color
          )}
        >
          <Icon className="h-6 w-6" />
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-bold tracking-tight">{item.title}</h1>
          {item.description && (
            <p className="mt-1 text-sm text-muted-foreground">
              {item.description}
            </p>
          )}
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline">{item.category}</Badge>
            <Badge variant="outline">{item.status}</Badge>
            <span className="text-xs text-muted-foreground">
              by {item.createdBy.displayName}
            </span>
          </div>
        </div>
      </div>

      {/* 탭 */}
      <Tabs defaultValue="meetings">
        <TabsList>
          <TabsTrigger value="meetings" className="gap-1.5">
            <Mic className="h-3.5 w-3.5" />
            회의록
            {item.meetingCount > 0 && (
              <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-[10px]">
                {item.meetingCount}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="notes" className="gap-1.5">
            <FileText className="h-3.5 w-3.5" />
            노트
          </TabsTrigger>
          <TabsTrigger value="actions" className="gap-1.5">
            <CheckSquare className="h-3.5 w-3.5" />
            액션
            {item.actionItemCount > 0 && (
              <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-[10px]">
                {item.actionItemCount}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="files" className="gap-1.5">
            <Paperclip className="h-3.5 w-3.5" />
            파일
          </TabsTrigger>
        </TabsList>

        <TabsContent value="meetings">
          <PlaceholderTab
            icon={Mic}
            title="아직 회의록이 없습니다"
            description="회의를 녹음하거나 파일을 업로드하면 여기에 표시됩니다."
          />
        </TabsContent>

        <TabsContent value="notes">
          <PlaceholderTab
            icon={FileText}
            title="아직 노트가 없습니다"
            description="새 노트를 작성하면 여기에 표시됩니다."
          />
        </TabsContent>

        <TabsContent value="actions">
          <PlaceholderTab
            icon={CheckSquare}
            title="아직 액션 아이템이 없습니다"
            description="회의에서 추출된 액션 아이템이 여기에 표시됩니다."
          />
        </TabsContent>

        <TabsContent value="files">
          <PlaceholderTab
            icon={Paperclip}
            title="아직 첨부파일이 없습니다"
            description="파일을 드래그앤드롭하여 업로드하세요."
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function PlaceholderTab({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <Card className="mt-4">
      <CardContent className="flex flex-col items-center justify-center py-12">
        <Icon className="h-10 w-10 text-muted-foreground/30" />
        <h3 className="mt-3 text-sm font-medium">{title}</h3>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}
