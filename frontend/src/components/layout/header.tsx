"use client";

import { Menu, MessageSquare, Search } from "lucide-react";
import { UserButton } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "./theme-toggle";
import { useUIStore } from "@/store/ui";

export function Header() {
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const toggleRAGPanel = useUIStore((s) => s.toggleRAGPanel);
  const isRAGPanelOpen = useUIStore((s) => s.isRAGPanelOpen);

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-4">
      {/* 좌측: 모바일 메뉴 + 검색 */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={toggleSidebar}
          aria-label="사이드바 토글"
        >
          <Menu className="h-4 w-4" />
        </Button>

        <div className="hidden items-center gap-2 rounded-md border border-input bg-muted/40 px-3 py-1.5 text-sm text-muted-foreground sm:flex">
          <Search className="h-3.5 w-3.5" />
          <span>검색...</span>
          <kbd className="ml-4 rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium">
            ⌘K
          </kbd>
        </div>
      </div>

      {/* 우측: RAG 토글 + 테마 + 유저 */}
      <div className="flex items-center gap-1">
        <Button
          variant={isRAGPanelOpen ? "secondary" : "ghost"}
          size="icon"
          onClick={toggleRAGPanel}
          aria-label="AI 어시스턴트 토글"
        >
          <MessageSquare className="h-4 w-4" />
        </Button>
        <ThemeToggle />
        <UserButton />
      </div>
    </header>
  );
}
