"use client";

interface CitationBadgeProps {
  number: number;
  onClick: () => void;
  isActive?: boolean;
}

/** 인라인 출처 번호별 색상 시스템 */
const CITATION_COLORS: Record<
  number,
  { bg: string; bgActive: string; color: string }
> = {
  1: {
    bg: "var(--accent-subtle)",
    bgActive: "var(--accent)",
    color: "var(--accent)",
  },
  2: {
    bg: "color-mix(in srgb, var(--chart-3) 10%, transparent)",
    bgActive: "var(--chart-3)",
    color: "var(--chart-3)",
  },
  3: {
    bg: "color-mix(in srgb, var(--warning) 10%, transparent)",
    bgActive: "var(--warning)",
    color: "var(--warning)",
  },
};

const DEFAULT_COLOR = {
  bg: "var(--surface-hover)",
  bgActive: "var(--text-secondary)",
  color: "var(--text-secondary)",
};

export function CitationBadge({ number, onClick, isActive = false }: CitationBadgeProps) {
  const palette = CITATION_COLORS[number] ?? DEFAULT_COLOR;

  return (
    <button
      type="button"
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

/** CitationBadge에서 사용하는 색상을 외부에서도 접근 가능하도록 export */
export function getCitationColor(number: number) {
  return CITATION_COLORS[number] ?? DEFAULT_COLOR;
}
