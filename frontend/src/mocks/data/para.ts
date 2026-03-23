import type { ParaItem } from "@/types/para";

const now = new Date().toISOString();

const defaultUser = {
  id: "user-001",
  displayName: "당근",
  avatarUrl: null,
};

export const mockParaItems: ParaItem[] = [
  // Projects
  {
    id: "para-proj-001",
    workspaceId: "ws-default-001",
    category: "project",
    title: "가정회비 CMS 고도화",
    description:
      "하나로 공과금 시스템과 CMS 자동이체 프로그램 연동 개발. 수기 입력 제거가 목표.",
    status: "active",
    paraOrder: 0,
    createdBy: { id: "user-002", displayName: "튜닝", avatarUrl: null },
    contentCount: 5,
    meetingCount: 3,
    actionItemCount: 4,
    createdAt: "2026-03-10T09:00:00Z",
    updatedAt: now,
  },
  {
    id: "para-proj-002",
    workspaceId: "ws-default-001",
    category: "project",
    title: "식구 중복 계정 통합",
    description:
      "동일인 여러 교회 중복 등록 문제 해결. AI 기반 자동 중복 제거 솔루션.",
    status: "active",
    paraOrder: 1,
    createdBy: { id: "user-003", displayName: "사부", avatarUrl: null },
    contentCount: 3,
    meetingCount: 2,
    actionItemCount: 2,
    createdAt: "2026-03-12T09:00:00Z",
    updatedAt: now,
  },
  {
    id: "para-proj-003",
    workspaceId: "ws-default-001",
    category: "project",
    title: "가정연합 홈페이지 리뉴얼",
    description: "가정연합 공식 홈페이지 디자인 및 기능 고도화.",
    status: "active",
    paraOrder: 2,
    createdBy: defaultUser,
    contentCount: 2,
    meetingCount: 1,
    actionItemCount: 3,
    createdAt: "2026-03-15T09:00:00Z",
    updatedAt: now,
  },

  // Areas
  {
    id: "para-area-001",
    workspaceId: "ws-default-001",
    category: "area",
    title: "보안 관리",
    description:
      "조직 전체 IT 보안 정책 수립 및 관리. 데이터 유출 방지, 접근 권한 관리.",
    status: "active",
    paraOrder: 0,
    createdBy: defaultUser,
    contentCount: 4,
    meetingCount: 2,
    actionItemCount: 5,
    createdAt: "2026-02-01T09:00:00Z",
    updatedAt: now,
  },
  {
    id: "para-area-002",
    workspaceId: "ws-default-001",
    category: "area",
    title: "팀 온보딩",
    description:
      "새로운 팀원 온보딩 프로세스 관리. 문서화, 교육 세션, 계정 생성.",
    status: "active",
    paraOrder: 1,
    createdBy: defaultUser,
    contentCount: 2,
    meetingCount: 1,
    actionItemCount: 1,
    createdAt: "2026-02-15T09:00:00Z",
    updatedAt: now,
  },

  // Resources
  {
    id: "para-res-001",
    workspaceId: "ws-default-001",
    category: "resource",
    title: "AWS 전환 참고자료",
    description:
      "온프레미스에서 AWS 클라우드 전환 시 참고할 아키텍처, 비용 분석, 마이그레이션 가이드.",
    status: "active",
    paraOrder: 0,
    createdBy: defaultUser,
    contentCount: 6,
    meetingCount: 0,
    actionItemCount: 0,
    createdAt: "2026-03-01T09:00:00Z",
    updatedAt: now,
  },
  {
    id: "para-res-002",
    workspaceId: "ws-default-001",
    category: "resource",
    title: "기술 아티클 모음",
    description: "팀에서 공유된 기술 블로그, 컨퍼런스 발표 자료 등.",
    status: "active",
    paraOrder: 1,
    createdBy: { id: "user-002", displayName: "튜닝", avatarUrl: null },
    contentCount: 12,
    meetingCount: 0,
    actionItemCount: 0,
    createdAt: "2026-01-20T09:00:00Z",
    updatedAt: now,
  },

  // Archives
  {
    id: "para-arch-001",
    workspaceId: "ws-default-001",
    category: "archive",
    title: "2025년 시스템 점검",
    description: "2025년 연말 IT 시스템 전체 점검 프로젝트. 완료.",
    status: "archived",
    paraOrder: 0,
    createdBy: defaultUser,
    contentCount: 8,
    meetingCount: 4,
    actionItemCount: 0,
    createdAt: "2025-11-01T09:00:00Z",
    updatedAt: "2025-12-31T09:00:00Z",
  },
];
