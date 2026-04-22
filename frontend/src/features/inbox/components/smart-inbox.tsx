"use client";

import { useState } from "react";
import { SmartInboxItemCard } from "./inbox-item-card";
import { useInbox } from "../hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import type { InboxItem } from "../types";

/* ── 로딩 스켈레톤 ── */

function InboxSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="p-4 rounded-lg border animate-pulse"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 rounded" style={{ background: "var(--surface-active)" }} />
            <div className="flex-1 space-y-2">
              <div className="h-4 rounded w-2/3" style={{ background: "var(--surface-active)" }} />
              <div className="h-3 rounded w-full" style={{ background: "var(--surface-active)" }} />
              <div className="h-3 rounded w-3/4" style={{ background: "var(--surface-active)" }} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── 컴포넌트 ── */

export function SmartInbox() {
  const [isAutoExpanded, setIsAutoExpanded] = useState(false);
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  /* isProcessed 미지정 → 전체 목록 fetch 후 클라이언트 분기 */
  const { data, isLoading, error } = useInbox(activeWorkspaceId ?? undefined);

  /* 로딩 상태 */
  if (isLoading) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <h1
            className="text-2xl font-bold mb-1"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            Inbox
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            AI가 분류한 항목을 확인하고 프로젝트에 연결하세요
          </p>
        </div>
        <InboxSkeleton />
      </div>
    );
  }

  /* 에러 상태 */
  if (error) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <h1
            className="text-2xl font-bold mb-1"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            Inbox
          </h1>
        </div>
        <div
          className="flex flex-col items-center justify-center py-16 text-center"
        >
          <span className="text-4xl mb-4">⚠️</span>
          <p className="text-sm" style={{ color: "var(--error)" }}>
            데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.
          </p>
        </div>
      </div>
    );
  }

  const items: InboxItem[] = data?.items ?? [];

  /* isProcessed === false → 확인 필요, isProcessed === true → AI 자동 처리 */
  const needsReview = items.filter((item) => !item.isProcessed);
  const autoProcessed = items.filter((item) => item.isProcessed);

  const needsReviewCount = needsReview.length;
  const autoProcessedCount = autoProcessed.length;

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
          AI가 분류한 항목을 확인하고 프로젝트에 연결하세요
        </p>
      </div>

      {/* 확인 필요 그룹 */}
      {needsReviewCount > 0 && (
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-base">⚠️</span>
            <h2
              className="text-sm font-semibold"
              style={{ color: "var(--warning)", fontFamily: "var(--font-display)" }}
            >
              확인 필요
            </h2>
            <span
              className="px-1.5 py-0.5 rounded-full text-[10px] font-medium"
              style={{
                background: "rgba(251,191,36,0.1)",
                color: "var(--warning)",
              }}
            >
              {needsReviewCount}건
            </span>
          </div>
          <div className="grid gap-3">
            {needsReview.map((item) => (
              <SmartInboxItemCard key={item.id} item={item} />
            ))}
          </div>
        </section>
      )}

      {/* AI 자동 처리 그룹 */}
      {autoProcessedCount > 0 && (
        <section>
          <button
            onClick={() => setIsAutoExpanded(!isAutoExpanded)}
            className="flex items-center gap-2 mb-3 w-full text-left"
            style={{ cursor: "pointer", minHeight: "44px" }}
          >
            <span className="text-base">✅</span>
            <h2
              className="text-sm font-semibold"
              style={{ color: "var(--success)", fontFamily: "var(--font-display)" }}
            >
              AI가 자동 처리한 항목
            </h2>
            <span
              className="px-1.5 py-0.5 rounded-full text-[10px] font-medium"
              style={{
                background: "rgba(52,211,153,0.1)",
                color: "var(--success)",
              }}
            >
              {autoProcessedCount}건
            </span>
            <span
              className="ml-auto text-xs transition-transform"
              style={{
                color: "var(--text-muted)",
                transform: isAutoExpanded ? "rotate(180deg)" : "rotate(0deg)",
              }}
            >
              ▼
            </span>
          </button>

          {isAutoExpanded && (
            <div className="grid gap-3">
              {autoProcessed.map((item) => (
                <SmartInboxItemCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </section>
      )}

      {/* 모두 비어있을 때 */}
      {needsReviewCount === 0 && autoProcessedCount === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-4xl mb-4">📥</span>
          <h3
            className="text-lg font-semibold mb-2"
            style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
          >
            처리할 항목이 없습니다
          </h3>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            회의를 녹음하거나 노트를 추가하면 AI가 자동으로 분류합니다
          </p>
        </div>
      )}
    </div>
  );
}
