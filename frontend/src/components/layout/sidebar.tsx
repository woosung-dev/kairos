"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useProjects } from "@/features/projects/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { Home, Inbox, Plus, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "홈", icon: Home },
  { href: "/inbox", label: "Inbox", icon: Inbox },
  { href: "/new", label: "콘텐츠 추가", icon: Plus },
  { href: "/search", label: "검색", icon: Search },
];

interface SidebarProps {
  collapsed?: boolean;
}

export function Sidebar({ collapsed = false }: SidebarProps) {
  const pathname = usePathname();
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const { data } = useProjects(activeWorkspaceId ?? undefined, {
    status: "active",
  });

  const projects = data?.items ?? [];

  return (
    <aside
      className="flex flex-col h-full shrink-0 border-r overflow-y-auto transition-[width] duration-200"
      style={{
        width: collapsed
          ? "var(--sidebar-collapsed-width)"
          : "var(--sidebar-width)",
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
      }}
    >
      {/* 로고 */}
      <div
        className="border-b flex items-center"
        style={{
          borderColor: "var(--border-subtle)",
          padding: collapsed ? "16px 8px" : "16px",
          justifyContent: collapsed ? "center" : "flex-start",
        }}
      >
        <Link
          href="/"
          className="text-lg font-bold"
          style={{
            fontFamily: "var(--font-display)",
            color: "var(--accent)",
          }}
          title="Kairos"
        >
          {collapsed ? "K" : "Kairos"}
        </Link>
      </div>

      {/* 네비게이션 */}
      <nav
        className="flex-1 py-3 space-y-1"
        style={{ padding: collapsed ? "12px 4px" : "12px 8px" }}
      >
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center rounded text-sm transition-colors"
              style={{
                background: isActive ? "var(--surface-active)" : "transparent",
                color: isActive
                  ? "var(--text-primary)"
                  : "var(--text-secondary)",
                borderRadius: "var(--radius-sm)",
                padding: collapsed ? "8px 0" : "8px 12px",
                justifyContent: collapsed ? "center" : "flex-start",
                gap: collapsed ? "0" : "12px",
              }}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={18} />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* 프로젝트 리스트: collapsed에서 숨김 */}
      {!collapsed && (
        <div
          className="px-4 py-3 border-t"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <div className="flex items-center justify-between mb-2">
            <span
              className="text-xs font-medium uppercase tracking-wider"
              style={{ color: "var(--text-muted)" }}
            >
              프로젝트
            </span>
          </div>
          {projects.length === 0 ? (
            <p
              className="text-xs py-4 text-center"
              style={{ color: "var(--text-muted)" }}
            >
              프로젝트 없음
            </p>
          ) : (
            <div className="space-y-0.5">
              {projects.map((project) => {
                const isActive = pathname === `/projects/${project.id}`;
                return (
                  <Link
                    key={project.id}
                    href={`/projects/${project.id}`}
                    className="block px-2 py-1.5 rounded text-xs truncate transition-colors"
                    style={{
                      background: isActive
                        ? "var(--surface-active)"
                        : "transparent",
                      color: isActive
                        ? "var(--text-primary)"
                        : "var(--text-secondary)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  >
                    {project.title}
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
