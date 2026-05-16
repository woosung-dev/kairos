// 소스 추가 모달 — 4가지 입력 방법 (파일/메모/URL/텍스트) → 기존 notes / meetings API 재사용
"use client";

import { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useCreateNote } from "@/features/notes/hooks";
import { useCreateMeeting } from "@/features/meetings/hooks";
import { usePresignedUpload } from "@/features/upload/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";

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

/* ── 헬퍼: URL → tiptap 링크 문서 ── */
function urlToTiptapDoc(url: string, note?: string): Record<string, unknown> {
  const paragraphs: Array<Record<string, unknown>> = [
    {
      type: "paragraph",
      content: [
        {
          type: "text",
          marks: [{ type: "link", attrs: { href: url } }],
          text: url,
        },
      ],
    },
  ];
  if (note && note.trim()) {
    paragraphs.push({
      type: "paragraph",
      content: [{ type: "text", text: note.trim() }],
    });
  }
  return { type: "doc", content: paragraphs };
}

/* ── 헬퍼: 파일이 오디오/비디오인지 — STT 파이프라인 진입 분기 ── */
function isAudioOrVideo(file: File): boolean {
  return file.type.startsWith("audio/") || file.type.startsWith("video/");
}

/* ── 헬퍼: 파일이 텍스트 계열인지 — note 적재 분기 ── */
function isPlainText(file: File): boolean {
  if (file.type.startsWith("text/")) return true;
  const lower = file.name.toLowerCase();
  return lower.endsWith(".txt") || lower.endsWith(".md");
}

/* ── 입력 방법 타입 ── */

type InputMethod = "file" | "memo" | "url" | "paste";

interface InputMethodCard {
  id: InputMethod;
  icon: string;
  label: string;
  description: string;
}

const INPUT_METHODS: InputMethodCard[] = [
  {
    id: "file",
    icon: "📄",
    label: "파일 업로드",
    description: "오디오, 문서, PDF, 이미지를 드래그 앤 드롭하세요",
  },
  {
    id: "memo",
    icon: "📝",
    label: "빠른 메모",
    description: "아이디어나 메모를 빠르게 기록합니다",
  },
  {
    id: "url",
    icon: "🔗",
    label: "URL 입력",
    description: "웹 페이지 URL을 입력하면 내용을 가져옵니다",
  },
  {
    id: "paste",
    icon: "📋",
    label: "텍스트 붙여넣기",
    description: "텍스트를 복사하여 직접 붙여넣으세요",
  },
];

/* ── 컴포넌트 ── */

interface SourceAddModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigateToMemo?: () => void;
}

export function SourceAddModal({ isOpen, onClose, onNavigateToMemo }: SourceAddModalProps) {
  const [selectedMethod, setSelectedMethod] = useState<InputMethod | null>(null);

  if (!isOpen) return null;

  function handleMethodSelect(method: InputMethod) {
    if (method === "memo" && onNavigateToMemo) {
      onClose();
      onNavigateToMemo();
      return;
    }
    setSelectedMethod(method);
  }

  function handleBack() {
    setSelectedMethod(null);
  }

  return (
    /* 백드롭 */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.5)" }}
    >
      {/* 오버레이 클릭으로 닫기 */}
      <div className="absolute inset-0" onClick={onClose} />

      {/* 모달 */}
      <div
        className="relative w-full max-w-lg mx-4 p-6 rounded-lg border"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            {selectedMethod && (
              <button
                onClick={handleBack}
                className="text-xs mr-1"
                style={{ color: "var(--text-muted)", cursor: "pointer", minHeight: "44px" }}
              >
                ← 뒤로
              </button>
            )}
            <h2
              className="text-lg font-bold"
              style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
            >
              소스 추가
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-sm"
            style={{ color: "var(--text-muted)", cursor: "pointer", minHeight: "44px" }}
          >
            &times;
          </button>
        </div>

        {/* 입력 방법 선택 */}
        {!selectedMethod && (
          <div className="grid grid-cols-2 gap-3">
            {INPUT_METHODS.map((method) => (
              <button
                key={method.id}
                onClick={() => handleMethodSelect(method.id)}
                className="p-4 rounded-lg border text-left transition-colors"
                style={{
                  background: "var(--background)",
                  borderColor: "var(--border-subtle)",
                  borderRadius: "var(--radius-lg)",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
                onMouseOver={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
                onMouseOut={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
              >
                <span className="text-2xl mb-2 block">{method.icon}</span>
                <h3 className="text-sm font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
                  {method.label}
                </h3>
                <p className="text-[11px] leading-snug" style={{ color: "var(--text-muted)" }}>
                  {method.description}
                </p>
              </button>
            ))}
          </div>
        )}

        {/* 파일 업로드 뷰 */}
        {selectedMethod === "file" && <FileUploadView onClose={onClose} />}

        {/* URL 입력 뷰 */}
        {selectedMethod === "url" && <UrlInputView onClose={onClose} />}

        {/* 텍스트 붙여넣기 뷰 */}
        {selectedMethod === "paste" && <PasteView onClose={onClose} />}
      </div>
    </div>
  );
}

/* ── 파일 업로드 뷰 ── */

function FileUploadView({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const presignedUpload = usePresignedUpload(wid ?? undefined);
  const createMeeting = useCreateMeeting(wid ?? undefined);
  const createNote = useCreateNote(wid ?? undefined);

  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
    }
  }, []);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  }

  async function handleSubmit() {
    if (!file || !wid || isSubmitting) return;
    setIsSubmitting(true);
    const baseTitle = file.name.replace(/\.[^/.]+$/, "");

    try {
      if (isAudioOrVideo(file)) {
        // 오디오/비디오 → 회의 STT 파이프라인 (presigned upload + create meeting)
        toast.message("파일 업로드 중...");
        const fileKey = await presignedUpload.upload(file);
        const meeting = await createMeeting.mutateAsync({
          title: baseTitle,
          fileKey,
        });
        toast.success(`"${file.name}" 처리를 시작합니다`);
        onClose();
        router.push(`/meetings/${meeting.id}`);
      } else if (isPlainText(file)) {
        // 텍스트 파일 (.txt/.md) → 노트 적재
        const text = await file.text();
        await createNote.mutateAsync({
          title: baseTitle,
          content: textToTiptapDoc(text),
        });
        toast.success(`"${file.name}" 메모로 저장됨`);
        onClose();
      } else {
        toast.message(`"${file.name}" 형식은 곧 지원될 예정입니다 (BL-044 후속)`);
        setIsSubmitting(false);
        return;
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "업로드 실패";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  }

  const canSubmit = !!file && !!wid && !isSubmitting;

  return (
    <div className="space-y-4">
      {/* 드래그 앤 드롭 영역 */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className="flex flex-col items-center justify-center h-40 rounded-lg border-2 border-dashed transition-colors"
        style={{
          borderColor: isDragging ? "var(--accent)" : file ? "var(--accent)" : "var(--border)",
          background: isDragging ? "var(--accent-subtle)" : file ? "var(--accent-subtle)" : "transparent",
          cursor: "pointer",
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileChange}
          className="hidden"
          accept="audio/*,video/*,.pdf,.doc,.docx,.txt,.md,.png,.jpg,.jpeg"
        />
        {file ? (
          <>
            <span className="text-2xl mb-2">✅</span>
            <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
              {file.name}
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {(file.size / 1024).toFixed(1)} KB
            </p>
          </>
        ) : (
          <>
            <span className="text-3xl mb-2">📄</span>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              파일을 여기에 드래그하거나 클릭하여 선택
            </p>
            <p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>
              오디오/비디오 → 회의, 텍스트(.txt/.md) → 노트
            </p>
          </>
        )}
      </div>

      {/* 제출 버튼 */}
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{
            background: canSubmit ? "var(--accent)" : "var(--surface-active)",
            color: canSubmit ? "var(--background)" : "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            cursor: canSubmit ? "pointer" : "not-allowed",
            minHeight: "44px",
          }}
        >
          {isSubmitting ? "처리 중..." : "업로드"}
        </button>
      </div>
    </div>
  );
}

/* ── URL 입력 뷰 ── */

function UrlInputView({ onClose }: { onClose: () => void }) {
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const createNote = useCreateNote(wid ?? undefined);
  const [url, setUrl] = useState("");
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    const trimmed = url.trim();
    if (!trimmed || !wid || isSubmitting) return;

    setIsSubmitting(true);
    try {
      // URL parsing: 도메인을 노트 제목으로 사용
      let host = trimmed;
      try {
        host = new URL(trimmed).hostname || trimmed;
      } catch {
        // invalid URL - 전체 문자열을 제목으로
      }
      await createNote.mutateAsync({
        title: `🔗 ${host}`,
        content: urlToTiptapDoc(trimmed, note),
      });
      toast.success("URL이 메모로 저장되었습니다");
      onClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "저장 실패";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  }

  const canSubmit = !!url.trim() && !!wid && !isSubmitting;

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs mb-1.5" style={{ color: "var(--text-secondary)" }}>
          URL 주소
        </label>
        <input
          type="url"
          placeholder="https://example.com/article"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            borderRadius: "var(--radius-sm)",
          }}
        />
      </div>
      <div>
        <label className="block text-xs mb-1.5" style={{ color: "var(--text-secondary)" }}>
          메모 (선택)
        </label>
        <textarea
          placeholder="URL에 대한 짧은 설명을 남기세요"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none resize-none"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            borderRadius: "var(--radius-sm)",
          }}
        />
      </div>
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{
            background: canSubmit ? "var(--accent)" : "var(--surface-active)",
            color: canSubmit ? "var(--background)" : "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            cursor: canSubmit ? "pointer" : "not-allowed",
            minHeight: "44px",
          }}
        >
          {isSubmitting ? "저장 중..." : "가져오기"}
        </button>
      </div>
    </div>
  );
}

/* ── 텍스트 붙여넣기 뷰 ── */

function PasteView({ onClose }: { onClose: () => void }) {
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  const createNote = useCreateNote(wid ?? undefined);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    const trimmedText = text.trim();
    if (!trimmedText || !wid || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const noteTitle = title.trim() || trimmedText.slice(0, 40);
      await createNote.mutateAsync({
        title: noteTitle,
        content: textToTiptapDoc(trimmedText),
      });
      toast.success("텍스트가 저장되었습니다");
      onClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "저장 실패";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  }

  const canSubmit = !!text.trim() && !!wid && !isSubmitting;

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs mb-1.5" style={{ color: "var(--text-secondary)" }}>
          제목 (선택)
        </label>
        <input
          type="text"
          placeholder="콘텐츠 제목"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            borderRadius: "var(--radius-sm)",
          }}
        />
      </div>
      <div>
        <label className="block text-xs mb-1.5" style={{ color: "var(--text-secondary)" }}>
          텍스트 내용
        </label>
        <textarea
          placeholder="텍스트를 붙여넣으세요..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={8}
          className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none resize-none"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            borderRadius: "var(--radius-sm)",
          }}
        />
      </div>
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{
            background: canSubmit ? "var(--accent)" : "var(--surface-active)",
            color: canSubmit ? "var(--background)" : "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            cursor: canSubmit ? "pointer" : "not-allowed",
            minHeight: "44px",
          }}
        >
          {isSubmitting ? "저장 중..." : "저장"}
        </button>
      </div>
    </div>
  );
}
