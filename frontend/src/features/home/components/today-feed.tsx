"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Inbox,
  CheckCircle2,
  Activity,
  Mic,
  FileText,
  ArrowRight,
  GraduationCap,
  FolderOpen,
} from "lucide-react";
import {
  useActivityFeed,
  type ActionDueEntry,
  type RecentActivity,
} from "../hooks";

/* ─── 서브 컴포넌트 ─── */

function OnboardingBanner() {
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) return null;

  return (
    <div
      className="rounded-lg border p-5 mb-6"
      style={{
        background: "var(--surface)",
        borderColor: "var(--accent)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div className="flex items-start gap-3 mb-4">
        <div
          className="flex items-center justify-center w-8 h-8 rounded shrink-0"
          style={{
            background: "var(--accent-subtle)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <GraduationCap size={18} style={{ color: "var(--accent)" }} />
        </div>
        <div>
          <h3
            className="text-sm font-semibold mb-1"
            style={{
              color: "var(--text-primary)",
              fontFamily: "var(--font-display)",
            }}
          >
            Kairos 시작 가이드
          </h3>
          <p
            className="text-xs leading-relaxed"
            style={{ color: "var(--text-secondary)" }}
          >
            사이드바의 <strong>🚀 시작하기</strong> · <strong>💡 아이디어</strong> · <strong>📋 회의록</strong> 프로젝트에서 바로 시작할 수 있습니다.
            회의를 녹음하거나 메모를 작성하면 AI가 자동으로 요약·액션·태그를 붙입니다.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <Link
          href="/projects"
          className="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-medium transition-colors cursor-pointer"
          style={{
            background: "var(--accent)",
            color: "var(--background)",
            borderRadius: "var(--radius-sm)",
            minHeight: 36,
          }}
        >
          <FolderOpen size={14} />
          프로젝트 둘러보기
        </Link>
        <Link
          href="/new"
          className="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-medium border transition-colors cursor-pointer"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-secondary)",
            borderRadius: "var(--radius-sm)",
            minHeight: 36,
          }}
        >
          <Mic size={14} />
          첫 회의 녹음하기
        </Link>
        <Link
          href="/notes"
          className="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-medium border transition-colors cursor-pointer"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-secondary)",
            borderRadius: "var(--radius-sm)",
            minHeight: 36,
          }}
        >
          <FileText size={14} />
          빠른 메모 작성
        </Link>
      </div>

      <button
        type="button"
        onClick={() => setIsDismissed(true)}
        className="text-[11px] cursor-pointer"
        style={{ color: "var(--text-muted)" }}
      >
        다시 보지 않기
      </button>
    </div>
  );
}

function InboxCard({ count }: { count: number }) {
  return (
    <Link
      href="/inbox"
      className="flex items-center justify-between p-4 rounded-lg border transition-colors cursor-pointer"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-md)",
      }}
      onMouseOver={(e) => {
        e.currentTarget.style.borderColor = "var(--accent)";
      }}
      onMouseOut={(e) => {
        e.currentTarget.style.borderColor = "var(--border-subtle)";
      }}
    >
      <div className="flex items-center gap-3">
        <div
          className="flex items-center justify-center w-8 h-8 rounded"
          style={{
            background: "rgba(251,191,36,0.1)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <Inbox size={16} style={{ color: "#FBBF24" }} />
        </div>
        <div>
          <p
            className="text-sm font-medium"
            style={{ color: "var(--text-primary)" }}
          >
            Inbox 미분류 항목
          </p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            {count}건의 항목이 정리를 기다리고 있습니다
          </p>
        </div>
      </div>
      <div className="flex items-center gap-1">
        <span
          className="flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold"
          style={{
            background: "#FBBF24",
            color: "var(--background)",
          }}
        >
          {count}
        </span>
        <ArrowRight size={14} style={{ color: "var(--text-muted)" }} />
      </div>
    </Link>
  );
}

function ActionsDueList({ actions }: { actions: ActionDueEntry[] }) {
  if (actions.length === 0) return null;

  return (
    <div
      className="rounded-lg border p-4"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-md)",
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <CheckCircle2 size={14} style={{ color: "var(--accent)" }} />
        <h3
          className="text-xs font-semibold uppercase tracking-wider"
          style={{
            color: "var(--text-muted)",
            fontFamily: "var(--font-display)",
          }}
        >
          진행 중 액션 ({actions.length})
        </h3>
      </div>
      <div className="space-y-2">
        {actions.map((action) => (
          <div
            key={action.id}
            className="flex items-center gap-2 text-sm"
          >
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{ background: "var(--accent)" }}
            />
            <span style={{ color: "var(--text-primary)" }}>
              {action.title}
            </span>
            <span
              className="text-[10px] px-1.5 py-0.5 rounded"
              style={{
                background: "var(--surface-hover)",
                color: "var(--text-muted)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              {action.projectName}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecentActivityList({ activities }: { activities: RecentActivity[] }) {
  if (activities.length === 0) return null;

  const ICON_MAP = {
    meeting: Mic,
    note: FileText,
    action: CheckCircle2,
  };

  return (
    <div
      className="rounded-lg border p-4"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-md)",
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <Activity size={14} style={{ color: "var(--text-muted)" }} />
        <h3
          className="text-xs font-semibold uppercase tracking-wider"
          style={{
            color: "var(--text-muted)",
            fontFamily: "var(--font-display)",
          }}
        >
          최근 활동
        </h3>
      </div>
      <div className="space-y-2.5">
        {activities.map((act) => {
          const Icon = ICON_MAP[act.type];
          return (
            <div
              key={`${act.type}-${act.id}`}
              className="flex items-center gap-2.5 text-sm"
            >
              <Icon
                size={13}
                style={{ color: "var(--text-muted)" }}
                className="shrink-0"
              />
              <span
                className="truncate"
                style={{ color: "var(--text-primary)" }}
              >
                {act.title}
              </span>
              <span
                className="shrink-0 text-[10px]"
                style={{ color: "var(--text-muted)" }}
              >
                {act.timestamp}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Placeholder (L3 인사이트 미구현) ─── */
// L3 프로젝트 인사이트는 ADR-007에 따라 Phase 4에서 도입 예정.
// 현재는 관련 섹션을 렌더하지 않음.
function InsightsCard() {
  return null;
}

/* ─── TodayFeed 메인 ─── */

interface TodayFeedProps {
  /** 현재 활성 워크스페이스 ID. 없으면 피드를 표시하지 않음. */
  workspaceId: string | undefined;
}

export function TodayFeed({ workspaceId }: TodayFeedProps) {
  const { inboxCount, actionsDue, activities, isReady, hasContent } =
    useActivityFeed(workspaceId);

  return (
    <div className="px-6 py-8 overflow-y-auto max-w-3xl mx-auto">
      <h1
        className="text-2xl font-bold mb-6"
        style={{
          fontFamily: "var(--font-display)",
          color: "var(--text-primary)",
        }}
      >
        오늘의 Kairos
      </h1>

      {!isReady ? (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          불러오는 중...
        </p>
      ) : !hasContent ? (
        <OnboardingBanner />
      ) : (
        <div className="space-y-4">
          {inboxCount > 0 && <InboxCard count={inboxCount} />}
          <ActionsDueList actions={actionsDue} />
          <InsightsCard />
          <RecentActivityList activities={activities} />
        </div>
      )}
    </div>
  );
}
