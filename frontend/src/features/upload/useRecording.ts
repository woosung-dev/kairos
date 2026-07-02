// 브라우저 마이크 녹음을 관리하는 훅 — MediaRecorder API 기반
'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

export type RecordingState = 'idle' | 'recording' | 'stopped';

export interface StartRecordingOptions {
  // true면 마이크와 함께 화면 공유 오디오(탭 오디오 또는 시스템 오디오)를 믹싱해 녹음
  includeShareAudio?: boolean;
}

export interface UseRecordingReturn {
  state: RecordingState;
  duration: number;
  startRecording: (options?: StartRecordingOptions) => Promise<void>;
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
  // 화면 공유 오디오 믹싱 모드에서만 사용 — 마이크 스트림, 공유 스트림, 믹싱용 AudioContext
  const micStreamRef = useRef<MediaStream | null>(null);
  const displayStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
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

  const startRecording = useCallback(async (options?: StartRecordingOptions) => {
    // getUserMedia resolve 이전 중복 호출 방지 (in-flight guard)
    if (isStartingRef.current || mediaRecorderRef.current?.state === 'recording') return;
    isStartingRef.current = true;

    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      isStartingRef.current = false;
      setError('이 브라우저는 마이크 녹음을 지원하지 않습니다');
      return;
    }

    const includeShareAudio = options?.includeShareAudio ?? false;
    if (includeShareAudio && !navigator.mediaDevices.getDisplayMedia) {
      isStartingRef.current = false;
      setError('이 브라우저는 회의/영상 소리 캡처를 지원하지 않습니다 (Chrome/Edge 권장)');
      return;
    }

    setError(null);
    setRecordedBlob(null);
    revokeObjectUrl();
    setObjectUrl(null);
    chunksRef.current = [];

    let micStream: MediaStream | null = null;
    let displayStream: MediaStream | null = null;
    let audioContext: AudioContext | null = null;

    const cleanupAuxStreams = () => {
      micStream?.getTracks().forEach((t) => t.stop());
      displayStream?.getTracks().forEach((t) => t.stop());
      audioContext?.close().catch(() => {});
    };

    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // getUserMedia resolve 후 언마운트된 경우 마이크 즉시 해제
      if (!isMountedRef.current) {
        cleanupAuxStreams();
        isStartingRef.current = false;
        return;
      }

      let stream: MediaStream = micStream;

      if (includeShareAudio) {
        // 공유 다이얼로그 취소 시 NotAllowedError로 reject → catch 블록에서 마이크까지 정리
        // systemAudio: 'include' — 전체 화면/창 공유 선택 시 시스템 오디오(Zoom 데스크톱 앱 등)
        // 옵션을 기본 노출시키는 Chromium 힌트. 미지원 브라우저는 무시됨.
        displayStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
          systemAudio: 'include',
        } as DisplayMediaStreamOptions);
        // 비디오 트랙은 필요 없으므로 즉시 정지
        displayStream.getVideoTracks().forEach((t) => t.stop());

        if (!isMountedRef.current) {
          cleanupAuxStreams();
          isStartingRef.current = false;
          return;
        }

        audioContext = new AudioContext();
        const destination = audioContext.createMediaStreamDestination();
        audioContext.createMediaStreamSource(micStream).connect(destination);
        if (displayStream.getAudioTracks().length > 0) {
          audioContext.createMediaStreamSource(displayStream).connect(destination);
        }
        stream = destination.stream;

        // 사용자가 브라우저 네이티브 "공유 중지" 버튼을 누르면 녹음도 함께 종료
        displayStream.getAudioTracks().forEach((t) => {
          t.onended = () => {
            if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop();
          };
        });

        micStreamRef.current = micStream;
        displayStreamRef.current = displayStream;
        audioContextRef.current = audioContext;
      }

      streamRef.current = stream;

      const mimeType = getSupportedMimeType();
      if (!mimeType) {
        isStartingRef.current = false;
        cleanupAuxStreams();
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
        cleanupAuxStreams();
        micStreamRef.current = null;
        displayStreamRef.current = null;
        audioContextRef.current = null;
        // 명시적 stop 버튼 외에 브라우저가 마이크를 회수한 경우도 처리
        setState('stopped');
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
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
      cleanupAuxStreams();
      setError(err instanceof Error ? err.message : '마이크 접근 실패');
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
      // setState('stopped')과 timer 정리는 onstop에서 처리 (브라우저 회수 케이스도 커버)
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
      micStreamRef.current?.getTracks().forEach((t) => t.stop());
      displayStreamRef.current?.getTracks().forEach((t) => t.stop());
      audioContextRef.current?.close().catch(() => {});
      revokeObjectUrl();
    };
  }, []);

  return { state, duration, startRecording, stopRecording, recordedBlob, objectUrl, error, reset };
}
