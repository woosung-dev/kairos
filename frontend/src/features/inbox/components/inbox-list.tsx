"use client";

import { useState } from "react";
import { EmptyState } from "@/components/empty-state";
import { useInbox } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { InboxItemCard } from "./inbox-item-card";

const FILTERS = ["전체", "미처리", "처리완료"] as const;

export function InboxList() {
  const [activeFilter, setActiveFilter] = useState<(typeof FILTERS)[number]>("전체");
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const { data, isLoading } = useInbox(activeWorkspaceId ?? undefined);

  const items = data?.items ?? [];

  const filteredItems = items.filter((item) => {
    if (activeFilter === "미처리") return !item.isProcessed;
    if (activeFilter === "처리완료") return item.isProcessed;
    return true;
  });

  return (
    <div className="p-6">
      {/* 헤더 */}
      <div className="mb-6">
        <h1
          className="text-2xl font-bold mb-1"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          Inbox
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          AI가 추천한 항목을 확인하고 프로젝트에 연결하세요
        </p>
      </div>

      {/* 필터 탭 */}
      <div className="flex items-center gap-1 mb-6 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        {FILTERS.map((filter) => (
          <button
            key={filter}
            onClick={() => setActiveFilter(filter)}
            className="px-3 py-2 text-sm font-medium transition-colors"
            style={{
              color: activeFilter === filter ? "var(--accent)" : "var(--text-muted)",
              borderBottom: activeFilter === filter ? "2px solid var(--accent)" : "2px solid transparent",
            }}
          >
            {filter}
          </button>
        ))}
      </div>

      {/* 로딩 */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <span className="text-sm" style={{ color: "var(--text-muted)" }}>
            불러오는 중...
          </span>
        </div>
      )}

      {/* 카드 리스트 */}
      {!isLoading && filteredItems.length === 0 ? (
        <EmptyState
          icon="📥"
          title="처리할 항목이 없습니다"
          description="회의를 녹음하거나 노트를 추가하면 AI가 자동으로 분류합니다"
        />
      ) : (
        !isLoading && (
          <div className="grid gap-3">
            {filteredItems.map((item) => (
              <InboxItemCard key={item.id} item={item} />
            ))}
          </div>
        )
      )}
    </div>
  );
}
