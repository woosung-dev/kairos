// 공통 타입 정의 — 백엔드 API 응답과 100% 호환

export type UUID = string;

export interface Timestamped {
  createdAt: string; // ISO 8601
  updatedAt: string;
}

export interface UserBrief {
  id: UUID;
  displayName: string;
  avatarUrl: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string | null;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
