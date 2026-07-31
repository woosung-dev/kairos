"use client";

// RAG 검색 범위 + 필터 UI. Sprint 24 Wave 2 T-RAG-MOCK-REMOVE (BUG-POW-005)
// 로 MOCK_SELECTABLE_SOURCES 제거 후 "선택한 소스" 탭을 empty state 로 변경 (실 API + selection state 는 BL-NEW-RAG-SOURCE-SELECT 진입 시 구현).

import { useState } from "react";
import { useRagStore } from "../store";

// "현재 프로젝트" 는 글로벌 /search 에 현재 프로젝트 컨텍스트가 없어 무동작(전체와 동일)이라 제거
// (BUG-SEARCH-CURRENT-PROJECT-NOOP). searchFilter.projectId 인프라는 향후 in-project RAG 용으로 store 에 유지.
type ScopeTab = "all" | "selected";

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
  { value: "external_document", label: "외부 문서" },
] as const;

export function SearchScope() {
  const { searchFilter, setSearchFilter } = useRagStore();
  const [scopeTab, setScopeTab] = useState<ScopeTab>("all");

  return (
    <div className="px-4 py-2 space-y-2">
      {/* 스코프 탭 */}
      <div className="flex items-center gap-1">
        {(
          [
            { key: "all", label: "전체" },
            { key: "selected", label: "선택한 소스" },
          ] as const
        ).map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setScopeTab(tab.key)}
            className="px-2.5 py-1 rounded-full text-caption font-medium transition-colors cursor-pointer"
            style={{
              background:
                scopeTab === tab.key
                  ? "var(--accent-subtle)"
                  : "transparent",
              color:
                scopeTab === tab.key
                  ? "var(--accent)"
                  : "var(--text-muted)",
              border:
                scopeTab === tab.key
                  ? "1px solid var(--accent)"
                  : "1px solid var(--border-subtle)",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 필터: 기간 + 유형 */}
      <div className="flex items-center gap-2">
        <select
          value={searchFilter.timeRange || ""}
          onChange={(e) =>
            setSearchFilter({
              timeRange: (e.target.value || null) as
                | "1m"
                | "3m"
                | "6m"
                | null,
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
              sourceType: (e.target.value || null) as
                | "meeting"
                | "note"
                | "external_document"
                | null,
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

      {/* "선택한 소스" 탭 — Sprint 24 Wave 2: MOCK 제거 후 empty state (BL-NEW-RAG-SOURCE-SELECT 진입 시 실 API + selection state). */}
      {scopeTab === "selected" && (
        <div
          className="mt-1 rounded border border-dashed px-3 py-3 text-caption leading-relaxed"
          style={{
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-muted)",
            background: "var(--surface)",
          }}
        >
          소스 선택 기능 준비 중 — 현재는 전체 워크스페이스에서 검색합니다.
        </div>
      )}
    </div>
  );
}
