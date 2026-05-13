import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div
      className="flex items-center justify-center min-h-screen"
      style={{ background: "var(--background)" }}
    >
      <SignUp forceRedirectUrl="/dashboard" signInForceRedirectUrl="/dashboard" />
    </div>
  );
}
