# Kairos — Product Requirements Document

> *그리스어 καιρός — 흘러가는 시간(Chronos) 속 결정적 순간.*
> *모든 회의엔 포착해야 할 카이로스가 있다.*

> **버전:** 1.1
> **최종 수정:** 2026-03-23

---

## 0. 프로젝트 철학

**Kairos(καιρός)**는 그리스어로 단순히 흘러가는 시간(Chronos)과 달리,
**결정적인 순간, 포착해야 할 기회의 시간**을 뜻한다.

모든 회의 속에는 놓치면 사라지는 카이로스가 있고,
이 플랫폼은 그것을 포착해 조직의 자산으로 만든다.

---

## 1. 문제 정의

### 현재 상황
- 회의록은 Notion 등에 **파편화**되어 쌓이지만, 이후 실행으로 이어지지 않음
- 액션 아이템은 수동으로 추출하고, 별도 Jira/Asana로 옮기는 **이중 작업** 발생
- 쌓인 데이터는 "검색하면 나오는 파일" 수준이고, **지식으로 활용되지 않음**
- 프로젝트가 끝나면 그 안의 맥락(회의록, 결정사항)이 **사장**됨

### 해결하고자 하는 것
> **"회의 녹음 하나가 들어오면, 액션이 생성되고, 지식이 쌓이고, 나중에 질문할 수 있는 자산이 된다."**

단순한 회의록 저장 도구가 아니라, **데이터가 쌓일수록 조직의 생산성과 창조력이 함께 커지는 성장형 지식 베이스.**

---

## 2. 타겟 유저

- **주요:** 사내 전체 직원 (부서 간 협업 프로젝트 진행자)
- **핵심 페르소나:**
  - 매주 3~5회 회의를 주도하는 팀 리더
  - 여러 프로젝트를 동시에 관리하는 PM
  - 과거 의사결정 맥락을 자주 다시 찾아야 하는 구성원

---

## 3. 핵심 가치 제안

| 기존 방식 | Kairos |
|-----------|--------|
| 회의 후 수동으로 회의록 작성 | 녹음 업로드 → AI 자동 요약/액션 추출 |
| 주제별 폴더 정리 | 실행도 기반 PARA 분류 (AI 추천 → 사람 확정) |
| 끝난 프로젝트 = 죽은 데이터 | Archive → RAG 소스로 재활용 |
| "어디 있더라?" 검색 | 자연어 질문 → pgvector RAG 답변 |

---

## 4. 시스템 아키텍처 요약

```
오디오/영상/텍스트 입력
  → Cloudflare R2 업로드
  → Whisper STT + pyannote 화자 분리
  → Claude API: 요약 + 액션 아이템 + PARA 분류 추천
  → Inbox 적재 (is_processed=False)
  → 사용자 PARA 분류 확정
  → pgvector 임베딩 저장
  → RAG 검색 & Q&A
```

**Tech Stack:** Next.js 16 + FastAPI + PostgreSQL(pgvector) + Cloudflare R2 + Claude API + Whisper

---

## 5. Phase 로드맵

---

### Phase 1 — 프론트엔드 스캐폴딩 (Mock Data) ✅ 진행 중

**목표:** 백엔드 없이 UI/UX를 먼저 완성해 흐름을 검증한다.

#### 완료
- [x] Next.js 16 프로젝트 초기화
- [x] 3-Panel 레이아웃 (사이드바 / 메인 / RAG 패널)
- [x] Inbox 뷰 UI (mock data)
- [x] PARA 아이템 CRUD (mock data)

#### 남은 작업
- [ ] Clerk 인증 연동 (sign-in / sign-up / proxy.ts)
- [ ] 회의 업로드 페이지 (파일 드롭존 + 인앱 녹음 UI)
- [ ] 회의 상세 페이지 (트랜스크립트 뷰어, mock data)
- [ ] 액션 아이템 칸반 보드 (To Do / In Progress / Done, mock data)
- [ ] PARA 분류 확정 워크플로우 (AI 추천 뱃지 → 클릭 확정)

---

### Phase 2 — 백엔드 + AI 파이프라인 연동

**목표:** "업로드 → 처리 → Inbox 자동 적재" 핵심 파이프라인 완성.

#### FastAPI 백엔드 스캐폴딩
- [ ] 프로젝트 구조 셋업 (uv, SQLModel, Alembic)
- [ ] DB 마이그레이션 (ERD 기반 전체 테이블 생성)
- [ ] Clerk JWT 검증 미들웨어
- [ ] 공통 유틸 (pagination, exceptions, R2 클라이언트)

#### AI 파이프라인
- [ ] Cloudflare R2 파일 업로드 API
- [ ] Whisper API + pyannote-audio 화자 분리
- [ ] Claude API 통합:
  - 회의 요약 (3~5줄)
  - 액션 아이템 추출 (담당자, 기한, 우선순위)
  - PARA 분류 추천
- [ ] Inbox 자동 적재 (is_processed=False → 사용자 확정)

#### 프론트엔드 API 연동
- [ ] Mock data → 실제 API 교체 (Inbox, PARA, 회의)
- [ ] React Query 뮤테이션 연동
- [ ] 업로드 진행률 UI (onUploadProgress)

---

### Phase 3 — 지식 검색 (RAG) + 고급 UI

**목표:** 쌓인 데이터를 "질문할 수 있는 자산"으로 전환.

#### pgvector RAG
- [ ] 텍스트 청킹 (512 토큰, 50 토큰 오버랩)
- [ ] OpenAI Embedding → pgvector 저장
- [ ] 유사도 검색 API
- [ ] Claude 스트리밍 답변 (StreamingResponse)
- [ ] RAG 채팅 패널 UI (우측 슬라이드, 프로젝트 범위 지정)

#### 노트 에디터
- [ ] Tiptap 블록 에디터 (StarterKit + Placeholder + CharacterCount)
- [ ] debounce 자동 저장 (500ms)
- [ ] 노트 → pgvector 임베딩 자동 등록

#### Archive 재활용
- [ ] Project 완료 → Archive 전환 (Resource 보존 옵션)
- [ ] Archive 데이터 RAG 소스 포함

---

### Phase 4 — 권한 관리 + 보고서 생성

**목표:** 실제 사내 배포 가능한 수준의 보안 + 부가가치 기능.

#### RBAC 권한 관리
- [ ] 역할 4단계: Owner / Admin / Member / Viewer
- [ ] 워크스페이스 / 문서 단위 권한 설정
- [ ] 초대 링크 + 이메일 초대

#### AI 문서 생성
- [ ] 주간/월간 보고서 자동 생성 (프로젝트 활동 요약)
- [ ] 슬라이드 발표 자료 초안 생성
- [ ] 인포그래픽 초안 (차트 데이터 기반)

#### 외부 연동 (검토)
- [ ] Google Meet 녹화본 자동 연동
- [ ] Zoom 클라우드 녹화 연동
- [ ] Slack 알림 (액션 아이템 마감 리마인더)

---

## 6. UI/UX 레퍼런스

| 영역 | 벤치마킹 |
|------|----------|
| 전체 레이아웃 | Linear.app (3-panel, 다크모드 우선) |
| 액션 아이템 | Jira 칸반보드 + 리스트 뷰 |
| 노트 에디터 | Notion 블록 에디터 |
| 지식 검색 | NotebookLM 스타일 RAG 채팅 |
| PARA 네비게이션 | 사이드바 계층 + 관계형 태그 |

---

## 7. 성공 지표 (MVP 기준)

- 회의 업로드 → Inbox 적재까지 **3분 이내**
- AI 액션 아이템 추출 정확도 **80% 이상** (사용자 체감)
- RAG 질문 → 답변 스트리밍 시작까지 **2초 이내**
- Phase 1~2 완료 후 내부 테스트 사용자 **5명 이상** 온보딩

---

## 8. 현재 컨텍스트

- **현재 Phase:** Phase 1 (프론트엔드 스캐폴딩) — 기본 레이아웃/Inbox/PARA 완료
- **다음 작업:** Phase 1 나머지 (Clerk 인증, 회의 업로드 UI, 칸반 보드)
- **백엔드:** 아직 미착수 (Phase 2에서 시작)

---

## 9. MVP 명시적 제외 목록

아래 기능은 MVP 범위에서 **의도적으로 제외**한다. Phase 2 이후 검토.

- NotebookLM 스타일 인포그래픽/슬라이드 자동 생성
- 실시간 라이브 트랜스크립션 (회의 중 실시간 STT)
- 크로스 프로젝트 RAG (조직 전체 검색)
- Jira / Slack / 외부 캘린더 연동
- 주간/월간 보고서 자동 생성
- 모바일 네이티브 앱 (PWA로 대체)
