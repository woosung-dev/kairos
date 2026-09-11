"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { externalDocumentKeys, integrationKeys } from "@/lib/query-keys";
import { useApiClient } from "@/lib/use-api-client";
import {
  createGoogleDriveAuthorizationUrl,
  disconnectGoogleDrive,
  fetchExternalDocumentDetail,
  fetchGoogleDriveConnection,
  fetchGoogleDriveDocuments,
  fetchIntegrationSyncRun,
  importGoogleDriveDocuments,
  resyncGoogleDriveDocument,
  unpublishGoogleDriveDocument,
  type DisconnectResult,
  type IntegrationSyncRun,
} from "./api";

/** 진행 중 sync run 폴링 간격. STT 와 달리 Drive export 는 초 단위로 끝난다. */
const SYNC_RUN_POLL_INTERVAL_MS = 2_000;

export function useExternalDocumentDetail(wid: string | undefined, id: string) {
  const api = useApiClient();

  return useQuery({
    queryKey: externalDocumentKeys.detail(wid ?? "", id),
    queryFn: () => fetchExternalDocumentDetail(api, wid!, id),
    enabled: !!wid && !!id,
    retry: (failureCount) => failureCount < 1,
  });
}

/**
 * 연결 상태. owner 전용 엔드포인트라 `enabled` 로 호출 자체를 막는다 —
 * 아니면 member 진입 때마다 403 을 발사한다.
 */
export function useGoogleDriveConnection(
  wid: string | undefined,
  options?: { enabled?: boolean },
) {
  const api = useApiClient();

  return useQuery({
    queryKey: integrationKeys.connection(wid ?? ""),
    queryFn: () => fetchGoogleDriveConnection(api, wid!),
    enabled: !!wid && (options?.enabled ?? true),
  });
}

export function useGoogleDriveDocuments(
  wid: string | undefined,
  options?: { enabled?: boolean },
) {
  const api = useApiClient();

  return useQuery({
    queryKey: integrationKeys.documents(wid ?? ""),
    queryFn: () => fetchGoogleDriveDocuments(api, wid!),
    enabled: !!wid && (options?.enabled ?? true),
  });
}

/**
 * 진행 중인 sync run 을 폴링한다 (I-EXT-3 · B-7).
 *
 * 종료 상태(`completed`/`failed`)에 닿으면 폴링을 멈춘다 — 끝난 run 을 계속
 * 두드리면 202 패턴이 사실상 상시 폴링이 된다.
 */
export function useIntegrationSyncRun(
  wid: string | undefined,
  syncRunId: string | null,
) {
  const api = useApiClient();

  return useQuery({
    queryKey: integrationKeys.syncRun(wid ?? "", syncRunId ?? ""),
    queryFn: () => fetchIntegrationSyncRun(api, wid!, syncRunId!),
    enabled: !!wid && !!syncRunId,
    refetchInterval: (query) => {
      const status = (query.state.data as IntegrationSyncRun | undefined)?.status;
      return status === "completed" || status === "failed"
        ? false
        : SYNC_RUN_POLL_INTERVAL_MS;
    },
  });
}

/** 인가 URL 을 받아 그대로 반환한다. 리다이렉트는 호출부가 결정한다. */
export function useCreateGoogleDriveAuthorizationUrl(wid: string | undefined) {
  const api = useApiClient();

  return useMutation({
    mutationFn: () => createGoogleDriveAuthorizationUrl(api, wid!),
  });
}

export function useImportGoogleDriveDocuments(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: { fileIds: string[]; projectId: string | null }) =>
      importGoogleDriveDocuments(api, wid!, body),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.documents(wid ?? ""),
      });
    },
  });
}

export function useResyncGoogleDriveDocument(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) =>
      resyncGoogleDriveDocument(api, wid!, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.documents(wid ?? ""),
      });
    },
  });
}

export function useUnpublishGoogleDriveDocument(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) =>
      unpublishGoogleDriveDocument(api, wid!, documentId),
    onSuccess: (_result, documentId) => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.documents(wid ?? ""),
      });
      // 발행 취소된 문서의 상세 캐시를 남기면 인용 클릭이 죽은 본문을 연다.
      queryClient.removeQueries({
        queryKey: externalDocumentKeys.detail(wid ?? "", documentId),
      });
    },
  });
}

export function useDisconnectGoogleDrive(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation<DisconnectResult, Error, void>({
    mutationFn: () => disconnectGoogleDrive(api, wid!),
    onSuccess: () => {
      // 연결 해제는 문서를 전부 회수하므로 상세 캐시도 통째로 버린다.
      queryClient.invalidateQueries({
        queryKey: integrationKeys.connection(wid ?? ""),
      });
      queryClient.invalidateQueries({
        queryKey: integrationKeys.documents(wid ?? ""),
      });
      queryClient.removeQueries({ queryKey: externalDocumentKeys.all });
    },
  });
}
