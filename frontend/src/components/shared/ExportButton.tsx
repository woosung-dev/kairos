"use client";
// 도메인 무관 내보내기 버튼 — export fn 주입받아 Markdown/JSON 다운로드 (notes/meetings 공용)

import { Download } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { toast } from "sonner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { triggerDownload } from "@/lib/download";

type ExportFormat = "md" | "json";

interface ExportButtonProps {
  /** (token, workspaceId, id, format) → Blob 를 반환하는 도메인별 export fn */
  exportFn: (
    token: string,
    workspaceId: string,
    id: string,
    format: ExportFormat,
  ) => Promise<Blob>;
  id: string;
  /** 다운로드 파일명 (확장자 제외). 빈 값이면 "Untitled". */
  title: string;
}

export function ExportButton({ exportFn, id, title }: ExportButtonProps) {
  const { getToken } = useAuth();
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);

  const handleExport = async (format: ExportFormat) => {
    try {
      const token = await getToken();
      if (!token || !wid) return;
      const blob = await exportFn(token, wid, id, format);
      triggerDownload(blob, `${title || "Untitled"}.${format}`);
      toast.success("내보내기 완료");
    } catch {
      toast.error("내보내기에 실패했습니다");
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="내보내기"
        title="내보내기 (Markdown / JSON)"
        className="inline-flex items-center justify-center gap-1.5 h-9 px-3 rounded-md cursor-pointer border text-xs font-medium transition-colors duration-150 hover:bg-[var(--surface-active)]"
        style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
      >
        <Download className="w-4 h-4" />
        <span>내보내기</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem className="cursor-pointer" onClick={() => handleExport("md")}>
          Markdown (.md)
        </DropdownMenuItem>
        <DropdownMenuItem className="cursor-pointer" onClick={() => handleExport("json")}>
          JSON (.json)
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
