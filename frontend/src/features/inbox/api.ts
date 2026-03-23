import type { InboxItem } from "@/features/inbox/types";
import type { UUID } from "@/types";
import { mockInboxItems } from "@/mocks/data/inbox";

// Query Key 팩토리
export const inboxKeys = {
  all: ["inbox"] as const,
  list: (workspaceId: string) => [...inboxKeys.all, "list", workspaceId] as const,
  detail: (id: string) => [...inboxKeys.all, "detail", id] as const,
};

// 지연 시뮬레이션
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function fetchInboxItems(workspaceId: string): Promise<InboxItem[]> {
  await delay(300);
  return mockInboxItems.filter(
    (item) => item.workspaceId === workspaceId && !item.isProcessed
  );
}

export async function classifyInboxItem(params: {
  inboxItemId: UUID;
  paraItemId: UUID;
}): Promise<InboxItem> {
  await delay(500);
  const item = mockInboxItems.find((i) => i.id === params.inboxItemId);
  if (!item) throw new Error("Inbox 아이템을 찾을 수 없습니다");

  // mock: isProcessed 변경
  const updated = { ...item, isProcessed: true };
  const idx = mockInboxItems.findIndex((i) => i.id === params.inboxItemId);
  if (idx !== -1) mockInboxItems[idx] = updated;
  return updated;
}

export async function dismissInboxItem(inboxItemId: UUID): Promise<void> {
  await delay(300);
  const idx = mockInboxItems.findIndex((i) => i.id === inboxItemId);
  if (idx !== -1) {
    mockInboxItems[idx] = { ...mockInboxItems[idx], isProcessed: true };
  }
}
