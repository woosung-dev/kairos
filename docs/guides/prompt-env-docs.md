# 환경변수 문서화 프롬프트

> 이 프롬프트를 다른 레포에서 AI에게 붙여넣으면 동일한 패턴의 환경변수 문서를 자동 생성합니다.

---

## 사용 방법

1. 아래 프롬프트를 복사
2. 대상 레포의 Claude Code (또는 다른 AI)에 붙여넣기
3. AI가 코드베이스를 탐색해 문서를 자동 생성

---

## 프롬프트

```
이 프로젝트의 환경변수 관리 체계를 구축해줘. 아래 두 가지를 만들어야 해.

---

## 목표

1. `docs/guides/secrets.md` 신규 생성 — 전체 환경변수 매트릭스
2. 루트 `README.md` 업데이트 (없으면 신규) — Quick Start 섹션에 env 설정 진입점 추가

---

## secrets.md 구성 요건

다음 내용을 포함해야 해:

### 1. 빠른 시작 섹션
- .env.example → .env.local 복사 명령어
- "발급처는 아래 표 참고" 안내

### 2. 전체 환경변수 매트릭스 테이블
아래 형식으로 모든 환경변수를 정리해:

| 변수명 | 로컬 | CI | 프로덕션 | 발급처 |
|---|:---:|:---:|:---:|---|

- **로컬**: `.env.local`에 직접 입력하는 값. 실제 예시값 또는 `✅` 표시.
- **CI**: GitHub Actions에서 어떻게 처리되는지. GitHub Secret이면 Secret 이름, 테스트용 fake면 `➖ fake`.
- **프로덕션**: 값이 어디에 저장되는지. (Vercel 환경변수 / GCP Secret Manager / GitHub Secret 등)
- **발급처**: 어디서 값을 얻는지. 대시보드 링크 또는 설명.

🔒 민감 정보(API 키, DB 패스워드 등)는 변수명 옆에 🔒 표시.

### 3. CI 전용 섹션 (있는 경우)
GitHub Actions에서만 사용하는 Secrets/Variables를 별도 표로 정리.
- 배포 자동화용 (예: WIF, 서비스 계정)
- E2E 테스트용 (있는 경우)

### 4. 프로덕션 전용 섹션 (있는 경우)
GCP Secret Manager 또는 다른 시크릿 저장소를 사용하는 경우, 등록 이름 매핑 표 추가.

### 5. 자주 하는 실수 섹션
이 프로젝트의 env 구조에서 발생하기 쉬운 실수 3~5개를 표로 정리.
(예: .env.local 커밋, 프로덕 키 로컬 사용, 특정 저장소 누락 등)

---

## README.md 업데이트 요건

루트 README.md에 "로컬 개발 환경 셋업" 섹션을 추가 또는 업데이트해:

```markdown
## 로컬 개발 환경 셋업

### 1. 환경변수 설정
\`\`\`bash
cp [백엔드경로]/.env.example [백엔드경로]/.env.local   # 있는 경우
cp [프론트엔드경로]/.env.example [프론트엔드경로]/.env.local   # 있는 경우
\`\`\`
발급처 및 CI/프로덕션 설정 방법 → `docs/guides/secrets.md`

### 2. 실행 방법
[프로젝트에 맞는 실행 명령어]
```

기존 README 내용은 유지하고, 섹션을 추가/보완하는 방식으로 진행해.

---

## 탐색 지시사항

작업 전 다음을 탐색해서 실제 값을 기반으로 문서를 작성해:

1. 모든 `.env.example` 파일 읽기
2. `.env.local`, `.env` 파일이 있으면 변수명만 확인 (값은 문서에 포함하지 말 것)
3. GitHub Actions 워크플로우 파일 (`*.yml`) 에서 env/secrets 참조 확인
4. 배포 관련 파일 (Dockerfile, docker-compose.yml, fly.toml, vercel.json 등) 확인
5. 백엔드 config/settings 파일 (예: config.py, settings.py, .env.ts) 에서 환경변수 목록 확인

탐색 결과를 바탕으로 누락된 환경변수가 없도록 완전한 문서를 만들어줘.

---

## 스타일 규칙

- 언어: 한국어 (코드, 변수명, 명령어 제외)
- 파일 헤더 첫 줄: 한 줄 한국어 주석으로 파일 역할 설명
- 표에서 값이 없거나 불필요한 경우: `➖` 사용
- 민감 정보: `🔒` 기호 사용
- 코드 블록: bash/markdown 언어 태그 명시
```

---

## 커스터마이징 포인트

프롬프트 사용 전 아래 항목을 레포에 맞게 수정하세요:

| 항목 | 기본값 | 변경 필요 시 |
|---|---|---|
| 배포 환경 | GCP Cloud Run + Vercel | Railway, Fly.io, AWS 등으로 변경 |
| 시크릿 저장소 | GCP Secret Manager | AWS Secrets Manager, Doppler 등으로 변경 |
| CI 플랫폼 | GitHub Actions | GitLab CI, CircleCI 등으로 변경 |
| 언어 정책 | 한국어 | 영어 프로젝트면 "언어: 영어"로 변경 |
| E2E 테스트 | Playwright | Cypress 등으로 변경 |
