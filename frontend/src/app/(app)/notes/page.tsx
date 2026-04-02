"use client";

import { useState } from "react";
import { NoteList } from "@/features/notes/components/note-list";
import { NoteEditor } from "@/features/notes/components/note-editor";
import { useNote } from "@/features/notes/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";

export default function NotesPage() {
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const { data: note } = useNote(wid ?? undefined, selectedNoteId ?? "");

  return (
    <div className="flex h-full">
      {/* 노트 목록 */}
      <div
        className="w-[280px] shrink-0 border-r overflow-y-auto"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <NoteList onSelect={setSelectedNoteId} />
      </div>

      {/* 에디터 */}
      <div className="flex-1">
        {note ? (
          <NoteEditor
            key={note.id}
            noteId={note.id}
            workspaceId={note.workspaceId}
            initialTitle={note.title}
            initialContent={note.content}
          />
        ) : (
          <div
            className="flex items-center justify-center h-full text-sm"
            style={{ color: "var(--text-muted)" }}
          >
            노트를 선택하거나 새로 만드세요
          </div>
        )}
      </div>
    </div>
  );
}
