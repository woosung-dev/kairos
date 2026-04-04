"use client";

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
import { exportMeeting } from "../api";

interface MeetingExportButtonProps {
  meetingId: string;
  meetingTitle: string;
}

export function MeetingExportButton({ meetingId, meetingTitle }: MeetingExportButtonProps) {
  const { getToken } = useAuth();
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);

  const handleExport = async (format: "md" | "json") => {
    try {
      const token = await getToken();
      if (!token || !wid) return;
      const blob = await exportMeeting(token, wid, meetingId, format);
      const ext = format === "md" ? "md" : "json";
      triggerDownload(blob, `${meetingTitle}.${ext}`);
      toast.success("내보내기 완료");
    } catch {
      toast.error("내보내기에 실패했습니다");
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="inline-flex items-center justify-center h-8 w-8 rounded-md cursor-pointer transition-colors duration-150 hover:bg-[var(--surface-active)]"
      >
        <Download className="w-4 h-4" style={{ color: "var(--text-secondary)" }} />
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
