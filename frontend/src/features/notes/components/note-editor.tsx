"use client";

import { useCallback, useEffect, useRef } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { CharacterCount } from "@tiptap/extension-character-count";
import { useUpdateNote } from "../hooks";

interface NoteEditorProps {
  noteId: string;
  workspaceId: string;
  initialTitle: string;
  initialContent: Record<string, unknown>;
}

export function NoteEditor({
  noteId,
  workspaceId,
  initialTitle,
  initialContent,
}: NoteEditorProps) {
  const updateNote = useUpdateNote(workspaceId);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: "내용을 입력하세요..." }),
      CharacterCount,
    ],
    content: initialContent as Record<string, unknown>,
    onUpdate: ({ editor: ed }) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        updateNote.mutate({
          id: noteId,
          data: { content: ed.getJSON() },
        });
      }, 500);
    },
  });

  const handleTitleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        updateNote.mutate({
          id: noteId,
          data: { title: value },
        });
      }, 500);
    },
    [noteId, updateNote],
  );

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <div className="flex flex-col h-full">
      <input
        defaultValue={initialTitle}
        onChange={handleTitleChange}
        placeholder="제목 없음"
        className="w-full bg-transparent text-xl font-semibold outline-none px-4 py-3 border-b"
        style={{
          color: "var(--text-primary)",
          fontFamily: "var(--font-display)",
          borderColor: "var(--border-subtle)",
        }}
      />
      <div className="flex-1 overflow-y-auto px-4 py-3">
        <EditorContent
          editor={editor}
          className="prose prose-invert max-w-none text-sm"
          style={{ color: "var(--text-primary)" }}
        />
      </div>
      {editor && (
        <div
          className="px-4 py-2 text-xs border-t flex items-center gap-2"
          style={{
            color: "var(--text-muted)",
            borderColor: "var(--border-subtle)",
          }}
        >
          <span>{editor.storage.characterCount.characters()} 자</span>
          {updateNote.isPending && (
            <span style={{ color: "var(--accent)" }}>저장 중...</span>
          )}
        </div>
      )}
    </div>
  );
}
