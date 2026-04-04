"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { usePresignedUpload } from "@/features/upload/hooks";
import { useCreateMeeting } from "@/features/meetings/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";

const CONTENT_TYPES = [
  {
    id: "meeting",
    icon: "🎙️",
    title: "회의 녹음",
    description: "오디오/영상 파일을 업로드하면 AI가 자동으로 요약합니다",
  },
  {
    id: "note",
    icon: "📝",
    title: "노트 작성",
    description: "아이디어, 메모, 회의록을 자유롭게 작성하세요",
  },
  {
    id: "attachment",
    icon: "📎",
    title: "자료 업로드",
    description: "문서, PDF, 이미지 등 프로젝트 관련 자료를 업로드하세요",
  },
] as const;

type ContentType = (typeof CONTENT_TYPES)[number]["id"];

export default function NewContentPage() {
  const router = useRouter();
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const hasRole = useWorkspaceStore((s) => s.hasRole);

  const [selected, setSelected] = useState<ContentType>("meeting");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploadStep, setUploadStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const presignedUpload = usePresignedUpload();
  const createMeeting = useCreateMeeting(activeWorkspaceId ?? undefined);

  const isUploading = !!uploadStep;

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      if (!title) {
        setTitle(selectedFile.name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  const handleUpload = async () => {
    if (!file || !title || !activeWorkspaceId) return;

    setError(null);

    try {
      // 1. Presigned URL 발급 + R2 업로드
      setUploadStep("파일 업로드 중...");
      const fileKey = await presignedUpload.upload(file);

      // 2. 회의 생성 (202 Accepted)
      setUploadStep("회의 생성 중...");
      const meeting = await createMeeting.mutateAsync({
        title,
        fileKey,
      });

      // 3. 회의 상세 페이지로 이동
      router.push(`/meetings/${meeting.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "업로드 실패");
      setUploadStep(null);
    }
  };

  // Viewer는 콘텐츠 생성 불가
  if (!hasRole("member")) {
    return (
      <div
        className="flex flex-col items-center justify-center h-full gap-2"
        style={{ color: "var(--text-muted)" }}
      >
        <p className="text-sm">콘텐츠를 추가하려면 Member 이상 권한이 필요합니다</p>
        <button
          onClick={() => router.back()}
          className="text-xs underline cursor-pointer"
          style={{ color: "var(--accent)" }}
        >
          돌아가기
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-2xl font-bold mb-1"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          콘텐츠 추가
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          프로젝트에 추가할 콘텐츠 유형을 선택하세요
        </p>
      </div>

      {/* 유형 선택 카드 */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {CONTENT_TYPES.map((type) => (
          <button
            key={type.id}
            onClick={() => setSelected(type.id)}
            className="p-6 rounded border text-left transition-colors"
            style={{
              background: selected === type.id ? "var(--surface-hover)" : "var(--surface)",
              borderColor: selected === type.id ? "var(--accent)" : "var(--border-subtle)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <span className="text-3xl mb-3 block">{type.icon}</span>
            <h3
              className="text-sm font-semibold mb-1"
              style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
            >
              {type.title}
            </h3>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {type.description}
            </p>
          </button>
        ))}
      </div>

      {/* 회의 녹음 업로드 폼 */}
      {selected === "meeting" && (
        <div
          className="p-6 rounded border"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <h2
            className="text-lg font-semibold mb-4"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            회의 녹음
          </h2>

          <div className="space-y-4">
            {/* 제목 */}
            <div>
              <label className="block text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
                회의 제목
              </label>
              <input
                type="text"
                placeholder="회의 제목을 입력하세요"
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

            {/* 파일 드롭존 */}
            <div>
              <label className="block text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
                녹음 파일
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*,video/*,.mp3,.wav,.m4a,.mp4,.webm"
                onChange={handleFileSelect}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full flex flex-col items-center justify-center h-32 rounded border-2 border-dashed transition-colors"
                style={{
                  borderColor: file ? "var(--accent)" : "var(--border)",
                  color: "var(--text-muted)",
                  background: file ? "var(--accent-subtle)" : "transparent",
                }}
              >
                {file ? (
                  <>
                    <span className="text-2xl mb-1">✅</span>
                    <p className="text-sm" style={{ color: "var(--text-primary)" }}>
                      {file.name}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {(file.size / 1024).toFixed(1)} KB — 클릭하여 변경
                    </p>
                  </>
                ) : (
                  <>
                    <span className="text-2xl mb-1">🎙️</span>
                    <p className="text-sm">클릭하여 파일 선택</p>
                    <p className="text-xs mt-1">MP3, WAV, M4A, MP4, WebM</p>
                  </>
                )}
              </button>
            </div>

            {/* 에러 */}
            {error && (
              <div
                className="px-3 py-2 rounded text-sm"
                style={{
                  background: "rgba(248,113,113,0.1)",
                  color: "var(--error)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                {error}
              </div>
            )}

            {/* 업로드 진행 */}
            {uploadStep && (
              <div
                className="px-3 py-2 rounded text-sm"
                style={{
                  background: "var(--accent-subtle)",
                  color: "var(--accent)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                ⏳ {uploadStep}
              </div>
            )}

            {/* 업로드 버튼 */}
            <div className="flex justify-end">
              <button
                onClick={handleUpload}
                disabled={!file || !title || isUploading || !activeWorkspaceId}
                className="px-6 py-2 rounded text-sm font-medium transition-opacity"
                style={{
                  background: file && title && !isUploading ? "var(--accent)" : "var(--surface-active)",
                  color: file && title && !isUploading ? "var(--background)" : "var(--text-muted)",
                  borderRadius: "var(--radius-sm)",
                  cursor: !file || !title || isUploading ? "not-allowed" : "pointer",
                }}
              >
                {isUploading ? "업로드 중..." : "업로드 시작"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 노트 / 자료 (Sprint 2+) */}
      {(selected === "note" || selected === "attachment") && (
        <div
          className="p-6 rounded border text-center"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <p style={{ color: "var(--text-muted)" }}>
            {selected === "note" ? "노트 작성" : "자료 업로드"}은 Sprint 2에서 구현됩니다
          </p>
        </div>
      )}
    </div>
  );
}
