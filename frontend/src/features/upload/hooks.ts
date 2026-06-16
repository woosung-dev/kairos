"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiClient } from "@/lib/api-client";

interface UploadState {
  isUploading: boolean;
  progress: number; // 0~100
  error: string | null;
}

/**
 * 백엔드 프록시를 통한 파일 업로드 훅. (R2 CORS 우회)
 *
 * POST /workspaces/{wid}/upload/file (multipart) → { fileKey }
 */
export function usePresignedUpload(wid: string | undefined) {
  const { getToken } = useAuth();
  const [state, setState] = useState<UploadState>({
    isUploading: false,
    progress: 0,
    error: null,
  });

  async function upload(file: File): Promise<string> {
    setState({ isUploading: true, progress: 0, error: null });

    try {
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");
      if (!wid) throw new Error("워크스페이스가 선택되지 않았습니다");

      setState((prev) => ({ ...prev, progress: 20 }));

      // 백엔드 프록시 업로드 (FE→BE→R2, CORS 불필요).
      // Sprint 29 R3 (api-multipart): 전용 fetch 대신 apiClient(FormData 지원) 통합.
      const formData = new FormData();
      formData.append("file", file);

      const data = await apiClient<{ fileKey: string }>(
        `/workspaces/${wid}/upload/file`,
        { token, method: "POST", body: formData }
      );
      setState({ isUploading: false, progress: 100, error: null });
      return data.fileKey;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "알 수 없는 오류";
      setState({ isUploading: false, progress: 0, error: message });
      throw err;
    }
  }

  return {
    upload,
    ...state,
  };
}
