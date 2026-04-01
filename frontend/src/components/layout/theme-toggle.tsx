"use client";

import { useCallback, useEffect, useState } from "react";

export function ThemeToggle() {
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    const theme = document.documentElement.getAttribute("data-theme");
    setIsDark(theme !== "light");
  }, []);

  const handleToggle = useCallback(() => {
    const next = isDark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    setIsDark(!isDark);
  }, [isDark]);

  return (
    <button
      onClick={handleToggle}
      className="p-1.5 rounded text-sm transition-colors"
      style={{ color: "var(--text-secondary)" }}
      aria-label="테마 전환"
    >
      {isDark ? "☀️" : "🌙"}
    </button>
  );
}
