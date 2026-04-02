"use client";

import { useRagStore } from "../store";

const TIME_OPTIONS = [
  { value: "", label: "전체 기간" },
  { value: "1m", label: "최근 1개월" },
  { value: "3m", label: "최근 3개월" },
  { value: "6m", label: "최근 6개월" },
] as const;

const SOURCE_OPTIONS = [
  { value: "", label: "모든 유형" },
  { value: "meeting", label: "회의" },
  { value: "note", label: "노트" },
] as const;

export function SearchScope() {
  const { searchFilter, setSearchFilter } = useRagStore();

  return (
    <div className="flex items-center gap-2 px-4 py-2">
      <select
        value={searchFilter.timeRange || ""}
        onChange={(e) =>
          setSearchFilter({
            timeRange: (e.target.value || null) as "1m" | "3m" | "6m" | null,
          })
        }
        className="px-2 py-1 rounded text-xs bg-transparent border outline-none"
        style={{
          borderColor: "var(--border)",
          color: "var(--text-secondary)",
          borderRadius: "var(--radius-sm)",
        }}
      >
        {TIME_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      <select
        value={searchFilter.sourceType || ""}
        onChange={(e) =>
          setSearchFilter({
            sourceType: (e.target.value || null) as "meeting" | "note" | null,
          })
        }
        className="px-2 py-1 rounded text-xs bg-transparent border outline-none"
        style={{
          borderColor: "var(--border)",
          color: "var(--text-secondary)",
          borderRadius: "var(--radius-sm)",
        }}
      >
        {SOURCE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
