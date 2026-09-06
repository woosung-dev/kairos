import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { useUIStore } from "@/store/ui";
import { CmdK } from "../cmd-k";

// ⌘K 팔레트에 표시된 단축키(G I/P/A/N/S, C) 의 전역 keydown 핸들러 — PR #189 후속 C.
// (1) 한국어 입력 소스에서는 e.key 가 'ㅎ'/'ㅏ' 로 들어오므로 물리 키 e.code 로 매칭해야 한다.
// (2) 수정키 단독 keydown(Shift 등) 은 pending 시퀀스를 지우면 안 된다.
// (3) 다이얼로그·combobox·menu 가 열려 있을 때 문자 키 단축키가 발화하면 안 된다 (WCAG 2.1.4).

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
}));

vi.mock("@/features/rag/hooks", () => ({
  useRagStream: () => ({ ask: vi.fn() }),
}));

vi.mock("@/components/onboarding/onboarding-tooltip", () => ({
  OnboardingTooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

function keyDown(target: Element | Window, init: KeyboardEventInit) {
  fireEvent.keyDown(target, init);
}

beforeEach(() => {
  vi.useFakeTimers();
  useUIStore.setState({ cmdKOpen: false });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe("CmdK 전역 단축키", () => {
  it("g → a 시퀀스로 /actions 로 이동한다", () => {
    render(<CmdK />);

    keyDown(window, { key: "g", code: "KeyG" });
    keyDown(window, { key: "a", code: "KeyA" });

    expect(push).toHaveBeenCalledWith("/actions");
  });

  it("한국어 입력 소스(ㅎ/ㅏ)에서도 물리 키(e.code)로 동작한다", () => {
    render(<CmdK />);

    keyDown(window, { key: "ㅎ", code: "KeyG" });
    keyDown(window, { key: "ㅏ", code: "KeyA" });

    expect(push).toHaveBeenCalledWith("/actions");
  });

  it("물리 위치가 다른 배열(AZERTY: A 키 = KeyQ)에서는 팔레트에 적힌 문자(e.key)로 맞는다", () => {
    render(<CmdK />);

    keyDown(window, { key: "g", code: "KeyG" });
    keyDown(window, { key: "a", code: "KeyQ" });

    expect(push).toHaveBeenCalledWith("/actions");
  });

  it("Dead 키·AltGraph 같은 비문자 keydown 도 시퀀스를 지우지 않는다", () => {
    render(<CmdK />);

    keyDown(window, { key: "g", code: "KeyG" });
    keyDown(window, { key: "AltGraph", code: "AltRight" });
    keyDown(window, { key: "Dead", code: "Quote" });
    keyDown(window, { key: "n", code: "KeyN" });

    expect(push).toHaveBeenCalledWith("/notes");
  });

  it("비모달 안내 Popover(data-slot=popover-content, role=dialog) 는 단축키를 막지 않는다", () => {
    render(
      <>
        <CmdK />
        <div role="dialog" data-slot="popover-content" aria-label="온보딩 툴팁" />
      </>,
    );

    keyDown(window, { key: "c", code: "KeyC" });

    expect(push).toHaveBeenCalledWith("/new");
  });

  it("g 뒤 1초가 지나면 시퀀스가 무효다", () => {
    render(<CmdK />);

    keyDown(window, { key: "g", code: "KeyG" });
    vi.advanceTimersByTime(1001);
    keyDown(window, { key: "a", code: "KeyA" });

    expect(push).not.toHaveBeenCalled();
  });

  it("g 와 두 번째 키 사이의 Shift 단독 keydown 은 시퀀스를 지우지 않는다", () => {
    render(<CmdK />);

    keyDown(window, { key: "g", code: "KeyG" });
    keyDown(window, { key: "Shift", code: "ShiftLeft", shiftKey: true });
    keyDown(window, { key: "p", code: "KeyP" });

    expect(push).toHaveBeenCalledWith("/projects");
  });

  it("c 단독으로 /new 로 이동한다", () => {
    render(<CmdK />);

    keyDown(window, { key: "c", code: "KeyC" });

    expect(push).toHaveBeenCalledWith("/new");
  });

  it("입력 필드 안에서는 무시한다", () => {
    render(
      <>
        <CmdK />
        <input aria-label="검색" />
      </>,
    );

    keyDown(document.querySelector("input")!, { key: "c", code: "KeyC" });

    expect(push).not.toHaveBeenCalled();
  });

  it("팔레트가 열려 있으면 무시한다", () => {
    useUIStore.setState({ cmdKOpen: true });
    render(<CmdK />);

    keyDown(window, { key: "c", code: "KeyC" });

    expect(push).not.toHaveBeenCalled();
  });

  it("다이얼로그가 열려 있으면 문자 키 단축키를 무시한다", () => {
    render(
      <>
        <CmdK />
        <div role="dialog" aria-label="새 프로젝트" />
      </>,
    );

    keyDown(window, { key: "c", code: "KeyC" });
    keyDown(window, { key: "g", code: "KeyG" });
    keyDown(window, { key: "a", code: "KeyA" });

    expect(push).not.toHaveBeenCalled();
  });

  it("닫힘 애니메이션 중인 팝업(data-closed) 은 단축키를 막지 않는다", () => {
    render(
      <>
        <CmdK />
        <div role="dialog" data-closed="" aria-label="닫히는 중" />
        <div role="menu" hidden />
      </>,
    );

    keyDown(window, { key: "g", code: "KeyG" });
    keyDown(window, { key: "a", code: "KeyA" });

    expect(push).toHaveBeenCalledWith("/actions");
  });

  it("combobox(Select 트리거) 에 포커스가 있으면 무시한다", () => {
    render(
      <>
        <CmdK />
        <button
          type="button"
          role="combobox"
          aria-label="상태 선택"
          aria-expanded={false}
          aria-controls="status-listbox"
        >
          진행 중
        </button>
      </>,
    );

    keyDown(document.querySelector('[role="combobox"]')!, { key: "c", code: "KeyC" });

    expect(push).not.toHaveBeenCalled();
  });
});
