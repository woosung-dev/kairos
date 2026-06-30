// Sprint 29 R4 (rag-markdown) 회귀 가드 — 마크다운 렌더 + [N] 출처 보존.
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MarkdownMessage } from "../markdown-message";

describe("MarkdownMessage — Sprint 29 R4 (rag-markdown)", () => {
  it("마크다운(### 제목 / **굵게** / 리스트)을 렌더한다 (raw 토큰 노출 X)", () => {
    const { container } = render(
      <MarkdownMessage
        content={"### 제목\n\n**굵게** 일반 텍스트\n\n- 항목1\n- 항목2"}
        onCitationClick={() => {}}
        activeCitation={null}
      />,
    );

    expect(
      screen.getByRole("heading", { level: 3, name: "제목" }),
    ).toBeInTheDocument();
    expect(container.querySelector("strong")?.textContent).toBe("굵게");
    expect(container.querySelectorAll("li")).toHaveLength(2);
    // raw markdown 토큰이 그대로 노출되지 않아야 함
    expect(container.textContent).not.toContain("###");
    expect(container.textContent).not.toContain("**");
  });

  it("인라인 출처 [N] 을 CitationBadge(button)로 렌더하고 클릭 시 콜백 호출", () => {
    const onCitationClick = vi.fn();
    render(
      <MarkdownMessage
        content={"결정 사항은 다음과 같다 [1] 그리고 추가로 [2] 있다."}
        onCitationClick={onCitationClick}
        activeCitation={null}
      />,
    );

    const badge1 = screen.getByRole("button", { name: "출처 1" });
    const badge2 = screen.getByRole("button", { name: "출처 2" });
    expect(badge1).toBeInTheDocument();
    expect(badge2).toBeInTheDocument();
    // raw [1] 텍스트가 아니라 badge 로 치환됨
    expect(document.body.textContent).not.toContain("[1]");

    fireEvent.click(badge1);
    expect(onCitationClick).toHaveBeenCalledWith(1);
  });

  it("마크다운 + 출처를 함께 렌더한다 (단락 내 [N] 보존)", () => {
    const onCitationClick = vi.fn();
    render(
      <MarkdownMessage
        content={"**핵심**: 마이그레이션 완료 [1]."}
        onCitationClick={onCitationClick}
        activeCitation={null}
      />,
    );
    expect(screen.getByRole("button", { name: "출처 1" })).toBeInTheDocument();
    // 굵게도 함께 렌더
    expect(document.querySelector("strong")?.textContent).toBe("핵심");
  });

  it("중첩 인라인 노드(**굵게 [1]**) 안의 출처도 보존한다 (codex review fix)", () => {
    const onCitationClick = vi.fn();
    const { container } = render(
      <MarkdownMessage
        content={"**중요한 결정 [1]** 이후 진행."}
        onCitationClick={onCitationClick}
        activeCitation={null}
      />,
    );
    // [1] 이 strong 내부에 있어도 CitationBadge 로 치환
    expect(screen.getByRole("button", { name: "출처 1" })).toBeInTheDocument();
    // raw [1] 텍스트가 남지 않음
    expect(container.textContent).not.toContain("[1]");
    // strong 안에 badge(button)가 위치
    expect(container.querySelector("strong button")).not.toBeNull();
  });

  // BL-F7 회귀 가드 — 표/인용/h4-h6 안의 [N] 도 CitationBadge 로 치환 (이전엔 raw 노출).
  it("BL-F7: blockquote / table cell / h4 안의 출처 [N] 도 CitationBadge 로 렌더한다", () => {
    const onCitationClick = vi.fn();
    const content = [
      "#### 작은 제목 [1]",
      "",
      "> 인용문 안의 근거 [2]",
      "",
      "| 항목 | 비고 |",
      "| --- | --- |",
      "| 결정 | 채택 [3] |",
    ].join("\n");
    const { container } = render(
      <MarkdownMessage
        content={content}
        onCitationClick={onCitationClick}
        activeCitation={null}
      />,
    );

    expect(screen.getByRole("button", { name: "출처 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "출처 2" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "출처 3" })).toBeInTheDocument();
    // raw [N] 잔존 없음
    expect(container.textContent).not.toContain("[1]");
    expect(container.textContent).not.toContain("[2]");
    expect(container.textContent).not.toContain("[3]");
    // 인용/표 구조 안에 badge 위치
    expect(container.querySelector("blockquote button")).not.toBeNull();
    expect(container.querySelector("td button")).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "출처 3" }));
    expect(onCitationClick).toHaveBeenCalledWith(3);
  });
});
