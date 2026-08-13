# 로컬 환경 셋업 가이드

## 사전 요구사항

| 도구 | 최소 버전 | 확인 명령어 |
|------|----------|------------|
| Node.js | 20+ | `node -v` |
| pnpm | 9+ | `pnpm -v` |
| Git | 2.30+ | `git --version` |

## 1. 저장소 클론 및 의존성 설치

```bash
git clone <repository-url> kairos
cd kairos/frontend
pnpm install
```

## 2. 환경 변수 설정

```bash
cp .env.example .env.local
```

`.env.local` 파일을 열어 아래 값을 채운다:

### Clerk 인증 키 발급

1. [Clerk 대시보드](https://dashboard.clerk.com/) 접속
2. "Create application" → Google OAuth 활성화
3. "API Keys" 탭에서 아래 값 복사:

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
```

### API 설정

```bash
# 백엔드 미연결 시 Mock 모드로 실행
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_API_MOCK=true
```

## 3. 개발 서버 실행

```bash
cd apps/web
pnpm dev
```

브라우저에서 `http://localhost:3000` 접속.

## 4. Mock 모드

현재 Phase 1에서는 백엔드 없이 Mock 데이터로 동작한다.

- `NEXT_PUBLIC_API_MOCK=true` 설정 시 `mocks/data/` 디렉토리의 데이터 사용
- Mock API는 `features/[domain]/api.ts`에서 지연 시뮬레이션 포함
- 데이터는 메모리에만 존재하므로 새로고침 시 초기화됨

## 5. 유용한 명령어

```bash
pnpm dev          # 개발 서버 (http://localhost:3000)
pnpm build        # 프로덕션 빌드
pnpm lint         # ESLint 실행
```

## 6. shadcn/ui 컴포넌트 추가

```bash
pnpm dlx shadcn@latest add [component-name]
```

> `components/ui/` 내 파일은 직접 수정하지 않는다. 커스텀이 필요하면 래핑 컴포넌트를 생성한다.

## 7. 트러블슈팅

### pnpm install 실패 시
```bash
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### Clerk 로그인 안 될 때
- `.env.local`의 `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`와 `CLERK_SECRET_KEY`가 올바른지 확인
- Clerk 대시보드에서 "Allowed origins"에 `http://localhost:3000` 추가

### 타입 에러 발생 시
- `node_modules/next/dist/docs/`를 참조하여 Next.js 16 API 변경사항 확인
- `params`는 반드시 `Promise<>` 타입으로 선언
