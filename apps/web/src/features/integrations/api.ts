import type { ApiClient } from "@/lib/api-client";
import type { components } from "@/types/api.gen";

// I-22 — wire 타입은 계약 생성물에서 가져온다. 수기 interface 를 새로 쓰지 않는다.
type Schemas = components["schemas"];

export type ExternalDocument = Schemas["ExternalDocumentResponse"];
export type ExternalDocumentDetail = Schemas["ExternalDocumentDetailResponse"];
export type IntegrationConnection = Schemas["IntegrationConnectionResponse"];
export type IntegrationSyncRun = Schemas["IntegrationSyncRunResponse"];
export type DisconnectResult = Schemas["DisconnectConnectionResponse"];
export type DocumentSyncStatus = ExternalDocument["syncStatus"];

export async function fetchExternalDocumentDetail(
  api: ApiClient,
  wid: string,
  id: string,
): Promise<ExternalDocumentDetail> {
  return api.fetch<ExternalDocumentDetail>(
    `/workspaces/${wid}/external-documents/${id}`,
  );
}

/** 연결 상태. 미연결이면 BE 가 `null` 을 준다. */
export async function fetchGoogleDriveConnection(
  api: ApiClient,
  wid: string,
): Promise<IntegrationConnection | null> {
  return api.fetch<IntegrationConnection | null>(
    `/workspaces/${wid}/integrations/google-drive`,
  );
}

/** 발행된 외부 문서 목록 (owner 전용). 본문은 BE 가 defer 한다. */
export async function fetchGoogleDriveDocuments(
  api: ApiClient,
  wid: string,
): Promise<ExternalDocument[]> {
  return api.fetch<ExternalDocument[]>(
    `/workspaces/${wid}/integrations/google-drive/documents`,
  );
}

/**
 * Google 인가 URL 을 받는다. 이 URL 로 브라우저를 보내면 OAuth 가 시작되고,
 * 완료 후 BE callback 이 `/settings?tab=integrations` 로 되돌린다.
 */
export async function createGoogleDriveAuthorizationUrl(
  api: ApiClient,
  wid: string,
): Promise<string> {
  const response = await api.fetch<Schemas["AuthorizationUrlResponse"]>(
    `/workspaces/${wid}/integrations/google-drive/authorize`,
    { method: "POST" },
  );
  return response.authorizationUrl;
}

/**
 * Picker 가 고른 파일을 가져온다 → 202 + syncRunId.
 *
 * ★본문에는 `fileIds` 와 `projectId` 만 넣는다. Picker 가 쥔 브라우저 access
 * token 은 절대 보내지 않는다 (ADR-026 D5).
 */
export async function importGoogleDriveDocuments(
  api: ApiClient,
  wid: string,
  body: { fileIds: string[]; projectId: string | null },
): Promise<string> {
  const response = await api.fetch<Schemas["SyncRunCreatedResponse"]>(
    `/workspaces/${wid}/integrations/google-drive/documents`,
    { method: "POST", body: JSON.stringify(body) },
  );
  return response.syncRunId;
}

/** 202 폴링 대상 — 문서별 상태가 함께 온다. */
export async function fetchIntegrationSyncRun(
  api: ApiClient,
  wid: string,
  syncRunId: string,
): Promise<IntegrationSyncRun> {
  return api.fetch<IntegrationSyncRun>(
    `/workspaces/${wid}/integrations/sync-runs/${syncRunId}`,
  );
}

/** 수동 재동기화 (자동 retry 없음 — ADR-026 D8). */
export async function resyncGoogleDriveDocument(
  api: ApiClient,
  wid: string,
  documentId: string,
): Promise<void> {
  await api.fetch<void>(
    `/workspaces/${wid}/integrations/google-drive/documents/${documentId}/sync`,
    { method: "POST" },
  );
}

/** 문서 1건 발행 취소 — 본문·청크·관련 캐시를 함께 회수한다. */
export async function unpublishGoogleDriveDocument(
  api: ApiClient,
  wid: string,
  documentId: string,
): Promise<void> {
  await api.fetch<void>(
    `/workspaces/${wid}/integrations/google-drive/documents/${documentId}`,
    { method: "DELETE" },
  );
}

/**
 * 연결 해제 — 발행 문서 전량 회수 + Google 토큰 폐기.
 *
 * `revoked=false` 는 해제 실패가 아니다. Kairos 쪽 회수는 끝났고 Google 측
 * 폐기만 확인되지 않은 상태이므로, UI 는 수동 해제를 안내해야 한다.
 */
export async function disconnectGoogleDrive(
  api: ApiClient,
  wid: string,
): Promise<DisconnectResult> {
  return api.fetch<DisconnectResult>(
    `/workspaces/${wid}/integrations/google-drive`,
    { method: "DELETE" },
  );
}
