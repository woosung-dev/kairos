"use client";

import { useState, useRef, useCallback } from "react";
import { toast } from "sonner";

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
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
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

  function handleSubmit() {
    if (!file) return;
    toast.success(`"${file.name}" 업로드가 시작되었습니다`);
    onClose();
  }

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
              오디오, PDF, 문서, 이미지
            </p>
          </>
        )}
      </div>

      {/* 제출 버튼 */}
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={!file}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{
            background: file ? "var(--accent)" : "var(--surface-active)",
            color: file ? "var(--background)" : "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            cursor: file ? "pointer" : "not-allowed",
            minHeight: "44px",
          }}
        >
          업로드
        </button>
      </div>
    </div>
  );
}

/* ── URL 입력 뷰 ── */

function UrlInputView({ onClose }: { onClose: () => void }) {
  const [url, setUrl] = useState("");

  function handleSubmit() {
    if (!url.trim()) return;
    toast.success("URL에서 콘텐츠를 가져오는 중...");
    onClose();
  }

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
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={!url.trim()}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{
            background: url.trim() ? "var(--accent)" : "var(--surface-active)",
            color: url.trim() ? "var(--background)" : "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            cursor: url.trim() ? "pointer" : "not-allowed",
            minHeight: "44px",
          }}
        >
          가져오기
        </button>
      </div>
    </div>
  );
}

/* ── 텍스트 붙여넣기 뷰 ── */

function PasteView({ onClose }: { onClose: () => void }) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");

  function handleSubmit() {
    if (!text.trim()) return;
    toast.success("텍스트가 저장되었습니다");
    onClose();
  }

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
          disabled={!text.trim()}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{
            background: text.trim() ? "var(--accent)" : "var(--surface-active)",
            color: text.trim() ? "var(--background)" : "var(--text-muted)",
            borderRadius: "var(--radius-sm)",
            cursor: text.trim() ? "pointer" : "not-allowed",
            minHeight: "44px",
          }}
        >
          저장
        </button>
      </div>
    </div>
  );
}
