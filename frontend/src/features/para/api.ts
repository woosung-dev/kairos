import type { ParaItem, ParaCategory } from "@/types/para";
import type { UUID } from "@/types";
import { mockParaItems } from "@/mocks/data/para";

// Query Key 팩토리
export const paraKeys = {
  all: ["para"] as const,
  list: (workspaceId: string) => [...paraKeys.all, "list", workspaceId] as const,
  byCategory: (workspaceId: string, category: ParaCategory) =>
    [...paraKeys.all, "list", workspaceId, category] as const,
  detail: (id: string) => [...paraKeys.all, "detail", id] as const,
};

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function fetchParaItems(
  workspaceId: string,
  category?: ParaCategory
): Promise<ParaItem[]> {
  await delay(300);
  let items = mockParaItems.filter((i) => i.workspaceId === workspaceId);
  if (category) {
    items = items.filter((i) => i.category === category);
  }
  return items.sort((a, b) => a.paraOrder - b.paraOrder);
}

export async function fetchParaItem(id: UUID): Promise<ParaItem | null> {
  await delay(200);
  return mockParaItems.find((i) => i.id === id) ?? null;
}

export async function createParaItem(params: {
  workspaceId: string;
  category: ParaCategory;
  title: string;
  description?: string;
}): Promise<ParaItem> {
  await delay(500);
  const newItem: ParaItem = {
    id: `para-${params.category.slice(0, 4)}-${Date.now()}`,
    workspaceId: params.workspaceId,
    category: params.category,
    title: params.title,
    description: params.description ?? null,
    status: "active",
    paraOrder: mockParaItems.filter(
      (i) => i.category === params.category
    ).length,
    createdBy: { id: "user-001", displayName: "당근", avatarUrl: null },
    contentCount: 0,
    meetingCount: 0,
    actionItemCount: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  mockParaItems.push(newItem);
  return newItem;
}

export async function updateParaItem(params: {
  id: UUID;
  title?: string;
  description?: string;
  status?: string;
}): Promise<ParaItem> {
  await delay(400);
  const idx = mockParaItems.findIndex((i) => i.id === params.id);
  if (idx === -1) throw new Error("PARA 아이템을 찾을 수 없습니다");

  mockParaItems[idx] = {
    ...mockParaItems[idx],
    ...(params.title && { title: params.title }),
    ...(params.description !== undefined && { description: params.description }),
    ...(params.status && { status: params.status as ParaItem["status"] }),
    updatedAt: new Date().toISOString(),
  };
  return mockParaItems[idx];
}

export async function archiveParaItem(id: UUID): Promise<ParaItem> {
  return updateParaItem({ id, status: "archived" });
}
