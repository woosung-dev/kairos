"use client";

import { Search, Users, LogOut, Settings } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useUIStore } from "@/store/ui";
import { useMembers } from "@/features/members/hooks";
import { useWorkspaces } from "@/features/workspaces/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { useClerk, useUser } from "@clerk/nextjs";
import { ThemeToggle } from "./theme-toggle";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

export function Header() {
  const { toggleSidebar, toggleRagOverlay } = useUIStore();
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const setActiveWorkspaceId = useWorkspaceStore((s) => s.setActiveWorkspaceId);
  // localStorage 의 stale wid 로 인한 404 fetch 차단 (BUG-H01)
  const { data: workspaces } = useWorkspaces();
  const isValidWid = !!wid && !!workspaces?.some((w) => w.id === wid);
  const { data: members } = useMembers(isValidWid ? wid! : undefined);
  const queryClient = useQueryClient();
  const { signOut } = useClerk();
  const { user } = useUser();

  const displayName = user?.fullName ?? user?.firstName ?? "User";
  const email = user?.primaryEmailAddress?.emailAddress ?? "";
  const avatarInitial = (user?.firstName?.[0] ?? "U").toUpperCase();

  return (
    <header
      className="flex items-center justify-between px-4 py-2 border-b shrink-0 gap-3"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
      }}
    >
      {/* 좌측: 사이드바 토글 + breadcrumb */}
      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded transition-colors hover:opacity-80"
          style={{ color: "var(--text-secondary)" }}
          aria-label="사이드바 토글"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <rect x="2" y="3" width="12" height="1.5" rx="0.5" />
            <rect x="2" y="7.25" width="12" height="1.5" rx="0.5" />
            <rect x="2" y="11.5" width="12" height="1.5" rx="0.5" />
          </svg>
        </button>
        <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
          Kairos
        </span>
        {members && members.length > 0 && (
          <span
            className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full"
            style={{
              background: "var(--surface-active)",
              color: "var(--text-muted)",
            }}
          >
            <Users size={10} />
            {members.length}
          </span>
        )}
      </div>

      {/* 중앙: RAG 검색바 스타일 (클릭 시 RAG 오버레이 열기) */}
      <button
        onClick={toggleRagOverlay}
        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm flex-1 max-w-md mx-auto transition-colors hover:opacity-90"
        style={{
          background: "var(--surface-hover)",
          color: "var(--text-muted)",
          borderRadius: "var(--radius-lg)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <Search size={14} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
        <span className="truncate">팀 지식 검색...</span>
        <kbd
          className="ml-auto px-1.5 py-0.5 rounded text-[10px] shrink-0"
          style={{
            background: "var(--surface-active)",
            color: "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            fontFamily: "var(--font-mono)",
          }}
        >
          ⌘K
        </kbd>
      </button>

      {/* 우측: 유저 드롭다운 메뉴 */}
      <div className="flex items-center gap-2 shrink-0">
        <DropdownMenu>
          <DropdownMenuTrigger
            className="flex items-center gap-2 p-1 rounded-lg transition-colors cursor-pointer outline-none"
            style={{ WebkitTapHighlightColor: "transparent" }}
          >
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-opacity hover:opacity-80"
              style={{
                background: "var(--accent-subtle)",
                color: "var(--accent)",
                borderRadius: "var(--radius-full)",
              }}
            >
              {avatarInitial}
            </div>
          </DropdownMenuTrigger>

          <DropdownMenuContent
            align="end"
            side="bottom"
            sideOffset={8}
            className="w-[240px]"
          >
            {/* 유저 정보 */}
            <div className="px-3 py-2.5">
              <div className="flex flex-col gap-0.5">
                <span
                  className="text-sm font-medium truncate"
                  style={{ color: "var(--text-primary)" }}
                >
                  {displayName}
                </span>
                {email && (
                  <span
                    className="text-xs truncate"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {email}
                  </span>
                )}
              </div>
            </div>

            <DropdownMenuSeparator />

            {/* 테마 토글 */}
            <div className="px-3 py-2">
              <ThemeToggle />
            </div>

            <DropdownMenuSeparator />

            {/* 설정 */}
            <DropdownMenuItem
              className="px-3 py-2 cursor-pointer"
              onSelect={() => {
                if (wid) {
                  window.location.href = `/workspace/${wid}/settings`;
                }
              }}
            >
              <Settings size={14} />
              <span>설정</span>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            {/* 로그아웃 — 워크스페이스 캐시/Zustand 정리 후 sign-out (BUG-H01) */}
            <DropdownMenuItem
              variant="destructive"
              className="px-3 py-2 cursor-pointer"
              onSelect={async () => {
                queryClient.clear();
                setActiveWorkspaceId("");
                await signOut({ redirectUrl: "/" });
              }}
            >
              <LogOut size={14} />
              <span>로그아웃</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
