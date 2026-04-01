# 데이터 흐름 예시 — 실제 회의록 기반

> DB 스키마, AI 파이프라인, UI 구현 시 **이 데이터가 시스템을 어떻게 흘러가는지**를 기준으로 삼는다.

---

## 원본 회의록 (Raw 데이터)

```
### 액션 아이템
- [x]  당근님: 가정행복국 담당자와 킥오프 미팅 조율 및 협업 환경 파악
       (서버 접근 권한, GitHub 등)
- [x]  튜닝님: CMS 고도화 개발 담당, 차세대 교회관리 시스템 전반 총괄
- [x]  사부님: 식구 중복 계정 통합 시스템 개발 (AI 기반 자동화)
- [ ]  당근님과 디자이너: 가정연합 홈페이지 고도화 개발 (금요일 미팅 참석)
- [ ]  보안성 검토 및 AWS 전환 제안 준비
- [ ]  청심 IT와 DB 현황 파악 및 협업 체계 구축

### 프로젝트 개요
협회와 포너즈가 진행하는 주요 개발 프로젝트 3개를 논의했습니다.
협회의 20년간 누적된 IT 문제를 해결하고 변혁을 이끌어내는 것이 목표입니다.

### 진행 예정 프로젝트
1. 가정회비 CMS 고도화 (가정행복국)
   - 현황: 하나로 공과금 시스템과 CMS 자동이체 프로그램이 분리되어 수기 입력 필요
   - 개발 내용: CMS 기능 개발 및 하나로 시스템과 DB 연동
   - 담당: 튜닝님

2. 식구 중복 문제 해결 (가정행복국)
   - 현황: 동일인이 여러 교회에 중복 등록되어 관리 어려움
   - 개발 내용: AI 기반 자동 중복 제거 솔루션
   - 담당: 사부님

3. 가정연합 홈페이지 고도화
   - 금요일(3/20) 오전 미팅 예정
   - 담당: 당근님 + 디자이너

### 보안 및 인프라 이슈
- 최근 데이터 유출 사고 발생
- 개선 방안: AWS 전환 추천, 보안 검토 및 취약성 개선 포함
```

---

## 시스템 흐름 (5단계)

### [1] STT / 텍스트 입력

사용자가 음성 파일 업로드 또는 텍스트 직접 입력.

| 동작 | 테이블 | 상태 |
|------|--------|------|
| R2 업로드 | — | `audio_url` 생성 |
| Whisper STT + 화자 분리 | `meetings` | `status: transcribing` |
| 트랜스크립트 저장 | `transcript_segments` | speaker, start_sec, end_sec, text |
| 완료 | `meetings` | `status: summarizing` |

---

### [2] AI 처리 (Gemini API)

트랜스크립트를 Gemini에 순차 전달. (`ai-pipeline.md` 참조)

**요약 결과:**
```json
{
  "summary": "협회 IT 문제 해결을 위한 3개 개발 프로젝트 킥오프 회의",
  "key_decisions": ["CMS 고도화 착수", "AI 기반 중복 제거 개발"],
  "topics": ["CMS", "중복 계정", "홈페이지 고도화", "보안"],
  "participants": ["당근님", "튜닝님", "사부님"]
}
```

**액션 아이템 추출 결과:**
```json
{
  "action_items": [
    {
      "title": "가정행복국 담당자와 킥오프 미팅 조율",
      "assignee": "당근님",
      "deadline": null,
      "priority": "high",
      "status": "todo",
      "context": "협업 환경 파악 (서버 접근 권한, GitHub 등)"
    },
    {
      "title": "보안성 검토 및 AWS 전환 제안 준비",
      "assignee": null,
      "deadline": null,
      "priority": "medium",
      "status": "todo",
      "context": "최근 데이터 유출 사고 대응"
    }
  ]
}
```

**프로젝트 연결 + 태그 추천 결과:**
```json
{
  "suggested_project": "가정회비 CMS 고도화",
  "suggested_tags": ["보안", "CMS", "인프라"],
  "confidence": 0.92,
  "reason": "기존 CMS 고도화 프로젝트와 관련된 회의"
}
```

| 동작 | 테이블 |
|------|--------|
| 요약 저장 | `meeting_summaries` |
| 액션 아이템 저장 | `action_items` |
| 회의 상태 변경 | `meetings.status = completed` |

---

### [3] Inbox 적재

AI 처리 완료 후, 회의가 Inbox에 자동 적재된다.

```sql
INSERT INTO inbox_items (
    workspace_id, source_type, source_id,
    ai_suggested_project_id, ai_suggested_tags,
    ai_confidence, is_processed
) VALUES (
    '...', 'meeting', '{meeting_id}',
    '{project_id or null}', '["보안", "CMS"]',
    0.92, false
);
```

| 상태 | 의미 |
|------|------|
| `is_processed = false` | 사용자 확인 대기 중 |
| `ai_suggested_project_id` | AI가 연결할 프로젝트 추천 |
| `ai_confidence = 0.92` | 높은 확신도 → ≥0.8이면 자동 확정 |

---

### [4] 사용자 분류 확정

사용자가 Inbox에서 AI 추천을 확인하고 프로젝트 연결을 확정한다 (또는 AI 자동 확정).

이 회의는 **여러 프로젝트에 동시 연결** (N:M):

```sql
-- "CMS 고도화" 프로젝트에 연결
INSERT INTO meeting_project_links (meeting_id, project_id)
VALUES ('{meeting_id}', '{cms_project_id}');

-- "보안 인프라 개선" 프로젝트에도 연결
INSERT INTO meeting_project_links (meeting_id, project_id)
VALUES ('{meeting_id}', '{security_project_id}');

-- Inbox 처리 완료
UPDATE inbox_items SET is_processed = true WHERE source_id = '{meeting_id}';
```

---

### [5] 임베딩 저장

분류 확정 후 (또는 비동기로), 콘텐츠를 벡터 임베딩으로 저장하여 RAG 소스로 활용.

```
트랜스크립트 전문
  → 계층적 청킹 (화자 구간 → 문단, 부모 참조)
  → OpenAI text-embedding-3-small (1536차원)
  → embedding_chunks 테이블 저장
```

```sql
INSERT INTO embedding_chunks (
    workspace_id, project_id,
    source_type, source_id,
    chunk_text, embedding,
    chunk_level, parent_chunk_id, metadata
) VALUES (
    '...', '{cms_project_id}',
    'meeting', '{meeting_id}',
    '가정회비 CMS 고도화... (~300-500자)',
    '[0.012, -0.034, ...]',  -- vector(1536)
    2,                        -- Level 2: paragraph (검색 단위)
    '{parent_chunk_id}',      -- Level 1: 화자 구간 참조
    '{"speaker": "튜닝님", "start_sec": 120}'
);
```

이후 RAG 검색 시 하이브리드 검색 (Full-text + Vector + RRF) → Re-ranking → Gemini 답변 생성.

> 상세 설계: [RAG 파이프라인 설계](rag-pipeline.md) 참조
