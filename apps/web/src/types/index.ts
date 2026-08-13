export type UUID = string;

export interface Timestamped {
  createdAt: string;
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
