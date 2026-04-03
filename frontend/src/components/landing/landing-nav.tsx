"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export function LandingNav() {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
      style={{
        background: isScrolled
          ? "rgba(250,250,250,0.8)"
          : "transparent",
        backdropFilter: isScrolled ? "blur(12px)" : "none",
        borderBottom: isScrolled
          ? "1px solid var(--border-subtle)"
          : "1px solid transparent",
      }}
    >
      <div className="max-w-6xl mx-auto flex items-center justify-between px-6 py-4">
        <Link
          href="/"
          className="text-xl font-bold"
          style={{
            fontFamily: "var(--font-display)",
            color: "var(--accent)",
          }}
        >
          Kairos
        </Link>

        <div className="flex items-center gap-4">
          <a
            href="#features"
            className="text-sm hidden sm:block"
            style={{ color: "var(--text-secondary)" }}
          >
            기능
          </a>
          <a
            href="#pricing"
            className="text-sm hidden sm:block"
            style={{ color: "var(--text-secondary)" }}
          >
            가격
          </a>
          <Link
            href="/sign-in"
            className="text-sm"
            style={{ color: "var(--text-secondary)" }}
          >
            로그인
          </Link>
          <Link
            href="/sign-up"
            className="px-4 py-2 rounded text-sm font-medium"
            style={{
              background: "var(--accent)",
              color: "#FFFFFF",
              borderRadius: "var(--radius-sm)",
            }}
          >
            무료로 시작하기
          </Link>
        </div>
      </div>
    </nav>
  );
}
