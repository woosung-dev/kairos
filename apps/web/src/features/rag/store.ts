"use client";

import { create } from "zustand";
import type { RagMessage, RagSource, SearchFilter } from "./types";

interface RagState {
  messages: RagMessage[];
  isStreaming: boolean;
  searchFilter: SearchFilter;
  addMessage: (message: RagMessage) => void;
  updateLastAssistantMessage: (content: string) => void;
  setSourcesOnLastAssistant: (sources: RagSource[]) => void;
  setIsStreaming: (streaming: boolean) => void;
  setSearchFilter: (filter: Partial<SearchFilter>) => void;
  clearMessages: () => void;
}

export const useRagStore = create<RagState>((set) => ({
  messages: [],
  isStreaming: false,
  searchFilter: {},

  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  updateLastAssistantMessage: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + content };
      }
      return { messages: msgs };
    }),

  setSourcesOnLastAssistant: (sources) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, sources };
      }
      return { messages: msgs };
    }),

  setIsStreaming: (streaming) => set({ isStreaming: streaming }),

  setSearchFilter: (filter) =>
    set((s) => ({ searchFilter: { ...s.searchFilter, ...filter } })),

  clearMessages: () => set({ messages: [] }),
}));
