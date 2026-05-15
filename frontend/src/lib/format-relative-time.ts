// 회의/노트/액션 timestamp 를 한국어 상대 시간 문자열로 변환
const MS_PER_MIN = 60 * 1000;
const MS_PER_HOUR = 60 * MS_PER_MIN;
const MS_PER_DAY = 24 * MS_PER_HOUR;

export function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < MS_PER_MIN) return "방금 전";
  if (diff < MS_PER_HOUR) return `${Math.floor(diff / MS_PER_MIN)}분 전`;
  if (diff < MS_PER_DAY) return `${Math.floor(diff / MS_PER_HOUR)}시간 전`;
  if (diff < 2 * MS_PER_DAY) return "어제";
  if (diff < 7 * MS_PER_DAY) return `${Math.floor(diff / MS_PER_DAY)}일 전`;
  return new Date(iso).toLocaleDateString("ko-KR", {
    month: "short",
    day: "numeric",
  });
}
