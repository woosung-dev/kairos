import { describe, expect, it } from "vitest";
import { formatDate, formatDateTime, isOverdue } from "../format-date";

// PR #189 후속 E — 앱 전역 날짜 포맷 헬퍼 (이전 테스트 0건).
// ★date-only 문자열은 new Date() 를 거치지 않아야 한다 — UTC 자정 해석으로 KST 외 시간대에서 하루가 밀린다.
describe("formatDate", () => {
  it("date-only 문자열은 시간대와 무관하게 그대로 YYYY.MM.DD 로 바꾼다", () => {
    expect(formatDate("2026-09-05")).toBe("2026.09.05");
    expect(formatDate("2026-01-01")).toBe("2026.01.01");
  });

  it("ISO datetime 과 Date 객체는 로컬 날짜로 포맷한다", () => {
    const d = new Date(2026, 8, 5, 14, 3);
    expect(formatDate(d)).toBe("2026.09.05");
    expect(formatDate(d.toISOString())).toBe("2026.09.05");
  });

  it("파싱 불가·빈 입력은 빈 문자열", () => {
    expect(formatDate("garbage")).toBe("");
    expect(formatDate("")).toBe("");
    expect(formatDate(null)).toBe("");
    expect(formatDate(undefined)).toBe("");
  });
});

describe("formatDateTime", () => {
  it("날짜 + 시:분 (0 패딩)", () => {
    expect(formatDateTime(new Date(2026, 8, 5, 9, 7))).toBe("2026.09.05 09:07");
    expect(formatDateTime(null)).toBe("");
    expect(formatDateTime("garbage")).toBe("");
  });
});

describe("isOverdue", () => {
  const today = new Date(2026, 8, 5); // 2026-09-05 로컬

  it("당일은 지연이 아니고 전일은 지연이다 (날짜만 비교)", () => {
    expect(isOverdue("2026-09-05", today)).toBe(false);
    expect(isOverdue("2026-09-04", today)).toBe(true);
    expect(isOverdue("2026-09-06", today)).toBe(false);
  });

  it("오늘 자정 직전 시각이 들어와도 당일 판정은 흔들리지 않는다", () => {
    expect(isOverdue("2026-09-05", new Date(2026, 8, 5, 23, 59))).toBe(false);
  });

  it("없거나 파싱 불가한 마감일은 지연이 아니다", () => {
    expect(isOverdue(null, today)).toBe(false);
    expect(isOverdue(undefined, today)).toBe(false);
    expect(isOverdue("garbage", today)).toBe(false);
  });
});
