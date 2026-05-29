"use client";

import { useState } from "react";
import type { RagSource } from "../types";

interface RagSourcesProps {
  sources: RagSource[];
}

const FRESHNESS_LABELS: Record<string, string> = {
  recent: "",
  normal: "보통",
  stale: "오래됨",
};

const SOURCE_TYPE_LABELS: Record<string, string> = {
  meeting: "회의",
  note: "노트",
};

export function RagSources({ sources }: RagSourcesProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="pl-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-caption mb-1"
        style={{ color: "var(--text-muted)" }}
      >
        <span>📎 소스 {sources.length}건</span>
        <span>{isExpanded ? "▾" : "▸"}</span>
      </button>

      {isExpanded && (
        <div className="flex flex-col gap-1.5">
          {sources.map((source) => (
            <div
              key={source.id}
              className="flex items-center gap-2 px-2 py-1.5 rounded text-caption"
              style={{
                background: "var(--surface-hover)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              <span
                className="px-1 rounded"
                style={{
                  background: "var(--surface-active)",
                  color: "var(--text-muted)",
                  borderRadius: "var(--radius-sm)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "9px",
                }}
              >
                {SOURCE_TYPE_LABELS[source.sourceType] || source.sourceType}
              </span>
              <span className="truncate" style={{ color: "var(--text-secondary)" }}>
                {source.source || "제목 없음"}
              </span>
              {source.speaker && (
                <span style={{ color: "var(--text-muted)" }}>
                  · {source.speaker}
                </span>
              )}
              {source.freshness === "stale" && (
                <span style={{ color: "var(--warning)" }}>
                  ⚠️ {FRESHNESS_LABELS.stale}
                </span>
              )}
              {source.freshness === "normal" && (
                <span style={{ color: "var(--text-muted)" }}>
                  {FRESHNESS_LABELS.normal}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
