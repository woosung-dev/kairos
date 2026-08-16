import { Suspense } from "react";

import { AuthForm } from "@/features/auth/components/auth-form";

export default function SignInPage() {
  return (
    // F-2C fix (Sprint 25 polish v2, codex 2차 P3): skip-link 타깃.
    // sign-up 패턴 mirror — div → main id="main-content" wrap.
    <main
      id="main-content"
      className="flex items-center justify-center min-h-screen px-4"
      style={{ background: "var(--background)" }}
    >
      {/* useSearchParams(callbackURL 읽기) 는 Suspense 경계를 요구한다. */}
      <Suspense fallback={null}>
        <AuthForm mode="signIn" />
      </Suspense>
    </main>
  );
}
