"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, FolderOpen, Plus, Inbox, FileText } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  href: string;
  icon: LucideIcon;
  label: string;
  isAccent?: boolean;
}

// Sprint 14 T-11: "검색" 자리에 "빠른 메모" 진입점 (모바일 사용 빈도 높음).
// 검색은 ⌘K + 헤더 검색바로 접근 (데스크톱과 동일 IA).
const NAV_ITEMS: NavItem[] = [
  { href: "/", icon: Home, label: "홈" },
  { href: "/projects", icon: FolderOpen, label: "프로젝트" },
  { href: "/new", icon: Plus, label: "추가", isAccent: true },
  { href: "/inbox", icon: Inbox, label: "Inbox" },
  { href: "/notes", icon: FileText, label: "메모" },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 flex items-center justify-around z-50"
      style={{
        height: "var(--bottom-nav-height)",
        background: "var(--surface)",
        borderTop: "1px solid var(--border)",
      }}
    >
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href;
        const Icon = item.icon;

        return (
          <Link
            key={item.href}
            href={item.href}
            className="flex flex-col items-center gap-0.5 p-2"
          >
            <Icon
              size={item.isAccent ? 24 : 20}
              style={{
                color: item.isAccent
                  ? "var(--accent)"
                  : isActive
                    ? "var(--text-primary)"
                    : "var(--text-muted)",
              }}
            />
            <span
              className="text-micro"
              style={{
                color: isActive ? "var(--text-primary)" : "var(--text-muted)",
              }}
            >
              {item.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
