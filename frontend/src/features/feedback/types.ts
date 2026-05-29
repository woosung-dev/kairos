// 피드백 제출 입력/응답 타입
export interface FeedbackInput {
  body: string;
  rating?: number | null;
  isAnonymous?: boolean;
  workspaceId?: string | null;
  pageUrl?: string | null;
}

export interface FeedbackResult {
  id: string;
  status: string;
  createdAt: string;
}
