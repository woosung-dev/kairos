// 앱 전역 상수

export const APP_NAME = "Kairos";
export const APP_DESCRIPTION =
  "AI 기반 미팅 & 지식 관리 플랫폼";

// 기본 워크스페이스 ID (MVP에서는 단일 워크스페이스)
export const DEFAULT_WORKSPACE_ID = "ws-default-001";

// API 설정
export const IS_MOCK = process.env.NEXT_PUBLIC_API_MOCK === "true";
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// PARA 카테고리 메타데이터
export const PARA_CATEGORIES = [
  { category: "project" as const, label: "Projects", icon: "Target" },
  { category: "area" as const, label: "Areas", icon: "Pin" },
  { category: "resource" as const, label: "Resources", icon: "BookOpen" },
  { category: "archive" as const, label: "Archives", icon: "Archive" },
] as const;
