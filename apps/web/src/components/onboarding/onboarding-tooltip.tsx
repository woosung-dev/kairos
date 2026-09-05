// 첫 방문 inline tooltip — Sprint 24 Wave 2 T-OBN-05 D 옵션 (Linear-style)
// 결정 anchor: git history §T-OBN-05
// 동작: localStorage 로 재방문 시 발화 X / dismiss(X) + Esc 종료 / analytics event (shown / dismissed)
// 2 무조건 (dashboard, search) + 2 조건부 (projects step<2, new step<3) — Codex cross-check 권장
"use client";

import { useEffect, useRef, useState } from "react";
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
  // CI fix (Sprint 24 Wave 2 PR #101 e2e fail): React 18 Strict Mode 의 useEffect 2회 실행 우회.
  // 기존: useEffect 안에서 setOpen + localStorage.setItem 동시 실행 → 첫 mount 시 마크 set
  //      → Strict Mode 두 번째 mount (cleanup → re-mount) 에서 localStorage 이미 set → early return
  //      → setOpen(true) 호출 안 됨 → tooltip 발화 X (CI e2e onboarding-tooltip-search FAIL 원인).
  // fix: useRef 로 첫 mount 한 번만 setOpen, localStorage 마크는 dismiss / open 후 setTimeout 으로 분리.
  const didInitRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (didInitRef.current) return; // Strict Mode re-mount 차단
    if (window.localStorage.getItem(STORAGE_KEY(page))) return; // 재방문 X

    // 조건부 페이지 gate (projects / new)
    if (page === "projects" || page === "new") {
      const threshold = STEP_GATED[page];
      // onboarding 데이터가 아직 없으면 발화 X (false-positive 회피)
      if (!onboarding || onboarding.step >= threshold) return;
      if (!isEmpty) return;
    }

    didInitRef.current = true;
    setOpen(true);
    trackEvent("tooltip_shown", page);
    // Codex F-11 fix (Sprint 24 Wave 2 P3): open 후 storage key set — 페이지 leave / Cmd+K close 시 재발화 회피.
    // Strict Mode 호환: setOpen 직후 동기 setItem 하면 두 번째 mount 시 early return → setOpen 안 됨.
    // setTimeout 으로 다음 tick (Strict Mode 의 unmount → re-mount cycle 완료 후) 에 setItem.
    window.setTimeout(() => {
      window.localStorage.setItem(STORAGE_KEY(page), "1");
    }, 0);
  }, [page, onboarding, isEmpty]);

  const handleDismiss = () => {
    setOpen(false);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY(page), "1");
    }
    trackEvent("tooltip_dismissed", page);
  };

  return (
    <Popover
      open={open}
      onOpenChange={(o) => {
        if (o) {
          // Codex F-14 fix (Sprint 24 Wave 2 P2): dismissed 후 trigger click 재발화 차단.
          // localStorage key set 이미 있으면 open 요청 무시 (one-time onboarding contract 보장).
          if (typeof window !== "undefined" && window.localStorage.getItem(STORAGE_KEY(page))) {
            return;
          }
          setOpen(true);
        } else {
          handleDismiss();
        }
      }}
    >
      {/* Codex F-6 + F-16 fix (Sprint 24 Wave 2 P2): real layout box + full-width 보존.
          F-6: display:contents 는 bounding rect 0 → Popover positioning 깨짐. wrapper 필수.
          F-16: inline-block 은 shrink-wrap → 자식 w-full / block 컨트롤 (search button, Cmd-K) 가 collapse.
          해결: block + w-full + min-w-0 — 자식의 full-width 보존, 부모 flex container 에서도 안전. */}
      {/* BUG-S27d-1 fix (Sprint 27d opus follow-up): Base UI PopoverTrigger 의 default
          nativeButton={true} 가 <button> 렌더링을 기대 → render prop 의 <div> 와 충돌해
          a11y console.error. nativeButton={false} 로 div trigger 허용 (children 이
          button 인 경우 button-in-button 회피). */}
      <PopoverTrigger
        nativeButton={false}
        render={(props) => (
          <div {...props} className="block w-full min-w-0">
            {children}
          </div>
        )}
      />
      {/* initialFocus/finalFocus=false — 안내 말풍선이 포커스를 가져가면 ⌘K 팔레트의 autoFocus
          input 이 포커스를 잃어 첫 방문 사용자의 앞 글자가 사라진다 (실측: "?9월…" 에서 "?9" 소실).
          툴팁은 읽기 전용이라 포커스를 가질 이유가 없다. */}
      <PopoverContent
        className="max-w-xs"
        initialFocus={false}
        finalFocus={false}
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
