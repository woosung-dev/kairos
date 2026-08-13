# apps/web/src/features/projects — CONTEXT

ProjectDashboard가 정식 라우트 컴포넌트 (Sprint 7 BE-T14, AD-46).
온보딩 게이트는 회의·노트 콘텐츠가 없고 로딩이 아닐 때만 OnboardingView를 렌더한다.
ProjectMembersPanel은 DashboardContent의 children으로 게이트를 따르고, ProjectAdminDialogs의 관리 다이얼로그는 게이트 밖에서 항상 렌더한다.
ProjectDetail 컴포넌트는 BE-T14 구현 후 폐기 완료.
