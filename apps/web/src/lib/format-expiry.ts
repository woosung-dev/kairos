// 초대 링크 / 토큰의 만료 시각을 한국어 상대 표시 문자열로 변환
export function formatExpiry(expiresAt: string | null): string {
  if (!expiresAt) return "만료 없음";
  const date = new Date(expiresAt);
  const now = new Date();
  const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return "만료됨";
  if (diffDays === 1) return "1일 남음";
  return `${diffDays}일 남음`;
}
