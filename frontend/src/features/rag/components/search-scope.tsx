"use client";

import { useState } from "react";
import { useRagStore } from "../store";
import { Mic, FileText, Check } from "lucide-react";

type ScopeTab = "all" | "project" | "selected";

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

/** Mock: 선택 가능한 소스 목록 */
interface SelectableSource {
  id: string;
  name: string;
  type: "meeting" | "note";
  projectId: string;
  projectName: string;
}

const MOCK_SELECTABLE_SOURCES: SelectableSource[] = [
  { id: "s1", name: "Sprint 3 회고 회의", type: "meeting", projectId: "p1", projectName: "Kairos" },
  { id: "s2", name: "AI 검색 파이프라인 설계", type: "note", projectId: "p1", projectName: "Kairos" },
  { id: "s3", name: "배포 전략 회의", type: "meeting", projectId: "p1", projectName: "Kairos" },
  { id: "s4", name: "사용자 인터뷰 정리", type: "note", projectId: "p2", projectName: "사이드 프로젝트" },
  { id: "s5", name: "MVP 범위 논의", type: "meeting", projectId: "p2", projectName: "사이드 프로젝트" },
];

export function SearchScope() {
  const { searchFilter, setSearchFilter } = useRagStore();
  const [scopeTab, setScopeTab] = useState<ScopeTab>("all");
  const [selectedSourceIds, setSelectedSourceIds] = useState<Set<string>>(
    new Set(),
  );

  /** 프로젝트별 그룹핑 */
  const groupedSources = MOCK_SELECTABLE_SOURCES.reduce<
    Record<string, { projectName: string; sources: SelectableSource[] }>
  >((acc, src) => {
    if (!acc[src.projectId]) {
      acc[src.projectId] = { projectName: src.projectName, sources: [] };
    }
    acc[src.projectId].sources.push(src);
    return acc;
  }, {});

  const handleToggleSource = (id: string) => {
    setSelectedSourceIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleToggleAll = () => {
    const allIds = MOCK_SELECTABLE_SOURCES.map((s) => s.id);
    const isAllSelected = allIds.every((id) => selectedSourceIds.has(id));
    if (isAllSelected) {
      setSelectedSourceIds(new Set());
    } else {
      setSelectedSourceIds(new Set(allIds));
    }
  };

  const isAllSelected =
    MOCK_SELECTABLE_SOURCES.length > 0 &&
    MOCK_SELECTABLE_SOURCES.every((s) => selectedSourceIds.has(s.id));

  return (
    <div className="px-4 py-2 space-y-2">
      {/* 스코프 탭 */}
      <div className="flex items-center gap-1">
        {(
          [
            { key: "all", label: "전체" },
            { key: "project", label: "현재 프로젝트" },
            { key: "selected", label: "선택한 소스" },
          ] as const
        ).map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setScopeTab(tab.key)}
            className="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors cursor-pointer"
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
            {tab.key === "selected" && selectedSourceIds.size > 0 && (
              <span className="ml-1">({selectedSourceIds.size})</span>
            )}
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

      {/* "선택한 소스" 탭: 소스 체크리스트 */}
      {scopeTab === "selected" && (
        <div
          className="mt-1 rounded border overflow-hidden"
          style={{
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {/* 전체 선택/해제 */}
          <button
            type="button"
            onClick={handleToggleAll}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-[11px] font-medium cursor-pointer transition-colors"
            style={{
              background: "var(--surface)",
              color: "var(--text-secondary)",
              borderBottom: "1px solid var(--border-subtle)",
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.background = "var(--surface-hover)";
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = "var(--surface)";
            }}
          >
            <span
              className="flex items-center justify-center rounded"
              style={{
                width: 14,
                height: 14,
                border: isAllSelected
                  ? "none"
                  : "1.5px solid var(--border)",
                background: isAllSelected
                  ? "var(--accent)"
                  : "transparent",
                borderRadius: 3,
              }}
            >
              {isAllSelected && <Check size={10} style={{ color: "var(--background)" }} />}
            </span>
            전체 {isAllSelected ? "해제" : "선택"}
          </button>

          {/* 프로젝트별 소스 목록 */}
          <div
            className="max-h-[200px] overflow-y-auto"
            style={{ background: "var(--background)" }}
          >
            {Object.entries(groupedSources).map(
              ([projId, { projectName, sources }]) => (
                <div key={projId}>
                  <div
                    className="px-3 py-1 text-[10px] uppercase tracking-wider font-semibold"
                    style={{
                      color: "var(--text-muted)",
                      background: "var(--surface-hover)",
                    }}
                  >
                    {projectName}
                  </div>
                  {sources.map((src) => {
                    const isChecked = selectedSourceIds.has(src.id);
                    return (
                      <button
                        key={src.id}
                        type="button"
                        onClick={() => handleToggleSource(src.id)}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-[11px] cursor-pointer transition-colors"
                        style={{
                          color: "var(--text-secondary)",
                        }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.background =
                            "var(--surface-hover)";
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.background = "transparent";
                        }}
                      >
                        <span
                          className="flex items-center justify-center rounded shrink-0"
                          style={{
                            width: 14,
                            height: 14,
                            border: isChecked
                              ? "none"
                              : "1.5px solid var(--border)",
                            background: isChecked
                              ? "var(--accent)"
                              : "transparent",
                            borderRadius: 3,
                          }}
                        >
                          {isChecked && (
                            <Check
                              size={10}
                              style={{ color: "var(--background)" }}
                            />
                          )}
                        </span>
                        {src.type === "meeting" ? (
                          <Mic
                            size={12}
                            style={{ color: "var(--text-muted)" }}
                            className="shrink-0"
                          />
                        ) : (
                          <FileText
                            size={12}
                            style={{ color: "var(--text-muted)" }}
                            className="shrink-0"
                          />
                        )}
                        <span className="truncate">{src.name}</span>
                      </button>
                    );
                  })}
                </div>
              ),
            )}
          </div>
        </div>
      )}
    </div>
  );
}
