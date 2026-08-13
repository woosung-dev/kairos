// 인라인 출처 번호별 색상 시스템 — RAG citation 배지 / source viewer 공용 (FSD shared util)

interface CitationPalette {
  bg: string;
  bgActive: string;
  color: string;
}

const CITATION_COLORS: Record<number, CitationPalette> = {
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

const DEFAULT_COLOR: CitationPalette = {
  bg: "var(--surface-hover)",
  bgActive: "var(--text-secondary)",
  color: "var(--text-secondary)",
};

/** 출처 번호별 색상 팔레트 반환 (미정의 번호는 기본색). */
export function getCitationColor(number: number): CitationPalette {
  return CITATION_COLORS[number] ?? DEFAULT_COLOR;
}
