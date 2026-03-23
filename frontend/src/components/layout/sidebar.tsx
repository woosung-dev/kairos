"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Inbox,
  Target,
  Pin,
  BookOpen,
  Archive,
  CalendarCheck,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { DEFAULT_WORKSPACE_ID } from "@/lib/constants";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: number;
}

const inboxNav: NavItem = {
  label: "Inbox",
  href: "/inbox",
  icon: <Inbox className="h-4 w-4" />,
  badge: 5, // TODO: mock data에서 가져오기
};

const paraNav: NavItem[] = [
  {
    label: "Projects",
    href: `/workspace/${DEFAULT_WORKSPACE_ID}/projects`,
    icon: <Target className="h-4 w-4" />,
  },
  {
    label: "Areas",
    href: `/workspace/${DEFAULT_WORKSPACE_ID}/areas`,
    icon: <Pin className="h-4 w-4" />,
  },
  {
    label: "Resources",
    href: `/workspace/${DEFAULT_WORKSPACE_ID}/resources`,
    icon: <BookOpen className="h-4 w-4" />,
  },
  {
    label: "Archives",
    href: `/workspace/${DEFAULT_WORKSPACE_ID}/archives`,
    icon: <Archive className="h-4 w-4" />,
  },
];

const bottomNav: NavItem = {
  label: "Weekly Review",
  href: "/weekly-review",
  icon: <CalendarCheck className="h-4 w-4" />,
};

function NavLink({ item, isActive }: { item: NavItem; isActive: boolean }) {
  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        isActive
          ? "bg-accent text-accent-foreground"
          : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
      )}
    >
      {item.icon}
      <span className="flex-1">{item.label}</span>
      {item.badge != null && item.badge > 0 && (
        <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-[10px] font-semibold text-primary-foreground">
          {item.badge}
        </span>
      )}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full w-64 flex-col border-r border-border bg-sidebar">
      {/* 로고 */}
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <span className="text-sm font-bold">K</span>
        </div>
        <span className="text-lg font-semibold tracking-tight">Kairos</span>
      </div>

      <ScrollArea className="flex-1 px-3 py-3">
        {/* Inbox */}
        <NavLink item={inboxNav} isActive={pathname.startsWith("/inbox")} />

        <Separator className="my-3" />

        {/* PARA 카테고리 */}
        <div className="mb-2 flex items-center justify-between px-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            PARA
          </span>
          <Button variant="ghost" size="icon" className="h-5 w-5">
            <Plus className="h-3 w-3" />
          </Button>
        </div>
        <nav className="flex flex-col gap-0.5">
          {paraNav.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              isActive={pathname.startsWith(item.href)}
            />
          ))}
        </nav>

        <Separator className="my-3" />

        {/* 하단 네비 */}
        <NavLink
          item={bottomNav}
          isActive={pathname.startsWith("/weekly-review")}
        />
      </ScrollArea>
    </div>
  );
}
