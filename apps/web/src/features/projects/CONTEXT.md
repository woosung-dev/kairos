# apps/web/src/features/projects — CONTEXT

ProjectDashboard가 정식 라우트 컴포넌트 (Sprint 7 BE-T14, AD-46).
온보딩 게이트는 회의·노트 콘텐츠가 없고 로딩이 아닐 때만 OnboardingView를 렌더한다.
ProjectMembersPanel은 DashboardContent의 **형제**로 온보딩 게이트 밖에서 항상 렌더한다 (비공개가 아니면 패널이 null 을 반환한다 — 이전엔 children 이라 콘텐츠 0 인 비공개 프로젝트에서 owner 가 멤버를 추가할 수 없었다, PR #189). ProjectAdminDialogs의 관리 다이얼로그도 게이트 밖에서 항상 렌더한다.
ProjectDetail 컴포넌트는 BE-T14 구현 후 폐기 완료.
