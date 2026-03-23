# 데이터 모델 관계도 (ERD)

## 핵심 엔티티 관계

```mermaid
erDiagram
    User {
        uuid id PK
        string clerkId UK
        string displayName
        string email
        string avatarUrl
    }

    Workspace {
        uuid id PK
        string name
        uuid ownerId FK
        timestamp createdAt
        timestamp updatedAt
    }

    WorkspaceMember {
        uuid id PK
        uuid workspaceId FK
        uuid userId FK
        enum role "owner | admin | member | viewer"
    }

    InboxItem {
        uuid id PK
        uuid workspaceId FK
        string title
        string summary
        enum sourceType "meeting | note | attachment"
        uuid sourceId
        enum aiSuggestedParaType "project | area | resource | archive"
        uuid aiSuggestedParaId
        string aiSuggestedParaTitle
        float aiConfidence
        boolean isProcessed
        timestamp createdAt
        timestamp updatedAt
    }

    ParaItem {
        uuid id PK
        uuid workspaceId FK
        enum category "project | area | resource | archive"
        string title
        string description
        enum status "active | completed | archived"
        int paraOrder
        uuid createdById FK
        timestamp createdAt
        timestamp updatedAt
    }

    Meeting {
        uuid id PK
        uuid workspaceId FK
        string title
        timestamp recordedAt
        int durationSec
        enum status "uploading | transcribing | summarizing | completed | failed"
        boolean hasTranscript
        boolean hasSummary
        int actionItemCount
        uuid createdById FK
        timestamp createdAt
        timestamp updatedAt
    }

    MeetingParaLink {
        uuid id PK
        uuid meetingId FK
        uuid paraItemId FK
    }

    TranscriptSegment {
        uuid id PK
        uuid meetingId FK
        string speaker
        float startSec
        float endSec
        string text
    }

    MeetingSummary {
        uuid id PK
        uuid meetingId FK
        string summary
        json keyDecisions
        json topics
    }

    ActionItem {
        uuid id PK
        uuid meetingId FK
        uuid paraItemId FK
        string title
        string description
        uuid assigneeId FK
        date dueDate
        enum priority "high | medium | low"
        enum status "todo | in_progress | done | cancelled"
        timestamp createdAt
        timestamp updatedAt
    }

    Note {
        uuid id PK
        uuid paraItemId FK
        string title
        json content "Tiptap JSON"
        uuid createdById FK
        timestamp createdAt
        timestamp updatedAt
    }

    Embedding {
        uuid id PK
        uuid sourceId
        enum sourceType "meeting | note | action"
        vector embedding "1536차원"
        string chunkText
        int chunkIndex
        timestamp createdAt
    }

    User ||--o{ Workspace : "소유"
    Workspace ||--o{ WorkspaceMember : "멤버"
    User ||--o{ WorkspaceMember : "소속"
    Workspace ||--o{ InboxItem : "포함"
    Workspace ||--o{ ParaItem : "포함"
    Workspace ||--o{ Meeting : "포함"
    ParaItem ||--o{ ActionItem : "포함"
    ParaItem ||--o{ Note : "포함"
    Meeting ||--o{ TranscriptSegment : "포함"
    Meeting ||--o| MeetingSummary : "1:1 요약"
    Meeting ||--o{ ActionItem : "추출"
    Meeting ||--o{ MeetingParaLink : "N:M 연결"
    ParaItem ||--o{ MeetingParaLink : "N:M 연결"
    User ||--o{ ParaItem : "생성"
    User ||--o{ Meeting : "생성"
    User ||--o{ ActionItem : "담당"
```

## 관계 설명

### N:M 관계
- **Meeting ↔ ParaItem**: `MeetingParaLink` 중간 테이블로 다대다 연결. 하나의 회의가 여러 PARA 아이템에 연결 가능.

### 1:N 관계
- **Workspace → ParaItem, Meeting, InboxItem**: 모든 콘텐츠는 워크스페이스 소속
- **ParaItem → ActionItem, Note**: PARA 아이템 하위에 액션/노트 종속
- **Meeting → TranscriptSegment, ActionItem**: 회의에서 트랜스크립트와 액션 아이템 추출

### 1:1 관계
- **Meeting → MeetingSummary**: 회의당 AI 요약 하나

### 임베딩 (폴리모픽)
- **Embedding**: `sourceType`과 `sourceId`로 Meeting, Note, ActionItem 등 다양한 소스와 연결
- pgvector 1536차원 (text-embedding-3-small 기준)
