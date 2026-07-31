import type { ApiClient } from "@/lib/api-client";

export interface ExternalDocumentDetail {
  id: string;
  projectId: string | null;
  driveFileId: string;
  title: string;
  mimeType: string;
  originUrl: string;
  revisionId: string;
  syncStatus: "pending" | "processing" | "completed" | "failed" | "stale" | "reauth_required" | "purged";
  lastSyncedAt: string | null;
  plainText: string;
}

export async function fetchExternalDocumentDetail(
  api: ApiClient,
  wid: string,
  id: string,
): Promise<ExternalDocumentDetail> {
  return api.fetch<ExternalDocumentDetail>(
    `/workspaces/${wid}/external-documents/${id}`,
  );
}
