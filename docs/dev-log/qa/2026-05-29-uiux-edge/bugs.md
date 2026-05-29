# Kairos 2차 정검 — 버그 백로그 (P0~P3, evaluator 보정 반영 최종)

출처 = 라이브(MCP Playwright 3계정) + Channel A 통합테스트(test DB, 16 PASS) + 6-lens Workflow(42 confirmed/6 refuted) + **evaluator 패널(빈컨텍스트 opus×2 + codex) adversarial 보정**. fix 는 별도 PR + 사용자 승인.

> **evaluator 보정 핵심**: opus 8.1/7.6 GO-WITH-CHANGES, codex 5.5 REVISE. 세 평가자가 **동일한 보정점**에 수렴 — ① DARK-CONTRAST 비율 오기(1.59→2.98) ② PERSONAL-INVITE "silent fail" 코드상 토스트 존재로 반증→P3 ③ A11Y 클러스터 대부분 false positive(visible text/sr-only 존재)→avatar 만 잔존 ④ LANDING-TEXT-WHITE 라이트 스샷상 정상→reframe ⑤ WS-MEMBER-UNIQUE는 멀티워커 데이터무결성→**P1 격상** ⑥ codex 가 미탐 contract 버그 2건 추가 발굴. 모두 반영 완료.

상태: `신규`/`확정(carry-over)`/`정적`/`관찰`. 각 헤드라인은 3평가자 중 최소 1이 코드 file:line 재현.

## FIX 적용 현황 (branch `sprint-28b/uiux-edge-fixes`, 6 commits, 미푸쉬)
| ID | 적용 | commit |
|---|---|---|
| SEC-CLERK-SECRET-COMMITTED (P0) | ✅ 파일 redaction (**rotation 은 운영자 잔여**) | d5463cc |
| BUG-WS-MEMBER-UNIQUE (P1) | ✅ FIXED — 모델+마이그레이션 **Neon 적용** + 회귀가드 2건 | 5cf7dae |
| BUG-MEETING-FAILED-UI (+OBS-MEETING-ACTIONS) (P2) | ✅ FIXED — BE errorMessage 노출 + FE 실패뷰+재업로드 CTA + export 게이트 | 68d6f30 |
| UX-NEW-GRID-375 (P2) | ✅ FIXED — grid-cols-1 sm:grid-cols-3 (375 스샷 검증) | 8335d26 |
| DARK-CONTRAST-MUTED (P2) | ✅ FIXED — #5C5C63→#7A7A82 (4.66:1 AA) | 8335d26 |
| RQ-KEY-COLLISION (P2) | ✅ FIXED — projectKeys.list params 포함 | 8335d26 |
| FE-PAGESIZE-PARAM-MISMATCH (P3) | ✅ FIXED — page_size→pageSize | 8335d26 |

검증: **전체 BE 528 pass/1 skip 무회귀** · FE `tsc --noEmit` clean · 라이브 스샷(p5-fix-new-mobile375-after / p5-fix-meeting-failed-after).

## FIX 적용 현황 — Sprint 28c P3 polish (branch `sprint-28c/a11y-polish`, PR1)
| ID | 적용 | commit |
|---|---|---|
| A11Y-AVATAR-LABEL (P3) | ✅ FIXED — avatar trigger `aria-label="계정 메뉴"` (라이브 a11y tree 확인) | c9c20f1 |
| A11Y-ICON-RAIL-768 (P3) | ✅ FIXED — collapsed nav + 설정 링크 `aria-label` (focus-visible 은 전역 :focus-visible 이미 적용 → 비추가). 768 라이브 스냅샷 확인 | c9c20f1 + b2d4ab1 |
| UX-CMDK-GLYPH (P3) | ✅ FIXED — kbd `var(--font-mono), system-ui, sans-serif` per-glyph fallback. ⌘K 렌더 4곳 전수(header/cmd-k/dashboard/rag-home) | b2244f3 |
| OBS-VIEWER-VISIBILITY-BTN (P3) | ✅ FIXED — VisibilityBadge `interactive` prop(BUG-H02 onClick 가드 유지) + detail/dashboard `interactive={canManage}`. viewer 라이브 = disabled/default cursor/label 툴팁 | b39dea6 |
| BUG-ARCHIVED-PROJECT-LEAK (P3) | ✅ FIXED — service.list_projects status=None→'active' 기본. repo 는 flexible 유지(pipeline auto-link 무영향). 테스트 반전 + reachability | 03ad9b2 |
| DESIGN-TOKEN-DRIFT (P3) | ✅ FIXED — citation-badge/action-kanban/today-feed 하드코드 hex→var() + ::selection→var(--accent-foreground). 토큰 resolve 동일값 = 시각 무회귀 | f0bb461 |
| BUG-SEARCH-CURRENT-PROJECT-NOOP (P3, B2 결정=숨김) | ✅ FIXED — 글로벌 search "현재 프로젝트" 탭 제거(전체/선택한소스만). projectId 인프라 유지 | 0f04524 |

검증(PR1): **로컬 CI 게이트 4종 green** — backend pytest **526 passed** · vitest **56 passed** · next build(+typecheck) · security-headers public-only **2/2** · `tsc --noEmit` clean. 라이브 MCP Playwright(3계정 중 C·B) console.error 0(B 의 stale-wid 403 은 BUG-H01 류 기존이슈, 본 변경 무관). 스샷 `screenshots/s28c-*`(dashboard ⌘K / search 2탭 / viewer 비대화형 배지 다크).

## FIX 적용 현황 — Sprint 28c 설계종속 (branch `sprint-28c/memory-ws-filter`, PR2)
| ID | 적용 | commit |
|---|---|---|
| BUG-MEMORY-WS-FILTER (P3, 결정=WHERE+테스트) | ✅ FIXED — memory 5 mutation workspace_id WHERE + cross-ws 차단 통합테스트 3건(정적→실증). composite FK 는 제외(memory 는 타 FK target 아님). BE 529 pass. PR #118 merged | b733547 |

## FIX 적용 현황 — Sprint 28c P3 polish 2차 (branch `sprint-28c/p3-polish-2`, PR3)
| ID | 적용 | commit |
|---|---|---|
| 라이트모드 semantic 토큰 (P3, DESIGN-TOKEN-DRIFT 후속) | ✅ FIXED — [data-theme=light] 에 --warning/error/info/success/chart-1..5 -600 계열 정의(다크 상속 → amber on white ≈1.4:1 해소, 랜딩 라이트 cat 색과 정합). 다크 무변경 | 52906dd |
| LANDING-TEXT-WHITE (nit) | ✅ FIXED — CTA 3곳(hero/nav/pricing) text-white→var(--accent-foreground). 다크 랜딩(accent #3ECFB4) 흰텍스트 ≈1.7:1 → 어두운 텍스트 고대비. 브랜드 accent 무변경 | edf8365 |
| DESIGN-TOKEN cluster (skeleton, P3) | ✅ FIXED — 공용 components/ui/skeleton.tsx + 6개 ad-hoc 스켈레톤 통일(시각 패리티 유지) | 7c7f119 |

검증(PR3, FE-only): vitest **56** · next build(+typecheck) · `tsc --noEmit` clean · security-headers public-only **2/2**. **사후 라이브 확인 완료**(:3000 점유 프로세스 종료 후 Kairos 재기동, dev 캐시 clean 후): ① P3-C 다크 랜딩 CTA computed color = `#0A0A0B`(어두운 텍스트) on accent `#3ECFB4` → 기존 흰텍스트 ≈1.7:1 해소(스샷 `s28c-landing-dark.png`), 라이트는 흰텍스트 유지(`s28c-landing-light.png`). ② P3-A `[data-theme=light]` probe `--warning` resolve = `rgb(217,119,6)`=`#D97706`(신규 라이트값, 기존 다크 #fbbf24 아님). ③ 라이트 대시보드 정상 렌더(`s28c-light-dashboard.png`, console.error 0). nit 잔여: 로딩카피/px 타이포 통일(의도적 → skip).

## FIX 적용 현황 — Sprint 28d P3 마감 + 안정화 (branch `sprint-28d/fe-polish-stabilize`)
> PR3 가 "의도적 skip" 한 로딩카피/px 타이포를 **사용자 재결정(전부 토큰화)** 으로 마감 + 머지된 라이트 semantic 토큰의 DESIGN.md atomic 문서화 + dogfooding 안정화 carry 2건.

| ID | 적용 | 비고 |
|---|---|---|
| DESIGN-TOKEN px 타이포 (P3, cluster 잔여) | ✅ FIXED — `globals.css @utility .text-caption(11px)/.text-micro(10px)` 정의 + `text-[11px]`(23)/`text-[10px]`(43) 전부 치환(34파일). 생성 CSS 동일 px = 시각 무회귀 | 사용자 Q1 = 전부 토큰화 |
| DESIGN-TOKEN 로딩 카피 (P3, cluster 잔여) | ✅ FIXED — "로딩 중…/로딩 중..." 8건 → canonical "불러오는 중..."(loading.tsx 기준) 통일 | 주석/aria 미접촉 |
| 라이트 semantic 토큰 (P3, A4 atomic doc) | ✅ FIXED — 머지된 `[data-theme=light]` -600 토큰을 `DESIGN.md §Color` Light Semantic 표 + Decisions Log + Scale 에 문서화(텍스트 대비 caveat 포함) | 코드는 52906dd(PR3) |
| BL-S27c-12 logout stale workspace (P1) | ✅ FIXED — store `ownerUserId`+`ensureOwner` race-free 가드 + panel-layout self-heal. 단위테스트 3건 | REFACTORING-BACKLOG 동기화 |
| BL-S27e-2 사이드바 nav flicker (P3) | ✅ FIXED — NAV_BOTTOM 역할 게이트가 role 미해결(null) 시 낙관적 노출(viewer 확정 때만 숨김) | 루트코즈=workspaceRole persist 제외 |
| BL-S27c-8 PopoverTrigger A11Y (P1) | ✅ 이미 해소(Sprint 27d BUG-S27d-1, stale backlog) — 코드 재확인 | — |

검증(Sprint 28d, FE-only): `tsc --noEmit` clean · `next build` 전 라우트 OK · vitest **59**(+3 ensureOwner) · 생성 CSS `.text-caption{font-size:11px}`/`.text-micro{font-size:10px}` 확인. 라이브(계정전환 403/nav flicker)는 로컬 2-계정 + 백엔드 스모크 권고(변경 저위험: px=시각무변·copy=문자열·B1 단위테스트·B3 빌드clean).

**Sprint 28c 결정/연기 (사용자 confirm)**:
- **BL-DATA-HYGIENE-SEED** → **GA/ADR-024 연기**. ⚠️ 조사결과 lazy seed(`auth/dependencies.py`)는 이미 JWT claims(name/email)를 읽어 User 를 채움. displayName="사용자"/email="" 의 원인은 **Clerk 기본 세션토큰이 email/name claim 미포함**(JWT 템플릿 커스터마이즈 필요)임 → 코드 fix 아님. Clerk Prod 설정 시 기존 코드가 자동 동작.
- **BUG-MEMORY-WS-FILTER composite FK** → 제외(라이브 IDOR 없음 + memory 는 타 composite FK 의 target 아님).
- **search project picker** → 제외(과한 범위, 탭 숨김 채택).

**미적용 (잔여 — 사용자 결정/후속)**:
- **BUG-INBOX-PROMOTE-STUB** (P2) — 제품 결정 필요. "다른 프로젝트"·"수정" 둘 다 동일 미구현 editing stub → picker 구현(기능) vs edit affordance 제거(UX 축소) 택1.
- **(정정·완료)** 실패 pipeline 은 error_message 를 **정상 기록함**(BE 로그 검증 — httpx 404 `str(e)`). 초기 "값 null" 은 uvicorn 이 redaction 전 stale 코드였던 탓 — BE 재기동 후 detail 응답 errorMessage 정상 반환 확인. FE 는 **친화적 메시지만** 표시(원시 httpx 오류·서명 URL 의 UI 덤프 회피); errorMessage 는 API 에 support/디버깅용 보존(status 엔드포인트와 동일). 선택 polish = pipeline 이 error_message 를 사용자친화 문구로 sanitize.
- **P3 polish** → **Sprint 28c 전부 처리**(PR1 6 + PR2 memory + PR3 라이트토큰/랜딩CTA/skeleton, 위 `FIX 적용 현황 — Sprint 28c` 3개 표 참조). 잔여: BL-DATA-HYGIENE-SEED(GA 연기, 코드 fix 아님) · 로딩카피/px 타이포 통일(의도적 → skip).

---

## P0 — 시크릿 노출 (QA 블로커와 분리)

### SEC-CLERK-SECRET-COMMITTED `확정`
- 실 Clerk **dev** secret `CLERK_SECRET_KEY=sk_test_mvhptL…` 평문 커밋 — `docs/superpowers/specs/2026-04-02-sprint1-fe-api-design.md:30`(commit 384f88c). (같은 파일 line 5 의 `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY pk_test_…` 는 publishable=공개 설계라 시크릿 아님.)
- dev 키라 blast radius 제한 + repo private 전제 → **3평가자 중 "가장 약한 P0"** 이나 rotation 규율상 P0 유지.
- 조치: 키 rotation + 파일 제거 + git 히스토리 스크럽 + public 전환 금지.

---

## P1

### BUG-WS-MEMBER-UNIQUE `확정 (P2→P1 격상, evaluator 권고)`
- **근거**: `workspaces/models.py:22-28` WorkspaceMember = id PK only, composite UNIQUE/`__table_args__` 없음; alembic `c3d4e5f6a7b8:36` 인덱스 `unique=False`. Channel A: asyncio N=5 는 단일 이벤트루프 직렬화로 우연히 1 row이나, **강제 2-트랜잭션 interleave → 중복 row 2개**(test_rbac_edges_s28b.py, evaluator 가 16/16 PASS 재실행 확인).
- **격상 이유**: 운영 = GCP Cloud Run(>1 인스턴스 수평 확장). 테넌시 조인 테이블에 DB UNIQUE backstop 부재 → 멀티워커 동시 첫로그인/invite수락 시 **RBAC 멤버십 row 무결성 silent 손상** 가능 = UX 아닌 데이터무결성 리스크.
- **권고**: `UniqueConstraint(workspace_id, user_id)` + 마이그레이션(기존 중복 dedup 선행).

---

## P2

### BUG-MEETING-FAILED-UI `신규·확정` (3평가자 HOLDS UP, 근본원인 정밀화)
- **repro**: status="failed"(badge "실패") 미팅 상세가 generic "요약 정보가 없습니다 / AI 분석이 완료되면 요약이 자동으로 생성됩니다" placeholder 렌더 + retry/copy/error 전무. (`screenshots/p2-meeting-failed.png`)
- **근본원인(정밀화)**: `meeting-detail.tsx:116 isProcessing = status!=='completed' && status!=='failed'` → failed 가 탭뷰(:213)로 fall-through → 기본탭 요약 = `meeting-summary-view.tsx:16-30` 가 transient/permanent 동일 카피. **error_message 는 pipeline 이 기록(`pipeline_service.py:249`)하나 detail 응답 스키마가 미노출(`meetings/service.py:119`)** → 라이브 API `errorMessage:null`. (codex 정정 — "pipeline 미기록"이 아니라 "detail 응답 누락".) export 버튼도 failed 에 노출(:156) → 빈 산출 가능(OBS-MEETING-ACTIONS 와 결합).
- **권고**: dedicated FailedMeetingView(detail 응답에 error_message 노출 + 재시도) + 비-completed 시 export 비활성.

### UX-NEW-GRID-375 `신규·확정` (3평가자 HOLDS UP)
- `app/(app)/new/page.tsx:143 <div className="grid grid-cols-3 gap-4 mb-8">` mobile breakpoint 부재 → 375px 에서 카드 압착 + 단어 중간 줄바꿈("회의 녹 음","노트 작 성","자료 업 로드"). 768/desktop 정상. (`p1-new-mobile375.png`)
- **권고**: `grid-cols-1 sm:grid-cols-3` + 하위탭 wrap.

### DARK-CONTRAST-MUTED `신규` (비율 보정)
- `globals.css:68 --text-muted #5C5C63` on `--background #0A0A0B` = **2.98:1** (surface #141416 위 2.77:1). **WCAG AA 일반텍스트 4.5:1 미달**(~3:1 비텍스트 floor 도 경계). ⚠️ 초안의 "1.59:1" 은 오기 — 3평가자 공통 지적, 2.98:1 로 정정(결론=AA fail 은 유지).
- **권고**: 다크 muted 토큰 명도 ≥4.5:1.
- (대조: `--text-secondary #8E8E93` = ~6:1 AA pass — 비대상, refuted.)

### RQ-KEY-COLLISION `신규 (codex 발굴, 코드 확인)`
- **근거**: `features/projects/hooks.ts:66 useProjects` queryKey = `projectKeys.list(wid)` 로 **params(status) 미포함**. 그런데 `sidebar.tsx:170-171` 가 동일 wid 에 `{status:'active'}` 와 `{status:'archived'}` 두 번 호출 → **같은 캐시키 충돌** → activeData/archivedData 가 먼저 resolve 된 쪽 데이터로 수렴(활성/보관 목록 교차오염 가능).
- **권고**: queryKey 에 status/params 포함(`projectKeys.list(wid, params)`).

### BUG-INBOX-PROMOTE-STUB `확정(carry-over)`
- inbox "✏️ 다른 프로젝트"(`inbox-item-card.tsx:275`) → "프로젝트 선택 기능은 준비 중입니다"(`:325`) 비기능 stub. (✅확정·🗑무시 정상.) (`p2-inbox-promote-stub.png`)
- **권고**: picker 구현 또는 버튼 임시 숨김.

---

## P3

### BUG-PERSONAL-INVITE-UX `확정 (P2→P3, silent-fail 주장 철회)`
- **확정분**: `settings/page.tsx:225`(+:157) InviteManager 가 `isAdminOrOwner` 만 게이트, `workspace.type==='personal'` 가드 없음 → 개인 WS 에 초대 UI 노출. BE 는 정상 403(`invite_service.py:60`).
- **철회분**: 초안의 "silent fail/에러토스트 없음"은 **코드 반증** — `members/hooks.ts:174 useCreateInvite.onError → toast.error` + `api-client.ts:33` 에러 전파 존재. 라이브 스냅샷이 토스트 타이밍을 놓친 것. → 잘못된 affordance(P3 polish)이지 데이터/보안 이슈 아님.
- **권고**: 개인 WS 면 초대 탭/UI hide.

### A11Y-AVATAR-LABEL `신규 (클러스터 축소 — 1건만 잔존)`
- **잔존(실)**: user avatar DropdownMenuTrigger 가 accessible name 없음 — `header.tsx:92`.
- **refuted(false positive)**: 검색바 버튼=visible text("팀 지식 검색…", :74) / dialog close=`sr-only "Close"`(`ui/dialog.tsx:75`) / Archive 토글=visible text(`sidebar.tsx:251`) → 모두 접근가능명 보유, 비대상. (초안 클러스터 과대 — 3평가자 지적.)
- **권고**: avatar 트리거에 aria-label.

### BUG-SEARCH-CURRENT-PROJECT-NOOP `신규` (3평가자 HOLDS UP)
- 글로벌 `/search` "현재 프로젝트" 탭이 local scopeTab 만 토글(`search-scope.tsx:26`), `searchFilter.projectId` 미설정(`rag/hooks.ts:51`) + activeProjectId 컨텍스트 없음 → 전체와 동일 결과. (대조: "선택한 소스"=정직 stub.)
- **권고**: 글로벌 search 에선 hide 또는 picker/안내.

### BUG-ARCHIVED-PROJECT-LEAK `신규·정적 (P3 확정, 캘리브레이션 일관화)`
- `projects/repository.py:46,68` `if status:` → status=None 이면 archived+completed 전체 반환(Channel A test PASS). **그러나 사용자 `/projects` 페이지는 status='active' 전송(`projects/page.tsx:17`) → 메인 그리드 무영향**. 라이브 확인(Archive 4 인데 그리드는 active 만). = **백엔드 기본 contract latent 갭**(P3), 사용자영향 낮음. (report/bugs P2↔P3 불일치 → P3 로 통일.)
- **권고**: list 기본을 active-only 또는 명시 status 요구(defense-in-depth).

### FE-PAGESIZE-PARAM-MISMATCH `신규 (codex 발굴, 코드 확인)`
- `projects/api.ts:38` 가 `searchParams.set("page_size", …)`(snake) 전송하나 BE `projects/router.py:50` 는 `alias="pageSize"`(camel) 기대 → **FE pageSize 무시, BE default 20 사용**. 영향 제한(FE 가 통상 20).
- **권고**: FE 가 `pageSize` 전송 또는 BE populate_by_name.

### LANDING-TEXT-WHITE `신규·nit (reframe)`
- 초안 "white-on-white 사라짐"은 **오진** — 내 라이트 랜딩 스샷(`p1-landing-loggedout-light.png`)상 CTA 정상(accent 배경에 흰텍스트 가독). 실제(경미): `hero-section.tsx:90`/`landing-nav.tsx:64`/`pricing/page.tsx:77` 의 흰텍스트가 accent 배경 대비 다소 낮음(특히 다크 랜딩 accent). → nit.
- **권고**: 필요 시 accent 대비 점검.

### OBS-VIEWER-VISIBILITY-BTN `신규·관찰`
- `project-detail.tsx:141-150` VisibilityBadge 가 viewer 에게도 렌더(onClick 가드로 다이얼로그는 차단하나 disabled 시각상태 없음).
- **권고**: admin+ 아니면 비대화형 배지.

### OBS-MEETING-ACTIONS-PROCESSING `신규·관찰`
- processing/failed 미팅에도 export 버튼 활성(`meeting-detail.tsx:156`) → 빈/실패 미팅 export 시 오해 산출(BUG-MEETING-FAILED-UI 와 결합, evaluator 가 "다소 과소평가" 지적).
- **권고**: 비-completed 시 export 비활성.

### A11Y-ICON-RAIL-768 `신규`
- `sidebar.tsx:318` collapse 시 `title=`(HTML title) 사용, aria-label 아님 + focus-visible 미명시(`:301-351`).
- **권고**: collapsed nav aria-label + focus-visible. (bottom-nav 는 visible text 보유 → 비대상.)

### UX-CMDK-GLYPH `신규·cosmetic`
- ⌘(U+2318) 가 Geist Mono 미포함 → 검색 단축키 배지 깨짐. **권고**: 폰트 fallback 또는 "Cmd+K" 텍스트.

### BL-DATA-HYGIENE-SEED `확정(carry-over)`
- ADR-022 webhook SKIP → 전 멤버 displayName "사용자"/email=""(fresh C 포함, WS명 "사용자의 개인 Kairos"). **권고**: lazy seed 시 Clerk JWT claims 동기화.

### BUG-MEMORY-WS-FILTER `정적(carry-over)`
- `memory/repository.py:55-95,139` 5 mutation PK-only WHERE(composite FK 없음). 현재 서비스 pre-validate 로 실 IDOR 없으나 2-layer 갭. **권고**: workspace_id WHERE 또는 composite FK.

### DESIGN-TOKEN-DRIFT (cluster) `신규·정적`
- 토큰 우회 하드코드(citation-badge `#A78BFA/#FBBF24`, action-kanban priority, today-feed 배지, `::selection{color:#fff}` globals.css:316) + 임의 px 타이포(`text-[10px]`) + 스켈레톤 3종 불일치 + 로딩 카피 불일치. **권고**: 단일 polish PR(토큰 var() 일원화 + 공용 Skeleton + 카피 통일).

---

## 버그 아님 / 종결
- **last-admin 가드 부재** — owner 존재 시 admin 0 허용(문서화 invariant 없음, codex 정합). last-owner 보호는 정상 403.
- **search "선택한 소스"** — 정직 stub("준비 중 — 전체 검색"). 수용.
- **bottom-nav aria-label / dialog-close / 검색버튼 / archive버튼 "부재"** — visible text 또는 sr-only 보유 → WCAG 통과(refuted).
- **text-secondary #8E8E93 대비** — AA pass(refuted, 명도계산 오류).
- **`/new` 탭 간 spacing**, **dark #EDEDEF on light** — 의도/정상(refuted).
- **max_uses 410 / expiry 410 / I-17 403 / 캐시 무효화 / last-owner 403 / 페이지네이션 contract** — Channel A PASS, 정상.
- **BUG-ROLE-ENUM-VALIDATION** — schema role pattern 검증 존재 → stale 종결.

---

## 이번 스윕 미커버 (evaluator 지적 — 후속 백로그)
정직한 범위 한계. 다음 스윕 권장:
1. **XSS/출력 이스케이프** — meeting title/note body/transcript/speaker 등 user 입력 렌더의 injection(LLM-trust-boundary invariant 미검).
2. **타 composite-key 동시성** — ProjectMember add / inbox promote 더블서밋 / action toggle 더블클릭 낙관 UI(같은 find-then-insert 패턴).
3. **기능적 a11y** — 키보드 tab순서/focus-trap/ESC-close/스크린리더(이번엔 정적 aria grep 만).
4. **네트워크 에러 상태** — offline/500/timeout 시 FE(React Query retry/stale) — 이번엔 R2 실패 1경로만.
5. **memory IDOR 실증** — cross-ws mutation 통합테스트(현재 정적 단정).
6. **invite 코드 brute-force/rate-limit**(12자 nanoid).
7. **롱콘텐츠/오버플로** — 긴 제목·100+ action item·긴 프로젝트명.
8. **prefers-reduced-motion** 양성 커버리지(globals.css:331 존재).
