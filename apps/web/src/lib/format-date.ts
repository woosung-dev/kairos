// 날짜 표시 헬퍼 — 앱 전역 단일 포맷.
//
// 이전엔 화면마다 `toLocaleDateString("ko-KR")`("2026. 9. 5."), ISO 원문("2026-09-09"),
// `slice(0, 10)`("2026-09-05") 이 섞여 같은 화면 안에서도 날짜 표기가 셋이었다.
// DESIGN.md 의 Data 규칙(Geist Mono, tabular-nums)에 맞춰 자릿수가 고정되는 "YYYY.MM.DD" 로 통일한다.
//
// ★날짜만 있는 문자열("YYYY-MM-DD", ActionItem.dueDate)은 `new Date()` 에 넣지 않는다 —
//   UTC 자정으로 해석돼 KST 이외 시간대에서 하루가 밀린다. 문자열을 직접 분해한다.

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** "2026.09.05" — 날짜만. 파싱 불가 입력은 빈 문자열. */
export function formatDate(input: string | Date | null | undefined): string {
  if (!input) return "";
  if (typeof input === "string") {
    const m = DATE_ONLY.exec(input);
    if (m) return `${m[1]}.${m[2]}.${m[3]}`;
  }
  const d = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`;
}

/** "2026.09.05 14:03" — 날짜 + 시:분 (audit 로그 등 시각이 의미 있는 곳). */
export function formatDateTime(input: string | Date | null | undefined): string {
  if (!input) return "";
  const d = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(d.getTime())) return "";
  return `${formatDate(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** 마감일이 오늘보다 이전인지. 날짜만 비교(시각 무시). */
export function isOverdue(
  dateStr: string | null | undefined,
  today: Date = new Date(),
): boolean {
  if (!dateStr) return false;
  const m = DATE_ONLY.exec(dateStr);
  const due = m
    ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
    : new Date(dateStr);
  if (Number.isNaN(due.getTime())) return false;
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  return due < start;
}
