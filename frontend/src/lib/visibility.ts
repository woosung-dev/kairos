// Project visibility 공유 어휘 — 타입 + 라벨/설명/색상 (projects + workspaces invite 공용)

export type ProjectVisibility = "public" | "draft" | "private";

export const VISIBILITY_LABELS: Record<ProjectVisibility, string> = {
  public: "공개",
  draft: "작업 중",
  private: "비공개",
};

export const VISIBILITY_DESCRIPTIONS: Record<ProjectVisibility, string> = {
  public: "워크스페이스 모든 멤버 접근",
  draft: "작성자 + admin/owner만 접근",
  private: "명시적 멤버 + admin/owner만 접근",
};

export const VISIBILITY_COLOR_VAR: Record<ProjectVisibility, string> = {
  public: "var(--visibility-public)",
  draft: "var(--visibility-draft)",
  private: "var(--visibility-private)",
};
