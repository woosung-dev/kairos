"use client";

import { useCallback, useEffect } from "react";
import { ChevronLeft, ChevronRight, FlaskConical } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export interface PrototypeVariant {
  key: string;
  label: string;
}

interface PrototypeSwitcherProps {
  variants: readonly PrototypeVariant[];
  currentVariant: string;
}

function isEditableTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLElement &&
    (target.tagName === "INPUT" ||
      target.tagName === "TEXTAREA" ||
      target.isContentEditable);
}

/** 개발용 UI 프로토타입 전용 스위처. production 빌드에서는 렌더하지 않는다. */
export function PrototypeSwitcher({
  variants,
  currentVariant,
}: PrototypeSwitcherProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentIndex = Math.max(
    variants.findIndex((variant) => variant.key === currentVariant),
    0,
  );
  const activeVariant = variants[currentIndex];

  const handleChangeVariant = useCallback(
    (direction: -1 | 1) => {
      const nextIndex = (currentIndex + direction + variants.length) % variants.length;
      const params = new URLSearchParams(searchParams.toString());
      params.set("variant", variants[nextIndex].key);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [currentIndex, pathname, router, searchParams, variants],
  );

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) return;
      if (event.key === "ArrowLeft") handleChangeVariant(-1);
      if (event.key === "ArrowRight") handleChangeVariant(1);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleChangeVariant]);

  if (process.env.NODE_ENV === "production") return null;

  return (
    <div
      className="fixed bottom-5 left-1/2 z-50 flex items-center gap-1 rounded-full border px-2 py-1 shadow-xl"
      style={{
        background: "var(--surface-active)",
        borderColor: "var(--border)",
        color: "var(--text-primary)",
        transform: "translateX(-50%)",
      }}
    >
      <FlaskConical size={14} style={{ color: "var(--accent)" }} aria-hidden />
      <button
        type="button"
        onClick={() => handleChangeVariant(-1)}
        className="rounded p-1 transition-colors hover:opacity-80"
        aria-label="이전 프로토타입 보기"
      >
        <ChevronLeft size={16} />
      </button>
      <span
        className="min-w-35 px-1 text-center text-caption"
        aria-live="polite"
        style={{ color: "var(--text-secondary)" }}
      >
        {activeVariant.key} — {activeVariant.label}
      </span>
      <button
        type="button"
        onClick={() => handleChangeVariant(1)}
        className="rounded p-1 transition-colors hover:opacity-80"
        aria-label="다음 프로토타입 보기"
      >
        <ChevronRight size={16} />
      </button>
    </div>
  );
}
