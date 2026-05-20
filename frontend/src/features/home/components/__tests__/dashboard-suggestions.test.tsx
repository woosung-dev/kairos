// Sprint 24 Wave 2 T-CMD-K-FIX (BUG-CURIOUS-002) — 추천 질문 click → cmd-k palette open + query 자동 입력
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DashboardSuggestions } from "../dashboard-suggestions";
import { useUIStore } from "@/store/ui";

describe("DashboardSuggestions — Sprint 24 Wave 2 T-CMD-K-FIX", () => {
  beforeEach(() => {
    // store 초기화 (zustand 는 module 단위 싱글톤이라 명시 reset 필요)
    useUIStore.setState({
      cmdKOpen: false,
      cmdKInitialQuery: "",
    });
  });

  it("추천 질문 4건이 모두 렌더된다", () => {
    render(<DashboardSuggestions />);
    expect(
      screen.getByRole("button", { name: /최근 회의에서 결정된 사항/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /진행 중인 프로젝트 현황/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /이번 주 액션 아이템/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /보안 관련 논의 내용/ }),
    ).toBeInTheDocument();
  });

  it("data-testid=dashboard-suggestion-button 가 4건 노출된다 (e2e selector 회귀 가드)", () => {
    render(<DashboardSuggestions />);
    const buttons = screen.getAllByTestId("dashboard-suggestion-button");
    expect(buttons).toHaveLength(4);
  });

  it("추천 질문 클릭 시 cmdKOpen=true + cmdKInitialQuery=clicked text", () => {
    render(<DashboardSuggestions />);

    // 사전 검증: palette 닫혀있음
    expect(useUIStore.getState().cmdKOpen).toBe(false);
    expect(useUIStore.getState().cmdKInitialQuery).toBe("");

    const btn = screen.getByRole("button", { name: /최근 회의에서 결정된 사항/ });
    fireEvent.click(btn);

    const state = useUIStore.getState();
    expect(state.cmdKOpen).toBe(true);
    expect(state.cmdKInitialQuery).toBe("최근 회의에서 결정된 사항은?");
  });

  it("다른 추천 질문 클릭 시 query 가 갱신된다 (dead-click 회귀 가드)", () => {
    render(<DashboardSuggestions />);

    fireEvent.click(
      screen.getByRole("button", { name: /최근 회의에서 결정된 사항/ }),
    );
    expect(useUIStore.getState().cmdKInitialQuery).toBe(
      "최근 회의에서 결정된 사항은?",
    );

    fireEvent.click(
      screen.getByRole("button", { name: /이번 주 액션 아이템/ }),
    );
    expect(useUIStore.getState().cmdKInitialQuery).toBe(
      "이번 주 액션 아이템은?",
    );
    expect(useUIStore.getState().cmdKOpen).toBe(true);
  });
});

describe("useUIStore.openCmdKWithQuery — Sprint 24 Wave 2 T-CMD-K-FIX", () => {
  beforeEach(() => {
    useUIStore.setState({ cmdKOpen: false, cmdKInitialQuery: "" });
  });

  it("openCmdKWithQuery 호출 시 palette 열림 + query set", () => {
    useUIStore.getState().openCmdKWithQuery("foo bar");
    expect(useUIStore.getState().cmdKOpen).toBe(true);
    expect(useUIStore.getState().cmdKInitialQuery).toBe("foo bar");
  });

  it("setCmdKInitialQuery 로 1회성 consumption 후 reset 가능", () => {
    useUIStore.getState().openCmdKWithQuery("baz");
    useUIStore.getState().setCmdKInitialQuery("");
    expect(useUIStore.getState().cmdKInitialQuery).toBe("");
    // palette 는 여전히 열린 상태 유지 (cmd-k consumer 가 끄는 책임)
    expect(useUIStore.getState().cmdKOpen).toBe(true);
  });
});
