// 빠른 메모 페이지 — BE notes API 연동 (Sprint 17 fix: ISSUE-005)
"use client";

import { useMemo, useState } from "react";
import { toast } from "sonner";
import { useNotes, useCreateNote } from "../hooks";
import { useProjects } from "@/features/projects/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import type { Note } from "../types";

/* ── 헬퍼: 일반 텍스트 → tiptap JSON 문서 ── */
function textToTiptapDoc(text: string): Record<string, unknown> {
  const trimmed = text.trim();
  if (!trimmed) return { type: "doc", content: [] };
  return {
    type: "doc",
    content: [
      {
        type: "paragraph",
        content: [{ type: "text", text: trimmed }],
      },
    ],
  };
}

/* ── 컴포넌트 ── */

export function QuickMemo() {
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const hasRole = useWorkspaceStore((s) => s.hasRole);
  const canWrite = hasRole("member");

  const { data: notesPage, isLoading: isLoadingNotes } = useNotes(wid ?? undefined);
  const { data: projectsPage } = useProjects(wid ?? undefined, { status: "active" });
  const createNote = useCreateNote(wid ?? undefined);

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [isComposing, setIsComposing] = useState(false);

  const notes = notesPage?.items ?? [];
  const projects = projectsPage?.items ?? [];

  // projectId → projectTitle 매핑 (메모 카드에 표시용)
  const projectTitleMap = useMemo(() => {
    const map = new Map<string, string>();
    projects.forEach((p) => map.set(p.id, p.title));
    return map;
  }, [projects]);

  async function handleSave() {
    if (!title.trim() && !content.trim()) {
      toast.error("제목 또는 내용을 입력해주세요");
      return;
    }
    if (!wid) {
      toast.error("워크스페이스가 선택되지 않았습니다");
      return;
    }

    try {
      await createNote.mutateAsync({
        title: title.trim() || "제목 없음",
        content: textToTiptapDoc(content),
        projectId: selectedProjectId || null,
      });
      setTitle("");
      setContent("");
      setSelectedProjectId("");
      setIsComposing(false);
      toast.success("메모가 저장되었습니다");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "메모 저장에 실패했습니다";
      toast.error(msg);
    }
  }

  return (
    <div className="p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1
            className="text-2xl font-bold mb-1"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            빠른 메모
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            아이디어를 빠르게 기록하세요. 마크다운 문법을 지원합니다.
          </p>
        </div>
        {canWrite && !isComposing && (
          <button
            onClick={() => setIsComposing(true)}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            + 새 메모
          </button>
        )}
      </div>

      {/* 메모 입력 폼 */}
      {isComposing && (
        <div
          className="p-4 rounded-lg border mb-6"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <input
            type="text"
            placeholder="메모 제목"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-transparent text-lg font-semibold outline-none mb-3"
            style={{
              color: "var(--text-primary)",
              fontFamily: "var(--font-display)",
            }}
          />

          <textarea
            placeholder="내용을 입력하세요... (마크다운 지원)"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={6}
            className="w-full bg-transparent text-sm outline-none resize-none leading-relaxed"
            style={{
              color: "var(--text-secondary)",
            }}
          />

          <div
            className="flex items-center justify-between mt-4 pt-3 border-t"
            style={{ borderColor: "var(--border-subtle)" }}
          >
            <div className="flex items-center gap-2">
              <label className="text-xs" style={{ color: "var(--text-muted)" }}>
                프로젝트:
              </label>
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="text-xs px-2 py-1.5 rounded border bg-transparent outline-none"
                style={{
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                <option value="">선택 안 함</option>
                {projects.map((proj) => (
                  <option key={proj.id} value={proj.id}>
                    {proj.title}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setIsComposing(false);
                  setTitle("");
                  setContent("");
                  setSelectedProjectId("");
                }}
                className="px-3 py-1.5 rounded text-xs font-medium transition-colors border"
                style={{
                  borderColor: "var(--border)",
                  color: "var(--text-muted)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                취소
              </button>
              <button
                onClick={handleSave}
                disabled={createNote.isPending}
                className="px-4 py-1.5 rounded text-xs font-medium transition-colors"
                style={{
                  background: "var(--accent)",
                  color: "var(--background)",
                  borderRadius: "var(--radius-sm)",
                  cursor: createNote.isPending ? "not-allowed" : "pointer",
                  minHeight: "44px",
                  opacity: createNote.isPending ? 0.6 : 1,
                }}
              >
                {createNote.isPending ? "저장 중..." : "저장"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 저장된 메모 목록 */}
      {isLoadingNotes ? (
        <div className="py-8 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          로딩 중...
        </div>
      ) : notes.length > 0 ? (
        <div className="grid gap-3">
          {notes.map((memo) => (
            <MemoCard
              key={memo.id}
              memo={memo}
              projectTitle={memo.projectId ? projectTitleMap.get(memo.projectId) ?? null : null}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-4xl mb-4">📝</span>
          <h3
            className="text-lg font-semibold mb-2"
            style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
          >
            아직 메모가 없습니다
          </h3>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            빠른 메모를 작성하면 AI가 자동으로 프로젝트에 연결합니다
          </p>
        </div>
      )}
    </div>
  );
}

/* ── 서브 컴포넌트 ── */

function MemoCard({
  memo,
  projectTitle,
}: {
  memo: Note;
  projectTitle: string | null;
}) {
  const createdDate = memo.createdAt?.slice(0, 10) ?? "";
  const preview = memo.plainText?.slice(0, 200) ?? "";

  return (
    <div
      className="p-4 rounded-lg border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        cursor: "pointer",
      }}
      onMouseOver={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
      onMouseOut={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
    >
      <div className="flex items-start justify-between mb-1">
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          {memo.title || "제목 없음"}
        </h3>
        <span className="text-[10px] shrink-0 ml-2" style={{ color: "var(--text-muted)" }}>
          {createdDate}
        </span>
      </div>
      <p className="text-xs line-clamp-2 mb-2" style={{ color: "var(--text-secondary)" }}>
        {preview || "내용 없음"}
      </p>
      {projectTitle && (
        <span
          className="px-1.5 py-0.5 rounded text-[10px]"
          style={{
            background: "var(--accent-subtle)",
            color: "var(--accent)",
          }}
        >
          {projectTitle}
        </span>
      )}
    </div>
  );
}
