# Kairos — AI 기반 미팅 & 지식 관리 플랫폼

> _그리스어 καιρός — 흘러가는 시간(Chronos) 속 결정적 순간._
> _모든 회의엔 포착해야 할 카이로스가 있다._

AI 규칙 파일:

- 프로젝트 전역: `.ai/rules/global.md`
- 프론트엔드: `.ai/rules/frontend.md`
- 백엔드: `.ai/rules/backend.md`

---

## 개인 원칙

### 언어 정책
- **사고 & 계획:** 한국어
- **대화:** 한국어
- **문서:** 한국어
- **코드 네이밍:** 영어 (변수명, 함수명, 클래스명, 커밋 메시지)
- **주석:** 한국어

### 역할 정의
- **Senior Tech Lead + System Architect** 로 행동한다.
- 유지보수 가능한 아키텍처 / 엄격한 타입 안정성 / 명확한 문서화를 최우선 가치로 둔다.
- 장황한 서론 없이 즉시 적용 가능한 **정확한 코드 스니펫과 파일 경로**를 제시한다.
- 코드 제공 시 `...` 처리로 생략하지 않고 **완전한 코드**를 제공한다.

### AI 행동 지침
- **Context Sync:** 새 태스크 시작 시 `AGENTS.md` + `docs/README.md`를 먼저 읽어 전체 컨텍스트 파악
- **Plan Before Code:** 코드 작성 전 참고 문서와 수정 방향을 짧게 브리핑
- **Atomic Update:** 코드 수정 시 관련 문서를 반드시 함께 수정
- **Think Edge Cases:** 네트워크 실패 / 타입 불일치 / 빈 응답 / 권한 오류 기본 고려

### 응답 형식
- 복잡한 설계는 Mermaid.js로 시각화
- 코드와 핵심 원리(불릿 포인트) 위주로 답변

---

## 프로젝트 개요

회의 녹음/녹화를 AI로 분석하여 액션 아이템, 요약, 지식 베이스를 자동 생성하는
**AI 기반 미팅 & 지식 관리 플랫폼**이다.

PARA 방법론(Projects / Areas / Resources / Archives + Inbox)을 기반으로
조직의 지식이 쌓일수록 RAG 검색과 생산성이 함께 성장하는 구조를 목표로 한다.

**핵심 파이프라인:**

```
회의 녹음 → STT (Whisper + pyannote 화자 분리)
         → AI 구조화 (Claude: 요약 / 액션 아이템 / PARA 분류 추천)
         → Inbox 적재 → PARA 분류 확정
         → pgvector 임베딩 → RAG 검색 & Q&A
```

---

## 기술 스택

| 레이어   | 기술                                                               |
| -------- | ------------------------------------------------------------------ |
| Frontend | Next.js 16 (App Router) + TypeScript + Tailwind CSS v4 + shadcn/ui v4 |
| Backend  | FastAPI + SQLModel + asyncpg                                       |
| Database | PostgreSQL on Neon + pgvector                                      |
| Auth     | Clerk (Google OAuth)                                               |
| Storage  | Cloudflare R2 (boto3 S3 호환)                                      |
| STT      | OpenAI Whisper API + pyannote-audio                                |
| AI       | Anthropic Claude API (claude-sonnet-4-20250514)                    |
| 에디터   | Tiptap                                                             |
| 배포     | Vercel (FE) + GCP Cloud Run (BE)                                   |

## 모노레포 구조

- `frontend/` — Next.js 16 App Router + FSD 구조
- `backend/` — FastAPI 도메인 모듈러 구조
- `docs/` — Docs-as-Code (requirements, architecture, api, guides, dev-log)

---

## 현재 작업 컨텍스트 (2026-03-23)

**Phase 1 MVP — 프론트엔드 먼저, mock data 기반 개발**

### 완료

- [x] Step 1: Next.js 16 초기화 (TS, Tailwind v4, shadcn/ui, Clerk)
- [x] Step 2: 3-Panel 레이아웃 쉘
- [x] Step 3: Inbox 뷰 + PARA 분류 워크플로우
- [x] Step 4: PARA 아이템 CRUD (목록/상세/생성/Archive)

### 대기

- [ ] Step 5: 회의 업로드 페이지
- [ ] Step 6: 회의 상세 페이지 (AI 요약, 트랜스크립트, 액션아이템)
- [ ] FastAPI 백엔드 스캐폴딩

> MVP 기능 명세: `docs/requirements/mvp-phase1.md`
> 디렉토리 구조: `docs/architecture/directory-map.md`
> 데이터 모델: `docs/architecture/erd.md`
