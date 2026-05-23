# Sprint 27d Pre-GA Audit — **agy 후속 세션** (Antigravity CLI)

> opus 1차 audit 종료 직후. 이 세션은 **agy (Antigravity CLI)** 가 같은 브랜치에서 이어서:
> ① opus 가 발견한 결함 4건 (BUG-S27d-1/2/3/4) **fix + 검증 루프** → ② opus 결과 cross-check → ③ DEFERRED 시나리오 3건 보강.
>
> **순서**: opus (완료, commit `6d70eb2`) → **agy (현재)** → codex (마지막).
> **CLI 종류**: agy = Antigravity CLI (codex CLI 류 자동 에이전트). Claude Code 의 gstack 과 무관.

---

## 새 세션 진입 절차 (사용자 액션)

1. **로컬 서버 기동 확인**
   ```bash
   curl -s -o /dev/null -w "FE: %{http_code} " http://localhost:3000/
   curl -s -o /dev/null -w "BE: %{http_code}\n" http://localhost:8000/api/v1/health
   # 둘 다 200 이어야 함
   ```

2. **브랜치 fetch + checkout**
   ```bash
   cd /Users/woosung/project/agy-project/kairos
   git fetch origin
   git checkout sprint-27d/pre-ga-audit-prompts
   git pull origin sprint-27d/pre-ga-audit-prompts
   ```

3. **Antigravity (agy) CLI 새 세션 시작** 후 본 프롬프트 전체 복붙.

4. **goal 등록** (Stop hook 자동 보장):
   ```
   /goal sprint-27d/pre-ga-audit-prompts 브랜치에서 ① 결함 4건 (BUG-S27d-1/2/3/4) fix + 각 fix 후 검증 루프 (회귀 가드 + 관련 test 실행) ② opus 1차 audit 결과 cross-check ③ DEFERRED 시나리오 3건 보강 ④ docs/sprints/sprint-27d-pre-ga-audit/agy/ 하위 산출물 (cross-check, deferred, integrated-report, report.html) 작성 ⑤ 동일 브랜치 commit + push (PR #108 업데이트)까지 모두 완료
   ```

---

## 0. 너의 임무 (3-단계)

너는 Kairos 프로젝트의 외부 5명 dogfooding 진입 직전 audit 의 **agy 후속 세션** 평가 + fix 에이전트.

같은 브랜치 `sprint-27d/pre-ga-audit-prompts` 에 추가 commit 으로:

### A. 결함 fix + 검증 루프 (Step 1, 90분)
opus 가 발견한 결함 중 **P1+P2 4건 fix** (Sentry SKIP, P3 2건은 BL-S27e-* 등재만):
- **BUG-S27d-1 P1** (OnboardingTooltip PopoverTrigger nativeButton 회귀)
- **BUG-S27d-2 P2** (`/actions` 404)
- **BUG-S27d-3 P2** (file upload mime validation 부재)
- **BUG-S27d-4 P1** (보안 헤더 부재)

각 fix 후 **검증 루프**:
- 회귀 가드 (해당 시나리오 재실행 → 결함 해소 확인)
- 인접 영역 test 실행 (`pytest` / `npm run typecheck` / `npm test`)

### B. opus 결과 cross-check (Step 2, 30분)
6 agent (QA-Function/EdgeCase/CTO/CEO/일반사용자/Solo-A-to-Z) 의 verdict 검증.

### C. DEFERRED 시나리오 3건 보강 (Step 3, 30분)
opus 가 실행 어려웠던 영역:
- agent-2 E3: Cross-tenant private RAG leak
- agent-2 E5: Project visibility 분기 (viewer/draft/private)
- agent-2 E7: localStorage workspace drift

### 산출물 (Step 4)
`docs/sprints/sprint-27d-pre-ga-audit/agy/`:
- `agy-fix-log.md` (각 fix + 검증 루프 결과)
- `agy-cross-check.md` (opus 6 agent verdict 재평가)
- `agy-deferred-scenarios.md` (E3/E5/E7 결과)
- `agy-integrated-report.md` (agy 종합)
- `agy-report.html` (단일 self-contained HTML, opus `report.html` 스타일 차용)
- `screenshots/`

### 커밋 + push (Step 5)
같은 브랜치 → PR #108 자동 업데이트.

---

## 1. 사전 컨텍스트

### 환경
- main HEAD: `457c994` (Sprint 27c P0 fix #107)
- 브랜치: `sprint-27d/pre-ga-audit-prompts` (opus commit `6d70eb2`, follow-up prompts commit `25924a6`)
- FE: `http://localhost:3000` / BE: `http://localhost:8000/api/v1`
- Clerk dev `creative-boxer-79.clerk.accounts.dev` (Production 미발급, ADR-022 SKIP)
- GEMINI_API_KEY: set ✅
- 로그인 계정: `d@e.com` (Personal workspace `e968c95f-4bbe-4f12-9468-2741c047e142` + Team `7f9f446d-9b7f-4ae7-aa9b-ac861fb81b11` "QA Cycle C Team")
- seed credentials: `~/.kairos-qa-secrets/seed-credentials-2026-05-17.env` (JWT expired, email/password 유효)
- **production audit SKIP** / **Sentry SKIP** (사용자 정책)

### opus 1차 audit 결과 (composite 7.53/10 GO)
| Agent | 점수 | verdict |
|-------|------|---------|
| agent-1 QA-Function | 7.2/10 | GO |
| agent-2 QA-EdgeCase | 8.0/10 | GO (IDOR 0 leak ✅) |
| agent-3 CTO | 6.5/10 | NEEDS-FIX (P1 1건) |
| agent-4 CEO | 7.5/10 | GO |
| agent-5 일반사용자 | 7.8/10 | GO |
| agent-6 Solo-A-to-Z | 8.2/10 | GO |
| **Composite** | **7.53** | **GO** |

### opus 결함 7건
| ID | 우선순위 | 결함 | fix? |
|----|---------|------|------|
| BUG-S27d-1 | P1 회귀 | OnboardingTooltip PopoverTrigger (BL-S27c-8) — /dashboard + CmdK 2위치 | **agy fix** |
| BUG-S27d-2 | P2 회귀 | `/actions` 404 (Sprint 27c carry-over) | **agy fix** |
| BUG-S27d-3 | P2 | File upload mime/extension validation 부재 | **agy fix** |
| BUG-S27d-4 | P1 | 보안 헤더 부재 (CSP/X-Frame/등 FE+BE) | **agy fix** |
| ~~BUG-S27d-5~~ | — | Sentry 정책 SKIP | 결함 아님 |
| BUG-S27d-6 | P3 | RAG latency dev avg 10.6s | BL-S27e-* 등재만 |
| BUG-S27d-7 | P3 | 사이드바 nav flicker | BL-S27e-* 등재만 |

---

## 2. Step 1 — 결함 fix + 검증 루프 (90분)

### 2.1. BUG-S27d-1 fix — OnboardingTooltip PopoverTrigger nativeButton 회귀 (20분)

**원인**: Base UI `PopoverTrigger` 컴포넌트가 `nativeButton={true}` 기대하지만 비-`<button>` element 로 렌더 → console.error.

**위치 추정**: `frontend/src/components/onboarding/OnboardingTooltip.tsx`
```bash
grep -r "PopoverTrigger" frontend/src --include="*.tsx" --include="*.ts" -l
```

**fix 패턴 (택1)**:
```tsx
// 옵션 A — render prop
<PopoverTrigger render={(props) => <button type="button" {...props} />}>
  ...
</PopoverTrigger>

// 옵션 B — nativeButton 비활성화
<PopoverTrigger nativeButton={false}>
  ...
</PopoverTrigger>
```

**검증 루프**:
```bash
# 1. typecheck
cd frontend && npm run typecheck
# 2. dev server hot-reload 후 MCP Playwright 로 /dashboard + ⌘K 진입
#    → console.error 0건 확인
# 3. vitest (해당 컴포넌트 spec 있다면)
cd frontend && npm test -- OnboardingTooltip
```

회귀 가드 PASS 시 `agy-fix-log.md` 에 결과 기록.

---

### 2.2. BUG-S27d-2 fix — `/actions` 404 (15분)

**선택지**:
- **옵션 A (권장)**: `/actions` → `/inbox` redirect (Next.js middleware 또는 page redirect)
- **옵션 B**: 신규 `/actions` 페이지 추가 (action item 칸반)

**옵션 A 구현**:
```tsx
// frontend/src/app/(app)/actions/page.tsx (신설)
import { redirect } from 'next/navigation';
export default function ActionsPage() {
  redirect('/inbox');
}
```

**검증 루프**:
- MCP Playwright: `/actions` 진입 → /inbox redirect 확인
- 404 console.error 0건

---

### 2.3. BUG-S27d-3 fix — File upload mime/extension validation (25분)

**위치**: `backend/src/upload/router.py` 또는 `backend/src/upload/service.py`

**fix 패턴**:
```python
# backend/src/upload/router.py
ALLOWED_MIMES = {
    "audio/mp4", "audio/x-m4a", "audio/mpeg", "audio/wav", "audio/webm",
    "video/mp4", "video/webm",
}
ALLOWED_EXTENSIONS = {".m4a", ".mp3", ".mp4", ".wav", ".webm"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

@router.post("/upload/file", status_code=201)
async def upload_file(file: UploadFile, ...):
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(415, "Unsupported file type")
    if not any(file.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(415, "Unsupported file extension")
    # size 검사 (UploadFile 의 size 체크)
    ...
```

**검증 루프**:
```bash
# 1. backend test
cd backend && uv run pytest tests/upload/ -v
# 2. fetch evaluate (재현 케이스)
#    POST /workspaces/{wid}/upload/file with evil.exe + text/plain → 415 기대 (opus 는 201)
# 3. 정상 케이스 (test.m4a) → 201 여전히 OK
```

---

### 2.4. BUG-S27d-4 fix — 보안 헤더 부재 (30분)

#### FE: `frontend/next.config.ts`
```ts
async headers() {
  return [
    {
      source: '/:path*',
      headers: [
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(self), geolocation=()' },
        // production HTTPS 시:
        // { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
      ],
    },
  ];
}
```

#### BE: `backend/src/main.py` ASGI middleware 추가
```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

**검증 루프**:
```bash
curl -I http://localhost:3000/ | grep -iE "x-frame|x-content|referrer"
curl -I http://localhost:8000/api/v1/health | grep -iE "x-frame|x-content|referrer"
# 모두 헤더 등장 확인
```

---

### 2.5. P3 결함 2건 — BL-S27e-* 등재만

`docs/REFACTORING-BACKLOG.md` (또는 동등 파일) 에 추가:
- **BL-S27e-1**: RAG latency 모니터링 + p95 < 5s 목표 (BUG-S27d-6, Sprint 28+)
- **BL-S27e-2**: 사이드바 nav flicker 디버깅 (BUG-S27d-7, Sprint 28+)

---

### 2.6. fix Step 통합 검증

```bash
# backend 전체 test
cd backend && uv run pytest -x

# frontend typecheck + vitest
cd frontend && npm run typecheck && npm test

# MCP Playwright 회귀 가드 — opus audit 의 핵심 시나리오 재실행
# (라우트 console.error 0건, IDOR 5/5 403, 회의 업로드 PASS)
```

---

## 3. Step 2 — opus cross-check (30분)

각 agent verdict 재평가:

| Agent | opus verdict | agy 재평가 | 일치? |
|-------|--------------|-----------|-------|
| agent-1 QA-Function 7.2 | 8 골든 플로우 5 PASS / 1 부분 / 2 DEFERRED | (재실행) | ✅/⚠️ |
| agent-2 QA-EdgeCase 8.0 | IDOR 5/5 403 + I-19 PASS | (재실행) | |
| agent-3 CTO 6.5 | 보안 헤더 부재 + RAG 10.6s | (fix 후 재측정) | |
| agent-4 CEO 7.5 | 랜딩 5섹션 + 모바일 정상 | (재확인) | |
| agent-5 일반사용자 7.8 | YES 추천 | (재평가) | |
| agent-6 Solo-A-to-Z 8.2 | 78 cells FAIL 2 | (fix 후 FAIL 0 기대) | |

→ `agy-cross-check.md`

---

## 4. Step 3 — DEFERRED 시나리오 보강 (30분)

### E3 — Cross-tenant private RAG leak
- 사용자 본인 (`d@e.com`) 의 Personal + Team workspace 양쪽 사용
- Team workspace 에 private project 만든 후 Personal workspace 에서 RAG 질의 → private project 의 note 가 인용되지 않는지 검증
- 또는 seed env 의 SENTINEL A/B 재로그인 시도 (email/password 유효)

### E5 — Project visibility 분기
- Personal workspace 에서 project 생성 시 visibility 옵션 (public/draft/private) UI 노출 확인
- 각 visibility 별 RAG 인용 정합 검증

### E7 — localStorage workspace drift
- 사용자 d@e.com logout → re-login
- localStorage `kairos-workspace.activeWorkspaceId` 가 stale 값 유지하는지
- stale workspace_id 로 API 호출 시 403 graceful

→ `agy-deferred-scenarios.md`

---

## 5. Step 4 — 산출물 + Step 5 commit + push

### `agy-integrated-report.md`
- fix 4건 결과 + 검증 루프 PASS
- cross-check 매트릭스
- DEFERRED 3건 결과
- 신규 결함 (있다면 `BUG-S27d-AGY-*`)
- 갱신된 composite verdict (fix 반영 후)
- 다음 (codex) 세션 인계 정보

### `agy-report.html`
opus `docs/sprints/sprint-27d-pre-ga-audit/report.html` 스타일 차용 (dark mode, condition grid, bug card, score table). agy 결과 섹션 추가.

### commit + push
```bash
git add docs/sprints/sprint-27d-pre-ga-audit/agy/ \
        backend/src/upload/ \
        frontend/src/components/onboarding/ \
        frontend/src/app/\(app\)/actions/ \
        frontend/next.config.ts \
        backend/src/main.py \
        docs/REFACTORING-BACKLOG.md

git commit -m "fix+docs: Sprint 27d agy follow-up — 결함 4건 fix + cross-check + DEFERRED 보강

(상세 본문)

Co-Authored-By: Antigravity Agent <noreply@...>"

git push origin sprint-27d/pre-ga-audit-prompts
# PR #108 자동 업데이트
```

---

## 6. agy (Antigravity CLI) 특화 가이드

- **gstack 무관** — 본 세션은 Claude Code 의 gstack skill 과 무관. Antigravity 자체 도구만 사용.
- **MCP Playwright** — 동일 사용 (browser_navigate, snapshot, evaluate, file_upload, click 등)
- **Bash + curl 적극** — fix 검증 + test 실행에 필수
- **Read / Write / Edit / Grep** — 표준 file 도구
- **한국어 응답** — CLAUDE.md 글로벌 (사용자가 한국어 → 응답도 한국어)
- **memory** — 파일 (`docs/sprints/...`) 로 persist, 세션 간 인계는 codex 세션이 read

---

## 7. 시작 신호

```
opus 산출물 8개 (SCOPE + agent-1~6 + integrated-report) read 후 Step 1.1 BUG-S27d-1 fix 부터 시작해줘.
```

### 종료 보고 형식

- fix 4건 결과: BUG-S27d-1/2/3/4 status (DONE/PARTIAL/FAIL)
- 검증 루프 PASS 여부: pytest / typecheck / vitest / MCP Playwright 회귀
- agy cross-check 6 agent 일치율 N/6
- DEFERRED 3건 결과 (E3/E5/E7)
- 신규 결함 BUG-S27d-AGY-* N건
- 갱신된 composite verdict (fix 반영 후 기대치)
- PR #108 update commit hash
- 다음 세션 (codex) 진입 가이드

---

## 8. 다음 세션 (codex) 진입

agy 종료 후 사용자가 codex CLI 새 세션 시작 시 `docs/sprints/sprint-27d-pre-ga-audit/prompts/agent-followup-codex.md` 사용.
codex 는 fix 가 정상 작동하는지 회귀 가드 + adversarial 시각 + 3-세션 통합.
