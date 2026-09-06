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
// ★매칭은 물리 키 `e.code`("KeyG") 다 — 한국어 입력 소스에서는 `e.key` 가 'ㅎ'/'ㅏ' 로 들어와
//   `e.key.toLowerCase()` 매칭이 전부 미동작했다 (2026-09-06 실측). 수정키 단독 keydown(Shift 등)은
//   시퀀스를 지우지 않고, 다이얼로그·combobox·menu 가 열린 상태에서는 발화하지 않는다 (WCAG 2.1.4).
const SEQUENCE_TIMEOUT_MS = 1000;
// 물리 키(e.code) 우선, 문자(e.key) 폴백 — QWERTY 한국어 IME 는 code 로, AZERTY/Dvorak 처럼 물리 위치가
// 다른 배열은 팔레트에 적힌 문자 그대로 key 로 맞는다.
const GO_TARGETS_BY_CODE: Record<string, string> = {
  KeyI: "/inbox",
  KeyP: "/projects",
  KeyA: "/actions",
  KeyN: "/notes",
  KeyS: "/search",
};
const GO_TARGETS_BY_KEY: Record<string, string> = {
  i: "/inbox",
  p: "/projects",
  a: "/actions",
  n: "/notes",
  s: "/search",
};

function resolveGoTarget(e: KeyboardEvent): string | undefined {
  return GO_TARGETS_BY_CODE[e.code] ?? GO_TARGETS_BY_KEY[e.key.toLowerCase()];
}
function isKey(e: KeyboardEvent, code: string, char: string): boolean {
  return e.code === code || e.key.toLowerCase() === char;
}
/** 문자 키만 시퀀스 판정 대상 — Shift/AltGraph/Dead/화살표 같은 비문자 keydown 은 pending 을 건드리지 않는다. */
function isCharacterKey(e: KeyboardEvent): boolean {
  return e.key.length === 1 || e.code in GO_TARGETS_BY_CODE || e.code === "KeyG" || e.code === "KeyC";
}

/** 입력 중이거나 키보드로 조작 중인 위젯(select/combobox/listbox/menu) 위에서는 단축키를 먹지 않는다. */
function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    target.isContentEditable ||
    target.closest(
      '[role="combobox"],[role="listbox"],[role="menu"],[role="menuitem"],[role="textbox"]',
    ) !== null
  );
}

/**
 * 열린 팝업(다이얼로그·메뉴·리스트박스) 이 있으면 문자 키는 그 위젯의 것이다 — base-ui Popup 은
 * role 만 붙이고 문자 키를 stopPropagation 하지 않으므로 여기서 문서 단위로 막는다.
 * ★닫힘 애니메이션 동안 DOM 에 남는 Popup(`data-closed`)·`hidden` 은 열린 것이 아니다 — Escape 직후의
 *   g → a 첫 키를 삼키지 않도록 제외한다.
 * ★비모달 안내 Popover(온보딩 툴팁) 도 floating-ui 기본값으로 role=dialog 를 달지만 내비를 막을 이유가 없다 —
 *   `data-slot="popover-content"` 로 제외한다.
 */
const OPEN_POPUP_SELECTOR = ['[role="dialog"]', '[role="alertdialog"]', '[role="menu"]', '[role="listbox"]']
  .map((role) => `${role}:not([data-closed]):not([hidden]):not([data-slot="popover-content"])`)
  .join(",");

function isPopupOpen(): boolean {
  return document.querySelector(OPEN_POPUP_SELECTOR) !== null;
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
      if ((e.metaKey || e.ctrlKey) && isKey(e, "KeyK", "k")) {
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
      // 이하 단축키 시퀀스 — 팔레트가 열려 있거나 수정키 조합이면 무시
      if (cmdKOpen || e.metaKey || e.ctrlKey || e.altKey) return;
      // 비문자 키(수정키·Dead·화살표 등) 단독 keydown 은 판정 대상이 아니다 — pending 을 지우지 않는다 (g → Shift → a 유효).
      if (!isCharacterKey(e)) return;
      // 입력 중이거나 다이얼로그가 열려 있으면 무시 (pending 은 타임아웃으로 자연 소멸)
      if (isTypingTarget(e.target) || isPopupOpen()) return;
      if (pendingGo !== null) {
        clearPending();
        const target = resolveGoTarget(e);
        if (target) {
          e.preventDefault();
          router.push(target);
        }
        return;
      }
      if (isKey(e, "KeyG", "g")) {
        pendingGo = window.setTimeout(clearPending, SEQUENCE_TIMEOUT_MS);
        return;
      }
      if (isKey(e, "KeyC", "c")) {
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
