# Kairos — AI 기반 미팅 & 지식 관리 플랫폼

> _그리스어 καιρός — 흘러가는 시간(Chronos) 속 결정적 순간._
> _모든 회의엔 포착해야 할 카이로스가 있다._

AI 행동 규칙:

- 공통 규칙: `.claude/rules/global.md`
- 백엔드 규칙: `.claude/rules/backend.md`
- 프론트엔드 규칙: `.claude/rules/frontend.md`

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

## 기술 스택 (확정)

| 레이어   | 기술                                                            |
| -------- | --------------------------------------------------------------- |
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui |
| Backend  | FastAPI + SQLModel + asyncpg                                    |
| Database | PostgreSQL on Neon + pgvector                                   |
| Auth     | Clerk (Google OAuth)                                            |
| Storage  | Cloudflare R2 (boto3 S3 호환)                                   |
| STT      | OpenAI Whisper API + pyannote-audio                             |
| AI       | Anthropic Claude API (claude-sonnet-4-20250514)                 |
| 에디터   | Tiptap                                                          |
| 배포     | Vercel (FE) + GCP Cloud Run (BE)                                |

## 모노레포 구조

- `frontend/` — Next.js 14 App Router + FSD 구조
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
