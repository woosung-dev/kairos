"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useUIStore } from "@/store/ui";
import { useRagStream } from "@/features/rag/hooks";

const CMD_GROUPS = [
  {
    label: "검색",
    items: [
      { icon: "🔍", label: "지식 검색", shortcut: "⌘K", action: "focus" },
      { icon: "💬", label: "AI 검색", shortcut: "?", action: "rag-mode" },
    ],
  },
  {
    label: "이동",
    items: [
      { icon: "📥", label: "Inbox", shortcut: "G I", action: "navigate:/inbox" },
      { icon: "📁", label: "프로젝트", shortcut: "G P", action: "navigate:/" },
      { icon: "📝", label: "노트", shortcut: "G N", action: "navigate:/notes" },
      { icon: "🔍", label: "검색 페이지", shortcut: "G S", action: "navigate:/search" },
    ],
  },
  {
    label: "생성",
    items: [
      { icon: "➕", label: "콘텐츠 추가", shortcut: "C", action: "navigate:/new" },
    ],
  },
];

export function CmdK() {
  const { cmdKOpen, toggleCmdK, toggleRagOverlay } = useUIStore();
  const [search, setSearch] = useState("");
  const [isRagMode, setIsRagMode] = useState(false);
  const { ask } = useRagStream();
  const router = useRouter();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        toggleCmdK();
      }
      if (e.key === "Escape" && cmdKOpen) {
        toggleCmdK();
        setSearch("");
        setIsRagMode(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [cmdKOpen, toggleCmdK]);

  // ? 접두사로 RAG 모드 자동 전환
  useEffect(() => {
    if (search.startsWith("?")) {
      setIsRagMode(true);
    }
  }, [search]);

  const handleSubmit = () => {
    if (!search.trim()) return;

    if (isRagMode || search.startsWith("?")) {
      const question = search.startsWith("?") ? search.slice(1).trim() : search.trim();
      if (question) {
        ask(question);
        toggleRagOverlay();
      }
    }

    toggleCmdK();
    setSearch("");
    setIsRagMode(false);
  };

  const handleItemClick = (action: string) => {
    if (action === "rag-mode") {
      setIsRagMode(true);
      setSearch("?");
      return;
    }
    if (action.startsWith("navigate:")) {
      router.push(action.replace("navigate:", ""));
    }
    toggleCmdK();
    setSearch("");
  };

  if (!cmdKOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      <div
        className="absolute inset-0"
        style={{ background: "rgba(0,0,0,0.5)" }}
        onClick={() => {
          toggleCmdK();
          setSearch("");
          setIsRagMode(false);
        }}
      />

      <div
        className="relative w-full max-w-[520px] rounded-lg border shadow-2xl overflow-hidden"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <div className="px-4 py-3 border-b flex items-center gap-2" style={{ borderColor: "var(--border-subtle)" }}>
          {isRagMode && (
            <span
              className="px-1.5 py-0.5 rounded text-[10px] font-medium shrink-0"
              style={{
                background: "var(--accent)",
                color: "var(--background)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              AI
            </span>
          )}
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder={isRagMode ? "질문을 입력하세요..." : "검색하거나 명령 입력... (? 로 AI 검색)"}
            className="w-full bg-transparent text-sm outline-none"
            style={{ color: "var(--text-primary)" }}
            autoFocus
          />
        </div>

        {!isRagMode && (
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
                    onClick={() => handleItemClick(item.action)}
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
        )}

        {isRagMode && (
          <div className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
            Enter로 질문 전송. AI 검색 패널에서 답변을 확인합니다.
          </div>
        )}
      </div>
    </div>
  );
}
