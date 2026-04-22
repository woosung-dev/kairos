# backend/src/workspaces/templates.py
"""워크스페이스 생성 시 자동 시딩되는 템플릿 프로젝트 정의."""


class TemplateProject:
    __slots__ = ("title", "description", "tags", "sort_order")

    def __init__(
        self,
        title: str,
        description: str,
        tags: list[str],
        sort_order: int,
    ) -> None:
        self.title = title
        self.description = description
        self.tags = tags
        self.sort_order = sort_order


# 신규 워크스페이스가 빈 화면이 되지 않도록 기본 3개 프로젝트를 시딩한다.
# 사용자는 자유롭게 삭제/수정할 수 있으며, 템플릿 여부를 표시하는 플래그는 두지 않는다.
DEFAULT_TEMPLATE_PROJECTS: tuple[TemplateProject, ...] = (
    TemplateProject(
        title="🚀 시작하기",
        description=(
            "Kairos 온보딩 가이드 — 첫 회의 녹음을 여기에 올려보세요. "
            "AI가 자동으로 요약·액션 아이템·태그를 붙이고, "
            "RAG 검색 범위를 이 프로젝트로 지정하면 관련 답변만 모아볼 수 있습니다."
        ),
        tags=["onboarding"],
        sort_order=0,
    ),
    TemplateProject(
        title="💡 아이디어",
        description=(
            "떠오르는 생각·제품 스케치·리서치 메모를 빠르게 덤프하는 공간. "
            "형식에 얽매이지 말고 던져두면 나중에 RAG가 모아서 인사이트를 뽑아냅니다."
        ),
        tags=["idea"],
        sort_order=1,
    ),
    TemplateProject(
        title="📋 회의록",
        description=(
            "어디에 귀속될지 애매한 정기 회의·1:1·킥오프 기록의 기본 수납함. "
            "주제가 명확해지면 전용 프로젝트로 옮기세요."
        ),
        tags=["meeting"],
        sort_order=2,
    ),
)
