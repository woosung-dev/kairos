// 첫 방문 inline tooltip — Sprint 24 Wave 2 T-OBN-05 D 옵션 (Linear-style)
// 결정 anchor: docs/superpowers/specs/2026-05-20-sprint24-wave2-trusty-heron-design.md §T-OBN-05
// 동작: localStorage 로 재방문 시 발화 X / dismiss(X) + Esc 종료 / analytics event (shown / dismissed)
// 2 무조건 (dashboard, search) + 2 조건부 (projects step<2, new step<3) — Codex cross-check 권장
"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useOnboarding } from "@/features/onboarding/hooks";

export type TooltipPage = "dashboard" | "search" | "projects" | "new";

const COPY: Record<TooltipPage, string> = {
  dashboard: "AI 검색은 ⌘K — 워크스페이스 회의/노트 전체 검색",
  search: "검색 범위는 현재 워크스페이스 전체입니다",
  projects: "+ 새 프로젝트로 시작하세요",
  new: "회의 음성을 업로드하면 AI 가 자동 요약합니다",
};

const STORAGE_KEY = (page: TooltipPage) =>
  `kairos.onboarding.tooltip_shown.${page}`;

// 조건부 페이지의 step gate — step < threshold + empty 시 발화
const STEP_GATED: Record<"projects" | "new", number> = {
  projects: 2, // step < 2 + empty
  new: 3, // step < 3 + empty
};

// 외부 analytics 가 mount 되어 있으면 발화. 없으면 no-op.
function trackEvent(event: string, page: TooltipPage) {
  if (typeof window === "undefined") return;
  // 글로벌 analytics SDK 가 있으면 발화 (Sentry / GA / Segment 등)
  const w = window as unknown as {
    analytics?: { track?: (event: string, props: Record<string, unknown>) => void };
  };
  w.analytics?.track?.(event, { page });
}

interface OnboardingTooltipProps {
  page: TooltipPage;
  /** /projects, /new 의 empty state 여부 (조건부 페이지에서만 의미 있음) */
  isEmpty?: boolean;
  children: ReactNode;
}

export function OnboardingTooltip({
  page,
  isEmpty,
  children,
}: OnboardingTooltipProps) {
  const { data: onboarding } = useOnboarding();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.localStorage.getItem(STORAGE_KEY(page))) return; // 재방문 X

    // 조건부 페이지 gate (projects / new)
    if (page === "projects" || page === "new") {
      const threshold = STEP_GATED[page];
      // onboarding 데이터가 아직 없으면 발화 X (false-positive 회피)
      if (!onboarding || onboarding.step >= threshold) return;
      if (!isEmpty) return;
    }

    setOpen(true);
    trackEvent("tooltip_shown", page);
  }, [page, onboarding, isEmpty]);

  const handleDismiss = () => {
    setOpen(false);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY(page), "1");
    }
    trackEvent("tooltip_dismissed", page);
  };

  return (
    <Popover open={open} onOpenChange={(o) => (o ? setOpen(true) : handleDismiss())}>
      <PopoverTrigger
        render={(props) => (
          <div {...props} className="contents">
            {children}
          </div>
        )}
      />
      <PopoverContent
        className="max-w-xs"
        data-testid={`onboarding-tooltip-${page}`}
        onKeyDown={(e) => {
          if (e.key === "Escape") handleDismiss();
        }}
      >
        <div className="flex items-start gap-2">
          <p className="text-sm leading-relaxed">{COPY[page]}</p>
          <button
            type="button"
            onClick={handleDismiss}
            className="text-muted-foreground hover:text-foreground shrink-0"
            aria-label="닫기"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
