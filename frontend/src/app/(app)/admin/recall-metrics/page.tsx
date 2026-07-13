"use client";

// Sprint 15 R7 — Founder admin recall-metrics 페이지
import { useQuery } from "@tanstack/react-query";
import { useUser } from "@clerk/nextjs";
import { useApiClient } from "@/lib/use-api-client";
import { useWorkspaceStore } from "@/features/workspaces/store";

const FOUNDER_CLERK_ID = process.env.NEXT_PUBLIC_FOUNDER_CLERK_ID;

interface MemoryMetrics {
  capture_count: number;
  recall_count: number;
  promote_count: number;
  recall_p50_ms: number | null;
  recall_p95_ms: number | null;
}

export default function RecallMetricsPage() {
  const { user, isLoaded } = useUser();
  const api = useApiClient();
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  const isFounder = !!FOUNDER_CLERK_ID && user?.id === FOUNDER_CLERK_ID;

  const metrics = useQuery({
    queryKey: ["memory", "metrics", workspaceId],
    queryFn: async () => {
      if (!workspaceId) throw new Error("auth/workspace 미설정");
      // api.fetch 는 `${API_BASE_URL}/api/v1` prefix 자동 부여 + 토큰 첨부. 중복 prefix 금지.
      return api.fetch<MemoryMetrics>(
        `/workspaces/${workspaceId}/memory/metrics`,
      );
    },
    enabled: !!workspaceId && isFounder,
    refetchInterval: 30_000,
  });

  // F-2C v2 (Sprint 25 polish, agy 3차 발견): panel-layout 의 <main id="main-content"> 안에
  // 자체 <main> nest → HTML5 spec 위반 (페이지당 main 1개). section 으로 교체.
  if (!isLoaded) return <section className="p-8">불러오는 중...</section>;
  if (!isFounder) {
    return (
      <section className="p-8 max-w-2xl">
        <h1 className="text-2xl font-semibold mb-2">접근 권한 없음</h1>
        <p className="text-sm text-muted-foreground">
          이 페이지는 founder 전용입니다. `NEXT_PUBLIC_FOUNDER_CLERK_ID`로 식별되는 사용자만 진입할 수 있어요.
        </p>
      </section>
    );
  }

  const data = metrics.data;

  return (
    <section className="p-8 max-w-3xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">메모리 메트릭</h1>
        <p className="text-sm text-muted-foreground">
          현재 워크스페이스의 캡쳐 / 회상 / 프로모트 누적 + 회상 latency p50/p95.
          30초마다 자동 갱신.
        </p>
      </header>

      {metrics.isLoading && <p>불러오는 중...</p>}
      {metrics.isError && (
        <p className="text-destructive">메트릭 조회 실패: {metrics.error?.message}</p>
      )}

      {data && (
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded-lg border border-border p-4">
            <dt className="text-xs uppercase text-muted-foreground mb-1">캡쳐</dt>
            <dd className="text-3xl font-mono">{data.capture_count}</dd>
          </div>
          <div className="rounded-lg border border-border p-4">
            <dt className="text-xs uppercase text-muted-foreground mb-1">회상</dt>
            <dd className="text-3xl font-mono">{data.recall_count}</dd>
          </div>
          <div className="rounded-lg border border-border p-4">
            <dt className="text-xs uppercase text-muted-foreground mb-1">프로모트</dt>
            <dd className="text-3xl font-mono">{data.promote_count}</dd>
          </div>
          <div className="rounded-lg border border-border p-4">
            <dt className="text-xs uppercase text-muted-foreground mb-1">회상 p50 / p95</dt>
            <dd className="text-xl font-mono">
              {data.recall_p50_ms ?? "—"} / {data.recall_p95_ms ?? "—"}
              <span className="text-xs text-muted-foreground ml-1">ms</span>
            </dd>
          </div>
        </dl>
      )}
    </section>
  );
}
