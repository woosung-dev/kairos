"use client";

// 홈 피드 비즈니스 로직 — inbox count + due 액션 + 최근 활동 집계
import { useMemo } from "react";

import { useInbox } from "@/features/inbox/hooks";
import { useActionItems } from "@/features/actions/hooks";
import { useMeetings } from "@/features/meetings/hooks";
import { useNotes } from "@/features/notes/hooks";
import { useProjects } from "@/features/projects/hooks";
import type { ActionItem } from "@/features/actions/types";
import { formatRelativeTime } from "@/lib/format-relative-time";

export interface ActionDueEntry {
  id: string;
  title: string;
  projectName: string;
}

export type ActivityType = "meeting" | "note" | "action";

export interface RecentActivity {
  id: string;
  type: ActivityType;
  title: string;
  /** 정렬용 원본 ISO 타임스탬프 */
  rawTime: string;
  /** 표시용 상대 시간 */
  timestamp: string;
}

const RECENT_LIMIT = 5;
const ACTIONS_LIMIT = 5;

export interface ActivityFeed {
  inboxCount: number;
  actionsDue: ActionDueEntry[];
  activities: RecentActivity[];
  isReady: boolean;
  hasContent: boolean;
}

/** 홈 피드 종합 데이터 — 5개 React Query + 3개 useMemo 집계. */
export function useActivityFeed(workspaceId: string | undefined): ActivityFeed {
  const inboxQuery = useInbox(workspaceId);
  const actionsQuery = useActionItems(workspaceId);
  const meetingsQuery = useMeetings(workspaceId);
  const notesQuery = useNotes(workspaceId);
  const projectsQuery = useProjects(workspaceId);

  const inboxCount = useMemo(() => {
    const items = inboxQuery.data?.items ?? [];
    return items.filter((it) => !it.isProcessed).length;
  }, [inboxQuery.data]);

  const actionsDue = useMemo<ActionDueEntry[]>(() => {
    const actions = actionsQuery.data?.items ?? [];
    const projects = projectsQuery.data?.items ?? [];
    const projectNameById = new Map(projects.map((p) => [p.id, p.title]));

    return actions
      .filter((a: ActionItem) => a.status === "todo")
      .slice(0, ACTIONS_LIMIT)
      .map((a) => ({
        id: a.id,
        title: a.title,
        projectName: a.projectId ? projectNameById.get(a.projectId) ?? "—" : "—",
      }));
  }, [actionsQuery.data, projectsQuery.data]);

  const activities = useMemo<RecentActivity[]>(() => {
    const entries: RecentActivity[] = [];

    for (const m of meetingsQuery.data?.items ?? []) {
      const raw = m.updatedAt ?? m.createdAt;
      entries.push({
        id: m.id,
        type: "meeting",
        title: m.title,
        rawTime: raw,
        timestamp: formatRelativeTime(raw),
      });
    }
    for (const n of notesQuery.data?.items ?? []) {
      entries.push({
        id: n.id,
        type: "note",
        title: n.title || "(제목 없음)",
        rawTime: n.updatedAt,
        timestamp: formatRelativeTime(n.updatedAt),
      });
    }
    for (const a of actionsQuery.data?.items ?? []) {
      entries.push({
        id: a.id,
        type: "action",
        title: a.title,
        rawTime: a.updatedAt,
        timestamp: formatRelativeTime(a.updatedAt),
      });
    }

    return entries
      .sort((x, y) => new Date(y.rawTime).getTime() - new Date(x.rawTime).getTime())
      .slice(0, RECENT_LIMIT);
  }, [meetingsQuery.data, notesQuery.data, actionsQuery.data]);

  const isReady =
    !!workspaceId &&
    !inboxQuery.isLoading &&
    !actionsQuery.isLoading &&
    !meetingsQuery.isLoading &&
    !notesQuery.isLoading;

  const hasContent =
    inboxCount > 0 ||
    actionsDue.length > 0 ||
    activities.length > 0 ||
    (meetingsQuery.data?.total ?? 0) > 0 ||
    (notesQuery.data?.total ?? 0) > 0;

  return { inboxCount, actionsDue, activities, isReady, hasContent };
}
