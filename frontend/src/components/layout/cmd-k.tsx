"use client";

import { useEffect, useState } from "react";
import { useUIStore } from "@/store/ui";

const CMD_GROUPS = [
  {
    label: "검색",
    items: [
      { icon: "🔍", label: "지식 검색", shortcut: "⌘K" },
      { icon: "💬", label: "RAG 질문", shortcut: "⌘J" },
    ],
  },
  {
    label: "이동",
    items: [
      { icon: "📥", label: "Inbox", shortcut: "G I" },
      { icon: "📁", label: "프로젝트", shortcut: "G P" },
      { icon: "🔍", label: "검색 페이지", shortcut: "G S" },
    ],
  },
  {
    label: "생성",
    items: [
      { icon: "➕", label: "콘텐츠 추가", shortcut: "C" },
    ],
  },
];

export function CmdK() {
  const { cmdKOpen, toggleCmdK } = useUIStore();
  const [search, setSearch] = useState("");

  // 키보드 단축키
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        toggleCmdK();
      }
      if (e.key === "Escape" && cmdKOpen) {
        toggleCmdK();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [cmdKOpen, toggleCmdK]);

  if (!cmdKOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      {/* 오버레이 */}
      <div
        className="absolute inset-0"
        style={{ background: "rgba(0,0,0,0.5)" }}
        onClick={toggleCmdK}
      />

      {/* 모달 */}
      <div
        className="relative w-full max-w-[520px] rounded-lg border shadow-2xl overflow-hidden"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        {/* 검색 입력 */}
        <div className="px-4 py-3 border-b" style={{ borderColor: "var(--border-subtle)" }}>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="검색하거나 명령 입력..."
            className="w-full bg-transparent text-sm outline-none"
            style={{ color: "var(--text-primary)" }}
            autoFocus
          />
        </div>

        {/* 커맨드 목록 */}
        <div className="max-h-[300px] overflow-y-auto py-2">
          {CMD_GROUPS.map((group) => (
            <div key={group.label}>
              <div
                className="px-4 py-1.5 text-xs font-medium uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
              >
                {group.label}
              </div>
              {group.items.map((item) => (
                <button
                  key={item.label}
                  className="flex items-center justify-between w-full px-4 py-2 text-sm transition-colors"
                  style={{ color: "var(--text-secondary)" }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.background = "var(--surface-hover)";
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.background = "transparent";
                  }}
                >
                  <div className="flex items-center gap-3">
                    <span>{item.icon}</span>
                    <span>{item.label}</span>
                  </div>
                  <kbd
                    className="text-[10px] px-1.5 py-0.5 rounded"
                    style={{
                      background: "var(--surface-active)",
                      color: "var(--text-muted)",
                      fontFamily: "var(--font-mono)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  >
                    {item.shortcut}
                  </kbd>
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
