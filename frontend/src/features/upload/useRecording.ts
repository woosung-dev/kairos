// 브라우저 마이크 녹음을 관리하는 훅 — MediaRecorder API 기반
'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

export type RecordingState = 'idle' | 'recording' | 'stopped';

export interface UseRecordingReturn {
  state: RecordingState;
  duration: number;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  recordedBlob: Blob | null;
  objectUrl: string | null;
  error: string | null;
  reset: () => void;
}

const SUPPORTED_MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/mp4',
];

function getSupportedMimeType(): string {
  for (const mt of SUPPORTED_MIME_TYPES) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(mt)) return mt;
  }
  return '';
}

export function useRecording(): UseRecordingReturn {
  const [state, setState] = useState<RecordingState>('idle');
  const [duration, setDuration] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  // getUserMedia 비동기 완료 전 중복 호출 방지
  const isStartingRef = useRef(false);
  // 언마운트 후 getUserMedia resolve 시 마이크 누수 방지
  const isMountedRef = useRef(true);

  const revokeObjectUrl = () => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
  };

  const startRecording = useCallback(async () => {
    // getUserMedia resolve 이전 중복 호출 방지 (in-flight guard)
    if (isStartingRef.current || mediaRecorderRef.current?.state === 'recording') return;
    isStartingRef.current = true;

    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      isStartingRef.current = false;
      setError('이 브라우저는 마이크 녹음을 지원하지 않습니다');
      return;
    }

    setError(null);
    setRecordedBlob(null);
    revokeObjectUrl();
    setObjectUrl(null);
    chunksRef.current = [];

    let stream: MediaStream | null = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // getUserMedia resolve 후 언마운트된 경우 마이크 즉시 해제
      if (!isMountedRef.current) {
        stream.getTracks().forEach((t) => t.stop());
        isStartingRef.current = false;
        return;
      }
      streamRef.current = stream;

      const mimeType = getSupportedMimeType();
      if (!mimeType) {
        isStartingRef.current = false;
        stream.getTracks().forEach((t) => t.stop());
        setError('이 브라우저에서 지원하는 오디오 포맷이 없습니다');
        return;
      }

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        const url = URL.createObjectURL(blob);
        objectUrlRef.current = url;
        setRecordedBlob(blob);
        setObjectUrl(url);
        stream?.getTracks().forEach((t) => t.stop());
      };

      recorder.start(100);
      setState('recording');
      setDuration(0);
      isStartingRef.current = false;

      timerRef.current = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);
    } catch (err) {
      isStartingRef.current = false;
      stream?.getTracks().forEach((t) => t.stop());
      setError(err instanceof Error ? err.message : '마이크 접근 실패');
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
      setState('stopped');
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  }, []);

  const reset = useCallback(() => {
    revokeObjectUrl();
    setState('idle');
    setDuration(0);
    setRecordedBlob(null);
    setObjectUrl(null);
    setError(null);
    chunksRef.current = [];
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (timerRef.current) clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      revokeObjectUrl();
    };
  }, []);

  return { state, duration, startRecording, stopRecording, recordedBlob, objectUrl, error, reset };
}
