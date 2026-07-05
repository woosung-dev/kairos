"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
            // PERF: 탭 refocus 마다 앱 셸 쿼리 7개+ 가 일제 재발화 → 팀 인원수에
            // 비례해 BE 부하 증폭. 실시간성 필요한 쿼리(회의 status polling)는
            // refetchInterval 로 개별 관리하므로 전역 focus refetch 는 끈다.
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
