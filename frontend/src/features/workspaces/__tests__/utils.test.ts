// BL-035 buildDisambiguationMap + inferWorkspaceType 단위 테스트
import { describe, expect, it } from "vitest";
import {
  buildDisambiguationMap,
  inferWorkspaceType,
} from "../utils";

type Ws = Parameters<typeof buildDisambiguationMap>[0][number];

const ws = (
  id: string,
  name: string,
  createdAt: string,
  type: "personal" | "team" | undefined = "team",
): Ws => ({ id, name, type: type ?? "team", createdAt });

describe("inferWorkspaceType", () => {
  it("BE 응답 type 우선 사용", () => {
    expect(inferWorkspaceType({ name: "X", type: "personal" })).toBe("personal");
    expect(inferWorkspaceType({ name: "X", type: "team" })).toBe("team");
  });

  it("type 누락 시 personal seed suffix 휴리스틱", () => {
    expect(
      inferWorkspaceType({ name: "Alice의 개인 Kairos", type: undefined as never }),
    ).toBe("personal");
  });

  it("type 누락 + suffix 미일치 시 team fallback", () => {
    expect(
      inferWorkspaceType({ name: "Some Team", type: undefined as never }),
    ).toBe("team");
  });
});

describe("buildDisambiguationMap (BL-035)", () => {
  it("단일 이름은 접미사 미부여", () => {
    const map = buildDisambiguationMap([
      ws("a", "Solo", "2026-05-13T00:00:00"),
      ws("b", "Other", "2026-05-13T01:00:00"),
    ]);
    expect(map.size).toBe(0);
  });

  it("동일 이름 2개 이상이면 created_at 오름차순 #N", () => {
    const map = buildDisambiguationMap([
      ws("late", "Dup", "2026-05-13T05:00:00"),
      ws("early", "Dup", "2026-05-13T01:00:00"),
      ws("mid", "Dup", "2026-05-13T03:00:00"),
    ]);
    expect(map.get("early")).toBe("#1");
    expect(map.get("mid")).toBe("#2");
    expect(map.get("late")).toBe("#3");
  });

  it("type 별 그룹화 — team / personal 간 번호 충돌 없음", () => {
    const map = buildDisambiguationMap([
      ws("t1", "Same", "2026-05-13T01:00:00", "team"),
      ws("t2", "Same", "2026-05-13T02:00:00", "team"),
      ws("p1", "Same", "2026-05-13T03:00:00", "personal"),
      ws("p2", "Same", "2026-05-13T04:00:00", "personal"),
    ]);
    // 두 그룹 각각 #1, #2 — type 분리.
    expect(map.get("t1")).toBe("#1");
    expect(map.get("t2")).toBe("#2");
    expect(map.get("p1")).toBe("#1");
    expect(map.get("p2")).toBe("#2");
  });

  it("일부 그룹만 중복일 때 — 다른 그룹은 접미사 미부여", () => {
    const map = buildDisambiguationMap([
      ws("solo", "Solo", "2026-05-13T01:00:00"),
      ws("d1", "Dup", "2026-05-13T02:00:00"),
      ws("d2", "Dup", "2026-05-13T03:00:00"),
    ]);
    expect(map.has("solo")).toBe(false);
    expect(map.get("d1")).toBe("#1");
    expect(map.get("d2")).toBe("#2");
  });

  it("빈 배열 — 빈 Map 반환", () => {
    expect(buildDisambiguationMap([]).size).toBe(0);
  });
});
