"use client";

import { useEffect, useRef } from "react";

/**
 * IntersectionObserver 기반 입장 애니메이션 훅.
 * 요소가 뷰포트에 진입하면 'visible' 클래스를 추가 (one-shot).
 * prefers-reduced-motion 시 즉시 visible 처리.
 */
export function useReveal<T extends HTMLElement = HTMLElement>() {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // 모션 축소 설정 시 즉시 표시
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.classList.add("visible");
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.1 },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return ref;
}
