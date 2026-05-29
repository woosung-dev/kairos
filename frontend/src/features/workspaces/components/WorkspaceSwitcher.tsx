// 워크스페이스 전환 dropdown — BL-014 (Sprint 17 workspace-switcher-ui). 좌측 topbar에서 호출.
"use client";

import { useMemo, useState } from "react";
import { ChevronDown, Plus, Check } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { useWorkspaces, useCreateWorkspace } from "../hooks";
import { useWorkspaceStore } from "../store";
import { WorkspaceTypeBadge } from "./WorkspaceTypeBadge";
import { inferWorkspaceType, buildDisambiguationMap } from "../utils";

interface WorkspaceSwitcherProps {
  memberCount?: number;
}

export function WorkspaceSwitcher({ memberCount }: WorkspaceSwitcherProps) {
  const { data: workspaces } = useWorkspaces();
  const activeWid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const setActiveWorkspaceId = useWorkspaceStore((s) => s.setActiveWorkspaceId);
  const queryClient = useQueryClient();
  const { mutate: createWorkspace, isPending: isCreating } = useCreateWorkspace();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");

  const active = workspaces?.find((w) => w.id === activeWid);
  const activeType = active ? inferWorkspaceType(active) : "team";

  const suffixMap = useMemo(
    () => buildDisambiguationMap(workspaces ?? []),
    [workspaces],
  );
  const activeSuffix = active ? suffixMap.get(active.id) : undefined;

  // Sprint 23 D1 fix: queryClient.clear() → predicate invalidate (ws list 보존) + router.refresh() 제거.
  // queryClient.clear() 가 workspaces.list 까지 invalidate → user 의 ws list 잠시 사라짐 + race.
  // workspaces.list 만 보존 + 나머지 wid-scoped query 만 invalidate.
  const invalidateWorkspaceScopedQueries = () => {
    queryClient.invalidateQueries({
      predicate: (query) => {
        const key = query.queryKey;
        // workspaces.list (`["workspaces", "list"]`) 만 보존 — 사용자 ws list 유지
        return !(
          Array.isArray(key) &&
          key[0] === "workspaces" &&
          key[1] === "list"
        );
      },
    });
  };

  const handleSwitch = (wid: string) => {
    if (wid === activeWid) return;
    setActiveWorkspaceId(wid);
    invalidateWorkspaceScopedQueries();
    // router.refresh() 제거: invalidateQueries 만으로 wid 의존 컴포넌트 모두 새 데이터.
    // Sprint 23 D1 진단 결과 — router.refresh() 가 RSC 재페치를 추가 트리거 → race.
  };

  const handleCreate = () => {
    const name = newName.trim();
    if (!name) return;
    createWorkspace(name, {
      onSuccess: (ws) => {
        setActiveWorkspaceId(ws.id);
        invalidateWorkspaceScopedQueries();
        setNewName("");
        setIsCreateOpen(false);
      },
    });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="flex items-center gap-2 px-2 py-1 rounded-md transition-colors hover:opacity-80 cursor-pointer outline-none"
        style={{
          background: "transparent",
          color: "var(--text-secondary)",
        }}
        aria-label="워크스페이스 전환"
      >
        <span className="text-sm">
          {active?.name ?? "Kairos"}
          {activeSuffix && (
            <span className="ml-1" style={{ color: "var(--text-muted)" }}>
              {activeSuffix}
            </span>
          )}
        </span>
        {active && (
          <WorkspaceTypeBadge workspace={active} size="sm" />
        )}
        {activeType === "team" && typeof memberCount === "number" && memberCount > 0 && (
          <span
            className="text-xs"
            style={{ color: "var(--text-muted)" }}
          >
            {memberCount}
          </span>
        )}
        <ChevronDown size={12} style={{ color: "var(--text-muted)" }} />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" side="bottom" sideOffset={6} className="w-[260px]">
        <div className="px-3 py-2">
          <span
            className="text-caption uppercase tracking-wide"
            style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
          >
            워크스페이스
          </span>
        </div>
        <DropdownMenuSeparator />

        {(workspaces ?? []).map((ws) => {
          const isActive = ws.id === activeWid;
          const suffix = suffixMap.get(ws.id);
          return (
            <DropdownMenuItem
              key={ws.id}
              className="px-3 py-2 cursor-pointer flex items-center gap-2"
              onClick={() => handleSwitch(ws.id)}
              title={suffix ? `${ws.name} (생성: ${ws.createdAt.slice(0, 10)})` : ws.name}
            >
              <WorkspaceTypeBadge workspace={ws} size="sm" />
              <span
                className="text-sm truncate flex-1"
                style={{ color: "var(--text-primary)" }}
              >
                {ws.name}
                {suffix && (
                  <span className="ml-1" style={{ color: "var(--text-muted)" }}>
                    {suffix}
                  </span>
                )}
              </span>
              {isActive && (
                <Check size={14} style={{ color: "var(--accent)" }} />
              )}
            </DropdownMenuItem>
          );
        })}

        <DropdownMenuSeparator />

        {!isCreateOpen ? (
          <DropdownMenuItem
            className="px-3 py-2 cursor-pointer"
            closeOnClick={false}
            onClick={(e) => {
              e.preventDefault();
              setIsCreateOpen(true);
            }}
          >
            <Plus size={14} />
            <span>새 워크스페이스</span>
          </DropdownMenuItem>
        ) : (
          <div className="px-3 py-2 flex flex-col gap-2">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="이름 입력"
              maxLength={60}
              autoFocus
              className="px-2 py-1 rounded text-sm outline-none"
              style={{
                background: "var(--surface-hover)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-subtle)",
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleCreate();
                } else if (e.key === "Escape") {
                  setIsCreateOpen(false);
                  setNewName("");
                }
              }}
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setIsCreateOpen(false);
                  setNewName("");
                }}
                className="px-2 py-1 text-xs rounded"
                style={{ color: "var(--text-muted)" }}
              >
                취소
              </button>
              <button
                onClick={handleCreate}
                disabled={isCreating || !newName.trim()}
                className="px-2 py-1 text-xs rounded disabled:opacity-50"
                style={{
                  background: "var(--accent)",
                  color: "var(--accent-foreground, white)",
                }}
              >
                {isCreating ? "생성중..." : "생성"}
              </button>
            </div>
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
