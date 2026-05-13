"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useWorkspaces, useCreateWorkspace } from "@/features/workspaces/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { useRagStream } from "@/features/rag/hooks";
import { useUIStore } from "@/store/ui";
import { EmptyState } from "@/components/empty-state";
import { TodayFeed } from "@/features/home/components/today-feed";
import { Mic, FileText, Inbox, FolderOpen } from "lucide-react";

function CreateWorkspaceDialog({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const createWorkspace = useCreateWorkspace();
  const setActiveWorkspaceId = useWorkspaceStore((s) => s.setActiveWorkspaceId);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    const ws = await createWorkspace.mutateAsync(name.trim());
    setActiveWorkspaceId(ws.id);
    setName("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0" style={{ background: "rgba(0,0,0,0.5)" }} onClick={onClose} />
      <div className="relative z-10 w-full max-w-md p-6 rounded-lg border" style={{ background: "var(--surface)", borderColor: "var(--border)", borderRadius: "var(--radius-lg)" }}>
        <h2 className="text-lg font-bold mb-4" style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}>워크스페이스 만들기</h2>
        <form onSubmit={handleSubmit}>
          <label className="block text-xs mb-1" style={{ color: "var(--text-secondary)" }}>워크스페이스 이름</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="예: 우리팀" autoFocus className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none mb-4" style={{ borderColor: "var(--border)", color: "var(--text-primary)", borderRadius: "var(--radius-sm)" }} />
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded text-sm" style={{ color: "var(--text-secondary)" }}>취소</button>
            <button type="submit" disabled={!name.trim() || createWorkspace.isPending} className="px-4 py-2 rounded text-sm font-medium disabled:opacity-50" style={{ background: "var(--accent)", color: "var(--background)", borderRadius: "var(--radius-sm)" }}>
              {createWorkspace.isPending ? "생성 중..." : "만들기"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const SUGGESTED_QUESTIONS = [
  "이번 주 회의 내용 요약해줘",
  "진행 중인 프로젝트 현황은?",
  "최근 결정 사항 정리해줘",
  "미완료 액션 아이템은?",
];

const QUICK_ACCESS = [
  { icon: Mic, label: "회의 추가", href: "/new" },
  { icon: FileText, label: "노트", href: "/notes" },
  { icon: Inbox, label: "Inbox", href: "/inbox" },
  { icon: FolderOpen, label: "프로젝트", href: "/projects" },
];

export default function DashboardPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { toggleCmdK } = useUIStore();
  const { ask } = useRagStream();

  const { data: workspaces, isLoading: isLoadingWs } = useWorkspaces();
  const { activeWorkspaceId, setActiveWorkspaceId } = useWorkspaceStore();

  const hasWorkspaces = workspaces && workspaces.length > 0;
  // localStorage에 남은 stale wid 가 현재 워크스페이스 목록에 없으면 첫 워크스페이스로 fallback
  const currentWid = activeWorkspaceId && workspaces?.find((w) => w.id === activeWorkspaceId) ? activeWorkspaceId : workspaces?.[0]?.id;

  // render 중 setState 금지 — useEffect로 분리 (BUG-H01)
  useEffect(() => {
    if (currentWid && currentWid !== activeWorkspaceId) {
      setActiveWorkspaceId(currentWid);
    }
  }, [currentWid, activeWorkspaceId, setActiveWorkspaceId]);

  if (isLoadingWs) {
    return <div className="flex items-center justify-center h-64"><p className="text-sm" style={{ color: "var(--text-muted)" }}>로딩 중...</p></div>;
  }

  if (!hasWorkspaces) {
    return (
      <div className="p-6">
        <EmptyState icon="🏢" title="워크스페이스를 만들어주세요" description="워크스페이스를 만들면 회의 녹음, 프로젝트 관리를 시작할 수 있습니다" />
        <div className="flex justify-center mt-4">
          <button onClick={() => setIsDialogOpen(true)} className="px-4 py-2 rounded text-sm font-medium" style={{ background: "var(--accent)", color: "var(--background)", borderRadius: "var(--radius-sm)" }}>워크스페이스 만들기</button>
        </div>
        <CreateWorkspaceDialog isOpen={isDialogOpen} onClose={() => setIsDialogOpen(false)} />
      </div>
    );
  }

  return (
    <div className="overflow-y-auto">
      <TodayFeed workspaceId={currentWid} />

      <div className="px-6 pb-8 max-w-3xl mx-auto">
        <h2 className="text-lg font-bold mb-4" style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}>무엇이든 질문하세요</h2>

        <button onClick={toggleCmdK} className="w-full flex items-center justify-between px-4 py-3 rounded border text-sm transition-colors mb-10" style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text-muted)", borderRadius: "var(--radius-md)" }}>
          <span>검색하거나 질문 입력...</span>
          <kbd className="px-2 py-0.5 rounded text-[10px]" style={{ background: "var(--surface-active)", borderRadius: "var(--radius-sm)", fontFamily: "var(--font-mono)" }}>⌘K</kbd>
        </button>

      <div className="mb-10">
        <h2 className="text-sm font-semibold mb-4 uppercase tracking-wider" style={{ color: "var(--text-muted)", fontFamily: "var(--font-display)" }}>추천 질문</h2>
        <div className="grid grid-cols-2 gap-2">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button key={q} onClick={() => ask(q)} className="text-left px-3 py-2.5 rounded border text-sm transition-colors" style={{ borderColor: "var(--border-subtle)", color: "var(--text-secondary)", borderRadius: "var(--radius-sm)" }} onMouseOver={(e) => (e.currentTarget.style.borderColor = "var(--accent)")} onMouseOut={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}>
              {q}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-sm font-semibold mb-4 uppercase tracking-wider" style={{ color: "var(--text-muted)", fontFamily: "var(--font-display)" }}>빠른 접근</h2>
        <div className="grid grid-cols-4 gap-3">
          {QUICK_ACCESS.map((item) => (
            <Link key={item.label} href={item.href} className="flex flex-col items-center gap-2 px-4 py-4 rounded border text-sm transition-colors" style={{ borderColor: "var(--border-subtle)", color: "var(--text-secondary)", borderRadius: "var(--radius-md)" }} onMouseOver={(e) => (e.currentTarget.style.background = "var(--surface-hover)")} onMouseOut={(e) => (e.currentTarget.style.background = "transparent")}>
              <item.icon size={24} style={{ color: "var(--text-muted)" }} />
              <span>{item.label}</span>
            </Link>
          ))}
        </div>
      </div>
      </div>

      <CreateWorkspaceDialog isOpen={isDialogOpen} onClose={() => setIsDialogOpen(false)} />
    </div>
  );
}
