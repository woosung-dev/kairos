"use client";

import { useEffect, useState } from "react";

/**
 * 미디어 쿼리 매칭 상태를 반환하는 훅
 * SSR 시 false 반환 → 클라이언트 hydration 후 실제 값 반영
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    setMatches(media.matches);

    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    media.addEventListener("change", handler);
    return () => media.removeEventListener("change", handler);
  }, [query]);

  return matches;
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
