// Sprint 15 Memory 도메인 React Query 훅 + MediaRecorder MIME negotiation
"use client";

import { useAuth } from "@clerk/nextjs";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useRef, useState } from "react";
import { toast } from "sonner";
import {
  captureText,
  captureVoice,
  getMemory,
  memoryKeys,
  promoteMemory,
  recallMemory,
} from "./api";

// MIME 우선순위 — Chrome (opus webm) → 일반 webm → iOS Safari (mp4) → AAC fallback.
// patch §7 P-R4 (A1 fix): MediaRecorder.isTypeSupported로 동적 negotiation.
const MIME_PRIORITY = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/aac",
] as const;

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  for (const mime of MIME_PRIORITY) {
    if (MediaRecorder.isTypeSupported(mime)) return mime;
  }
  return undefined;
}

/**
 * 텍스트 메모 capture mutation
 */
export function useCaptureText(workspaceId: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (text: string) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      if (!workspaceId) throw new Error("워크스페이스가 선택되지 않았습니다");
      return captureText(token, workspaceId, text);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.all });
      // 저장 후 사용자 피드백 — sheet 즉시 닫혀서 confirm 없으면 dead UX.
      toast.success("메모를 저장했어요. AI 정리 중…");
    },
    onError: (err: Error) => {
      toast.error(err.message || "메모 저장에 실패했습니다");
    },
  });
}

/**
 * 음성 메모 capture mutation
 */
export function useCaptureVoice(workspaceId: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { blob: Blob; filename: string }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      if (!workspaceId) throw new Error("워크스페이스가 선택되지 않았습니다");
      return captureVoice(token, workspaceId, input.blob, input.filename);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.all });
      toast.success("음성을 업로드했어요. STT + AI 정리 중…");
    },
    onError: (err: Error) => {
      toast.error(err.message || "음성 메모 저장에 실패했습니다");
    },
  });
}

/**
 * Memory recall query — 디바운싱은 호출 측에서 수행하고, q를 그대로 전달.
 */
export function useRecall(
  workspaceId: string | undefined,
  q: string,
  enabled = true
) {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: memoryKeys.recall(workspaceId ?? "", q),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      if (!workspaceId) throw new Error("워크스페이스가 선택되지 않았습니다");
      return recallMemory(token, workspaceId, q);
    },
    enabled: enabled && !!workspaceId && q.trim().length >= 2,
    staleTime: 30_000,
  });
}

/**
 * R6: Memory promote mutation — 원본 보존 + target team ws 복제 (1-button).
 * 성공 시 invalidate + toast. 실패 시 toast로 사용자 피드백.
 */
export function usePromote(workspaceId: string | undefined) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      memoryId: string;
      targetWorkspaceId: string;
    }) => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      if (!workspaceId) throw new Error("워크스페이스가 선택되지 않았습니다");
      return promoteMemory(
        token,
        workspaceId,
        input.memoryId,
        input.targetWorkspaceId
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.all });
      toast.success("팀에 복사 중…");
    },
    onError: (err: Error) => {
      toast.error(err.message || "팀으로 올리는 데 실패했어요");
    },
  });
}

/**
 * Memory 단건 polling 훅 (R1 status processing → active 전환 추적용)
 */
export function useMemoryDetail(
  workspaceId: string | undefined,
  memoryId: string | undefined
) {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: memoryKeys.detail(workspaceId ?? "", memoryId ?? ""),
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      if (!workspaceId || !memoryId) throw new Error("필수 파라미터 누락");
      return getMemory(token, workspaceId, memoryId);
    },
    enabled: !!workspaceId && !!memoryId,
  });
}

export type RecorderState =
  | "idle"
  | "recording"
  | "permission-denied"
  | "unsupported";

/**
 * MediaRecorder 래퍼 — MIME negotiation + 권한/지원 상태 노출.
 * stop 콜백에 (blob, filename) 전달, 호출자는 mutation으로 업로드.
 */
export function useRecorder() {
  const [state, setState] = useState<RecorderState>("idle");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  async function start(onStop: (blob: Blob, filename: string) => void) {
    if (typeof MediaRecorder === "undefined") {
      setState("unsupported");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mime = pickMimeType();
      const recorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      const actualMime = recorder.mimeType || "audio/webm";
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: actualMime });
        const ext = actualMime.includes("mp4")
          ? "mp4"
          : actualMime.includes("aac")
            ? "aac"
            : "webm";
        const filename = `voice-${Date.now()}.${ext}`;
        onStop(blob, filename);
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setState("idle");
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setState("recording");
    } catch (err) {
      console.error("[useRecorder] start failed", err);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setState("permission-denied");
    }
  }

  function stop() {
    mediaRecorderRef.current?.stop();
  }

  function cancel() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    setState("idle");
  }

  return { state, start, stop, cancel };
}
