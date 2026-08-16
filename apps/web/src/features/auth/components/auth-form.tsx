"use client";
// 로그인 / 회원가입 공용 폼 (ADR-031 — Clerk 의 <SignIn>/<SignUp> 대체)
//
// ★셀렉터가 계약이다. 예전에는 e2e 가 `input[name="identifier"]` 를 잡았는데 그건 Clerk SDK 의
//   내부 규약이었다 — 벤더가 바뀌면 같이 깨진다. 이제 폼이 우리 코드이므로 `data-testid` 를
//   명시적 계약으로 둔다 (`apps/web/e2e/auth.setup.ts` 와 한 쌍).

import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useState } from "react";

import { authClient } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Mode = "signIn" | "signUp";

const COPY = {
  signIn: {
    title: "다시 오셨네요",
    submit: "로그인",
    google: "Google 계정으로 계속하기",
    switchPrompt: "아직 계정이 없으신가요?",
    switchLabel: "회원가입",
    switchHref: "/sign-up",
  },
  signUp: {
    title: "Kairos 시작하기",
    submit: "회원가입",
    google: "Google 계정으로 시작하기",
    switchPrompt: "이미 계정이 있으신가요?",
    switchLabel: "로그인",
    switchHref: "/sign-in",
  },
} as const;

/** Better Auth 에러 코드를 한국어로 옮긴다. 미매핑은 원문 노출 대신 일반 문구로 덮는다. */
function toKoreanError(code: string | undefined, fallback: string): string {
  switch (code) {
    case "INVALID_EMAIL_OR_PASSWORD":
      return "이메일 또는 비밀번호가 올바르지 않습니다.";
    case "USER_ALREADY_EXISTS":
      return "이미 가입된 이메일입니다. 로그인해 주세요.";
    case "PASSWORD_TOO_SHORT":
      return "비밀번호는 8자 이상이어야 합니다.";
    case "INVALID_EMAIL":
      return "이메일 형식이 올바르지 않습니다.";
    default:
      return fallback || "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";
  }
}

export function AuthForm({ mode }: { mode: Mode }) {
  const copy = COPY[mode];
  const router = useRouter();
  const searchParams = useSearchParams();
  // 보호 라우트에서 튕겨온 경우 원래 목적지로 돌려보낸다 (proxy.ts 가 심어준다).
  const callbackURL = searchParams.get("callbackURL") ?? "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsPending(true);
    try {
      const result =
        mode === "signIn"
          ? await authClient.signIn.email({ email, password, callbackURL })
          : await authClient.signUp.email({
              email,
              password,
              name: name.trim() || email.split("@")[0],
              callbackURL,
            });
      if (result.error) {
        setError(toKoreanError(result.error.code, result.error.message ?? ""));
        return;
      }
      router.push(callbackURL);
      // 서버 컴포넌트(랜딩 리다이렉트 등)가 새 세션을 보도록 강제한다.
      router.refresh();
    } catch {
      setError("네트워크 오류로 요청이 실패했습니다. 연결을 확인해 주세요.");
    } finally {
      setIsPending(false);
    }
  };

  const handleGoogle = async () => {
    setError(null);
    setIsPending(true);
    try {
      await authClient.signIn.social({ provider: "google", callbackURL });
      // 성공 시 Google 로 이동하므로 여기로 돌아오지 않는다.
    } catch {
      setError("Google 로그인을 시작하지 못했습니다. 잠시 후 다시 시도해 주세요.");
      setIsPending(false);
    }
  };

  return (
    <div className="w-full max-w-sm">
      <h1
        className="mb-6 text-center"
        style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)" }}
      >
        {copy.title}
      </h1>

      <Button
        type="button"
        variant="outline"
        size="lg"
        className="w-full"
        onClick={handleGoogle}
        disabled={isPending}
        data-testid="auth-google"
      >
        {copy.google}
      </Button>

      <div className="my-5 flex items-center gap-3">
        <span className="h-px flex-1" style={{ background: "var(--border)" }} />
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>또는</span>
        <span className="h-px flex-1" style={{ background: "var(--border)" }} />
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        {mode === "signUp" && (
          <label className="flex flex-col gap-1.5">
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>이름</span>
            <Input
              name="name"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="표시할 이름 (선택)"
              data-testid="auth-name"
            />
          </label>
        )}

        <label className="flex flex-col gap-1.5">
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>이메일</span>
          <Input
            name="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            data-testid="auth-email"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>비밀번호</span>
          <Input
            name="password"
            type="password"
            required
            minLength={8}
            autoComplete={mode === "signIn" ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            data-testid="auth-password"
          />
        </label>

        {error && (
          <p
            role="alert"
            data-testid="auth-error"
            style={{ fontSize: 13, color: "var(--destructive, #dc2626)", lineHeight: 1.6 }}
          >
            {error}
          </p>
        )}

        <Button
          type="submit"
          size="lg"
          className="mt-1 w-full"
          disabled={isPending}
          data-testid="auth-submit"
        >
          {isPending ? "처리 중…" : copy.submit}
        </Button>
      </form>

      <p
        className="mt-5 text-center"
        style={{ fontSize: 13, color: "var(--text-secondary)" }}
      >
        {copy.switchPrompt}{" "}
        <Link
          href={copy.switchHref}
          style={{ color: "var(--accent)", textDecoration: "underline" }}
        >
          {copy.switchLabel}
        </Link>
      </p>

      {/* 비밀번호 재설정은 아직 없다 — 이메일 발송 인프라가 레포에 0건이기 때문이다(ADR-031
          "이번 범위에서 제외한 갭"). 사용자가 잠긴 뒤에 알게 되는 것이 최악이라 미리 알린다. */}
      {mode === "signIn" && (
        <p
          className="mt-2 text-center"
          style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6 }}
        >
          비밀번호를 잊으셨다면 Google 로그인을 쓰시거나 운영자에게 문의해 주세요.
        </p>
      )}
    </div>
  );
}
