# 디렉토리 구조 맵

## 프론트엔드 (FSD 기반)

```
frontend/
└── src/
    ├── app/                           # 라우트 진입점 (Thin Component)
    │   ├── (auth)/                    # Clerk 인증
    │   ├── dashboard/
    │   ├── inbox/
    │   ├── weekly-review/
    │   └── workspace/[id]/
    │       ├── projects/[paraId]/
    │       │   ├── meetings/
    │       │   ├── notes/
    │       │   ├── actions/
    │       │   ├── files/
    │       │   └── ask/
    │       ├── areas/[paraId]/
    │       ├── resources/[paraId]/
    │       └── archives/
    │
    ├── components/                    # 도메인 무관 공통 UI
    │   ├── ui/                        # shadcn/ui (수정 금지)
    │   └── layout/                    # Sidebar, Header, PanelLayout
    │
    ├── features/                      # 도메인별 비즈니스 레이어
    │   ├── inbox/
    │   ├── para/
    │   ├── meetings/
    │   ├── actions/
    │   ├── editor/
    │   └── rag/
    │
    ├── hooks/                         # 공통 유틸리티 훅
    ├── lib/                           # 서드파티 설정, 유틸
    ├── mocks/                         # Mock data (개발용)
    ├── store/                         # Zustand 전역 상태
    └── types/                         # 전역 공유 타입
```

## 백엔드 (도메인 모듈러 구조)

```
backend/
└── src/
    ├── auth/                          # Clerk JWT 검증
    ├── inbox/                         # Inbox 적재 + 분류
    ├── para/                          # PARA CRUD + N:M 링크
    ├── meetings/                      # 회의 인제스트, STT, AI 파이프라인
    ├── actions/                       # 액션 아이템
    ├── notes/                         # Tiptap 노트
    ├── rag/                           # RAG 검색 + Claude 답변
    ├── common/
    │   ├── database.py                # AsyncSession 팩토리
    │   ├── exceptions.py              # 전역 예외 핸들러
    │   ├── r2.py                      # Cloudflare R2 클라이언트
    │   └── pagination.py
    └── core/
        └── config.py                  # pydantic-settings
```

각 도메인 폴더는 다음 파일로 구성:
`router.py` / `service.py` / `repository.py` / `schemas.py` / `models.py` / `dependencies.py` / `exceptions.py`
