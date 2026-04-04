"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Inbox,
  CheckCircle2,
  Lightbulb,
  Activity,
  Mic,
  FileText,
  ArrowRight,
  GraduationCap,
} from "lucide-react";

/* ─── Mock 데이터 ─── */

interface InboxAlert {
  count: number;
}

interface ActionDue {
  id: string;
  title: string;
  projectName: string;
  isCompleted: boolean;
}

interface Insight {
  id: string;
  text: string;
  sourceLabel: string;
}

interface RecentActivity {
  id: string;
  type: "meeting" | "note" | "action";
  title: string;
  timestamp: string;
}

const MOCK_INBOX: InboxAlert | null = { count: 5 };

const MOCK_ACTIONS_DUE: ActionDue[] = [
  {
    id: "a1",
    title: "RAG 캐시 TTL 조정",
    projectName: "Kairos",
    isCompleted: false,
  },
  {
    id: "a2",
    title: "배포 모니터링 대시보드 설정",
    projectName: "Kairos",
    isCompleted: false,
  },
  {
    id: "a3",
    title: "사용자 피드백 정리",
    projectName: "사이드 프로젝트",
    isCompleted: true,
  },
];

const MOCK_INSIGHTS: Insight[] = [
  {
    id: "i1",
    text: "지난주 대비 회의 시간이 30% 감소했습니다. 비동기 커뮤니케이션이 증가하고 있습니다.",
    sourceLabel: "Sprint 3 회고",
  },
];

const MOCK_ACTIVITIES: RecentActivity[] = [
  {
    id: "r1",
    type: "meeting",
    title: "Sprint 4 킥오프",
    timestamp: "2시간 전",
  },
  {
    id: "r2",
    type: "note",
    title: "배포 체크리스트 작성",
    timestamp: "4시간 전",
  },
  {
    id: "r3",
    type: "action",
    title: "CI/CD 파이프라인 구성 완료",
    timestamp: "어제",
  },
];

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
            샘플 데이터로 RAG 기반 지식 검색을 체험해보세요.
            회의를 녹음하거나 메모를 작성하면 AI가 자동으로 정리합니다.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <Link
          href="/new"
          className="flex items-center gap-1.5 px-3 py-2 rounded text-xs font-medium transition-colors cursor-pointer"
          style={{
            background: "var(--accent)",
            color: "var(--background)",
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

function ActionsDueList({ actions }: { actions: ActionDue[] }) {
  const pending = actions.filter((a) => !a.isCompleted);

  if (pending.length === 0) return null;

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
          오늘 마감 액션 ({pending.length})
        </h3>
      </div>
      <div className="space-y-2">
        {pending.map((action) => (
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

function InsightsCard({ insights }: { insights: Insight[] }) {
  if (insights.length === 0) return null;

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
        <Lightbulb size={14} style={{ color: "#FBBF24" }} />
        <h3
          className="text-xs font-semibold uppercase tracking-wider"
          style={{
            color: "var(--text-muted)",
            fontFamily: "var(--font-display)",
          }}
        >
          새 인사이트
        </h3>
      </div>
      <div className="space-y-2">
        {insights.map((insight) => (
          <div key={insight.id}>
            <p
              className="text-sm leading-relaxed"
              style={{ color: "var(--text-primary)" }}
            >
              {insight.text}
            </p>
            <span
              className="text-[10px] mt-1 inline-block"
              style={{ color: "var(--text-muted)" }}
            >
              {insight.sourceLabel}
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
              key={act.id}
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

/* ─── TodayFeed 메인 ─── */

interface TodayFeedProps {
  /** true면 데이터 없는 상태 (온보딩 배너 표시) */
  isEmpty?: boolean;
}

export function TodayFeed({ isEmpty = false }: TodayFeedProps) {
  return (
    <div className="px-6 py-8 overflow-y-auto max-w-3xl mx-auto">
      {/* 환영 메시지 */}
      <h1
        className="text-2xl font-bold mb-6"
        style={{
          fontFamily: "var(--font-display)",
          color: "var(--text-primary)",
        }}
      >
        오늘의 Kairos
      </h1>

      {isEmpty ? (
        /* ─── 온보딩 (데이터 없을 때) ─── */
        <OnboardingBanner />
      ) : (
        /* ─── 일반 피드 ─── */
        <div className="space-y-4">
          {/* Inbox 미분류 알림 */}
          {MOCK_INBOX && <InboxCard count={MOCK_INBOX.count} />}

          {/* 오늘 마감 액션 */}
          <ActionsDueList actions={MOCK_ACTIONS_DUE} />

          {/* 새 인사이트 */}
          <InsightsCard insights={MOCK_INSIGHTS} />

          {/* 최근 활동 요약 */}
          <RecentActivityList activities={MOCK_ACTIVITIES} />
        </div>
      )}
    </div>
  );
}
