"use client";

import { useQuery } from "@tanstack/react-query";
import { externalDocumentKeys } from "@/lib/query-keys";
import { useApiClient } from "@/lib/use-api-client";
import { fetchExternalDocumentDetail } from "./api";

export function useExternalDocumentDetail(wid: string | undefined, id: string) {
  const api = useApiClient();

  return useQuery({
    queryKey: externalDocumentKeys.detail(wid ?? "", id),
    queryFn: () => fetchExternalDocumentDetail(api, wid!, id),
    enabled: !!wid && !!id,
    retry: (failureCount) => failureCount < 1,
  });
}
