// React Query key factory 중앙 레지스트리 — 15 feature 의 캐시 키 형태를 한 곳에서 관리 (PR-3 c9)
// 키 배열 구조는 각 feature api.ts 에서 형태 불변으로 이동했다. 변경 시 캐시 무효화/교차
// invalidate 가 깨지므로 __tests__/query-keys.test.ts 스냅샷으로 회귀를 가드한다.
// param 타입은 feature 소유를 유지 — import type 은 컴파일 시 제거되어 런타임 순환 없음.

import type { FetchInboxParams } from "@/features/inbox/api";
import type { FetchProjectsParams } from "@/features/projects/api";

export const workspaceKeys = {
  all: ["workspaces"] as const,
  list: () => [...workspaceKeys.all, "list"] as const,
  detail: (id: string) => [...workspaceKeys.all, "detail", id] as const,
};

// Sprint 23 D3 fix: queryKey 에 params 포함 → cache 격리.
// 이전: useInbox(wid) 와 useInbox(wid, { isProcessed: false }) 가 같은 cache 사용 → 마지막 호출자의 params 가 실 fetch 결정 → 다른 callsite 의 의도 손상.
// 이후: 각 (wid, params) 조합이 별도 cache entry. invalidate 시 inboxKeys.byWorkspace(wid) prefix 로 일괄 무효화.
export const inboxKeys = {
  all: ["inbox"] as const,
  byWorkspace: (wid: string) => [...inboxKeys.all, "list", wid] as const,
  list: (wid: string, params?: FetchInboxParams) =>
    [...inboxKeys.byWorkspace(wid), params ?? {}] as const,
};

export const noteKeys = {
  all: ["notes"] as const,
  list: (wid: string, projectId?: string) =>
    [...noteKeys.all, "list", wid, projectId ?? "all"] as const,
  detail: (wid: string, id: string) =>
    [...noteKeys.all, "detail", wid, id] as const,
};

export const meetingKeys = {
  all: ["meetings"] as const,
  list: (wid: string, projectId?: string) =>
    [...meetingKeys.all, "list", wid, projectId ?? "all"] as const,
  detail: (wid: string, id: string) =>
    [...meetingKeys.all, "detail", wid, id] as const,
  status: (wid: string, id: string) =>
    [...meetingKeys.all, "status", wid, id] as const,
};

export const actionKeys = {
  all: ["actions"] as const,
  list: (wid: string) => [...actionKeys.all, "list", wid] as const,
};

export const projectKeys = {
  all: ["projects"] as const,
  // S28b RQ-KEY-COLLISION fix: params(status 등) 를 키에 포함 — 안 그러면
  // 사이드바의 active/archived useProjects 두 호출이 같은 키로 충돌(교차오염).
  // invalidate 는 list(wid) prefix 로 모든 param 변형 매칭.
  list: (wid: string, params?: FetchProjectsParams) =>
    params
      ? ([...projectKeys.all, "list", wid, params] as const)
      : ([...projectKeys.all, "list", wid] as const),
  detail: (wid: string, id: string) =>
    [...projectKeys.all, "detail", wid, id] as const,
  members: (wid: string, id: string) =>
    [...projectKeys.all, "members", wid, id] as const,
};

export const memberKeys = {
  all: ["members"] as const,
  list: (wid: string) => [...memberKeys.all, "list", wid] as const,
};

export const inviteKeys = {
  all: ["invites"] as const,
  list: (wid: string) => [...inviteKeys.all, "list", wid] as const,
  info: (code: string) => [...inviteKeys.all, "info", code] as const,
};

export const memoryKeys = {
  all: ["memory"] as const,
  detail: (wid: string, mid: string) =>
    [...memoryKeys.all, "detail", wid, mid] as const,
  recall: (wid: string, q: string) =>
    [...memoryKeys.all, "recall", wid, q] as const,
};

export const ragKeys = {
  all: ["rag"] as const,
};

export const auditKeys = {
  all: ["audit"] as const,
  promotions: (wid: string, itemType: string | null) =>
    [...auditKeys.all, "promotions", wid, itemType ?? "all"] as const,
};

export const onboardingKeys = {
  all: ["onboarding"] as const,
  status: (wid: string | null) => [...onboardingKeys.all, "status", wid] as const,
};
