# Sprint 1 FE API 연결 설계

> **목적:** 재스캐폴딩된 FE 빈 껍데기를 Sprint 1 BE API에 연결. "업로드 → AI 요약 확인" End-to-End 동작.
> **작성일:** 2026-04-02
> **선행:** Sprint 1 BE 완료 (12개 API + Neon DB), FE 재스캐폴딩 완료

---

## 범위

| 연결 | API | 상태 |
|------|-----|------|
| Clerk 인증 | 로그인/로그아웃 | 이번 |
| 워크스페이스 | POST/GET /workspaces | 이번 |
| 파일 업로드 | POST /upload/presigned-url → R2 | 이번 |
| 회의 생성 | POST /meetings (202) | 이번 |
| 상태 폴링 | GET /meetings/{id}/status | 이번 |
| 회의 상세 | GET /meetings/{id} | 이번 |
| 회의 목록 | GET /meetings | 이번 |
| Inbox, 프로젝트, 액션, RAG | Sprint 2 BE 미존재 | 나중에 |

---

## 1. 환경변수

### frontend/.env.local

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_<REDACTED — Clerk 대시보드에서 확인>
CLERK_SECRET_KEY=sk_test_<REDACTED — .env.local 에만 보관, 절대 커밋 금지>
NEXT_PUBLIC_API_URL=http://localhost:8000
```

> ⚠️ 2026-05-29 보안: 실 Clerk dev secret 이 본 문서에 평문 커밋되어 있던 것을 redaction 함(SEC-CLERK-SECRET-COMMITTED). 키는 .env.local 에만 두고 커밋 금지. **Clerk 대시보드에서 secret rotation 필요**(노출된 키 무효화). Clerk 키는 backend/.env 와 동일 프로젝트.

---

## 2. 신규 파일

### src/lib/api-client.ts

Clerk JWT를 자동 첨부하는 fetch 래퍼.

```typescript
import { useAuth } from "@clerk/nextjs";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiClient(
  path: string,
  options?: RequestInit & { token?: string }
) {
  const { token, ...fetchOptions } = options || {};
  const res = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...fetchOptions,
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...fetchOptions.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "요청 실패" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
```

### src/features/workspaces/types.ts

```typescript
import type { UUID, Timestamped } from "@/types";

export interface Workspace extends Timestamped {
  id: UUID;
  name: string;
  ownerId: UUID;
  memberCount?: number;
}

export interface CreateWorkspaceRequest {
  name: string;
}
```

### src/features/workspaces/api.ts

```typescript
import { apiClient } from "@/lib/api-client";

export const workspaceKeys = {
  all: ["workspaces"] as const,
  list: () => [...workspaceKeys.all, "list"] as const,
};

export async function fetchWorkspaces(token: string) {
  return apiClient("/workspaces", { token });
}

export async function createWorkspace(token: string, name: string) {
  return apiClient("/workspaces", {
    token,
    method: "POST",
    body: JSON.stringify({ name }),
  });
}
```

### src/features/workspaces/hooks.ts

React Query 래핑: useWorkspaces, useCreateWorkspace.

### src/features/meetings/api.ts

```typescript
export const meetingKeys = {
  all: ["meetings"] as const,
  list: (wid: string) => [...meetingKeys.all, "list", wid] as const,
  detail: (wid: string, id: string) => [...meetingKeys.all, "detail", wid, id] as const,
  status: (wid: string, id: string) => [...meetingKeys.all, "status", wid, id] as const,
};

export async function fetchMeetings(token: string, wid: string, page = 1) { ... }
export async function fetchMeetingDetail(token: string, wid: string, id: string) { ... }
export async function fetchMeetingStatus(token: string, wid: string, id: string) { ... }
export async function createMeeting(token: string, wid: string, data: CreateMeetingRequest) { ... }
```

### src/features/meetings/hooks.ts

React Query 래핑: useMeetings, useMeetingDetail, useMeetingStatus (3초 polling), useCreateMeeting.

### src/features/upload/hooks.ts

```typescript
export function usePresignedUpload() {
  // 1. POST /upload/presigned-url → { uploadUrl, fileKey }
  // 2. PUT uploadUrl (R2 직접 업로드, Content-Type 설정)
  // 3. fileKey 반환
}
```

---

## 3. 수정할 페이지

### src/app/page.tsx (랜딩)

로그인 상태면 `/app`으로 리다이렉트. `auth()` 또는 `currentUser()` 사용.

### src/app/(app)/page.tsx (RAG 홈)

- 워크스페이스가 없으면 "워크스페이스를 만들어주세요" + 생성 다이얼로그
- 워크스페이스가 있으면 회의 목록 표시 (빈 상태 또는 실제 목록)
- 빠른 접근 카드에 회의 카운트 표시

### src/app/(app)/new/page.tsx (콘텐츠 추가)

- "회의 녹음" 선택 시:
  1. 파일 드롭존에서 파일 선택
  2. usePresignedUpload로 R2 업로드
  3. useCreateMeeting으로 회의 생성 (202)
  4. `/app/meetings/[id]`로 리다이렉트

### src/app/(app)/meetings/[id]/page.tsx (회의 상세)

- useMeetingStatus로 상태 폴링 (status !== "completed"일 때)
- 폴링 중: 프로그레스 표시 ("트랜스크립트 생성 중...", "AI 요약 중...")
- 완료 시: useMeetingDetail로 요약 + 트랜스크립트 표시
- 실패 시: 에러 메시지 + 재시도 버튼 (없으면 새로 업로드 안내)

---

## 4. 데이터 흐름

```
[랜딩 /]
  → Clerk 로그인 → /(app)
  → 워크스페이스 없으면 생성 다이얼로그
  → 워크스페이스 있으면 RAG 홈 (회의 목록)

[콘텐츠 추가 /(app)/new]
  → 파일 선택
  → POST /upload/presigned-url → { uploadUrl, fileKey }
  → PUT uploadUrl (R2 직접 업로드, 프로그레스 바)
  → POST /workspaces/{wid}/meetings { title, fileKey }
  → 202 Accepted { id, status: "uploading" }
  → redirect → /(app)/meetings/{id}

[회의 상세 /(app)/meetings/{id}]
  → GET /meetings/{id}/status (3초 polling)
  → "uploading" → "transcribing" → "summarizing" → "completed"
  → GET /meetings/{id} → 요약 + 트랜스크립트 렌더링
```

---

## 5. 완료 기준

- Clerk 로그인/로그아웃 동작
- 워크스페이스 생성 가능
- 파일 업로드 → R2 저장 → 회의 생성 (202)
- 상태 폴링 UI (단계별 표시)
- AI 요약 + 트랜스크립트 표시
- **End-to-End: 녹음 파일 업로드 → 2분 내 AI 요약 확인 가능**

---

## 6. 범위 외

- Inbox, 프로젝트 CRUD, 액션 아이템 (Sprint 2 BE 미존재)
- RAG 검색 실제 연결 (Sprint 3)
- Cmd+K 실제 기능 (검색 API 필요)
- 회의 목록 페이지네이션 (Sprint 2)
