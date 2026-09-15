"use client";

import { useEffect, useRef } from "react";
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

/** 재동기화 202 뒤 결과를 다시 읽기까지의 여유. Drive export 는 보통 1~2초다. */
const RESYNC_SETTLE_DELAY_MS = 3_000;

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
  const queryClient = useQueryClient();
  const previousStatusRef = useRef<IntegrationSyncRun["status"] | undefined>(
    undefined,
  );

  const query = useQuery({
    queryKey: integrationKeys.syncRun(wid ?? "", syncRunId ?? ""),
    queryFn: () => fetchIntegrationSyncRun(api, wid!, syncRunId!),
    enabled: !!wid && !!syncRunId,
    retry: (failureCount) => failureCount < 1,
    refetchInterval: (query) => {
      // ★에러 시 폴링을 멈춘다. 없으면 404(삭제된 run·워크스페이스 전환)나 403 에서
      //   data 가 영원히 undefined 라 종료 조건에 닿지 못하고 2초마다 요청을 쏟는다
      //   — meetings/hooks.ts 가 같은 storm 을 겪고 넣은 가드다.
      if (query.state.error) return false;
      const status = (query.state.data as IntegrationSyncRun | undefined)?.status;
      return status === "completed" || status === "failed"
        ? false
        : SYNC_RUN_POLL_INTERVAL_MS;
    },
  });

  // ★종료 전이에서 문서 목록을 무효화한다.
  //
  //   import 의 onSuccess(202 시점)에서만 무효화하면, 그때는 BackgroundTask 가
  //   아직 문서를 만들기 전이라 **빈 목록을 받아 fresh 로 굳힌다**. 전역 staleTime
  //   60s + refetchOnWindowFocus:false 라 그 뒤로 다시 읽지 않아, 가져오기가
  //   성공해도 표가 계속 비어 보인다. meetings 의 완료 전이 무효화와 같은 패턴.
  const status = query.data?.status;
  useEffect(() => {
    if (
      (status === "completed" || status === "failed") &&
      previousStatusRef.current !== status
    ) {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.documents(wid ?? ""),
      });
    }
    previousStatusRef.current = status;
  }, [status, wid, queryClient]);

  return query;
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
    // 여기서 무효화하지 않는다 — 202 시점에는 BackgroundTask 가 아직 문서를 만들기
    // 전이라 빈 목록을 fresh 로 굳힐 뿐이다. 갱신은 useIntegrationSyncRun 의
    // 종료 전이가 담당한다.
  });
}

export function useResyncGoogleDriveDocument(wid: string | undefined) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) =>
      resyncGoogleDriveDocument(api, wid!, documentId),
    onSuccess: async () => {
      // 202 직후 무효화하면 아직 안 바뀐 상태를 읽고 60s staleTime 으로 굳는다.
      // 재동기화는 sync run 을 만들지 않아 폴링할 대상이 없으므로, 한 박자 뒤
      // 한 번 더 읽어 사용자가 결과를 보게 한다. (자동 동기화 부재 — ADR-026 D8)
      await new Promise((resolve) =>
        setTimeout(resolve, RESYNC_SETTLE_DELAY_MS),
      );
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
