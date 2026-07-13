"use client";

import { onboardingKeys } from "@/lib/query-keys";
import { useCallback } from "react";
import { useApiClient } from "@/lib/use-api-client";
import { useQueryClient } from "@tanstack/react-query";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { askRag } from "./api";
import { useRagStore } from "./store";
import type { SSESearchResultsEvent, SSEAnswerEvent } from "./types";

export function useRagStream() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const wid = useWorkspaceStore((s) => s.activeWorkspaceId);
  // Sprint 29 R3 (rag-store): selector 별 구독 — 이전 전체 구독은 SSE 토큰마다 store 가
  // 바뀔 때 useRagStream 소비자(cmd-k 포함)를 전부 re-render 시켰다. action 은 안정 식별자,
  // searchFilter 만 데이터.
  const addMessage = useRagStore((s) => s.addMessage);
  const updateLastAssistantMessage = useRagStore(
    (s) => s.updateLastAssistantMessage,
  );
  const setSourcesOnLastAssistant = useRagStore(
    (s) => s.setSourcesOnLastAssistant,
  );
  const setIsStreaming = useRagStore((s) => s.setIsStreaming);
  const searchFilter = useRagStore((s) => s.searchFilter);

  const ask = useCallback(
    async (question: string) => {
      if (!wid) return;

      // 거동 보존: 토큰 부재 시 메시지 추가 없이 조용히 반환 (기존 null-token 분기).
      const token = await api.getToken().catch(() => null);
      if (!token) return;

      // 사용자 메시지 추가
      addMessage({
        id: crypto.randomUUID(),
        role: "user",
        content: question,
        createdAt: new Date().toISOString(),
      });

      // 어시스턴트 플레이스홀더
      addMessage({
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        isStreaming: true,
        createdAt: new Date().toISOString(),
      });

      setIsStreaming(true);

      try {
        const response = await askRag(api, wid, {
          question,
          projectId: searchFilter.projectId ?? null,
          timeRange: searchFilter.timeRange ?? null,
          sourceType: searchFilter.sourceType ?? null,
        });

        const reader = response.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let currentEvent = "";
          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              const data = line.slice(5).trim();
              if (!data) continue;

              try {
                const parsed = JSON.parse(data);
                switch (currentEvent) {
                  case "thinking":
                    break;
                  case "search_results": {
                    const sr = parsed as SSESearchResultsEvent;
                    setSourcesOnLastAssistant(sr.chunks);
                    break;
                  }
                  case "answer": {
                    const ans = parsed as SSEAnswerEvent;
                    updateLastAssistantMessage(ans.token);
                    break;
                  }
                  case "done":
                    // Sprint 22 OBN-02: 첫 RAG ask 성공 시 BE 가 step=4 advance → 재조회
                    queryClient.invalidateQueries({
                      queryKey: onboardingKeys.all,
                    });
                    break;
                }
              } catch {
                // JSON 파싱 실패 무시
              }
            }
          }
        }
      } catch {
        updateLastAssistantMessage(
          "오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        );
      } finally {
        setIsStreaming(false);
      }
    },
    [wid, api, addMessage, updateLastAssistantMessage, setSourcesOnLastAssistant, setIsStreaming, searchFilter, queryClient]
  );

  return { ask };
}
