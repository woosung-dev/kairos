// 콘텐츠 없음 상태 — 도메인 공통 placeholder UI (Sprint 24 Wave 2 T-OBN-05 D 옵션)
// Sprint 22 OBN-03 의 onboarding-aware hint 분기는 제거. plain copy 유지.
"use client";

import Link from "next/link";

// Codex F-7 fix (Sprint 24 Wave 2 P3): action 이 href Link 만이 아니라 onClick 도 지원.
// /projects empty state CTA 가 /new (content add) 가 아닌 CreateProjectDialog 를 열어야 함.
type EmptyStateAction =
  | { label: string; href: string; onClick?: never }
  | { label: string; onClick: () => void; href?: never };

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: EmptyStateAction;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  const actionClassName = "px-4 py-2 rounded text-sm font-medium transition-colors";
  const actionStyle = {
    background: "var(--accent)",
    color: "var(--background)",
    borderRadius: "var(--radius-sm)",
  };
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="mb-4" style={{ color: "var(--text-muted)" }}>{icon}</div>}
      <h3
        className="text-lg font-semibold mb-2"
        style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
      >
        {title}
      </h3>
      {description && (
        <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
          {description}
        </p>
      )}
      {action && (action.href ? (
        <Link href={action.href} className={actionClassName} style={actionStyle}>
          {action.label}
        </Link>
      ) : (
        <button type="button" onClick={action.onClick} className={actionClassName} style={actionStyle}>
          {action.label}
        </button>
      ))}
    </div>
  );
}
