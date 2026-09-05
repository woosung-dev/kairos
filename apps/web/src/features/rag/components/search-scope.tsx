"use client";

// RAG 검색 범위 + 필터 UI. Sprint 24 Wave 2 T-RAG-MOCK-REMOVE (BUG-POW-005)
// 로 MOCK_SELECTABLE_SOURCES 제거 후 "선택한 소스" 탭을 empty state 로 변경 (실 API + selection state 는 BL-NEW-RAG-SOURCE-SELECT 진입 시 구현).

import { useRagStore } from "../store";
import type { SearchFilter } from "../types";

// "현재 프로젝트" 는 글로벌 /search 에 현재 프로젝트 컨텍스트가 없어 무동작(전체와 동일)이라 제거
// (BUG-SEARCH-CURRENT-PROJECT-NOOP). searchFilter.projectId 인프라는 향후 in-project RAG 용으로 store 에 유지.
// 2026-09-06: "선택한 소스" 탭도 제거 — 누르면 "준비 중" 안내만 나오는 dead-end 였다.
// 소스 단위 선택은 BL-NEW-RAG-SOURCE-SELECT 진입 시 실 API 와 함께 되살린다.

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
] as const satisfies ReadonlyArray<{
  value: NonNullable<SearchFilter["sourceType"]> | "";
  label: string;
}>;

export function SearchScope() {
  const { searchFilter, setSearchFilter } = useRagStore();

  return (
    <div className="px-4 py-2 space-y-2">
      {/* 필터: 기간 + 유형 — 검색 범위는 항상 현재 워크스페이스 전체 */}
      <div className="flex items-center gap-2">
        <span className="text-caption" style={{ color: "var(--text-muted)" }}>
          필터
        </span>
        <select
          value={searchFilter.timeRange || ""}
          onChange={(e) =>
            setSearchFilter({
              timeRange: (e.target.value || null) as SearchFilter["timeRange"],
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
              sourceType: (e.target.value || null) as SearchFilter["sourceType"],
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
    </div>
  );
}
