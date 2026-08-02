"use client";

import { Search, LogOut, Settings } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useUIStore } from "@/store/ui";
import { useMembers } from "@/features/members/hooks";
import { useIsValidWorkspaceId } from "@/features/workspaces/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { WorkspaceSwitcher } from "@/features/workspaces/components/WorkspaceSwitcher";
import { useClerk, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
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
  // localStorage 의 stale wid 로 인한 404 fetch 차단 (BUG-H01)
  const isValidWid = useIsValidWorkspaceId(wid ?? undefined);
  const { data: members } = useMembers(isValidWid ? wid! : undefined);
  const queryClient = useQueryClient();
  const { signOut } = useClerk();
  const { user } = useUser();
  const router = useRouter();

  const displayName = user?.fullName ?? user?.firstName ?? "User";
  const email = user?.primaryEmailAddress?.emailAddress ?? "";
  const avatarInitial = (user?.firstName?.[0] ?? "U").toUpperCase();

  return (
    <header
      className="flex items-center justify-between px-2 md:px-4 py-2 border-b shrink-0 gap-2 md:gap-3"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
      }}
    >
      {/* 좌측: 사이드바 토글 + breadcrumb. Sprint 24 Wave 2 T-MOBILE-HEADER: 모바일에서 min-w-0 + shrink 허용으로 우측 영역 보호 */}
      <div className="flex items-center gap-2 md:gap-3 min-w-0 shrink">
        {/* Sprint 14 T-10: 모바일에서 사이드바 토글 숨김 (BottomNav 1차 내비). md(768)+에서만 노출. */}
        <button
          onClick={toggleSidebar}
          className="hidden md:inline-flex p-1.5 rounded transition-colors hover:opacity-80"
          style={{ color: "var(--text-secondary)" }}
          aria-label="사이드바 토글"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <rect x="2" y="3" width="12" height="1.5" rx="0.5" />
            <rect x="2" y="7.25" width="12" height="1.5" rx="0.5" />
            <rect x="2" y="11.5" width="12" height="1.5" rx="0.5" />
          </svg>
        </button>
        <WorkspaceSwitcher memberCount={members?.length} />
      </div>

      {/* 중앙: RAG 검색바 스타일 (클릭 시 RAG 오버레이 열기). Sprint 24 Wave 2 T-MOBILE-HEADER: 모바일 width 축소 + label 단축 (BUG-MOBILE-001 우측 avatar 잘림 fix) */}
      <button
        onClick={toggleRagOverlay}
        className="flex items-center gap-1.5 md:gap-2 px-2 md:px-4 py-2 rounded-lg text-sm flex-1 min-w-0 max-w-[160px] md:max-w-md mx-auto transition-colors hover:opacity-90"
        style={{
          background: "var(--surface-hover)",
          color: "var(--text-muted)",
          borderRadius: "var(--radius-lg)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <Search size={14} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
        <span className="truncate hidden md:inline">팀 지식 검색...</span>
        <span className="truncate md:hidden">검색</span>
        <kbd
          className="ml-auto px-1.5 py-0.5 rounded text-micro shrink-0"
          style={{
            background: "var(--surface-active)",
            color: "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            // ⌘(U+2318) 가 Geist Mono 미포함 → system-ui per-glyph fallback (UX-CMDK-GLYPH)
            fontFamily: "var(--font-mono), system-ui, sans-serif",
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
            aria-label="계정 메뉴"
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
              onClick={() => {
                // P1 fix (2026-06-01): 존재하지 않던 /workspace/{wid}/settings (404 + full reload)
                // → SPA 클라이언트 네비게이션으로 /settings (사이드바 설정 링크와 동일 타깃).
                router.push("/settings");
              }}
            >
              <Settings size={14} />
              <span>설정</span>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            {/* 로그아웃 — query cache 정리 후 sign-out. activeWorkspaceId 초기화는 panel-layout
                self-heal 과 경합해 즉시 되채워지므로 계정 전환 방어는 ensureOwner 가 담당한다.
                base-ui Menu.Item 은 onClick 사용 — onSelect (Radix API) 는 미동작. */}
            <DropdownMenuItem
              variant="destructive"
              className="px-3 py-2 cursor-pointer"
              onClick={async () => {
                queryClient.clear();
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
