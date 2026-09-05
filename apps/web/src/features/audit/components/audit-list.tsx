"use client";

// Sprint 24 Wave 2 T-AUDIT-VIEW — Audit 목록 + item_type 필터 + 더 보기
import { useMemo, useState } from "react";
import { formatDateTime } from "@/lib/format-date";
import { useAuditPromotions } from "../hooks";
import type { AuditItemType } from "../types";

interface AuditListProps {
  workspaceId: string;
}

const ITEM_TYPE_LABEL: Record<AuditItemType | "all", string> = {
  all: "전체",
  meeting: "회의",
  note: "노트",
  inbox: "Inbox",
  action: "액션",
};

const ITEM_TYPES: ("all" | AuditItemType)[] = [
  "all",
  "meeting",
  "note",
  "inbox",
  "action",
];

// F-10: 폰트는 DESIGN.md 토큰(--font-mono)만 — 하드코딩 패밀리 목록은 토큰 교체 시 드리프트.
const MONO_STYLE = {
  fontFamily: "var(--font-mono)",
  fontVariantNumeric: "tabular-nums" as const,
};

export function AuditList({ workspaceId }: AuditListProps) {
  const [filterValue, setFilterValue] = useState<"all" | AuditItemType>("all");
  const itemType = filterValue === "all" ? null : filterValue;

  const query = useAuditPromotions(workspaceId, itemType);

  const flatRows = useMemo(
    () => query.data?.pages.flatMap((p) => p.items) ?? [],
    [query.data],
  );

  if (query.isLoading) {
    return (
      <p
        data-testid="audit-loading"
        className="text-sm"
        style={{ color: "var(--text-muted)" }}
      >
        audit 로그를 불러오는 중...
      </p>
    );
  }

  if (query.isError) {
    return (
      <p
        data-testid="audit-error"
        className="text-sm"
        style={{ color: "var(--text-muted)" }}
      >
        audit 로그를 불러올 수 없습니다.{" "}
        {query.error instanceof Error ? query.error.message : ""}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* 필터 dropdown — itemType 선택 */}
      <div className="flex items-center gap-2">
        <label
          htmlFor="audit-filter"
          className="text-sm"
          style={{ color: "var(--text-muted)" }}
        >
          유형:
        </label>
        <select
          id="audit-filter"
          data-testid="audit-filter"
          value={filterValue}
          onChange={(e) =>
            setFilterValue(e.target.value as "all" | AuditItemType)
          }
          className="px-3 py-1.5 rounded-md text-sm border cursor-pointer"
          style={{
            background: "var(--surface)",
            color: "var(--text-primary)",
            borderColor: "var(--border)",
          }}
        >
          {ITEM_TYPES.map((t) => (
            <option key={t} value={t}>
              {ITEM_TYPE_LABEL[t]}
            </option>
          ))}
        </select>
      </div>

      {/* 결과 테이블 */}
      {flatRows.length === 0 ? (
        <p
          data-testid="audit-empty"
          className="text-sm"
          style={{ color: "var(--text-muted)" }}
        >
          promote 이력이 없습니다.
        </p>
      ) : (
        <div
          className="overflow-x-auto rounded-md border"
          style={{ borderColor: "var(--border)" }}
        >
          <table
            data-testid="audit-table"
            className="w-full text-sm"
            style={MONO_STYLE}
          >
            <thead style={{ background: "var(--surface)" }}>
              <tr>
                <th
                  className="px-3 py-2 text-left font-medium"
                  style={{ color: "var(--text-muted)", fontSize: 11 }}
                >
                  유형
                </th>
                <th
                  className="px-3 py-2 text-left font-medium"
                  style={{ color: "var(--text-muted)", fontSize: 11 }}
                >
                  원본 ID
                </th>
                <th
                  className="px-3 py-2 text-left font-medium"
                  style={{ color: "var(--text-muted)", fontSize: 11 }}
                >
                  복제본 ID
                </th>
                <th
                  className="px-3 py-2 text-left font-medium"
                  style={{ color: "var(--text-muted)", fontSize: 11 }}
                >
                  임베딩
                </th>
                <th
                  className="px-3 py-2 text-left font-medium"
                  style={{ color: "var(--text-muted)", fontSize: 11 }}
                >
                  생성 시각
                </th>
              </tr>
            </thead>
            <tbody>
              {flatRows.map((row) => (
                <tr
                  key={row.id}
                  className="border-t"
                  style={{ borderColor: "var(--border)" }}
                >
                  <td
                    className="px-3 py-2"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {ITEM_TYPE_LABEL[row.itemType] ?? row.itemType}
                  </td>
                  <td
                    className="px-3 py-2"
                    style={{
                      color: "var(--text-muted)",
                      fontSize: 11,
                    }}
                  >
                    {row.sourceItemId.slice(0, 8)}
                  </td>
                  <td
                    className="px-3 py-2"
                    style={{
                      color: "var(--text-muted)",
                      fontSize: 11,
                    }}
                  >
                    {row.newItemId.slice(0, 8)}
                  </td>
                  <td
                    className="px-3 py-2"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {row.embeddingStatus}
                  </td>
                  <td
                    className="px-3 py-2"
                    style={{
                      color: "var(--text-muted)",
                      fontSize: 11,
                    }}
                  >
                    {formatDateTime(row.createdAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 더 보기 버튼 — cursor 기반 페이지네이션 */}
      {query.hasNextPage && (
        <div className="flex justify-center">
          <button
            type="button"
            data-testid="audit-load-more"
            onClick={() => query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
            className="px-4 py-2 rounded-md text-sm font-medium cursor-pointer"
            style={{
              background: "var(--surface-active)",
              color: "var(--text-primary)",
              opacity: query.isFetchingNextPage ? 0.6 : 1,
            }}
          >
            {query.isFetchingNextPage ? "불러오는 중..." : "더 보기"}
          </button>
        </div>
      )}
    </div>
  );
}
