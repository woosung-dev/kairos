// 콘텐츠 3개 미만 프로젝트의 온보딩 안내 뷰 — 회의 녹음/노트 작성 유도 (BL-AV-1 분해)
"use client";

import { Mic, Rocket, StickyNote } from "lucide-react";
import Link from "next/link";

export function OnboardingView() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <Rocket className="w-12 h-12 mb-6" style={{ color: "var(--text-muted)" }} />
      <h2
        className="text-xl font-bold mb-2"
        style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
      >
        프로젝트를 시작하세요
      </h2>
      <p className="text-sm mb-8 max-w-md" style={{ color: "var(--text-muted)" }}>
        첫 회의를 녹음하거나 노트를 작성해보세요. AI가 자동으로 요약하고 지식을 구조화합니다.
      </p>
      <div className="flex items-center gap-3">
        <Link
          href="/new"
          className="px-5 py-2.5 rounded text-sm font-medium transition-colors"
          style={{
            background: "var(--accent)",
            color: "var(--background)",
            borderRadius: "var(--radius-sm)",
            minHeight: "44px",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            cursor: "pointer",
          }}
        >
          <Mic className="w-4 h-4" />
          회의 녹음
        </Link>
        <Link
          href="/notes"
          className="px-5 py-2.5 rounded text-sm font-medium transition-colors border"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            borderRadius: "var(--radius-sm)",
            minHeight: "44px",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            cursor: "pointer",
          }}
        >
          <StickyNote className="w-4 h-4" />
          노트 작성
        </Link>
      </div>
    </div>
  );
}
