"use client";

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: {
    label: string;
    href: string;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
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
