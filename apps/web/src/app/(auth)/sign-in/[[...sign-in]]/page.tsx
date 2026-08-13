import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    // F-2C fix (Sprint 25 polish v2, codex 2차 P3): skip-link 타깃.
    // sign-up 패턴 mirror — div → main id="main-content" wrap.
    <main
      id="main-content"
      className="flex items-center justify-center min-h-screen"
      style={{ background: "var(--background)" }}
    >
      <SignIn forceRedirectUrl="/dashboard" signUpForceRedirectUrl="/dashboard" />
    </main>
  );
}
