# ADR-001: 기술 스택 의사결정 기록

**날짜:** 2026-03-23
**상태:** 확정

---

## 1. Next.js 16 채택

### 결정
Next.js 16 (App Router) + React 19 조합을 채택한다.

### 배경
- React 19의 Server Components, Server Actions가 안정화되어 풀스택 개발 생산성이 향상됨
- App Router가 Pages Router를 완전히 대체하는 방향으로 확정됨
- Vercel 배포 환경과의 최적화된 통합

### 주의사항
- `params`, `searchParams`가 `Promise<>` 타입으로 변경 → 모든 페이지에서 `await` 필수
- `middleware.ts` 대신 `proxy.ts` 사용
- 기존 Next.js 14/15 가이드를 따르면 런타임 에러 발생 가능
- 반드시 `node_modules/next/dist/docs/` 참조

---

## 2. shadcn/ui v4 + Base UI 전환

### 결정
shadcn/ui v4 (base-nova 스타일, @base-ui/react 기반)를 채택한다.

### 배경
- shadcn v4부터 내부 의존성이 Radix UI → Base UI로 전환됨
- Base UI는 더 가볍고 접근성(a11y) 지원이 개선됨
- 기존 shadcn v3 코드와 import 경로가 다를 수 있음

### 주의사항
- `@radix-ui/*` 직접 import 금지
- `@base-ui/react` 의존성이 자동 설치됨
- `components/ui/` 파일 직접 수정 금지 (래핑 컴포넌트 사용)

---

## 3. Zod v4 채택

### 결정
Form 검증 라이브러리로 Zod v4를 채택한다.

### 배경
- Zod v4는 성능 개선과 더 나은 타입 추론을 제공
- `react-hook-form`의 `@hookform/resolvers`가 Zod v4를 지원

### 주의사항
- import 경로가 `"zod"` → `"zod/v4"`로 변경됨
- `import { z } from "zod/v4"` 필수
- 기본 API(`z.string()`, `z.object()` 등)는 대부분 호환

---

## 4. PARA 방법론 기반 지식 관리 구조

### 결정
Tiago Forte의 PARA 방법론(Projects / Areas / Resources / Archives + Inbox)을 핵심 지식 관리 구조로 채택한다.

### 배경
- 회의록이 단순 저장이 아닌 조직의 지식 자산으로 변환되어야 함
- 폴더 계층 대신 N:M 관계형 연결을 통해 하나의 회의가 여러 프로젝트에 동시 연결 가능
- Inbox를 1차 진입점으로 사용하여 AI 분류 추천 후 사용자가 확정하는 워크플로우

### 구조
- **Inbox**: 모든 새 콘텐츠의 진입점, AI가 PARA 분류 추천
- **Projects**: 마감일과 결과물이 있는 한시적 업무
- **Areas**: 지속적 책임 영역 (마감 없음)
- **Resources**: 참고 자료, 관심사
- **Archives**: 완료/중단된 항목 (검색 가능 보존)

---

## 5. 상태 관리 3단계 분리

### 결정
서버 상태(React Query) + 전역 클라이언트 상태(Zustand) + 로컬 상태(useState)로 3단 분리한다.

### 배경
- Redux의 보일러플레이트 과다 문제 회피
- 서버 상태와 클라이언트 상태의 명확한 분리로 캐시 관리 단순화
- Zustand의 최소한의 API로 전역 상태를 가볍게 유지

---

## 6. Mock-First 프론트엔드 개발

### 결정
백엔드 API 없이 Mock 데이터로 프론트엔드를 먼저 완성한다.

### 배경
- 프론트엔드 UI/UX를 빠르게 검증하고 반복할 수 있음
- API 응답 타입을 먼저 정의하면 백엔드 개발 시 계약(Contract)으로 활용 가능
- `NEXT_PUBLIC_API_MOCK=true` 환경 변수로 Mock/실제 API 전환
