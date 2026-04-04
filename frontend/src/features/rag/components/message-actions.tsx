"use client";

import { useState } from "react";
import { Copy, StickyNote, ExternalLink, Check } from "lucide-react";

interface MessageActionsProps {
  content: string;
  onSaveAsNote?: () => void;
  onExport?: () => void;
}

export function MessageActions({
  content,
  onSaveAsNote,
  onExport,
}: MessageActionsProps) {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      // 클립보드 접근 실패 시 무시
    }
  };

  return (
    <div className="flex items-center gap-1 mt-1.5 pl-0.5">
      <button
        type="button"
        onClick={handleCopy}
        className="flex items-center gap-1 px-2 py-1 rounded text-[11px] border transition-colors cursor-pointer"
        style={{
          borderColor: "var(--border-subtle)",
          color: isCopied ? "var(--accent)" : "var(--text-muted)",
          borderRadius: "var(--radius-sm)",
          minHeight: 28,
        }}
        onMouseOver={(e) => {
          e.currentTarget.style.borderColor = "var(--accent)";
          e.currentTarget.style.color = "var(--accent)";
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.borderColor = "var(--border-subtle)";
          e.currentTarget.style.color = isCopied
            ? "var(--accent)"
            : "var(--text-muted)";
        }}
      >
        {isCopied ? <Check size={12} /> : <Copy size={12} />}
        <span>{isCopied ? "복사됨" : "복사"}</span>
      </button>

      <button
        type="button"
        onClick={onSaveAsNote}
        className="flex items-center gap-1 px-2 py-1 rounded text-[11px] border transition-colors cursor-pointer"
        style={{
          borderColor: "var(--border-subtle)",
          color: "var(--text-muted)",
          borderRadius: "var(--radius-sm)",
          minHeight: 28,
        }}
        onMouseOver={(e) => {
          e.currentTarget.style.borderColor = "var(--accent)";
          e.currentTarget.style.color = "var(--accent)";
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.borderColor = "var(--border-subtle)";
          e.currentTarget.style.color = "var(--text-muted)";
        }}
      >
        <StickyNote size={12} />
        <span>노트로 저장</span>
      </button>

      <button
        type="button"
        onClick={onExport}
        className="flex items-center gap-1 px-2 py-1 rounded text-[11px] border transition-colors cursor-pointer"
        style={{
          borderColor: "var(--border-subtle)",
          color: "var(--text-muted)",
          borderRadius: "var(--radius-sm)",
          minHeight: 28,
        }}
        onMouseOver={(e) => {
          e.currentTarget.style.borderColor = "var(--accent)";
          e.currentTarget.style.color = "var(--accent)";
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.borderColor = "var(--border-subtle)";
          e.currentTarget.style.color = "var(--text-muted)";
        }}
      >
        <ExternalLink size={12} />
        <span>내보내기</span>
      </button>
    </div>
  );
}
