"use client";

import { X, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useUIStore } from "@/store/ui";

export function RAGPanel() {
  const isOpen = useUIStore((s) => s.isRAGPanelOpen);
  const close = () => useUIStore.getState().setRAGPanelOpen(false);

  if (!isOpen) return null;

  return (
    <div className="flex h-full w-96 flex-col border-l border-border bg-background">
      {/* 헤더 */}
      <div className="flex h-14 items-center justify-between border-b border-border px-4">
        <h3 className="text-sm font-semibold">AI 어시스턴트</h3>
        <Button variant="ghost" size="icon" onClick={close} aria-label="닫기">
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* 메시지 영역 */}
      <ScrollArea className="flex-1 p-4">
        <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            <span className="text-2xl">🔍</span>
          </div>
          <h4 className="text-sm font-medium">프로젝트 지식 검색</h4>
          <p className="max-w-[240px] text-xs text-muted-foreground">
            회의록, 노트, 첨부파일을 기반으로 질문에 답변합니다.
            프로젝트 또는 영역을 선택한 후 질문하세요.
          </p>
        </div>
      </ScrollArea>

      {/* 입력 영역 */}
      <div className="border-t border-border p-4">
        <div className="flex items-center gap-2 rounded-md border border-input bg-muted/30 px-3 py-2">
          <input
            type="text"
            placeholder="질문을 입력하세요..."
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            disabled
          />
          <Button variant="ghost" size="icon" className="h-7 w-7" disabled>
            <Send className="h-3.5 w-3.5" />
          </Button>
        </div>
        <p className="mt-2 text-[10px] text-muted-foreground">
          RAG 기능은 Step 6에서 활성화됩니다.
        </p>
      </div>
    </div>
  );
}
