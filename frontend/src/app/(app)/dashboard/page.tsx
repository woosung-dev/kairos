"use client";

import { useState } from "react";
import Link from "next/link";
import { Building2, Mic, StickyNote, Inbox, Folder } from "lucide-react";
import { useWorkspaces } from "@/features/workspaces/hooks";
import { CreateWorkspaceDialog } from "@/features/workspaces/components/create-workspace-dialog";
import { EmptyState } from "@/components/empty-state";
import { useUIStore } from "@/store/ui";
import { OnboardingTooltip } from "@/components/onboarding/onboarding-tooltip";
import { DashboardSuggestions } from "@/features/home/components/dashboard-suggestions";

export default function DashboardPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { toggleCmdK } = useUIStore();
  // Sprint 24 Wave 2 T-CMD-K-FIX: 추천 질문 클릭은 cmd-k palette open + query 자동 입력으로 변경.
  // 이전: ask() 직접 호출 → palette 안 열림 (BUG-CURIOUS-002 dead-click).
  // 추천 질문 UI 는 DashboardSuggestions 컴포넌트로 분리 (vitest 단위 테스트 가능).

  const { data: workspaces, isLoading: isLoadingWs } = useWorkspaces();

  // active 워크스페이스 동기화는 panel-layout 이 소유한다 (BL-FE-WS-HEAL-SCOPE-1).
  // 여기 있던 같은 보정은 이 페이지에 진입해야만 돌아서 /projects·/inbox 직접 진입 시
  // 접근 불가 wid 가 고착됐다. 공용 레이아웃으로 올리며 중복을 제거했다.
  const hasWorkspaces = workspaces && workspaces.length > 0;

  // 로딩 상태
  if (isLoadingWs) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          불러오는 중...
        </p>
      </div>
    );
  }

  // 워크스페이스 없음
  if (!hasWorkspaces) {
    return (
      <div className="p-6">
        <EmptyState
          icon={<Building2 className="w-10 h-10" />}
          title="워크스페이스를 만들어주세요"
          description="워크스페이스를 만들면 회의 녹음, 프로젝트 관리를 시작할 수 있습니다"
        />
        <div className="flex justify-center mt-4">
          <button
            onClick={() => setIsDialogOpen(true)}
            className="px-4 py-2 rounded text-sm font-medium"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            워크스페이스 만들기
          </button>
        </div>
        <CreateWorkspaceDialog
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center px-4 py-12">
      {/* RAG 검색 — 핵심 경험 (ADR-004) */}
      <div className="w-full max-w-2xl mb-12">
        <h1
          className="text-2xl font-bold mb-6 text-center"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          무엇이든 질문하세요
        </h1>
        <OnboardingTooltip page="dashboard">
          <button
            onClick={toggleCmdK}
            className="w-full flex items-center justify-between px-4 py-3 rounded border text-sm transition-colors"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--text-muted)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <span>검색하거나 질문 입력...</span>
            <kbd
              className="px-2 py-0.5 rounded text-micro"
              style={{
                background: "var(--surface-active)",
                borderRadius: "var(--radius-sm)",
                // ⌘(U+2318) 가 Geist Mono 미포함 → system-ui per-glyph fallback (UX-CMDK-GLYPH)
                fontFamily: "var(--font-mono), system-ui, sans-serif",
              }}
            >
              ⌘K
            </kbd>
          </button>
        </OnboardingTooltip>
      </div>

      {/* 추천 질문 — Sprint 24 Wave 2 T-CMD-K-FIX (BUG-CURIOUS-002) */}
      <DashboardSuggestions />

      {/* 빠른 접근 */}
      <div className="w-full max-w-2xl">
        <h2
          className="text-sm font-semibold mb-4 uppercase tracking-wider"
          style={{ color: "var(--text-muted)", fontFamily: "var(--font-display)" }}
        >
          빠른 접근
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { icon: <Mic className="w-6 h-6" />, label: "회의 추가", href: "/new" },
            { icon: <StickyNote className="w-6 h-6" />, label: "노트", href: "/notes" },
            { icon: <Inbox className="w-6 h-6" />, label: "Inbox", href: "/inbox" },
            { icon: <Folder className="w-6 h-6" />, label: "프로젝트", href: "/projects" },
          ].map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="flex flex-col items-center gap-2 px-4 py-4 rounded border text-sm transition-colors"
              style={{
                borderColor: "var(--border-subtle)",
                color: "var(--text-secondary)",
                borderRadius: "var(--radius-md)",
              }}
              onMouseOver={(e) =>
                (e.currentTarget.style.background = "var(--surface-hover)")
              }
              onMouseOut={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          ))}
        </div>
      </div>

      <CreateWorkspaceDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />
    </div>
  );
}
