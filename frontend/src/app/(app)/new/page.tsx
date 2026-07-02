"use client";

import { useState, useRef } from "react";
import { Mic, StickyNote, Paperclip, Circle, CheckCircle2, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { usePresignedUpload } from "@/features/upload/hooks";
import { useRecording, type RecordingState } from "@/features/upload/useRecording";
import { useCreateMeeting, useCaptureText } from "@/features/meetings/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";

const CONTENT_TYPES = [
  {
    id: "meeting",
    icon: <Mic className="w-8 h-8" />,
    title: "회의 녹음",
    description: "오디오/영상 파일을 업로드하면 AI가 자동으로 요약합니다",
  },
  {
    id: "note",
    icon: <StickyNote className="w-8 h-8" />,
    title: "노트 작성",
    description: "아이디어, 메모, 회의록을 자유롭게 작성하세요",
  },
  {
    id: "attachment",
    icon: <Paperclip className="w-8 h-8" />,
    title: "자료 업로드",
    description: "문서, PDF, 이미지 등 프로젝트 관련 자료를 업로드하세요",
  },
] as const;

type ContentType = (typeof CONTENT_TYPES)[number]["id"];

export default function NewContentPage() {
  const router = useRouter();
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const hasRole = useWorkspaceStore((s) => s.hasRole);
  // workspaceRole을 직접 구독 → 역할 로드 시 리렌더 트리거
  const workspaceRole = useWorkspaceStore((s) => s.workspaceRole);

  const [selected, setSelected] = useState<ContentType>("meeting");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploadStep, setUploadStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const presignedUpload = usePresignedUpload(activeWorkspaceId ?? undefined);
  const createMeeting = useCreateMeeting(activeWorkspaceId ?? undefined);

  const isUploading = !!uploadStep;

  const [meetingTab, setMeetingTab] = useState<"audio" | "record" | "text">("audio");
  const [captureTitle, setCaptureTitle] = useState("");
  const [captureContent, setCaptureContent] = useState("");
  const [captureError, setCaptureError] = useState<string | null>(null);
  const captureTextMutation = useCaptureText(activeWorkspaceId ?? undefined);
  const isCapturing = captureTextMutation.isPending;

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

  const handleCapture = async () => {
    if (!captureTitle || captureContent.length < 50 || !activeWorkspaceId) return;
    setCaptureError(null);
    try {
      const result = await captureTextMutation.mutateAsync({
        title: captureTitle,
        transcriptText: captureContent,
      });
      router.push(`/meetings/${result.id}`);
    } catch (err) {
      setCaptureError(err instanceof Error ? err.message : "캡처 실패");
    }
  };

  // 역할 로딩 중 (null) = 아직 API 응답 대기, 잠시 대기
  // Viewer는 콘텐츠 생성 불가
  if (workspaceRole !== null && !hasRole("member")) {
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
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
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
            <span className="mb-3 block">{type.icon}</span>
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

          {/* 탭 */}
          <div className="flex gap-1 mb-4 border-b" style={{ borderColor: "var(--border-subtle)" }}>
            {(["audio", "record", "text"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setMeetingTab(tab)}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors"
                style={{
                  color: meetingTab === tab ? "var(--accent)" : "var(--text-muted)",
                  borderBottom: meetingTab === tab ? "2px solid var(--accent)" : "2px solid transparent",
                }}
              >
                {tab === "audio" ? (
                  <>
                    <Mic className="w-4 h-4" />
                    오디오 업로드
                  </>
                ) : tab === "record" ? (
                  <>
                    <Circle className="w-3 h-3 fill-red-500 text-red-500" />
                    직접 녹음
                  </>
                ) : (
                  <>
                    <StickyNote className="w-4 h-4" />
                    텍스트로 입력
                  </>
                )}
              </button>
            ))}
          </div>

          {meetingTab === "audio" && (
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
                  data-testid="meeting-file-input"
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
                      <CheckCircle2 className="w-6 h-6 mb-1" />
                      <p className="text-sm" style={{ color: "var(--text-primary)" }}>
                        {file.name}
                      </p>
                      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                        {(file.size / 1024).toFixed(1)} KB — 클릭하여 변경
                      </p>
                    </>
                  ) : (
                    <>
                      <Mic className="w-6 h-6 mb-1" />
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
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-sm"
                  style={{
                    background: "var(--accent-subtle)",
                    color: "var(--accent)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {uploadStep}
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
          )}

          {meetingTab === "record" && (
            <RecordingView
              workspaceId={activeWorkspaceId ?? undefined}
              onComplete={async (fileKey, recTitle) => {
                if (!activeWorkspaceId) return;
                const meeting = await createMeeting.mutateAsync({ title: recTitle, fileKey });
                router.push(`/meetings/${meeting.id}`);
              }}
            />
          )}

          {meetingTab === "text" && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
                  회의 제목
                </label>
                <input
                  type="text"
                  placeholder="회의 제목을 입력하세요"
                  value={captureTitle}
                  onChange={(e) => setCaptureTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none"
                  style={{
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                    borderRadius: "var(--radius-sm)",
                  }}
                />
              </div>

              <div>
                <label className="block text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
                  회의 내용 <span style={{ color: "var(--text-muted)" }}>(최소 50자)</span>
                </label>
                <textarea
                  placeholder="회의록, 스크립트, 메모를 붙여넣으세요"
                  value={captureContent}
                  onChange={(e) => setCaptureContent(e.target.value)}
                  rows={10}
                  className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none resize-y"
                  style={{
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                    borderRadius: "var(--radius-sm)",
                  }}
                />
                <p
                  className="text-xs mt-1"
                  style={{ color: captureContent.length < 50 ? "var(--error)" : "var(--text-muted)" }}
                >
                  {captureContent.length}자
                  {captureContent.length < 50 ? ` (${50 - captureContent.length}자 더 필요)` : ""}
                </p>
              </div>

              {captureError && (
                <div
                  className="px-3 py-2 rounded text-sm"
                  style={{
                    background: "rgba(248,113,113,0.1)",
                    color: "var(--error)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  {captureError}
                </div>
              )}

              {isCapturing && (
                <div
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-sm"
                  style={{
                    background: "var(--accent-subtle)",
                    color: "var(--accent)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  <Loader2 className="w-4 h-4 animate-spin" />
                  AI가 처리 중입니다...
                </div>
              )}

              <div className="flex justify-end">
                <button
                  onClick={handleCapture}
                  disabled={!captureTitle || captureContent.length < 50 || isCapturing || !activeWorkspaceId}
                  className="px-6 py-2 rounded text-sm font-medium"
                  style={{
                    background:
                      captureTitle && captureContent.length >= 50 && !isCapturing
                        ? "var(--accent)"
                        : "var(--surface-active)",
                    color:
                      captureTitle && captureContent.length >= 50 && !isCapturing
                        ? "var(--background)"
                        : "var(--text-muted)",
                    borderRadius: "var(--radius-sm)",
                    cursor:
                      !captureTitle || captureContent.length < 50 || isCapturing
                        ? "not-allowed"
                        : "pointer",
                  }}
                >
                  {isCapturing ? "처리 중..." : "AI 분석 시작"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 노트 작성 — /notes 의 빠른 메모로 안내 */}
      {selected === "note" && (
        <div
          className="p-8 rounded border text-center space-y-4"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <div>
            <p
              className="flex items-center justify-center gap-1.5 text-base font-semibold mb-1"
              style={{
                color: "var(--text-primary)",
                fontFamily: "var(--font-display)",
              }}
            >
              <StickyNote className="w-4 h-4" />
              빠른 메모로 이동
            </p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              아이디어 · 회의록 · 자유 메모는 빠른 메모에서 작성합니다.
            </p>
          </div>
          <button
            onClick={() => router.push("/notes")}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            빠른 메모 열기
          </button>
        </div>
      )}

      {/* 자료 업로드 placeholder — 추후 SourceAddModal 또는 별도 페이지 통합 */}
      {selected === "attachment" && (
        <div
          className="p-6 rounded border text-center"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <p style={{ color: "var(--text-muted)" }}>
            자료 업로드는 곧 제공됩니다 (문서·PDF·이미지)
          </p>
        </div>
      )}
    </div>
  );
}

// 직접 녹음 탭 UI — useRecording + usePresignedUpload 조합 (독립 title 상태)
function RecordingView({
  workspaceId,
  onComplete,
}: {
  workspaceId: string | undefined;
  onComplete: (fileKey: string, title: string) => Promise<void>;
}) {
  const { state, duration, startRecording, stopRecording, recordedBlob, objectUrl, error, reset } =
    useRecording();
  const presignedUpload = usePresignedUpload(workspaceId);
  const [recordTitle, setRecordTitle] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [includeShareAudio, setIncludeShareAudio] = useState(false);
  const supportsShareAudio =
    typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getDisplayMedia;

  const formatDuration = (sec: number) => {
    const m = Math.floor(sec / 60).toString().padStart(2, '0');
    const s = (sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleUpload = async () => {
    if (!recordedBlob || !workspaceId) return;
    if (recordedBlob.size === 0) {
      setUploadError('녹음 데이터가 비어 있습니다. 다시 녹음해 주세요.');
      return;
    }
    setIsUploading(true);
    setUploadError(null);
    try {
      const ext = recordedBlob.type.includes('mp4') ? 'mp4' : 'webm';
      const file = new File([recordedBlob], `recording-${Date.now()}.${ext}`, {
        type: recordedBlob.type,
      });
      const fileKey = await presignedUpload.upload(file);
      const title = recordTitle.trim() || `녹음_${new Date().toLocaleDateString()}`;
      await onComplete(fileKey, title);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : '업로드 실패');
    } finally {
      setIsUploading(false);
    }
  };

  const stateLabel: Record<RecordingState, string> = {
    idle: '버튼을 눌러 마이크 녹음을 시작하세요',
    recording: '녹음 중… 버튼을 눌러 중지',
    stopped: '녹음 완료. 미리 듣고 업로드하세요',
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>
          회의 제목
        </label>
        <input
          type="text"
          placeholder="회의 제목을 입력하세요"
          value={recordTitle}
          onChange={(e) => setRecordTitle(e.target.value)}
          className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none"
          style={{ borderColor: 'var(--border)', color: 'var(--text-primary)', borderRadius: 'var(--radius-sm)' }}
        />
      </div>

      <div className="flex flex-col items-center gap-4 py-6">
        <div className="text-4xl font-mono tabular-nums" style={{ color: 'var(--text-primary)' }}>
          {formatDuration(duration)}
        </div>

        {(error ?? uploadError) && (
          <p className="text-sm" style={{ color: 'var(--error)' }}>{error ?? uploadError}</p>
        )}

        {state === 'idle' && (
          <>
            <label className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
              <input
                type="checkbox"
                checked={includeShareAudio}
                disabled={!supportsShareAudio}
                onChange={(e) => setIncludeShareAudio(e.target.checked)}
              />
              회의/영상 소리도 함께 녹음 (Zoom, Google Meet, YouTube 등)
            </label>
            {includeShareAudio && supportsShareAudio && (
              <p className="text-xs text-center max-w-sm" style={{ color: 'var(--text-muted)' }}>
                공유 창에서 Google Meet·YouTube 탭 소리는 해당 탭을 선택하고 &ldquo;탭 오디오 공유&rdquo;를
                체크해주세요. Zoom 데스크톱 앱처럼 브라우저 밖의 소리는 &ldquo;전체 화면&rdquo;을 선택하고
                시스템 오디오를 켜주세요 (macOS는 14.2 이상 + Chrome 141 이상 필요, PC의 다른 소리도 함께
                녹음될 수 있어요).
              </p>
            )}
            {!supportsShareAudio && (
              <p className="text-xs text-center max-w-xs" style={{ color: 'var(--text-muted)' }}>
                이 브라우저는 회의/영상 소리 캡처를 지원하지 않습니다 (Chrome/Edge 권장).
              </p>
            )}
            <button
              type="button"
              onClick={() => void startRecording({ includeShareAudio })}
              className="w-16 h-16 rounded-full flex items-center justify-center transition-colors"
              style={{ background: 'var(--accent)' }}
              aria-label="녹음 시작"
            >
              <span className="w-6 h-6 rounded-full bg-white" />
            </button>
          </>
        )}

        {state === 'recording' && (
          <button
            type="button"
            onClick={stopRecording}
            className="w-16 h-16 rounded-full flex items-center justify-center transition-colors animate-pulse"
            style={{ background: 'var(--error, #ef4444)' }}
            aria-label="녹음 중지"
          >
            <span className="w-5 h-5 rounded-sm bg-white" />
          </button>
        )}

        {state === 'stopped' && recordedBlob && (
          <div className="flex flex-col items-center gap-3 w-full max-w-sm">
            {objectUrl && <audio controls src={objectUrl} className="w-full" />}
            <div className="flex gap-2 w-full">
              <button
                type="button"
                onClick={reset}
                className="flex-1 px-4 py-2 rounded border text-sm"
                style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
              >
                다시 녹음
              </button>
              <button
                type="button"
                onClick={() => void handleUpload()}
                disabled={isUploading}
                className="flex-1 px-4 py-2 rounded text-sm disabled:opacity-50"
                style={{ background: 'var(--accent)', color: 'var(--accent-foreground, white)' }}
              >
                {isUploading ? '업로드 중…' : '업로드 & 분석'}
              </button>
            </div>
          </div>
        )}

        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          {stateLabel[state]}
        </p>
      </div>
    </div>
  );
}
