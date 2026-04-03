import { Check } from "lucide-react";
import Link from "next/link";

const FEATURES_INCLUDED = [
  "무제한 회의 녹음 & AI 요약",
  "RAG 기반 지식 검색",
  "프로젝트 & 노트 관리",
  "팀 워크스페이스",
];

export function PricingSection() {
  return (
    <section
      id="pricing"
      className="px-6 py-24"
      style={{ background: "var(--background)" }}
    >
      <div className="max-w-lg mx-auto">
        <div
          className="rounded-xl border p-8 text-center"
          style={{
            borderColor: "var(--accent)",
            borderWidth: "2px",
            borderRadius: "var(--radius-lg)",
            background: "var(--surface)",
          }}
        >
          {/* 배지 */}
          <div
            className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium mb-6"
            style={{
              background: "var(--accent-subtle)",
              color: "var(--accent)",
              borderRadius: "var(--radius-full)",
            }}
          >
            오픈 베타
          </div>

          <h2
            className="mb-3"
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: "28px",
              color: "var(--text-primary)",
            }}
          >
            지금은 무료입니다
          </h2>
          <p
            className="mb-8"
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "15px",
              lineHeight: 1.7,
              color: "var(--text-secondary)",
            }}
          >
            모든 기능을 무료로 사용할 수 있습니다.
            <br />
            정식 출시 후 합리적인 구독 플랜을 제공합니다.
          </p>

          {/* 포함 기능 */}
          <div className="space-y-3 mb-8 text-left">
            {FEATURES_INCLUDED.map((feature) => (
              <div key={feature} className="flex items-center gap-3">
                <Check
                  size={16}
                  style={{ color: "var(--accent)", flexShrink: 0 }}
                />
                <span
                  className="text-sm"
                  style={{
                    fontFamily: "var(--font-body)",
                    color: "var(--text-primary)",
                  }}
                >
                  {feature}
                </span>
              </div>
            ))}
          </div>

          {/* CTA */}
          <Link
            href="/sign-up"
            className="block w-full py-3 rounded text-sm font-semibold transition-opacity hover:opacity-90"
            style={{
              background: "var(--accent)",
              color: "#FFFFFF",
              borderRadius: "var(--radius-sm)",
            }}
          >
            무료로 시작하기
          </Link>

          <p
            className="mt-4 text-xs"
            style={{ color: "var(--text-muted)" }}
          >
            신용카드 필요 없음
          </p>
        </div>
      </div>
    </section>
  );
}
