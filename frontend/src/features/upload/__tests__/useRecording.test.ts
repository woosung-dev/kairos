// useRecording 훅 유닛 테스트 — MediaRecorder/getUserMedia 목 사용
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useRecording } from '../useRecording';

// ---- MockMediaRecorder 구현 ----
const mockStart = vi.fn();
const mockStop = vi.fn();

class MockMediaRecorder {
  static isTypeSupported = vi.fn().mockReturnValue(true);
  state = 'inactive';
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;

  constructor(_stream: MediaStream, _options?: MediaRecorderOptions) {}

  start(_timeslice?: number) {
    this.state = 'recording';
    mockStart();
  }

  stop() {
    this.state = 'inactive';
    mockStop();
    this.onstop?.();
  }
}

const mockGetUserMedia = vi.fn();

beforeEach(() => {
  mockStart.mockClear();
  mockStop.mockClear();
  mockGetUserMedia.mockClear();
  vi.stubGlobal('MediaRecorder', MockMediaRecorder);
  vi.stubGlobal('URL', {
    createObjectURL: vi.fn().mockReturnValue('blob:mock'),
    revokeObjectURL: vi.fn(),
  });
  mockGetUserMedia.mockResolvedValue({
    getTracks: () => [{ stop: vi.fn() }],
  });
  Object.defineProperty(global.navigator, 'mediaDevices', {
    value: { getUserMedia: mockGetUserMedia },
    configurable: true,
    writable: true,
  });
  vi.useFakeTimers();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe('useRecording', () => {
  it('초기 상태는 idle, duration 0, blob null', () => {
    const { result } = renderHook(() => useRecording());
    expect(result.current.state).toBe('idle');
    expect(result.current.duration).toBe(0);
    expect(result.current.recordedBlob).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('startRecording 호출 시 state가 recording으로 변경', async () => {
    const { result } = renderHook(() => useRecording());
    await act(async () => {
      await result.current.startRecording();
    });
    expect(result.current.state).toBe('recording');
    expect(mockGetUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(mockStart).toHaveBeenCalled();
  });

  it('recording 중 1초마다 duration 증가', async () => {
    const { result } = renderHook(() => useRecording());
    await act(async () => {
      await result.current.startRecording();
    });
    act(() => { vi.advanceTimersByTime(3000); });
    expect(result.current.duration).toBe(3);
  });

  it('stopRecording 호출 시 state=stopped, blob 생성', async () => {
    const { result } = renderHook(() => useRecording());
    await act(async () => {
      await result.current.startRecording();
    });
    act(() => { result.current.stopRecording(); });
    expect(result.current.state).toBe('stopped');
    expect(mockStop).toHaveBeenCalled();
    expect(result.current.recordedBlob).not.toBeNull();
  });

  it('마이크 권한 거부 시 error 상태 + state=idle 유지', async () => {
    mockGetUserMedia.mockRejectedValue(new Error('Permission denied'));
    const { result } = renderHook(() => useRecording());
    await act(async () => {
      await result.current.startRecording();
    });
    expect(result.current.error).toBe('Permission denied');
    expect(result.current.state).toBe('idle');
  });

  it('reset 호출 시 idle 상태로 초기화', async () => {
    const { result } = renderHook(() => useRecording());
    await act(async () => { await result.current.startRecording(); });
    act(() => { result.current.stopRecording(); });
    act(() => { result.current.reset(); });
    expect(result.current.state).toBe('idle');
    expect(result.current.duration).toBe(0);
    expect(result.current.recordedBlob).toBeNull();
  });

  it('startRecording 중복 호출 시 두 번째 호출 무시', async () => {
    const { result } = renderHook(() => useRecording());
    await act(async () => { await result.current.startRecording(); });
    await act(async () => { await result.current.startRecording(); }); // 두 번째
    expect(mockGetUserMedia).toHaveBeenCalledTimes(1);
  });

  it('navigator.mediaDevices 미지원 시 error 반환', async () => {
    Object.defineProperty(global.navigator, 'mediaDevices', {
      value: undefined,
      configurable: true,
      writable: true,
    });
    const { result } = renderHook(() => useRecording());
    await act(async () => { await result.current.startRecording(); });
    expect(result.current.error).toContain('지원하지 않습니다');
    expect(result.current.state).toBe('idle');
  });

  it('stream track이 stop 호출됨', async () => {
    const mockTrackStop = vi.fn();
    mockGetUserMedia.mockResolvedValue({
      getTracks: () => [{ stop: mockTrackStop }],
    });
    const { result } = renderHook(() => useRecording());
    await act(async () => { await result.current.startRecording(); });
    act(() => { result.current.stopRecording(); });
    expect(mockTrackStop).toHaveBeenCalled();
  });
});
