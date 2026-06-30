// 노트 상세 페이지 본문 — Sprint 24 Wave 2 T-NOTE-DETAIL (BUG-POW-003)
// Tiptap viewer (readonly default) + edit-in-place (pencil) + auto-save debounce 1s + Export + Promote.
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowUpRight, Check, Pencil } from "lucide-react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useNote, useUpdateNote } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { ExportButton } from "@/components/shared/ExportButton";
import { exportNote } from "../api";
import { ItemPromoteModal } from "@/components/shared/ItemPromoteModal";

const AUTOSAVE_DEBOUNCE_MS = 1000;

interface NoteDetailProps {
  noteId: string;
}

export function NoteDetail({ noteId }: NoteDetailProps) {
  const router = useRouter();
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const hasRole = useWorkspaceStore((s) => s.hasRole);
  const canWrite = hasRole("member");
  const { data: note, isLoading, error } = useNote(wid ?? undefined, noteId);
  const updateNote = useUpdateNote(wid ?? undefined);

  const [isEditing, setIsEditing] = useState(false);
  const [isPromoteOpen, setIsPromoteOpen] = useState(false);
  // Codex F-9 fix (Sprint 24 Wave 2 P2): title/content autosave 별도 timer.
  // 기존: 공유 debounceRef → title 입력 1s 안에 content 입력 시 title save cancel (또는 그 반대).
  // 해결: 별도 ref 로 독립 debounce, 둘 다 안전하게 commit.
  const titleDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const contentDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 입력 추적용 ref — 명시 save 시 최신 값 읽기 (uncontrolled input 패턴, react-hooks/set-state-in-effect 회피)
  const titleRef = useRef<string>("");

  const editor = useEditor(
    {
      immediatelyRender: false,
      editable: isEditing,
      extensions: [StarterKit],
      content: (note?.content as Record<string, unknown>) ?? { type: "doc", content: [] },
      onUpdate: ({ editor: ed }) => {
        if (!isEditing) return;
        if (contentDebounceRef.current) clearTimeout(contentDebounceRef.current);
        contentDebounceRef.current = setTimeout(() => {
          updateNote.mutate({ id: noteId, data: { content: ed.getJSON() } });
        }, AUTOSAVE_DEBOUNCE_MS);
      },
    },
    [noteId, note?.id],
  );

  // editable 토글 시 editor 의 editable 도 sync
  useEffect(() => {
    if (editor) editor.setEditable(isEditing);
  }, [editor, isEditing]);

  // unmount cleanup — 두 timer 모두 정리 (Codex F-9)
  useEffect(() => {
    return () => {
      if (titleDebounceRef.current) clearTimeout(titleDebounceRef.current);
      if (contentDebounceRef.current) clearTimeout(contentDebounceRef.current);
    };
  }, []);

  // note fetch 완료 시 titleRef seed (사용자 입력 전 명시 save 대비). ref 만 mutation — setState 아님.
  // Codex F-15 fix (Sprint 24 Wave 2 P2): edit 중에는 server title 로 overwrite 안 함
  // (autosave invalidation/refetch 시 사용자 draft title 손실 회피).
  useEffect(() => {
    if (note && !isEditing) titleRef.current = note.title;
  }, [note, isEditing]);

  const handleTitleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      titleRef.current = value;
      if (!isEditing) return;
      // Codex F-9: title 전용 debounce (content 와 독립)
      if (titleDebounceRef.current) clearTimeout(titleDebounceRef.current);
      titleDebounceRef.current = setTimeout(() => {
        updateNote.mutate({ id: noteId, data: { title: value } });
      }, AUTOSAVE_DEBOUNCE_MS);
    },
    [isEditing, noteId, updateNote],
  );

  const handleSaveAndExit = useCallback(() => {
    // 명시 save: 두 debounce timer 모두 비우고 즉시 mutate (Codex F-9)
    if (titleDebounceRef.current) {
      clearTimeout(titleDebounceRef.current);
      titleDebounceRef.current = null;
    }
    if (contentDebounceRef.current) {
      clearTimeout(contentDebounceRef.current);
      contentDebounceRef.current = null;
    }
    if (editor) {
      updateNote.mutate({
        id: noteId,
        data: { title: titleRef.current, content: editor.getJSON() },
      });
    }
    setIsEditing(false);
  }, [editor, noteId, updateNote]);

  if (!wid) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          워크스페이스를 선택하세요
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          노트 불러오는 중...
        </p>
      </div>
    );
  }

  if (error || !note) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <p className="text-sm" style={{ color: "var(--error)" }}>
          노트를 불러오지 못했습니다
        </p>
        <button
          type="button"
          onClick={() => router.back()}
          className="text-sm underline"
          style={{ color: "var(--text-secondary)" }}
        >
          뒤로 가기
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto px-6 py-6">
      {/* 상단 툴바: 뒤로가기 + 편집/저장 + Promote + Export */}
      <div
        className="flex items-center justify-between gap-2 pb-3 mb-4 border-b"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <Link
          href="/notes"
          aria-label="뒤로 가기"
          data-testid="note-detail-back-button"
          className="inline-flex items-center gap-1 text-sm transition-colors hover:opacity-80"
          style={{ color: "var(--text-secondary)" }}
        >
          <ArrowLeft size={14} />
          <span>뒤로</span>
        </Link>
        <div className="flex items-center gap-2">
          {canWrite && !isEditing && (
            <button
              type="button"
              aria-label="편집"
              data-testid="note-detail-edit-button"
              onClick={() => setIsEditing(true)}
              className="inline-flex items-center gap-1.5 h-9 px-3 rounded-md cursor-pointer border text-xs font-medium transition-colors duration-150 hover:bg-[var(--surface-active)]"
              style={{
                borderColor: "var(--border)",
                color: "var(--text-secondary)",
              }}
            >
              <Pencil className="w-4 h-4" />
              <span>편집</span>
            </button>
          )}
          {canWrite && isEditing && (
            <button
              type="button"
              aria-label="저장 후 닫기"
              data-testid="note-detail-save-button"
              onClick={handleSaveAndExit}
              className="inline-flex items-center gap-1.5 h-9 px-3 rounded-md cursor-pointer text-xs font-medium transition-colors duration-150"
              style={{
                background: "var(--accent)",
                color: "var(--accent-foreground)",
              }}
            >
              <Check className="w-4 h-4" />
              <span>저장</span>
            </button>
          )}
          <button
            type="button"
            data-testid="note-detail-promote-button"
            onClick={() => setIsPromoteOpen(true)}
            className="inline-flex items-center gap-1.5 h-9 px-3 rounded-md cursor-pointer border text-xs font-medium transition-colors duration-150 hover:bg-[var(--surface-active)]"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-secondary)",
            }}
            aria-label="팀으로 올리기"
          >
            <ArrowUpRight className="w-4 h-4" />
            <span>팀으로 올리기</span>
          </button>
          <ExportButton exportFn={exportNote} id={noteId} title={note.title || "Untitled"} />
        </div>
      </div>

      {/* 제목 — readonly 모드에서는 h1, edit 모드에서는 uncontrolled input.
          key 로 note.id 를 묶어 다른 노트 전환 시 remount → fresh defaultValue. */}
      {isEditing ? (
        <input
          key={`title-${note.id}`}
          type="text"
          defaultValue={note.title}
          onChange={handleTitleChange}
          placeholder="제목 없음"
          data-testid="note-detail-title-input"
          className="w-full bg-transparent text-2xl font-bold outline-none mb-4"
          style={{
            color: "var(--text-primary)",
            fontFamily: "var(--font-display)",
          }}
        />
      ) : (
        <h1
          data-testid="note-detail-title"
          className="text-2xl font-bold mb-4"
          style={{
            color: "var(--text-primary)",
            fontFamily: "var(--font-display)",
          }}
        >
          {note.title || "제목 없음"}
        </h1>
      )}

      {/* Tiptap viewer / editor */}
      <div
        data-testid="note-detail-editor"
        className="flex-1 overflow-y-auto"
      >
        <EditorContent
          editor={editor}
          className="prose prose-invert max-w-none text-sm"
          style={{ color: "var(--text-primary)" }}
        />
      </div>

      {/* 저장 상태 표시 */}
      {isEditing && updateNote.isPending && (
        <p
          className="text-xs mt-2"
          style={{ color: "var(--accent)" }}
          data-testid="note-detail-saving-indicator"
        >
          저장 중...
        </p>
      )}

      {/* Promote 모달 */}
      <ItemPromoteModal
        itemType="note"
        itemId={noteId}
        sourceWorkspaceId={wid}
        open={isPromoteOpen}
        onOpenChange={setIsPromoteOpen}
      />
    </div>
  );
}
