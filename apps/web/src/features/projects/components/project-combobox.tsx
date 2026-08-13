"use client";

import { useState, useRef, useEffect } from "react";
import { useProjects, useCreateProject } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";

interface ProjectComboboxProps {
  onSelect: (projectId: string) => void;
  onClose?: () => void;
  /** 이미 연결된 프로젝트 ID 목록 (필터링용) */
  excludeIds?: string[];
}

export function ProjectCombobox({ onSelect, onClose, excludeIds = [] }: ProjectComboboxProps) {
  const [search, setSearch] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const { data } = useProjects(activeWorkspaceId ?? undefined, { status: "active" });
  const createProject = useCreateProject(activeWorkspaceId ?? undefined);

  // 자동 포커스
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // 외부 클릭 감지
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose?.();
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  const filtered = (data?.items ?? [])
    .filter((p) => !excludeIds.includes(p.id))
    .filter((p) => p.title.toLowerCase().includes(search.toLowerCase()));

  const hasExactMatch = filtered.some(
    (p) => p.title.toLowerCase() === search.toLowerCase()
  );

  async function handleCreateAndSelect() {
    if (!search.trim() || isCreating) return;
    setIsCreating(true);
    try {
      const result = await createProject.mutateAsync({ title: search.trim() });
      onSelect(result.id);
      onClose?.();
    } finally {
      setIsCreating(false);
    }
  }

  function handleSelect(projectId: string) {
    onSelect(projectId);
    onClose?.();
  }

  return (
    <div
      ref={containerRef}
      className="absolute z-50 w-64 rounded border shadow-lg"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border)",
        borderRadius: "var(--radius-md)",
      }}
    >
      {/* 검색 입력 */}
      <div className="p-2 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        <input
          ref={inputRef}
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") onClose?.();
            if (e.key === "Enter" && filtered.length === 1) {
              handleSelect(filtered[0].id);
            }
          }}
          placeholder="프로젝트 검색..."
          className="w-full px-2 py-1.5 text-sm rounded outline-none"
          style={{
            background: "var(--background)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
          }}
        />
      </div>

      {/* 프로젝트 리스트 */}
      <div className="max-h-48 overflow-y-auto p-1">
        {filtered.length === 0 && !search.trim() && (
          <p className="px-2 py-3 text-xs text-center" style={{ color: "var(--text-muted)" }}>
            프로젝트가 없습니다
          </p>
        )}
        {filtered.map((project) => (
          <button
            key={project.id}
            onClick={() => handleSelect(project.id)}
            className="w-full text-left px-2 py-1.5 text-sm rounded transition-colors hover:opacity-80"
            style={{
              color: "var(--text-primary)",
              borderRadius: "var(--radius-sm)",
            }}
            onMouseEnter={(e) => {
              (e.target as HTMLElement).style.background = "var(--surface-active)";
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.background = "transparent";
            }}
          >
            {project.title}
          </button>
        ))}

        {/* 새 프로젝트 만들기 */}
        {search.trim() && !hasExactMatch && (
          <button
            onClick={handleCreateAndSelect}
            disabled={isCreating}
            className="w-full text-left px-2 py-1.5 text-sm rounded transition-colors flex items-center gap-1.5"
            style={{
              color: "var(--accent)",
              borderRadius: "var(--radius-sm)",
              opacity: isCreating ? 0.5 : 1,
            }}
            onMouseEnter={(e) => {
              (e.target as HTMLElement).style.background = "var(--surface-active)";
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.background = "transparent";
            }}
          >
            <span>+</span>
            <span>&ldquo;{search.trim()}&rdquo; 새 프로젝트 만들기</span>
          </button>
        )}
      </div>
    </div>
  );
}
