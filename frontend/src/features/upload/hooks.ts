"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiClient } from "@/lib/api-client";
import type { PresignedUrlResponse } from "./types";

interface UploadState {
  isUploading: boolean;
  progress: number; // 0~100
  error: string | null;
}

/**
 * Presigned URL을 이용한 R2 직접 업로드 훅.
 *
 * 1. POST /upload/presigned-url -> { uploadUrl, fileKey }
 * 2. PUT uploadUrl (R2 직접 업로드)
 * 3. fileKey 반환
 */
export function usePresignedUpload() {
  const { getToken } = useAuth();
  const [state, setState] = useState<UploadState>({
    isUploading: false,
    progress: 0,
    error: null,
  });

  async function upload(file: File): Promise<string> {
    setState({ isUploading: true, progress: 0, error: null });

    try {
      // 1. presigned URL 발급
      const token = await getToken();
      if (!token) throw new Error("인증이 필요합니다");

      const presigned = await apiClient<PresignedUrlResponse>(
        "/upload/presigned-url",
        {
          token,
          method: "POST",
          body: JSON.stringify({
            filename: file.name,
            contentType: file.type || "application/octet-stream",
          }),
        }
      );

      setState((prev) => ({ ...prev, progress: 30 }));

      // 2. R2 직접 업로드 (presigned URL)
      const uploadRes = await fetch(presigned.uploadUrl, {
        method: "PUT",
        body: file,
        headers: {
          "Content-Type": file.type || "application/octet-stream",
        },
      });

      if (!uploadRes.ok) {
        throw new Error("파일 업로드에 실패했습니다");
      }

      setState({ isUploading: false, progress: 100, error: null });

      // 3. fileKey 반환
      return presigned.fileKey;
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
