"use client";

import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <div className="flex items-center justify-between w-full">
        <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
          테마
        </span>
        <div className="w-[52px] h-[28px] rounded-full" style={{ background: "var(--surface-active)" }} />
      </div>
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="flex items-center justify-between w-full group"
      aria-label={isDark ? "라이트 모드로 전환" : "다크 모드로 전환"}
    >
      <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
        {isDark ? "다크 모드" : "라이트 모드"}
      </span>
      {/* 토글 스위치 */}
      <div
        className="relative w-[52px] h-[28px] rounded-full p-[3px] transition-colors duration-200"
        style={{
          background: isDark ? "var(--accent)" : "var(--border)",
        }}
      >
        <div
          className="flex items-center justify-center w-[22px] h-[22px] rounded-full transition-transform duration-200 shadow-sm"
          style={{
            background: "var(--surface)",
            transform: isDark ? "translateX(24px)" : "translateX(0px)",
          }}
        >
          {isDark ? (
            <Moon size={12} style={{ color: "var(--accent)" }} />
          ) : (
            <Sun size={12} style={{ color: "var(--text-secondary)" }} />
          )}
        </div>
      </div>
    </button>
  );
}
