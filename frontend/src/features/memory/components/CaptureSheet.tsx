// Memory capture sheet — 텍스트 / 음성 두 모드를 한 시트에서 처리
"use client";

import { useState } from "react";
import { Mic, Send, Square, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  useCaptureText,
  useCaptureVoice,
  useRecorder,
} from "../hooks";

interface CaptureSheetProps {
  workspaceId: string | undefined;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CaptureSheet({
  workspaceId,
  open,
  onOpenChange,
}: CaptureSheetProps) {
  const [text, setText] = useState("");
  const captureText = useCaptureText(workspaceId);
  const captureVoice = useCaptureVoice(workspaceId);
  const recorder = useRecorder();

  const isRecording = recorder.state === "recording";
  const isUnsupported = recorder.state === "unsupported";
  const isPermissionDenied = recorder.state === "permission-denied";

  function handleClose() {
    setText("");
    recorder.cancel();
    onOpenChange(false);
  }

  async function handleSubmitText() {
    const trimmed = text.trim();
    if (!trimmed || !workspaceId) return;
    await captureText.mutateAsync(trimmed);
    handleClose();
  }

  function handleToggleRecord() {
    if (isRecording) {
      recorder.stop();
      return;
    }
    recorder.start((blob, filename) => {
      captureVoice.mutate(
        { blob, filename },
        { onSuccess: handleClose }
      );
    });
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="h-[60vh] p-6">
        <SheetHeader>
          <SheetTitle>메모 추가</SheetTitle>
        </SheetHeader>
        <div className="mt-4 flex flex-col gap-3">
          <Textarea
            placeholder="지금 떠오른 생각, 결정, 아이디어를 적어주세요…"
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={6}
            disabled={isRecording}
            autoFocus
          />
          <div className="flex items-center justify-between gap-2">
            <Button
              type="button"
              variant={isRecording ? "destructive" : "outline"}
              onClick={handleToggleRecord}
              disabled={isUnsupported || captureText.isPending}
            >
              {isRecording ? (
                <>
                  <Square className="mr-2 h-4 w-4" /> 녹음 중지
                </>
              ) : (
                <>
                  <Mic className="mr-2 h-4 w-4" /> 음성 녹음
                </>
              )}
            </Button>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={handleClose}
                disabled={captureText.isPending || captureVoice.isPending}
              >
                <X className="mr-2 h-4 w-4" /> 취소
              </Button>
              <Button
                type="button"
                onClick={handleSubmitText}
                disabled={
                  !text.trim() ||
                  captureText.isPending ||
                  captureVoice.isPending ||
                  isRecording
                }
              >
                <Send className="mr-2 h-4 w-4" />
                {captureText.isPending ? "저장 중…" : "저장"}
              </Button>
            </div>
          </div>
          {isPermissionDenied && (
            <p className="text-sm text-destructive">
              마이크 권한이 거부되었습니다. 브라우저 설정에서 허용해 주세요.
            </p>
          )}
          {isUnsupported && (
            <p className="text-sm text-muted-foreground">
              이 브라우저는 음성 녹음을 지원하지 않습니다. 텍스트로 입력해 주세요.
            </p>
          )}
          {captureVoice.isPending && (
            <p className="text-sm text-muted-foreground">
              음성 업로드 중…
            </p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
