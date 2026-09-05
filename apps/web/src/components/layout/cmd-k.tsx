"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import { Search, MessageSquare, Inbox, Folder, StickyNote, Plus, ListChecks } from "lucide-react";
import { useUIStore } from "@/store/ui";
import { useRagStream } from "@/features/rag/hooks";
import { OnboardingTooltip } from "@/components/onboarding/onboarding-tooltip";

interface CmdItem {
  icon: LucideIcon;
  label: string;
  shortcut: string;
  action: string;
}

const CMD_GROUPS: { label: string; items: CmdItem[] }[] = [
  {
    label: "검색",
    items: [
      { icon: Search, label: "지식 검색", shortcut: "⌘K", action: "focus" },
      { icon: MessageSquare, label: "AI 검색", shortcut: "?", action: "rag-mode" },
    ],
  },
  {
    label: "이동",
    items: [
      { icon: Inbox, label: "Inbox", shortcut: "G I", action: "navigate:/inbox" },
      // 2026-09-06: "/" 는 랜딩(→ /dashboard 리다이렉트)이었다 — 프로젝트 목록은 /projects.
      { icon: Folder, label: "프로젝트", shortcut: "G P", action: "navigate:/projects" },
      { icon: ListChecks, label: "액션", shortcut: "G A", action: "navigate:/actions" },
      { icon: StickyNote, label: "노트", shortcut: "G N", action: "navigate:/notes" },
      { icon: Search, label: "검색 페이지", shortcut: "G S", action: "navigate:/search" },
    ],
  },
  {
    label: "생성",
    items: [
      { icon: Plus, label: "콘텐츠 추가", shortcut: "C", action: "navigate:/new" },
    ],
  },
];

// 팔레트에 표시되는 단축키의 실제 구현 — 이전엔 라벨만 있고 키 핸들러가 없었다 (BUG-CASUAL CMD-K-SEQ).
// "G" 를 누른 뒤 1초 안에 두 번째 키를 누르면 이동. "C" 는 단독. 입력 필드/contentEditable 안에서는 무시.
const SEQUENCE_TIMEOUT_MS = 1000;
const GO_TARGETS: Record<string, string> = {
  i: "/inbox",
  p: "/projects",
  a: "/actions",
  n: "/notes",
  s: "/search",
};

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    target.isContentEditable
  );
}

export function CmdK() {
  const {
    cmdKOpen,
    toggleCmdK,
    toggleRagOverlay,
    cmdKInitialQuery,
    setCmdKInitialQuery,
    cmdKAutoSubmit,
    setCmdKAutoSubmit,
  } = useUIStore();
  const [search, setSearch] = useState("");
  const [isRagMode, setIsRagMode] = useState(false);
  const { ask } = useRagStream();
  const router = useRouter();

  useEffect(() => {
    let pendingGo: number | null = null;
    const clearPending = () => {
      if (pendingGo !== null) {
        window.clearTimeout(pendingGo);
        pendingGo = null;
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        toggleCmdK();
        return;
      }
      if (e.key === "Escape" && cmdKOpen) {
        toggleCmdK();
        setSearch("");
        setIsRagMode(false);
        return;
      }
      // 이하 단축키 시퀀스 — 팔레트가 열려 있거나 입력 중이거나 수정키가 눌린 상태면 무시
      if (cmdKOpen || e.metaKey || e.ctrlKey || e.altKey || isTypingTarget(e.target)) return;
      const key = e.key.toLowerCase();
      if (pendingGo !== null) {
        clearPending();
        const target = GO_TARGETS[key];
        if (target) {
          e.preventDefault();
          router.push(target);
        }
        return;
      }
      if (key === "g") {
        pendingGo = window.setTimeout(clearPending, SEQUENCE_TIMEOUT_MS);
        return;
      }
      if (key === "c") {
        e.preventDefault();
        router.push("/new");
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      clearPending();
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [cmdKOpen, toggleCmdK, router]);

  // Sprint 24 Wave 2 T-CMD-K-FIX: openCmdKWithQuery 로 진입한 경우 query 자동 입력 + RAG 모드.
  // store 의 cmdKInitialQuery 가 set 되면 palette 도 열려있어야 함 (openCmdKWithQuery 가 함께 set).
  // Sprint 27e Post-Merge BUG-QA-3: autoSubmit=true 시 prefill 직후 RAG 자동 호출.
  useEffect(() => {
    if (cmdKOpen && cmdKInitialQuery) {
      const q = cmdKInitialQuery;
      const auto = cmdKAutoSubmit;
      setSearch(q);
      setIsRagMode(true);
      setCmdKInitialQuery(""); // 1회성 consumption
      setCmdKAutoSubmit(false);
      if (auto && q.trim()) {
        // RAG 모드 즉시 호출 — handleSubmit 의 RAG 분기와 동일 동작.
        const question = q.startsWith("?") ? q.slice(1).trim() : q.trim();
        if (question) {
          ask(question);
          toggleRagOverlay();
          toggleCmdK();
          setSearch("");
          setIsRagMode(false);
        }
      }
    }
  }, [cmdKOpen, cmdKInitialQuery, cmdKAutoSubmit, setCmdKInitialQuery, setCmdKAutoSubmit, ask, toggleRagOverlay, toggleCmdK]);

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

      <OnboardingTooltip page="search">
      {/* 2026-06-24 fix: OnboardingTooltip 의 PopoverTrigger 가 `block w-full` 래퍼로
          palette 를 감싸 부모 flex 의 justify-center 가 무효화(full-width 트리거 센터링) →
          palette 좌측 정렬·사이드바 겹침. mx-auto 로 트리거 내부에서 다시 중앙 정렬. */}
      <div
        data-testid="cmdk-panel"
        className="relative w-full max-w-[520px] mx-auto rounded-lg border shadow-2xl overflow-hidden"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <div className="px-4 py-3 border-b flex items-center gap-2" style={{ borderColor: "var(--border-subtle)" }}>
          {isRagMode && (
            <span
              className="px-1.5 py-0.5 rounded text-micro font-medium shrink-0"
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
                {group.items.map((item) => {
                  const ItemIcon = item.icon;
                  return (
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
                      <ItemIcon className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
                      <span>{item.label}</span>
                    </div>
                    <kbd
                      className="text-micro px-1.5 py-0.5 rounded"
                      style={{
                        background: "var(--surface-active)",
                        color: "var(--text-muted)",
                        // ⌘(U+2318) 가 Geist Mono 미포함 → system-ui per-glyph fallback (UX-CMDK-GLYPH)
                        fontFamily: "var(--font-mono), system-ui, sans-serif",
                        borderRadius: "var(--radius-sm)",
                      }}
                    >
                      {item.shortcut}
                    </kbd>
                  </button>
                  );
                })}
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
      </OnboardingTooltip>
    </div>
  );
}
