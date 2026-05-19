"use client";

export type EmptyStateContext = "meetings" | "projects" | "notes" | "inbox";

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: {
    label: string;
    href: string;
  };
  /** Sprint 22 OBN-03: 현재 사용자 onboarding step (0~4). 정의되면 context 별 가이드 힌트 표시. */
  onboardingStep?: number;
  /** Sprint 22 OBN-03: 도메인 context. 가이드 힌트 분기에 사용. */
  context?: EmptyStateContext;
}

/**
 * onboarding step + context 조합으로 추가 가이드 힌트 반환.
 * step >= 4 (완료) 면 힌트 없음. step undefined 면 힌트 없음.
 */
function getOnboardingHint(
  step: number | undefined,
  context: EmptyStateContext | undefined,
): string | null {
  if (step === undefined || step >= 4 || context === undefined) return null;

  if (context === "meetings" && step < 3) {
    return "첫 회의를 업로드해 보세요. 30초 녹음만으로도 AI 요약·액션 아이템이 자동 생성돼요.";
  }
  if (context === "projects" && step < 2) {
    return "프로젝트를 만들어 회의·노트·자료를 한 곳에 모으세요. AI 가 자동으로 인사이트를 정리합니다.";
  }
  if (context === "notes" && step < 3) {
    return "빠른 메모를 작성해 보세요. 작성한 메모는 자동으로 인덱싱되어 RAG 검색에 활용됩니다.";
  }
  if (context === "inbox" && step < 2) {
    return "회의나 노트가 생성되면 자동으로 분류되어 여기에 표시됩니다.";
  }
  return null;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  onboardingStep,
  context,
}: EmptyStateProps) {
  const hint = getOnboardingHint(onboardingStep, context);

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <span className="text-4xl mb-4">{icon}</span>}
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
      {hint && (
        <p
          className="text-sm mb-4 max-w-md"
          style={{ color: "var(--accent)" }}
        >
          {hint}
        </p>
      )}
      {action && (
        <a
          href={action.href}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{
            background: "var(--accent)",
            color: "var(--background)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {action.label}
        </a>
      )}
    </div>
  );
}
