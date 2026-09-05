"use client";

// Sprint 15 R7 — Founder admin recall-metrics 페이지
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useMe } from "@/features/auth/hooks";
import { useApiClient } from "@/lib/use-api-client";
import { useWorkspaceStore } from "@/features/workspaces/store";
import type { components } from "@/types/api.gen";

// ADR-031: 값이 외부 인증 ID → 내부 UUID(users.id) 로 바뀌었다.
// 내부 UUID 는 인증 공급자가 또 바뀌어도 불변이라, 이 빌드 인자를 다시 갱신할 일이 없다.
const FOUNDER_USER_ID = process.env.NEXT_PUBLIC_FOUNDER_USER_ID;

// ADR-027 D2 — wire 타입은 계약 생성물에서 import (수기 정의 금지)
type MemoryMetrics = components["schemas"]["MemoryMetricsOut"];

export default function RecallMetricsPage() {
  const { data: me, isPending: isMeLoading } = useMe();
  const api = useApiClient();
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  const isFounder = !!FOUNDER_USER_ID && me?.id === FOUNDER_USER_ID;

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
  if (isMeLoading) return <section className="p-8">불러오는 중...</section>;
  if (!isFounder) {
    return (
      <section className="p-8 max-w-2xl">
        <h1 className="text-2xl font-semibold mb-2">접근 권한 없음</h1>
        <p className="text-sm text-muted-foreground">
          이 페이지는 운영자 전용 메트릭 화면입니다. 일반 사용자에게는 제공되지 않습니다.
        </p>
        <Link
          href="/dashboard"
          className="mt-4 inline-flex items-center gap-1 text-sm underline"
          style={{ color: "var(--text-secondary)" }}
        >
          홈으로 돌아가기
        </Link>
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
