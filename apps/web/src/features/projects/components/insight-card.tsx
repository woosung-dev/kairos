"use client";

import { Lightbulb } from "lucide-react";

interface InsightCardProps {
  text: string;
}

export function InsightCard({ text }: InsightCardProps) {
  return (
    <div
      className="p-4 rounded-lg border"
      style={{
        background: "var(--accent-subtle)",
        borderColor: "var(--accent)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div className="flex items-start gap-3">
        <Lightbulb className="w-5 h-5 shrink-0" style={{ color: "var(--accent)" }} />
        <div className="flex-1 min-w-0">
          <p
            className="text-xs font-semibold mb-1 uppercase tracking-wide"
            style={{
              color: "var(--accent)",
              fontFamily: "var(--font-display)",
            }}
          >
            프로액티브 인사이트
          </p>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            {text}
          </p>
        </div>
      </div>
    </div>
  );
}
