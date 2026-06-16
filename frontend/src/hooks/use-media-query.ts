"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * 미디어 쿼리 매칭 상태를 반환하는 훅.
 *
 * Sprint 29 R3 (breakpoint-flicker): 이전엔 useState(false)+useEffect 로 첫 클라
 * 렌더가 항상 false → mount 후 실제 값으로 1틱 늦게 갱신되며 사이드바가 깜빡였다.
 * useSyncExternalStore 로 클라에서 matchMedia 를 동기 스냅샷으로 읽어(SSR=false 고정)
 * hydration 직후 즉시 정확한 값으로 렌더 → 추가 paint 지연 제거.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const media = window.matchMedia(query);
      media.addEventListener("change", onChange);
      return () => media.removeEventListener("change", onChange);
    },
    [query],
  );

  const getSnapshot = () => window.matchMedia(query).matches;
  // SSR + hydration 일치용 — 서버엔 matchMedia 없음. 클라 첫 스냅샷이 즉시 보정한다.
  const getServerSnapshot = () => false;

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/**
 * 3단계 반응형 breakpoint 감지
 * - Mobile: < 768px
 * - Compact: 768px ~ 1279px
 * - Desktop: >= 1280px
 */
export function useBreakpoint() {
  const isAboveMobile = useMediaQuery("(min-width: 768px)");
  const isAboveCompact = useMediaQuery("(min-width: 1280px)");

  const isMobile = !isAboveMobile;
  const isCompact = isAboveMobile && !isAboveCompact;
  const isDesktop = isAboveCompact;

  return { isMobile, isCompact, isDesktop };
}
