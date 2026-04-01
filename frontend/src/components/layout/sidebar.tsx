"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "홈", icon: "🏠" },
  { href: "/inbox", label: "Inbox", icon: "📥" },
  { href: "/new", label: "콘텐츠 추가", icon: "➕" },
  { href: "/search", label: "검색", icon: "🔍" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="flex flex-col h-full w-[220px] shrink-0 border-r overflow-y-auto"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
      }}
    >
      {/* 로고 */}
      <div className="px-4 py-4 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        <Link href="/" className="text-lg font-bold" style={{ fontFamily: "var(--font-display)", color: "var(--accent)" }}>
          Kairos
        </Link>
      </div>

      {/* 네비게이션 */}
      <nav className="flex-1 px-2 py-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors"
              style={{
                background: isActive ? "var(--surface-active)" : "transparent",
                color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* 프로젝트 리스트 */}
      <div className="px-4 py-3 border-t" style={{ borderColor: "var(--border-subtle)" }}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            프로젝트
          </span>
        </div>
        <p className="text-xs py-4 text-center" style={{ color: "var(--text-muted)" }}>
          프로젝트 없음
        </p>
      </div>
    </aside>
  );
}
