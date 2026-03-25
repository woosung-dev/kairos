# Kairos 전역 규칙

---

## 1. 개발 워크플로우

새로운 기능이나 주요 변경 사항은 아래 루프를 따른다:

1. **계획 (Plan)** — 작업 범위와 영향 분석, 관련 규칙·설계 문서 참조
2. **문서화 (Docs)** — 구현 계획을 `docs/` 적절한 위치에 작성
3. **리뷰 (Human Review)** — 사용자 피드백, 만족할 때까지 반복
4. **구현 (Implement)** — 확정된 문서 기반 코드 작성, 중단 없이 끝까지

---

## 2. 문서화 원칙

| 성격 | 위치 | 시점 |
|------|------|------|
| 기능 명세 (WHAT) | `docs/requirements/` | Phase 시작 시 |
| 설계 상세 (HOW) | `docs/architecture/` | Phase 시작 또는 종료 시 |
| API 명세 | `docs/api/` | 구현 전 |
| 의사결정 기록 (WHY) | `docs/dev-log/` | 결정 후 |
| 가이드 | `docs/guides/` | 필요 시 |

> **"문서가 없으면 기능도 없다."**

---

## 3. Git Convention

```
feat: 새로운 기능 추가
fix: 버그 수정
refactor: 코드 리팩토링 (기능 변경 없음)
docs: 문서 수정
chore: 빌드, 설정 파일 수정
test: 테스트 추가/수정
```

---

## 4. 환경 변수 관리

- 모든 환경 변수는 `.env.local` (로컬) 또는 배포 플랫폼 대시보드에서 관리한다.
- 코드에 하드코딩 절대 금지
- 민감 값은 반드시 `SecretStr` 타입으로 선언 (backend rules 참조)
- `.env.example` 파일을 항상 최신 상태로 유지한다

```bash
# Kairos 환경 변수 목록 (.env.example 기준)

# Auth
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=

# Database
DATABASE_URL=                    # Neon PostgreSQL connection string

# Storage (Cloudflare R2)
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_PUBLIC_URL=

# AI
ANTHROPIC_API_KEY=
OPENAI_API_KEY=                  # Whisper STT용

# App
NEXT_PUBLIC_API_URL=
```
