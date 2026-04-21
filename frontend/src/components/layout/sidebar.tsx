"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useProjects } from "@/features/projects/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import {
  Archive,
  ChevronDown,
  ChevronRight,
  CheckSquare,
  FileText,
  Home,
  Inbox,
  MessageSquare,
  Paperclip,
  Plus,
  Settings,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  hasBadge?: boolean;
  requiresWrite?: boolean;
}

/* 네비 순서: 홈 → Inbox(배지) → 오늘 할 일 → 구분선 → 빠른 메모 → + 추가 */
const NAV_TOP: NavItem[] = [
  { href: "/", label: "홈", icon: Home },
  { href: "/inbox", label: "Inbox", icon: Inbox, hasBadge: true },
  { href: "/today", label: "오늘 할 일", icon: CheckSquare },
];

const NAV_BOTTOM: NavItem[] = [
  { href: "/notes", label: "빠른 메모", icon: FileText, requiresWrite: true },
  { href: "/new", label: "+ 추가", icon: Plus, requiresWrite: true },
];

interface SidebarProps {
  collapsed?: boolean;
}

/** 프로젝트 하위 소스 아이템 (mock — 추후 API 연동) */
interface SourceItem {
  id: string;
  type: "meeting" | "note" | "file";
  title: string;
  href: string;
}

const SOURCE_ICON = {
  meeting: MessageSquare,
  note: FileText,
  file: Paperclip,
} as const;

/**
 * 프로젝트 하위 소스(회의/노트) 트리 — P2 예정
 * 현재는 빈 배열로 유지하며, 추후 별도 hook으로 연동 예정
 */
const EMPTY_SOURCES: SourceItem[] = [];

export function Sidebar({ collapsed = false }: SidebarProps) {
  const pathname = usePathname();
  const [isArchiveOpen, setIsArchiveOpen] = useState(false);
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const hasRole = useWorkspaceStore((s) => s.hasRole);

  const toggleProject = (projectId: string) => {
    setExpandedProjects((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) {
        next.delete(projectId);
      } else {
        next.add(projectId);
      }
      return next;
    });
  };

  const { data: activeData } = useProjects(activeWorkspaceId ?? undefined, {
    status: "active",
  });
  const { data: archivedData } = useProjects(activeWorkspaceId ?? undefined, {
    status: "archived",
  });

  const projects = activeData?.items ?? [];
  const archivedProjects = archivedData?.items ?? [];

  const renderNavItem = (item: NavItem) => {
    const isActive = pathname === item.href;
    const Icon = item.icon;

    return (
      <Link
        key={item.href}
        href={item.href}
        className="flex items-center rounded text-sm transition-colors"
        style={{
          background: isActive ? "var(--surface-active)" : "transparent",
          color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
          borderRadius: "var(--radius-sm)",
          padding: collapsed ? "8px 0" : "8px 12px",
          justifyContent: collapsed ? "center" : "flex-start",
          gap: collapsed ? "0" : "12px",
        }}
        title={collapsed ? item.label : undefined}
      >
        <Icon size={18} />
        {!collapsed && (
          <span className="flex-1">{item.label}</span>
        )}
        {/* Inbox 배지 (하드코딩 placeholder — 추후 실제 카운트 연동) */}
        {!collapsed && item.hasBadge && (
          <span
            className="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-full)",
            }}
          >
            3
          </span>
        )}
      </Link>
    );
  };

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
        className="py-3 space-y-1"
        style={{ padding: collapsed ? "12px 4px" : "12px 8px" }}
      >
        {/* 상단 네비: 홈 / Inbox / 오늘 할 일 */}
        {NAV_TOP.map(renderNavItem)}

        {/* 구분선 */}
        <div
          className="my-2"
          style={{
            borderTop: "1px solid var(--border-subtle)",
            margin: collapsed ? "8px 4px" : "8px 12px",
          }}
        />

        {/* 하단 네비: 빠른 메모 / + 추가 (Viewer에게 숨김) */}
        {NAV_BOTTOM.filter(
          (item) => !item.requiresWrite || hasRole("member")
        ).map(renderNavItem)}
      </nav>

      {/* 프로젝트 리스트: collapsed에서 숨김 */}
      {!collapsed && (
        <div
          className="px-4 py-3 border-t flex-1"
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
                const isActive = pathname === `/projects/${project.id}` ||
                  pathname.startsWith(`/projects/${project.id}/`);
                const isExpanded = expandedProjects.has(project.id);
                const sources = EMPTY_SOURCES;

                return (
                  <div key={project.id}>
                    {/* 프로젝트 행: 펼침 토글 + 링크 */}
                    <div
                      className="flex items-center rounded text-xs transition-colors"
                      style={{
                        background: isActive ? "var(--surface-active)" : "transparent",
                        borderRadius: "var(--radius-sm)",
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => toggleProject(project.id)}
                        className="shrink-0 p-1 rounded transition-colors hover:opacity-80"
                        style={{ color: "var(--text-muted)" }}
                        aria-label={isExpanded ? "접기" : "펼치기"}
                      >
                        {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                      </button>
                      <Link
                        href={`/projects/${project.id}`}
                        className="flex-1 py-1.5 pr-2 truncate"
                        style={{
                          color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                        }}
                      >
                        {project.title}
                      </Link>
                      {sources.length > 0 && (
                        <span
                          className="shrink-0 mr-2 text-[10px]"
                          style={{ color: "var(--text-muted)" }}
                        >
                          {sources.length}
                        </span>
                      )}
                    </div>

                    {/* 하위 소스 트리 */}
                    {isExpanded && sources.length > 0 && (
                      <div className="ml-4 space-y-px">
                        {sources.map((item) => {
                          const ItemIcon = SOURCE_ICON[item.type];
                          const isItemActive = pathname === item.href;
                          return (
                            <Link
                              key={item.id}
                              href={item.href}
                              className="flex items-center gap-1.5 px-2 py-1 rounded text-[11px] truncate transition-colors"
                              style={{
                                background: isItemActive ? "var(--surface-active)" : "transparent",
                                color: isItemActive ? "var(--text-primary)" : "var(--text-muted)",
                                borderRadius: "var(--radius-sm)",
                              }}
                            >
                              <ItemIcon size={12} className="shrink-0" />
                              <span className="truncate">{item.title}</span>
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Archive 섹션 (접이식) */}
          {archivedProjects.length > 0 && (
            <div className="mt-4">
              <button
                onClick={() => setIsArchiveOpen(!isArchiveOpen)}
                className="flex items-center gap-1.5 w-full text-xs font-medium uppercase tracking-wider mb-1 transition-colors hover:opacity-80"
                style={{ color: "var(--text-muted)" }}
              >
                {isArchiveOpen ? (
                  <ChevronDown size={12} />
                ) : (
                  <ChevronRight size={12} />
                )}
                <Archive size={12} />
                <span>Archive</span>
                <span
                  className="ml-auto text-[10px]"
                  style={{ color: "var(--text-muted)" }}
                >
                  {archivedProjects.length}
                </span>
              </button>
              {isArchiveOpen && (
                <div className="space-y-0.5">
                  {archivedProjects.map((project) => {
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
                            : "var(--text-muted)",
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
        </div>
      )}

      {/* 설정 링크 — 하단 고정 */}
      <div
        className="mt-auto pt-2 border-t"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <Link
          href="/settings"
          className="flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors duration-150"
          style={{
            color: pathname === "/settings" ? "var(--text-primary)" : "var(--text-muted)",
            background: pathname === "/settings" ? "var(--surface-active)" : "transparent",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <Settings size={16} />
          {!collapsed && <span>설정</span>}
        </Link>
      </div>
    </aside>
  );
}
