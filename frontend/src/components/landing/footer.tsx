export function Footer() {
  return (
    <footer
      className="px-6 py-8 border-t"
      style={{
        background: "var(--surface-hover)",
        borderColor: "var(--border-subtle)",
      }}
    >
      <div className="max-w-5xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span
            className="text-sm font-bold"
            style={{
              fontFamily: "var(--font-display)",
              color: "var(--accent)",
            }}
          >
            Kairos
          </span>
          <span
            className="text-xs"
            style={{ color: "var(--text-muted)" }}
          >
            &copy; 2026 Kairos. All rights reserved.
          </span>
        </div>
      </div>
    </footer>
  );
}
