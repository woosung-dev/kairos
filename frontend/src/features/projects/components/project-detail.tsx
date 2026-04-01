"use client";

import { useState } from "react";
import { EmptyState } from "@/components/empty-state";

const TABS = ["전체", "회의", "노트", "액션", "자료"] as const;

interface ProjectDetailProps {
  projectId: string;
}

const STAT_ITEMS = [
  { label: "회의", value: 0, icon: "🎙️" },
  { label: "노트", value: 0, icon: "📝" },
  { label: "액션", value: 0, icon: "✅" },
  { label: "RAG 검색", value: 0, icon: "🔍" },
];

export function ProjectDetail({ projectId }: ProjectDetailProps) {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>("전체");

  return (
    <div className="p-6">
      {/* 헤더 */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1
            className="text-2xl font-bold"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            프로젝트
          </h1>
          <span
            className="px-2 py-0.5 rounded-full text-xs font-medium"
            style={{
              background: "var(--accent-subtle)",
              color: "var(--accent)",
            }}
          >
            진행 중
          </span>
        </div>
        <p className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          ID: {projectId}
        </p>
      </div>

      {/* Stat 카드 */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {STAT_ITEMS.map((stat) => (
          <div
            key={stat.label}
            className="p-3 rounded border"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border-subtle)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-base">{stat.icon}</span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {stat.label}
              </span>
            </div>
            <p
              className="text-xl font-semibold"
              style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}
            >
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      {/* 탭 */}
      <div className="flex items-center gap-1 mb-6 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="px-3 py-2 text-sm font-medium transition-colors"
            style={{
              color: activeTab === tab ? "var(--accent)" : "var(--text-muted)",
              borderBottom: activeTab === tab ? "2px solid var(--accent)" : "2px solid transparent",
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* 콘텐츠 리스트 (빈 상태) */}
      <EmptyState
        icon="📄"
        title="콘텐츠를 추가하세요"
        description="회의, 노트, 자료를 추가하면 여기에 표시됩니다"
        action={{ label: "콘텐츠 추가", href: "/new" }}
      />
    </div>
  );
}
