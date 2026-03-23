"use client";

import { useState } from "react";
import { Inbox } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { InboxItemCard } from "./inbox-item-card";
import { ClassifyDialog } from "./classify-dialog";
import { useInboxItems, useClassifyInboxItem, useDismissInboxItem } from "../hooks";
import { useParaItems } from "@/features/para/hooks";
import { DEFAULT_WORKSPACE_ID } from "@/lib/constants";
import type { InboxItem } from "@/features/inbox/types";

export function InboxList() {
  const { data: items, isLoading } = useInboxItems(DEFAULT_WORKSPACE_ID);
  const { data: paraItems } = useParaItems(DEFAULT_WORKSPACE_ID);
  const classifyMutation = useClassifyInboxItem();
  const dismissMutation = useDismissInboxItem();

  const [selectedItem, setSelectedItem] = useState<InboxItem | null>(null);

  const handleClassify = (inboxItemId: string, paraItemId: string) => {
    classifyMutation.mutate(
      { inboxItemId, paraItemId },
      {
        onSuccess: () => {
          toast.success("분류가 완료되었습니다");
          setSelectedItem(null);
        },
        onError: () => {
          toast.error("분류에 실패했습니다");
        },
      }
    );
  };

  const handleDismiss = (inboxItemId: string) => {
    dismissMutation.mutate(inboxItemId, {
      onSuccess: () => {
        toast.success("아이템을 무시했습니다");
        setSelectedItem(null);
      },
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="h-24 animate-pulse bg-muted/30 p-4" />
          </Card>
        ))}
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <Inbox className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="mt-4 text-lg font-semibold">Inbox가 비어있습니다</h3>
          <p className="mt-1 max-w-sm text-center text-sm text-muted-foreground">
            모든 아이템이 분류되었습니다. 잘 하셨어요!
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="space-y-2">
        {items.map((item) => (
          <InboxItemCard
            key={item.id}
            item={item}
            onClassify={setSelectedItem}
          />
        ))}
      </div>

      <ClassifyDialog
        item={selectedItem}
        paraItems={paraItems ?? []}
        isOpen={selectedItem !== null}
        onClose={() => setSelectedItem(null)}
        onClassify={handleClassify}
        onDismiss={handleDismiss}
        isClassifying={classifyMutation.isPending}
      />
    </>
  );
}
