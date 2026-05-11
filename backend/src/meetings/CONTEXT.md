<!-- meetings 도메인 — STT + 화자 분리 + AI 요약 + 액션 추출 파이프라인 -->

# meetings CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- 회의 음성 인제스트 (R2 업로드 후 처리 트리거)
- STT + 화자 분리 (Whisper API + pyannote)
- AI 요약 / 결정사항 추출 (Gemini)
- 액션 아이템 추출 → `actions/repository`에 저장
- 프로젝트 자동 분류 추천 → `inbox/service`에 위임 (orchestrator 안)
- 회의 데이터 임베딩 트리거 → `embeddings/service`에 위임

## 2. 비책임

- 액션 CRUD 자체 (`actions` 도메인)
- 임베딩 저장/검색 (`embeddings`/`rag`)
- Inbox 자동 확정 로직 (`inbox`)

---

## 3. 엔티티 (소유)

- **Meeting** — 회의 메타 + status
  - status: `uploading` → `transcribing` → `analyzing` → `completed` / `failed`
  - `file_key` (R2 저장 경로), `error_message`, `has_transcript`, `has_summary`, `action_item_count`
- **TranscriptSegment** — 화자별 문장
  - `speaker` 기본값 `"Speaker"` (Sprint 1 화자 분리 미적용)
- **MeetingSummary** — 1:1 AI 요약 + `key_decisions` (JSON list) + `topics` (JSON list)

> **MeetingProjectLink**는 `projects` 도메인 소유. meetings는 read만.

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 | 비고 |
|---|---|---|---|
| out | `actions/repository` | Repository | 추출된 액션 저장 |
| out | `services/transcription` | external wrapper | Whisper + pyannote |
| out | `services/ai_processing` | external wrapper | Gemini 요약/분류 |
| out | `inbox/service` | via pipeline | Inbox 적재 (`MeetingPipelineService` 안) |
| out | `embeddings/service` | via pipeline | 트랜스크립트 임베딩 |
| in | (외부 호출) | — | upload 모듈에서 트리거 |

---

## 5. 핵심 흐름 — `MeetingPipelineService`

```
1. upload 완료 → POST /api/v1/workspaces/{wid}/meetings (202 Accepted)
2. BackgroundTask: pipeline.process_meeting(id)
   ├─ status=transcribing                     (commit — 진행 보고, 줄 71)
   ├─ Whisper → TranscriptSegment[]
   ├─ duration_sec 업데이트                   (commit — 줄 86)
   ├─ status=analyzing                        (commit — 진행 보고, 줄 90)
   ├─ Gemini summarize → MeetingSummary
   ├─ Gemini extract_actions → ActionItem[]   (via actions.repository, nullable project_id OK)
   ├─ Gemini classify_project → InboxItem 적재 (via inbox.service)
   ├─ Embedding 저장                          (via embeddings.service, 실패해도 비차단)
   └─ status=completed                        (commit — 최종, 줄 215)
   (실패 시 status=failed                     commit — 줄 222)
3. Client polling: GET /api/v1/workspaces/{wid}/meetings/{id}/status
```

> **현재 commit 횟수 (D-9)**: 5회 (status 전이 4회 + duration 보고 1회). 줄번호: 71/86/90/215/222. 헌법 I-2 "마지막 1회" 원칙과 불일치 — 진행 보고용 commit으로 명시 허용 vs 단일 commit 리팩토링 결정 보류.

---

## 6. 핵심 불변식

| # | 불변식 |
|---|---|
| M-1 | **status 머신 단방향 + 멱등 status 업데이트** (재시도 시 동일 상태 OK) |
| M-2 | **commit은 status 전이마다 + duration 보고 + 최종 1회** (총 5회, 줄 71/86/90/215/222. D-9 — 진행 보고용. 단일 commit 리팩토링은 ADR 후보) |
| M-3 | **외부 API 실패 시 status=`failed`** + `error_message` 저장 + 사용자 재시도 트리거 (retry 정책 자체는 Phase B) |
| M-4 | **트랜스크립트는 검색 가능 단위(L2)로 청킹 후 임베딩** |
| M-5 | **MeetingSummary는 회의당 1개 (덮어쓰기)** — 재처리 시 기존 요약 교체 |
| M-6 | **임베딩 단계는 비차단** — 임베딩 실패해도 파이프라인은 `completed`로 종료 (트랜스크립트/요약은 보존) |

---

## 7. 엔드포인트

> 모두 `/api/v1/workspaces/{workspace_id}/meetings` prefix.

```
POST   /                  인제스트 (202)
GET    /                  목록
GET    /{id}              디테일 (요약 + 트랜스크립트)
GET    /{id}/export       내보내기
GET    /{id}/status       진행상태 polling
```

---

## 8. 엣지 케이스

- 화자 식별 실패 (단일 화자 회의) → `speaker = "Speaker"` (현재 기본값)
- 무음 구간 / 짧은 회의 (< 30초) → AI 요약 스킵 옵션 (Phase B)
- 외부 API timeout → status=`failed`, `error_message` 저장, 사용자에게 재시도 버튼
- 같은 파일 재업로드 → 중복 검출 부재 (CONTEXT-MAP §7 D-8) — R2 hash 비교 미구현
