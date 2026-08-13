"use client";

import { getCitationColor } from "@/lib/citation-colors";

interface CitationBadgeProps {
  number: number;
  onClick: () => void;
  isActive?: boolean;
}

export function CitationBadge({ number, onClick, isActive = false }: CitationBadgeProps) {
  const palette = getCitationColor(number);

  return (
    <button
      type="button"
      data-testid={`citation-badge-${number}`}
      onClick={onClick}
      className="inline-flex items-center justify-center align-top cursor-pointer transition-colors"
      style={{
        width: 16,
        height: 16,
        fontSize: 9,
        fontWeight: 700,
        borderRadius: 3,
        lineHeight: 1,
        background: isActive ? palette.bgActive : palette.bg,
        color: isActive ? "var(--background)" : palette.color,
        border: "none",
        padding: 0,
        verticalAlign: "super",
        marginLeft: 1,
        marginRight: 1,
      }}
      aria-label={`출처 ${number}`}
    >
      {number}
    </button>
  );
}
