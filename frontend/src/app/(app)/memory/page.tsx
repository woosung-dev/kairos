// Sprint 15 R4 — /memory 페이지 (B3 search-first FAB layout)
"use client";

import { useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { useRecall } from "@/features/memory/hooks";
import { CaptureSheet } from "@/features/memory/components/CaptureSheet";
import { PromoteModal } from "@/features/memory/components/PromoteModal";
import { RecallResultCard } from "@/features/memory/components/RecallResultCard";
import { useBreakpoint } from "@/hooks/use-media-query";

const DEBOUNCE_MS = 300;

/**
 * 단순 디바운스 — 입력 폭주 시 React Query 호출을 묶어준다.
 * useDebounce 공통 훅이 아직 없어 페이지 로컬에 두는 편이 가볍다.
 */
function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(handle);
  }, [value, delay]);
  return debounced;
}

export default function MemoryPage() {
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const workspaceId = activeWorkspaceId ?? undefined;
  const { isMobile } = useBreakpoint();

  const [query, setQuery] = useState("");
  const [isCaptureOpen, setIsCaptureOpen] = useState(false);
  const [promoteMemoryId, setPromoteMemoryId] = useState<string | null>(null);
  const debouncedQuery = useDebouncedValue(query, DEBOUNCE_MS);

  const isEmpty = !query.trim();
  const isQueryReady = debouncedQuery.trim().length >= 2;

  const { data, isLoading, isError } = useRecall(
    workspaceId,
    debouncedQuery,
    isQueryReady
  );
  const hasResults = !!data && data.sources.length > 0;

  return (
    <div className="relative mx-auto min-h-screen max-w-3xl px-4 py-8">
      <header className="mb-6">
        <h1 className="mb-1 text-2xl font-semibold">메모 검색</h1>
        <p className="text-sm text-muted-foreground">
          저장한 모든 메모를 검색하세요. AI가 의미와 키워드 모두로 찾아드립니다.
        </p>
      </header>

      <div className="relative mb-6">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="무엇을 다시 찾고 싶으세요? (예: Sprint 15 wedge)"
          className="h-12 pl-10 text-base"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          autoFocus
        />
      </div>

      {isEmpty && (
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <p className="mb-4 text-sm text-muted-foreground">
            아직 검색어를 입력하지 않았어요. 오른쪽 아래 + 버튼으로 메모를
            먼저 추가해 보세요.
          </p>
          <p className="text-xs text-muted-foreground">↘ 우측 하단 + 버튼</p>
        </div>
      )}

      {!isEmpty && !isQueryReady && (
        <p className="text-sm text-muted-foreground">두 글자 이상 입력해 주세요.</p>
      )}

      {!isEmpty && isQueryReady && isLoading && (
        <p className="text-sm text-muted-foreground">검색 중…</p>
      )}

      {!isEmpty && isQueryReady && isError && (
        <p className="text-sm text-destructive">검색에 실패했습니다.</p>
      )}

      {!isEmpty && isQueryReady && !isLoading && data && !hasResults && (
        <div className="rounded-lg border border-border p-6 text-center">
          <p className="text-sm text-muted-foreground">매칭되는 메모가 없습니다.</p>
        </div>
      )}

      {hasResults && data && (
        <>
          {data.fallback_used && (
            <p className="mb-3 text-xs text-muted-foreground">
              키워드 매칭 결과를 보여드려요.
            </p>
          )}
          <div className="flex flex-col gap-3">
            {data.sources.map((source) => (
              <RecallResultCard
                key={source.memory_id}
                source={source}
                onPromote={(id) => setPromoteMemoryId(id)}
              />
            ))}
          </div>
        </>
      )}

      {/*
        Sprint 22 BL-017 + OBN-04: mobile bottom-nav 충돌 회피.
        - 데스크톱: bottom-8 (32px) — bottom-nav 없음.
        - 모바일: bottom-nav (56px) 위로 16px 띄움 → 72px (~bottom-18).
      */}
      <Button
        type="button"
        size="icon"
        className="fixed right-6 md:right-8 h-14 w-14 animate-pulse rounded-full shadow-xl"
        style={{
          bottom: isMobile
            ? "calc(var(--bottom-nav-height) + 16px)"
            : "2rem",
        }}
        onClick={() => setIsCaptureOpen(true)}
        aria-label="새 메모 추가"
      >
        <Plus className="h-6 w-6" />
      </Button>

      <CaptureSheet
        workspaceId={workspaceId}
        open={isCaptureOpen}
        onOpenChange={setIsCaptureOpen}
      />

      {promoteMemoryId && workspaceId && (
        <PromoteModal
          memoryId={promoteMemoryId}
          sourceWorkspaceId={workspaceId}
          open={promoteMemoryId !== null}
          onOpenChange={(open) => {
            if (!open) setPromoteMemoryId(null);
          }}
        />
      )}
    </div>
  );
}
