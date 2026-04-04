"use client";

import { useNotes, useCreateNote } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import type { Note } from "../types";

interface NoteListProps {
  projectId?: string;
  onSelect: (noteId: string) => void;
}

export function NoteList({ projectId, onSelect }: NoteListProps) {
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const hasRole = useWorkspaceStore((s) => s.hasRole);
  const { data, isLoading } = useNotes(wid ?? undefined, projectId);
  const createNote = useCreateNote(wid ?? undefined);
  const canWrite = hasRole("member");

  const handleCreate = async () => {
    const result = await createNote.mutateAsync({
      title: "",
      projectId: projectId ?? null,
    });
    onSelect(result.id);
  };

  if (isLoading) {
    return (
      <div className="p-4 text-sm" style={{ color: "var(--text-muted)" }}>
        로딩 중...
      </div>
    );
  }

  const notes = data?.items ?? [];

  return (
    <div className="flex flex-col">
      <div
        className="px-4 py-3 border-b flex items-center justify-between"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <h3
          className="text-sm font-semibold"
          style={{
            color: "var(--text-primary)",
            fontFamily: "var(--font-display)",
          }}
        >
          노트
        </h3>
        {canWrite && (
          <button
            onClick={handleCreate}
            disabled={createNote.isPending}
            className="text-xs px-2 py-1 rounded transition-colors"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            + 새 노트
          </button>
        )}
      </div>
      {notes.length === 0 ? (
        <div
          className="p-4 text-sm text-center"
          style={{ color: "var(--text-muted)" }}
        >
          아직 노트가 없습니다
        </div>
      ) : (
        <div className="flex flex-col">
          {notes.map((note: Note) => (
            <button
              key={note.id}
              onClick={() => onSelect(note.id)}
              className="text-left px-4 py-3 border-b transition-colors"
              style={{ borderColor: "var(--border-subtle)" }}
              onMouseOver={(e) =>
                (e.currentTarget.style.background = "var(--surface-hover)")
              }
              onMouseOut={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
              <div
                className="text-sm font-medium truncate"
                style={{ color: "var(--text-primary)" }}
              >
                {note.title || "제목 없음"}
              </div>
              <div
                className="text-xs mt-1 truncate"
                style={{ color: "var(--text-muted)" }}
              >
                {note.plainText?.slice(0, 80) || "내용 없음"}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
