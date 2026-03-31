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

    EmbeddingChunk {
        uuid id PK
        uuid workspaceId FK
        uuid paraItemId FK "PARA 범위 검색용"
        uuid sourceId
        enum sourceType "meeting | note | action"
        vector embedding "1536차원"
        string chunkText
        int chunkIndex
        int chunkLevel "0:document 1:section 2:paragraph"
        uuid parentChunkId FK "계층적 청킹 부모 참조"
        jsonb metadata "speaker, date, topic 등"
        timestamp createdAt
    }

    SemanticCache {
        uuid id PK
        uuid workspaceId FK
        uuid paraItemId FK "범위별 캐시"
        string question
        vector questionEmbedding "1536차원"
        string answer
        jsonb sources "출처 목록"
        int hitCount
        timestamp createdAt
        timestamp expiresAt "TTL 7일"
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
    Workspace ||--o{ EmbeddingChunk : "포함"
    Workspace ||--o{ SemanticCache : "포함"
    ParaItem ||--o{ EmbeddingChunk : "범위 검색"
    ParaItem ||--o{ SemanticCache : "범위별 캐시"
    EmbeddingChunk ||--o{ EmbeddingChunk : "부모-자식 계층"
```

## 관계 설명

### N:M 관계
- **Meeting ↔ ParaItem**: `MeetingParaLink` 중간 테이블로 다대다 연결. 하나의 회의가 여러 PARA 아이템에 연결 가능.

### 1:N 관계
- **Workspace → ParaItem, Meeting, InboxItem**: 모든 콘텐츠는 워크스페이스 소속
- **ParaItem → ActionItem, Note**: PARA 아이템 하위에 액션/노트 종속
- **Meeting → TranscriptSegment, ActionItem**: 회의에서 트랜스크립트와 액션 아이템 추출
- **Workspace → EmbeddingChunk, SemanticCache**: 멀티테넌시 격리
- **ParaItem → EmbeddingChunk**: PARA 범위 검색 (프로젝트/영역 단위 RAG)
- **ParaItem → SemanticCache**: PARA 범위별 캐시 격리

### 1:1 관계
- **Meeting → MeetingSummary**: 회의당 AI 요약 하나

### 자기 참조 (Self-referencing)
- **EmbeddingChunk → EmbeddingChunk**: `parentChunkId`로 계층적 청킹 구현. Level 2(문단)가 Level 1(화자 구간)을 부모로 참조.

### 임베딩 (폴리모픽)
- **EmbeddingChunk**: `sourceType`과 `sourceId`로 Meeting, Note, ActionItem 등 다양한 소스와 연결
- 1536차원 벡터 (text-embedding-3-small 기준)
- `chunkLevel`: 0(document) / 1(section) / 2(paragraph) — 검색 대상은 Level 2만
- `metadata` (JSONB): 화자명, 시간, 토픽 등 동적 메타데이터

### Semantic Cache
- **SemanticCache**: 의미적으로 유사한 질문에 대해 캐시된 답변을 즉시 반환
- `questionEmbedding`: 질문 벡터로 유사도 ≥ 0.93 시 캐시 히트
- `expiresAt`: TTL 7일 자동 만료
- 데이터 변경 시 해당 `paraItemId`의 캐시 무효화
- 상세 설계: [RAG 파이프라인 설계](rag-pipeline.md) 참조
