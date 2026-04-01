"use client";

import { useState } from "react";
import type { SearchScope as SearchScopeType } from "../types";

interface SearchScopeProps {
  onChange?: (scope: SearchScopeType) => void;
}

const TIME_OPTIONS = [
  { value: "all", label: "전체 기간" },
  { value: "1m", label: "최근 1개월" },
  { value: "3m", label: "최근 3개월" },
  { value: "6m", label: "최근 6개월" },
] as const;

const SOURCE_OPTIONS = [
  { value: "all", label: "모든 유형" },
  { value: "meeting", label: "회의" },
  { value: "note", label: "노트" },
  { value: "attachment", label: "자료" },
] as const;

export function SearchScope({ onChange }: SearchScopeProps) {
  const [scope, setScope] = useState<SearchScopeType>({
    timeRange: "all",
    sourceType: "all",
  });

  const handleChange = (key: keyof SearchScopeType, value: string) => {
    const next = { ...scope, [key]: value };
    setScope(next);
    onChange?.(next);
  };

  return (
    <div className="flex items-center gap-3 mt-2">
      {/* 시간 범위 */}
      <select
        value={scope.timeRange}
        onChange={(e) => handleChange("timeRange", e.target.value)}
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

      {/* 소스 타입 */}
      <select
        value={scope.sourceType}
        onChange={(e) => handleChange("sourceType", e.target.value)}
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
