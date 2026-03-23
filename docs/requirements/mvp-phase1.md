# MVP Phase 1 기능 명세

## 개요

회의를 단순히 기록하는 것을 넘어, 조직의 **성장형 지식 자산**으로 전환하는 플랫폼.
프론트엔드를 mock data로 먼저 완성한 뒤 백엔드를 연결하는 방식으로 진행한다.

---

## Feature 1: 멀티 소스 회의 인제스트

- 파일 업로드 (MP3/MP4/WebM 드래그앤드롭) → R2 → Whisper STT
- 인앱 녹음 (MediaRecorder API) → 업로드
- STT 결과: 화자 분리 타임스탬프 트랜스크립트

## Feature 2: AI 회의 처리 파이프라인

- 트랜스크립트 → Claude API → 구조화 출력 → Inbox 자동 적재
- AI 추출: 회의 요약 (3~5줄), 액션 아이템, 핵심 결정사항, PARA 분류 추천

## Feature 3: PARA + Inbox 지식 관리 시스템 (핵심)

### Inbox
- 모든 생성 콘텐츠의 1차 진입점
- AI가 PARA 분류 추천, 사용자가 확정

### PARA 4계층
| 카테고리     | 기준                         |
| ------------ | ---------------------------- |
| **Projects** | 마감일 O, 구체적 결과물 O    |
| **Areas**    | 마감일 X, 지속적 기준 유지   |
| **Resources**| 당장 실행 불필요, 참고용     |
| **Archives** | 비활성화, 검색 가능 보존     |

### N:M 관계형 연결
- 하나의 회의록이 여러 PARA 아이템에 동시에 연결 가능
- 태그/관계형 DB 기반 (폴더 계층 X)

## Feature 4: 확장 가능한 컨텍스트

- 텍스트 메모 (Tiptap), 이미지, 음성 클립, 참고 링크
- 모든 콘텐츠 → pgvector 자동 임베딩 → RAG 소스

## Feature 5: 액션 아이템 관리

- Kanban 보드 (To Do / In Progress / Done)
- 담당자, 기한, 우선순위 (High / Medium / Low)
- 회의록 ↔ 액션 아이템 양방향 연결

## Feature 6: RAG 기반 지식 검색

- 프로젝트/영역 범위 자연어 질문 → pgvector → Claude 답변
- Archive 과거 데이터 포함 검색
- UI: 우측 슬라이드 채팅 패널

## Feature 7: RBAC 권한 관리

| 역할   | 권한                              |
| ------ | --------------------------------- |
| Owner  | 전체 관리, 멤버 초대/삭제         |
| Admin  | 콘텐츠 CRUD, 멤버 초대            |
| Member | 본인 생성 콘텐츠 CRUD             |
| Viewer | 읽기 전용                          |

---

## UI 스펙

**3-Panel 레이아웃:**
- 좌측: PARA 사이드바 (Inbox / Projects / Areas / Resources / Archives)
- 중앙: 메인 콘텐츠
- 우측: RAG 채팅 패널 (토글)

**디자인:** Linear.app 스타일, 다크모드 우선

---

## 구현 순서 (Step 1~6)

1. Next.js 14 초기화
2. 3-Panel 대시보드 레이아웃
3. Inbox 뷰 + PARA 분류 워크플로우
4. PARA 아이템 CRUD + N:M 연결
5. 회의 업로드 페이지
6. 회의 상세 페이지 (mock data)
