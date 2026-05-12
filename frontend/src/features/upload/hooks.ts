"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";

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

      // 백엔드 프록시 업로드 (FE→BE→R2, CORS 불필요)
      const formData = new FormData();
      formData.append("file", file);

      const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";
      const res = await fetch(
        `${apiBase}/api/v1/workspaces/${wid}/upload/file`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        }
      );

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(
          (errBody as { detail?: string }).detail ?? "파일 업로드에 실패했습니다"
        );
      }

      const data = (await res.json()) as { fileKey: string };
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
