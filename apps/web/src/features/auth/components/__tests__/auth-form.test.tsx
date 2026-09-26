/**
 * E2-X01 — 로그인↔가입 전환과 성공 이동이 callbackURL(초대 페이지)을 유지하되 외부로는 보내지 않는다.
 * C-024 — Better Auth 에러 코드는 영어 원문 대신 한국어로 보인다.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AuthForm, toKoreanError } from "../auth-form";

const { push, refresh, signInEmail, signUpEmail, searchParamsRef } = vi.hoisted(() => ({
  push: vi.fn(),
  refresh: vi.fn(),
  signInEmail: vi.fn(),
  signUpEmail: vi.fn(),
  searchParamsRef: { current: new URLSearchParams() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
  useSearchParams: () => searchParamsRef.current,
}));

vi.mock("@/lib/auth-client", () => ({
  authClient: {
    signIn: { email: signInEmail, social: vi.fn() },
    signUp: { email: signUpEmail },
  },
}));

function renderWithQuery(mode: "signIn" | "signUp", query: string) {
  searchParamsRef.current = new URLSearchParams(query);
  return render(<AuthForm mode={mode} />);
}

function fillAndSubmit(mode: "signIn" | "signUp") {
  fireEvent.change(screen.getByTestId("auth-email"), { target: { value: "new@example.com" } });
  fireEvent.change(screen.getByTestId("auth-password"), { target: { value: "password123" } });
  if (mode === "signUp") {
    fireEvent.change(screen.getByTestId("auth-name"), { target: { value: "신규" } });
  }
  fireEvent.click(screen.getByTestId("auth-submit"));
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AuthForm — callbackURL 유지 (E2-X01)", () => {
  it("가입 화면의 로그인 전환 링크가 초대 경로를 이어 붙인다", () => {
    renderWithQuery("signUp", "callbackURL=%2Finvite%2Fabc123");
    expect(screen.getByTestId("auth-switch-link")).toHaveAttribute(
      "href",
      "/sign-in?callbackURL=%2Finvite%2Fabc123",
    );
  });

  it("로그인 화면의 가입 전환 링크도 초대 경로를 유지한다", () => {
    renderWithQuery("signIn", "callbackURL=%2Finvite%2Fabc123");
    expect(screen.getByTestId("auth-switch-link")).toHaveAttribute(
      "href",
      "/sign-up?callbackURL=%2Finvite%2Fabc123",
    );
  });

  it("callbackURL 이 없으면 전환 링크는 쿼리 없이 그대로", () => {
    renderWithQuery("signIn", "");
    expect(screen.getByTestId("auth-switch-link")).toHaveAttribute("href", "/sign-up");
  });

  it("가입 성공 뒤 초대 페이지로 돌아간다 (Better Auth 에도 같은 경로를 넘긴다)", async () => {
    signUpEmail.mockResolvedValue({ data: {}, error: null });
    renderWithQuery("signUp", "callbackURL=%2Finvite%2Fabc123");

    fillAndSubmit("signUp");

    await waitFor(() => expect(push).toHaveBeenCalledWith("/invite/abc123"));
    expect(signUpEmail).toHaveBeenCalledWith(
      expect.objectContaining({ callbackURL: "/invite/abc123" }),
    );
  });

  it("외부 URL callbackURL 은 무시하고 기본 목적지로 간다 (open redirect 차단)", async () => {
    signInEmail.mockResolvedValue({ data: {}, error: null });
    renderWithQuery("signIn", "callbackURL=%2F%2Fevil.example%2Fphish");

    expect(screen.getByTestId("auth-switch-link")).toHaveAttribute("href", "/sign-up");
    fillAndSubmit("signIn");

    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
    expect(signInEmail).toHaveBeenCalledWith(expect.objectContaining({ callbackURL: "/dashboard" }));
  });
});

describe("AuthForm — 에러 한국어화 (C-024)", () => {
  it("중복 가입은 영어 원문 대신 '이미 가입된 이메일입니다' 로 보인다", async () => {
    signUpEmail.mockResolvedValue({
      data: null,
      error: {
        code: "USER_ALREADY_EXISTS_USE_ANOTHER_EMAIL",
        message: "User already exists. Use another email.",
        status: 422,
      },
    });
    renderWithQuery("signUp", "");

    fillAndSubmit("signUp");

    const alert = await screen.findByTestId("auth-error");
    expect(alert).toHaveTextContent("이미 가입된 이메일입니다");
    expect(alert).not.toHaveTextContent("User already exists");
    expect(push).not.toHaveBeenCalled();
  });

  it("미매핑 코드도 영어 원문을 노출하지 않는다", () => {
    expect(toKoreanError("SOME_NEW_CODE", 400)).toBe(
      "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.",
    );
    expect(toKoreanError(undefined, 429)).toBe("요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.");
    expect(toKoreanError("PASSWORD_TOO_LONG")).toBe("비밀번호가 너무 깁니다.");
  });
});
