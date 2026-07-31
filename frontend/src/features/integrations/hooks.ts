"use client";

import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/lib/use-api-client";
import { fetchExternalDocumentDetail } from "./api";

const externalDocumentKeys = {
  detail: (wid: string, id: string) => ["external-documents", "detail", wid, id] as const,
};

export function useExternalDocumentDetail(wid: string | undefined, id: string) {
  const api = useApiClient();

  return useQuery({
    queryKey: externalDocumentKeys.detail(wid ?? "", id),
    queryFn: () => fetchExternalDocumentDetail(api, wid!, id),
    enabled: !!wid && !!id,
    retry: (failureCount) => failureCount < 1,
  });
}
