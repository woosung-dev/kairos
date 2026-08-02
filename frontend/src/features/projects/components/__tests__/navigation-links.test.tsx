import type { ComponentPropsWithoutRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import type { Project } from "@/features/projects/types";
import { OnboardingView } from "../dashboard/onboarding-view";
import { ProjectCard } from "../project-card";

vi.mock("next/link", () => ({
  default: ({ children, ...props }: ComponentPropsWithoutRef<"a">) => (
    <a {...props} data-next-link="true">
      {children}
    </a>
  ),
}));

const PROJECT: Project = {
  id: "project-1",
  workspaceId: "workspace-1",
  title: "테스트 프로젝트",
  description: null,
  status: "active",
  visibility: "private",
  tags: [],
  sortOrder: 0,
  createdAt: "2026-08-01T00:00:00.000Z",
  updatedAt: "2026-08-01T00:00:00.000Z",
};

afterEach(() => {
  cleanup();
});

describe("프로젝트 내부 탐색", () => {
  it("프로젝트 카드를 기존 href의 Next Link로 렌더한다", () => {
    render(<ProjectCard project={PROJECT} />);

    const card = screen.getByTestId("project-card-project-1");
    expect(card).toHaveAttribute("href", "/projects/project-1");
    expect(card).toHaveAttribute("data-next-link", "true");
  });

  it("온보딩 CTA를 기존 href의 Next Link로 렌더한다", () => {
    render(<OnboardingView />);

    const meetingLink = screen.getByRole("link", { name: "회의 녹음" });
    const noteLink = screen.getByRole("link", { name: "노트 작성" });

    expect(meetingLink).toHaveAttribute("href", "/new");
    expect(meetingLink).toHaveAttribute("data-next-link", "true");
    expect(noteLink).toHaveAttribute("href", "/notes");
    expect(noteLink).toHaveAttribute("data-next-link", "true");
  });
});
