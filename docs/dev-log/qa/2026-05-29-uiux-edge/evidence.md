# Kairos 2차 정검 (UI/UX + 엣지) — Evidence Log

날짜 2026-05-29. 메인 에이전트 MCP Playwright 라이브 + test DB 통합테스트 2채널. plan `~/.claude/plans/kairos-2-reactive-church.md`.

리뷰 게이트 = 빈컨텍스트 opus(6.5 GO-WITH-CHANGES) + codex(4.0 REVISE) → 18 결정 반영 plan v2. 사용자 결정 = 쓰기 test DB 격리(Option A).

---

## Phase 0 — 환경 (DONE)
- 운영 BE :8000 (→Neon, `/api/v1/health` 200) + FE :3000 기동. Docker 기동(test DB용).
- 로그인 = **A = d@e.com (owner)**. 활성 WS = "QA Cycle C Team" (id `7f9f446d-9b7f-4ae7-aa9b-ac861fb81b11`), 템플릿 프로젝트 3개(시작하기/아이디어/회의록) + Archive 3 + 멤버 1. **meetings 0 / notes 0** (API 확인).
- 테마 = next-themes `data-theme`, storageKey `theme`, defaultTheme dark. localStorage 조작+reload 로 스크립트 토글 가능.
- throwaway WS 생성은 Phase 2 착수 시(운영 오염 최소화).

## Phase 1 — UI/UX 전수 matrix (라이브, 운영 QA Cycle C Team)
스크린샷 `screenshots/p1-*` — {light-desktop, dark-desktop, mobile375, tablet768}.
- 캡처 라우트(11): dashboard, inbox, notes, projects, projects/[id], search, memory, settings, admin/recall-metrics, new, (actions→inbox redirect).
- **전 라우트 × 전 상태 console.error = 0** (prior 세션과 일치).
- 반응형 breakpoint 확인 — <768: bottom-nav(홈/프로젝트/추가/Inbox/메모)+사이드바 숨김. 768: 아이콘 전용 사이드바 rail(라벨 없음). desktop: 풀 사이드바.
- 메뉴 테마 토글 e128 동작. 다크 기본, 라이트 토글 정상.

### Phase 1 발견
| ID | 우선(잠정) | 발견 | 증거 | 근본원인(가정) |
|---|---|---|---|---|
| UX-NEW-GRID-375 | P2 | `/new` 콘텐츠 유형 3-col(회의녹음/노트작성/자료업로드) + 하위탭(오디오/직접녹음/텍스트)이 375px 에서 stack 안 됨 → 카드 ~110px 로 압착, 텍스트 어색 줄바꿈("노트 작 성","자료 업 로드"). 768/desktop 은 정상. | p1-new-mobile375.png vs p1-new-tablet768.png | `new/page.tsx` grid 가 mobile `grid-cols-1` breakpoint 부재(항상 3-col). [가정] |
| DATA-SEED-DISPLAYNAME | P3(=BL-DATA-HYGIENE-SEED 확정) | settings 멤버 목록에서 owner A(d@e.com)가 실명/이메일 없이 generic "사용자" + 아바타 "사"로 표시 | p1-settings-mobile375.png | ADR-022 webhook SKIP → Clerk displayName/email 미동기화 lazy seed. |
| UX-CMDK-GLYPH | P3/cosmetic [확인필요] | 검색바 ⌘K 단축키 배지가 "⌘" 글리프 대신 깨진 모양("XK"류)으로 보임 | p1-dashboard-light-desktop.png 등 | geist mono 폰트가 U+2318 미포함 가능. 실폰트 vs 스크린샷렌더 구분 필요. |
| A11Y-ICON-RAIL-768 | P3 | 768px 사이드바 아이콘 전용 rail — 보이는 라벨 없음(아이콘만). 키보드/스크린리더 라벨 확인 필요 | p1-dashboard-tablet768.png | 사이드바 collapse 시 라벨 제거 + aria-label 검증 필요. |

(다크모드 컨테이너 표면/대비, 빈/로딩/에러 상태 품질, 마이크로인터랙션 등 심층 시각 비평 = Phase 5 Workflow lens 가 스크린샷+코드로 수행.)

## Phase 2 — 미실행 기능 플로우 라이브 실행 (운영 throwaway WS "QA-EDGE-S28b" id `47f0f895-...`)
신규 팀 WS 생성 시 템플릿 3프로젝트 auto-seed 확인(시작하기/아이디어/회의록).

| 플로우 | 결과 | 증거 |
|---|---|---|
| 텍스트 미팅 생성→AI 분석 | ✅ 완료. 결정사항 2건·주제·액션 3건 정확 추출(할루시네이션 0). status uploading→completed. | meeting `61d1b30f-...`, p2-meeting-processing.png / p2-meeting-completed.png |
| 노트 생성 | ✅ 저장됨(`3ad269da-...`) "메모가 저장되었습니다" | |
| **노트 팀으로 올리기**(promote) | ✅ 실행. 다이얼로그 "팀으로 올리기 — 원본 유지", 대상 콤보 = QA Cycle C Team 만(개인 WS 제외, I-19 정합). 실행 토스트 "노트 복사 완료(임베딩 재생성 중)" | |
| **Inbox ✅확정**(promote) | ✅ 실행. "→ 프로젝트" + "↩ 되돌리기" 낙관 UI. undo 복원도 정상. | p2-inbox-populated.png |
| **Inbox ✏️다른 프로젝트** | ✅ stub 확정(BUG-INBOX-PROMOTE-STUB) — inline "프로젝트를 선택하세요 / 프로젝트 선택 기능은 준비 중입니다." 비기능 | p2-inbox-promote-stub.png |
| **Inbox 🗑무시**(dismiss) | ✅ 실행. "항목을 무시했습니다" 토스트, 항목 제거, 배지 0, 빈상태 | |
| **Action item 토글** | ✅ 실행. meeting-detail 액션탭 체크박스로 0/3→1/3, persist. (주의 — 토글은 meeting-detail 액션탭엔 있음. scout 의 "action-list quick-toggle 부재"는 별도 surface /actions 한정) | |
| **Meeting export MD** | ✅ 실행. 파일 다운로드 + 내용 완전(요약/결정/액션 `[x]` 토글반영/트랜스크립트). | `.playwright-mcp/QA-엣지정검-스프린트-킥오프.md` (1315B) |
| Meeting export JSON | (진행 중) | |
| Meeting export JSON | ✅ 실행. 파일 다운로드 + JSON 완전(id/status/transcript/summary.keyDecisions/topics/action) | `.playwright-mcp/QA-...킥오프.json` |
| **실패 미팅 유도+UI** | ✅ fake fileKey 미팅(`ad17a978-...`) → pipeline R2 fetch 실패 → status=**failed**(badge "실패"). **그러나 UI 결함 발견(아래 BUG-MEETING-FAILED-UI)** | p2-meeting-failed.png |
| **Search 전체 scope** | ✅ RAG 정확+인용 "소스 2건"(다크모드/RBAC 결정 정확 인용) | p2-search-result.png |
| **Search 유형필터 노트** | ✅ 작동. 미팅전용 질의 → "관련 정보를 찾지 못했습니다" + 소스=노트만(미팅 제외). **빈결과 graceful** 동시확인 | |
| **Search 선택한 소스** | ✅ honest stub "소스 선택 기능 준비 중 — 현재는 전체 워크스페이스에서 검색합니다" | |
| **오디오 실업로드 E2E** | ✅ 실 MP3(`~/Downloads/test-meeting.mp3` 56kbps mono) 업로드→meeting `64a34b74-...`→R2→Whisper→Gemini→embed→**완료**. 요약 "CMS 고도화 프로젝트 킥오프... JWT 인증 도입... 3월 완료" 핵심결정 2건 주제 2건 — 실오디오 내용 정합. 사용자 녹음 불필요(repo sample 사용). | p2-audio-processing.png / p2-audio-completed.png |

**Phase 2 종합: blind spot 2 전 플로우 실행 완료** — inbox promote/dismiss/stub · note 생성/팀올리기 · meeting export MD+JSON · action 토글 · 오디오 E2E · 실패미팅 · search scope/type/빈결과. 단순열람 아닌 실제 실행.

### Phase 3 Channel B 셋업 (as A, 운영 throwaway WS)
- invite 생성 — code `rWlqqPzniSRb`, role **admin**, 7일 만료, visibility 공개. (역할 picker = Admin/Member/Viewer 설명 포함 정상)
- private 프로젝트 생성 — `cd26d682-223d-4c34-a3c5-befb8313da40` visibility=private (B 미추가 상태).
- 효율 전략: B 가 admin 으로 invite 수락 → admin UI 관찰 → A 가 demote(admin→viewer, 캐시무효화 라이브 동시검증)+private 멤버 추가 → B viewer UI + private positive 관찰. (계정전환 3회)
- ⚠️ Project create API 필드 = `title`(not `name`); `name` 보내면 422. [관찰]

### Phase 2 발견 (search)
| ID | 우선 | 발견 | 증거 | 근본원인 |
|---|---|---|---|---|
| BUG-SEARCH-CURRENT-PROJECT-NOOP | P3 | 글로벌 `/search` 의 "현재 프로젝트" scope 탭은 현재 프로젝트 컨텍스트 없음 + 프로젝트 picker 없음 → 선택해도 워크스페이스 전체 결과 그대로 반환(no-op). **무메시지 silent** (대조: "선택한 소스"는 "준비 중 — 전체에서 검색" 정직 안내). 일관성 결여+오해소지. | 라이브 — 현재프로젝트 active 상태 "통합테스트 담당자" 질의가 전체와 동일 결과 | codex F-10: search-scope.tsx 가 local scopeTab 만 바꾸고 searchFilter.projectId 미설정. 글로벌 search 에선 hide 또는 picker/메시지 필요. |

### Phase 2 발견 (신규)
| ID | 우선 | 발견 | 증거 | 근본원인 |
|---|---|---|---|---|
| BUG-MEETING-FAILED-UI | **P2** | status="failed"(badge "실패") 미팅이 본문에 **generic 빈 placeholder "요약 정보가 없습니다 / AI 분석이 완료되면 요약이 자동으로 생성됩니다"** 를 렌더 — **오해소지**(영구 실패인데 "곧 생성됨"으로 보임). **retry 버튼 없음(BL-S27c-4 확정)·copy/error-detail 없음(BL-S27c-5 확정)·error 미표시.** 게다가 API `errorMessage: null` — R2 실패 경로가 error_message 미기록 → 표시할 진단정보 자체가 없음. 내보내기 버튼은 빈 미팅에도 노출(빈 export 가능). | p2-meeting-failed.png + API GET status=failed/errorMessage=null | meeting-detail.tsx 가 failed 상태에 dedicated 실패뷰 없이 completed-empty 분기로 fall-through + pipeline R2 실패 except 가 error_message 미설정. [가정→확인] |
| OBS-MEETING-ACTIONS-PROCESSING | P3 | meeting-detail 내보내기/워크스페이스 이동 버튼이 processing/failed 상태에서도 활성 노출(promote 는 BE 가 completed/failed 만 허용하므로 무해, export 는 빈 산출). 회색처리/숨김 권장 | p2-meeting-processing.png | UI 상태별 버튼 가드 부재. |

발견: meeting-detail 워크스페이스 이동·내보내기 버튼이 **processing(업로드 중) 상태에서도 노출** — codex P2-1 fix 는 promote 시 status guard(completed/failed 만) 백엔드 차단이므로 UI 노출은 무해하나 회색처리 권장 여지. [관찰]

## Phase 3 Channel A — 결정적 통합테스트 (test DB, 백그라운드 agent, 운영 무오염) ✅
파일 `backend/tests/qa_edge/test_rbac_edges_s28b.py` (12 tests). 전체 스위트 **524 pass / 1 skip, 회귀 0**. TestContainers pgvector pg16(운영 Neon 무관).

| 항목 | 결과 | 근거 |
|---|---|---|
| 캐시 무효화(이전 P1 fix) | ✅ wired. update_member_role/remove_member 가 invalidate_member_cache 호출(`invite_service.py:245-247,271-274`), warm 후 getter None — 60s stale window 없음 | |
| invite max_uses 소진 → 410 | ✅. **nuance**: max_uses=1 은 1차 수락 시 auto-deactivate(195-196) → 2차는 is_active=False 분기 먼저 → "비활성화된 초대 링크입니다" (둘 다 410, `invite_router.py:95-96`) | |
| invite 만료 → 410 | ✅ crafted 과거 expires_at → "만료된 초대 링크입니다" 410 | |
| I-17 cross-ws ProjectMember add → 403 | ✅ CrossWorkspaceMemberError "해당 사용자가 워크스페이스 멤버가 아닙니다" (`projects/service.py:197-199`) | |
| **BUG-WS-MEMBER-UNIQUE** | ✅ **갭 확정**. workspace_members(workspace_id,user_id) UNIQUE 부재(PK=id only, idx non-unique BL-036). asyncio N=5 → row 1 (app find_member 가드가 단일이벤트루프 직렬화로 우연히 성립). **강제 interleave 2 트랜잭션 → 중복 row 2** = 멀티워커 실재 갭 | |
| last-owner 보호 | ✅ 403 CannotModifyOwnerError (demote/remove 둘다). **last-admin 가드 없음** — owner 존재 시 admin 0 도달 가능(codex 정합, 버그 아님 문서화) | |

⚠️ 테스트파일 pyright 경고(session.exec(text()) 타입, utcnow deprecated) — 런타임 PASS, QA 증거용. 커밋 여부 Phase 8 결정.

## Phase 3 Channel B — 라이브 viewer/admin + private positive (운영, 계정전환 A↔B 3회)
셋업: invite admin → B 수락 → admin 관찰 → A 가 API 로 demote(admin→viewer, 200)+private project member add(201) → B viewer 관찰.

| 검증 | 결과 | 증거 |
|---|---|---|
| **invite 수락(admin)** | ✅ /invite/rWlqqPzniSRb "admin 역할로 참여" → 수락 → B admin 멤버. (owner displayName "사용자님이 초대했습니다" 노출=seed hygiene) | p3-invite-accept.png |
| **admin UI 라이브** | ✅ settings "admin · 멤버 2" + 멤버/초대/Audit 전 탭 노출 + 멤버 kebab(owner 행엔 없음). admin 이 private project 사이드바에 보임(admin=전 visibility). | p3-admin-settings.png |
| admin 멤버 kebab | ✅ "멤버 제거"만 노출(역할변경 없음=owner-only 정합). **단 B 자기행에도 노출 → admin self-removal 가능**(codex F-12 no-last-admin-guard UI 노출) | |
| **demote admin→viewer** | ✅ PATCH 200 (`{role:'viewer'}` accept). | |
| **private ProjectMember positive** | ✅ B(viewer+멤버)가 private "QA Private 프로젝트"(비공개) 접근 성공 — Visibility 비공개 + Project Members 렌더. **지난 세션 미검증(positive) 케이스 확정.** | p3-viewer-private-positive.png |
| **viewer UI 제약 라이브** | ✅ /projects "새 프로젝트" 버튼 없음 + 사이드바 "빠른메모"/"+추가" 숨김 + /new → 권한게이트 "콘텐츠를 추가하려면 Member 이상 권한이 필요합니다"+돌아가기. graceful. | p3-viewer-projects.png / p3-viewer-new.png |
| cache 무효화 라이브 | (smoke) B 재로그인 후 role=viewer 즉시 정합(stale 없음). 결정적 증거=Channel A 캐시테스트. | |

### Phase 3 발견
| ID | 우선 | 발견 | 근본원인 |
|---|---|---|---|
| OBS-VIEWER-VISIBILITY-BTN | P3 | private project 상세에서 viewer B 에게 "Visibility: 비공개" 토글 버튼 노출(visibility 변경은 admin+ → 클릭 시 403 예상). 읽기전용에 변경 컨트롤 노출 = 경미 UI 게이팅 누락 | visibility 버튼이 role-gate 없이 렌더. [관찰] |
| (corroborate) BUG-WS-MEMBER-UNIQUE·last-admin | — | Channel A 결정적 확정 + 본 라이브에서 admin self-removal kebab 노출로 UI 경로 corroborate | |

## Phase 4 — 데이터 상태 엣지
| 검증 | 결과 | 증거 |
|---|---|---|
| **신규 onboarding(C=f@e.com 첫 로그인)** | ✅ 개인 WS "사용자의 개인 Kairos" auto-create(lazy seed OK, 0 error). **프로젝트 없음** — 개인 WS 는 템플릿 미시드(팀 WS 는 3개 시드)=비대칭. displayName "사용자"(BL-DATA-HYGIENE-SEED 확정, fresh account). | p4-onboarding-C-dashboard.png |
| onboarding 빈상태 품질 | [관찰] 빈 dashboard 가 populated 와 동일 "추천 질문"(최근 회의 결정사항 등) 노출 — 데이터 0 인 신규 user 가 답 못얻는 질문 제시, "시작하기" 가이드 약함. first-run UX gap. | |
| **BUG-PERSONAL-INVITE-UX** | ✅ **확정+악화**. 개인 WS settings 에 초대탭+"초대 링크 생성"+전체 다이얼로그 노출 → 생성 클릭 → POST `/invites` **403**(I-19 BE 정상) **그러나 다이얼로그 유지+user-facing 에러 토스트 없음, console 403 만**(silent fail). 개인 WS 는 초대 UI 전체 hide 필요. | p4-personal-settings-C.png + console 403 (ws 4f4aeeff) |
| **페이지네이션**(Channel A agent, test DB) | ✅ shape `{items,total,page,pageSize,hasNext}` (`notes/service.py:129-135`, hasNext=page*size<total). 25 노트 → p1=20/total25/hasNext true, p2=5/hasNext false. projects 동일 contract. | test_data_state_s28b.py |
| **archived 프로젝트 list-filter**(agent, test DB) | ✅ **REAL 발견**: status 미지정 시 archived 프로젝트가 기본 `/projects` 목록에 **노출됨**(`repository.py:46` `if status:` 가드 → None 이면 전 status 반환, count 도 동일). status=active/archived 필터는 정상. **completed 상태도 동일 누출**. | test_data_state_s28b.py |
| processing/error 미팅 | ✅ Phase 2 에서 text processing(업로드중)·audio processing·failed(실패) 상태 모두 확인 | p2-meeting-processing/audio-processing/meeting-failed.png |

### Phase 4 발견
| ID | 우선 | 발견 | 근본원인 |
|---|---|---|---|
| BUG-ARCHIVED-PROJECT-LEAK | P2 | archived(+completed) 프로젝트가 status 필터 없는 기본 `/projects` 목록·count 에 노출(자동제외 안 함). 사용자가 종료/보관한 프로젝트가 활성 그리드에 섞임 | `projects/repository.py:46,55-70` `if status:` 가드 — 기본 목록에 active-only 필터 부재. FE `/projects` 가 status=active 미전송. |
| (refine) BUG-PERSONAL-INVITE-UX | P2 | 위 표 — silent 403(에러 토스트 없음) 추가 악화 | 개인 WS type 체크로 초대 UI 미렌더 필요 + mutation 에러 토스트 누락 |
| (confirm) BL-DATA-HYGIENE-SEED | P3 | fresh user C 도 email 미동기화 → displayName "사용자" / WS명 "사용자의 개인 Kairos" | ADR-022 webhook SKIP lazy seed |

## 별도 P0 — 커밋된 시크릿 (QA 블로커와 분리, 지난 세션 carry-over 재확인)
| ID | 우선 | 발견 | 조치 |
|---|---|---|---|
| SEC-CLERK-SECRET-COMMITTED | **P0** | 실 Clerk **dev** secret `CLERK_SECRET_KEY=sk_test_mvhptL…` 가 `docs/superpowers/specs/2026-04-02-sprint1-fe-api-design.md:30` 에 평문 커밋(여전히 존재). dev 키라 영향 제한적이나 repo private 유지 전제 + git 히스토리 잔존. | 키 rotation + 파일에서 제거 + git 히스토리 스크럽(BFG/filter-repo). public 전환 금지 재확인. |
