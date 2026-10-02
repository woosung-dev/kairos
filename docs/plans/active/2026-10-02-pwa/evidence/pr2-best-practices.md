# PR-2 best-practices 게이트 (GATE-PR2)

> **최종 결과: PASS — FAIL 0** (1차 REVISE·FAIL 1 → GEN-P2-3 수정 → 재게이트 PASS). 1차 보고는 원문 그대로 두고, 수정 내역과 재게이트 결과를 아래에 덧붙였다.

## 1차 게이트 (GATE-PR2)

> 2026-10-02 · 기준 = `vercel-react-best-practices` 스킬 (규칙 파일 35개 Read) · 대상 = `git diff origin/main...HEAD -- apps/web` (브랜치 `claude/pwa-push`, HEAD `1063903`, base `ef79e3c`) · 판정자 = 새 Evaluator (cold context, 읽기 전용)
> 번들 근거 = HEAD 빌드 `apps/web/.next` (BUILD_ID `jJAK7HEOWb_o5CEeqraLg`, 17:08, HEAD 커밋 17:02 이후)와 **기준선 = main 체크아웃의 기존 빌드** `kairos/apps/web/.next` (BUILD_ID `PcPpS_SvsOcN4yMWXprT_`, 16:22, `push-config` 문자열 0건). Turbopack 청크는 scratchpad node 스크립트로 모듈 단위까지 쪼개서 쟀다. 빌드·서버·브라우저는 쓰지 않았다.
> **결과: REVISE — FAIL 1** (35개 규칙 판정: FAIL 1 · PASS 27 · N/A 7)

### FAIL

#### FAIL-1 `bundle-conditional`: 소유자 표식의 zod 가 전체 zod(로케일 포함)를 `(app)` 셸 공용 청크로 끌어온다

- **원인 줄**: `apps/web/src/features/push/marker.ts:7` `import { z } from "zod/v4"`. 쓰는 곳은 2필드 스키마(`:11-14`)와 `safeParse` 1회(`:33`)뿐이다.
- **셸에 닿는 경로**: 두 갈래다.
  - `app/(app)/layout.tsx:5,14` `<PushSync />` → `features/push/hooks.ts:13-21` → `flows.ts:12-18` → `marker.ts:7`
  - `components/layout/header.tsx:13,33` `usePushLogoutCleanup` → 같은 `hooks.ts` 모듈
- **산출물 근거 (모듈 단위)**:
  - push 모듈(`1xdz26okyu-9u.js` 안의 id 43873, 5,689 B min / 2,404 B gz)이 `e.i(77829)` 로 zod 를 import 한다.
  - 77829 는 zod 4.6.5 전체다: 364,158 B min / 90,836 B gz. 로케일 문자열(`Ungültige`·`無効`)과 `toJSONSchema` 가 들어 있다.
  - zod 는 청크 `3uv5qtwtf2jn_.js` 에 있다 (391,191 B / 89.5 KB gz). 이 청크는 기준선 빌드와 **byte 동일**하다 (`cmp`).
  - HEAD 의 `(app)/layout` entryJSFiles 15개 청크 가운데 zod 를 import 하는 모듈은 **push 모듈 하나뿐**이다.
  - 기준선의 layout 그룹(14개 청크)에는 `3uv5qtwtf2jn_.js` 가 없다. 기준선에서 zod 를 정적으로 받는 라우트는 `/dashboard`·`/projects`·`/projects/[id]` 3개였다.
- **영향 (라우트별 정적 JS gz 합계, 기준선 → HEAD)**:

| 대상 | 기준선 | HEAD | Δ |
|---|---|---|---|
| `(app)` layout 그룹 | 142,244 | 235,793 | **+93,549 (+66%)** |
| `/meetings/[id]` (알림 클릭 착지) | 154,012 | 247,628 | +93,616 (+61%) |
| `/inbox` · `/actions` · `/notes` · `/new` · `/memory` · `/search` · `/admin/recall-metrics` · `/notes/[id]` | — | — | 각 약 +93.5 KB |
| `/settings` | 183,461 | 278,067 | +94,606 |
| `/dashboard` · `/projects` · `/projects/[id]` (zod 기존) | — | — | 각 +2,652 |

  - push 모듈 팩토리가 맨 위에서 `e.i(77829)` 를 부른다. 그래서 zod 는 받기만 하는 게 아니라 셸 hydration 때 파싱·평가까지 된다.
  - push 를 한 번도 켜지 않은 사용자도 모든 인증 라우트에서 이 비용을 낸다.
  - 이 레포는 이미 "(app) 공용 청크에서 무거운 것을 빼낸다" 는 선례를 두고 있다 (`components/layout/panel-layout.tsx:14-16` PR-3 c1).
- **수정안** — 권장은 (a).
  - (a) 표식 검증을 손으로 쓴 타입 가드로 바꾼다.
    - 같은 PR 의 `lib/pwa/push-notification.ts:61-84` 와 같은 방식으로, UUID 정규식 + `typeof` 로 판정한다.
    - `pushOwnerMarkerSchema` 는 다른 importer 가 0개다 (grep). 파싱 실패를 "없음" 으로 보는 의미는 그대로 둔다.
    - **[확인 필요]** 스펙 문구도 같이 바뀐다: `docs/requirements/pwa.md:320` ("zod v4 스키마로 파싱"), `docs/adr/035-web-push.md:103` ("zod 파싱").
  - (b) `zod/mini` 로 바꾼다.
    - 트리셰이킹이 되는 v4 API 다.
    - 그러나 `apps/web/AGENTS.md` §3 의 "`import { z } from "zod/v4"` 필수" 와 문자 그대로 충돌한다.
    - Turbopack 이 mini 네임스페이스를 얼마나 털어내는지 측정하지 못했다.
  - (c) push 흐름 전체를 `import()` 로 미룬다 (PushSync effect 안 + header onClick 안).
    - zod 는 여전히 모든 라우트에서 받지만 hydration 뒤로 밀린다.
    - 셋 중 침습도는 가장 높고 효과는 부분적이다.
- **수정 뒤 수용 기준**:
  - 재빌드 후 `(app)/layout` entryJSFiles 에 zod 를 담은 청크가 없다.
  - layout 그룹 gz ≈ 142 KB + push 약 2.4 KB.
  - `/meetings/[id]` 합계 ≈ 156 KB.

### 규칙별 판정

| 규칙 | 판정 | 근거 (file:line) | 메모 |
|---|---|---|---|
| `bundle-conditional` | **FAIL** | `features/push/marker.ts:7` | FAIL-1 |
| `bundle-barrel-imports` | PASS | `app/(app)/layout.tsx:5` · `header.tsx:13` · `settings/page.tsx:23-24` · `push/*` 상대 import | 레포 안 import 는 모두 파일 직접 경로이고 `features/push/index.ts` barrel 은 없다. lucide `Bell`·`Share` 는 named import 다 (Next 기본 optimizePackageImports 대상). zod `z` 네임스페이스가 로케일까지 통째로 실리는 건 FAIL-1 의 메커니즘이라 따로 세지 않았다 |
| `bundle-dynamic-imports` | PASS | `settings/page.tsx:24,420-424` | 설정 패널 문구는 `0e_n1-cyz71x-.js` 에만 있고, 이 청크는 settings manifest 에만 나온다. `PushSync` 는 null 렌더라 무거운 컴포넌트가 없다. 다만 설정 전용 코드가 일부 셸에 섞인다 (경미 1) |
| `bundle-analyzable-paths` | PASS | `lib/pwa/sw.ts:15` · `service-worker-registrar.tsx:18` | 상대 리터럴 import 이고 registrar 의 `new URL` 리터럴도 그대로다. `static/service-worker/sw.js` (14,236 B / 5,887 B gz, sha256 앞 16자 `72f56391d4abdfec`) 에 push·notificationclick·openWindow 가 들어 있고 zod 는 0이다 |
| `bundle-defer-third-party` | N/A | — | 새 서드파티가 없다 (sonner·react-query·lucide 는 원래 셸에 있다) |
| `async-parallel` | PASS | `flows.ts:202-208` · `:250-253` · `meetings/[id]/page.tsx:10` | 로그아웃 ①∥② 는 `Promise.allSettled` 이고 전체가 3초 상한이다. 키 불일치 정리도 allSettled 다. 페이지는 `Promise.all([params, searchParams])`. header 의 정리 → `signOut` 순차는 토큰 의존이라 필수다 (`header.tsx:175-181`) |
| `async-defer-await` | PASS | `flows.ts:161-165` · `:224-235` | 켜기의 등록 → 권한 순서는 스펙 §5.5 가 정한 것이다. 동기화는 표식(동기 읽기)을 먼저 읽고, 네트워크는 분기 안에서만 나간다 |
| `async-cheap-condition-before-await` | PASS | `hooks.ts:52` · `flows.ts:135-136,140` | 싼 동기 가드(meId·settled·lastSyncedMeId, ios·지원 판정)가 await 보다 앞이다. `denied` 판정이 `getRegistration()` 뒤에 오는 건 의도된 우선순위다 ("등록 없음 = 사용 불가" 가 먼저, 켜기 흐름과 같은 순서). `getRegistration` 은 네트워크가 아닌 로컬 호출이다 |
| `client-event-listeners` | PASS | `hooks.ts:86,93-95` · `sw.ts:34,41` | `controllerchange` 는 `{once:true}` 이고 cleanup 이 같은 참조를 지운다. 설정 패널은 인스턴스가 하나이고, 같은 함수·옵션을 다시 등록하면 DOM 이 중복을 걸러 준다. SW 리스너는 최상위에서 1회 등록한다 |
| `client-localstorage-schema` | PASS | `marker.ts:9,11-14,20-63` | 키에 버전(`kairos:push:v1`)이 있고 필드는 2개다. 모든 접근이 try/catch 이고 파싱 실패는 "없음" 이다 |
| `client-swr-dedup` | PASS | `hooks.ts:23-32` · `settings/page.tsx:75` | `pushKeys.config()` 하나를 셸(PushSync)과 설정 페이지가 같이 쓴다 → 요청 1회. staleTime 5분, retry false. 워크스페이스 전환 때 이 키까지 무효화되는 건 경미 2 |
| `client-passive-event-listeners` | N/A | — | scroll·touch·wheel 리스너가 없다 |
| `rerender-move-effect-to-event` | PASS | `hooks.ts:99-119` ← `push-settings-panel.tsx:53` · `flows.ts:63-64,163` | 권한 요청은 토글 onClick → `enablePush` 에서만 한다. 마운트 effect 는 상태 판정만 한다 (`resolvePushDeviceState` 는 권한을 요청하지 않는다). 딥링크 effect 는 사용자 동작이 아니라 URL 동기화다 |
| `rerender-derived-state-no-effect` | PASS | `push-settings-panel.tsx:25-26` · `workspaces/hooks.ts:174-183,213` | `isOn`·`isToggleDisabled`·`decision`·`isSettled` 는 렌더 중에 계산한다. effect 의 setState 는 외부 시스템 비동기 결과뿐이다 (`hooks.ts:80-82`) |
| `rerender-dependencies` | PASS | `hooks.ts:55,97` · `workspaces/hooks.ts:201-213` | deps 는 `api`(`useMemo([])`, `use-api-client.ts:79`)·문자열·boolean, store setter·queryClient·router 같은 안정 참조다 |
| `rerender-functional-setstate` | PASS | `hooks.ts:101,107,112,117` | 상수나 await 결과로만 set 하고 이전 값에 의존하지 않는다 |
| `rerender-defer-reads` | PASS | `workspaces/hooks.ts:167,192` | `ownerUserId` 를 구독하지만 effect 안에서만 쓴다. 바뀌는 일이 드물어 영향이 미미하다 (경미 4) |
| `rerender-no-inline-components` | PASS | `push-settings-panel.tsx` · `ios-install-hint.tsx` · `meeting-detail.tsx` | 컴포넌트 안에서 컴포넌트를 정의하지 않는다 |
| `rerender-derived-state` | N/A | — | 연속값 구독이 없다 |
| `rerender-transitions` | N/A | — | 빈번한 비긴급 갱신이 없다 |
| `advanced-init-once` | PASS | `hooks.ts:37,52-53` | 모듈 가드를 계정 id 로 둔다. StrictMode 에서 effect 가 두 번 돌아도 동기화는 1회이고, 계정 전환 시 다시 도는 것은 의도다 (스펙 §5.5 EVAL-P2-1 D3) |
| `advanced-event-handler-refs` | N/A | — | effect 에 넘어오는 handler prop 이 없다. `evaluate` 는 effect 지역 클로저다 |
| `advanced-use-latest` | N/A | `hooks.ts:51-55` | callback prop 이 없다. `vapidPublicKey` 가 바뀌어 effect 가 다시 돌아도 가드에서 즉시 return 한다 (재구독 0) |
| `advanced-effect-event-deps` | N/A | — | `useEffectEvent` 를 쓰지 않는다 |
| `rendering-conditional-render` | PASS | `settings/page.tsx:217,420` · `push-settings-panel.tsx:81` | `isPushEnabled` 는 `=== true` 로 만든 boolean 이고 패널은 삼항이다 |
| `rendering-hydration-no-flicker` | PASS | `utils.ts:61` (호출처 `hooks.ts:79` effect) · `flows.ts:59` (effect·핸들러 안) | navigator·Notification·matchMedia·localStorage 는 effect·핸들러 안에서만 읽는다. 첫 렌더는 서버·클라 모두 "loading" 이다. 서버 데이터로 인한 탭 깜빡임은 경미 3 |
| `rendering-hydration-suppress-warning` | PASS | — | diff 에 `suppressHydrationWarning`·`dangerouslySetInnerHTML` 이 0건이다 (grep) |
| `rendering-hoist-jsx` | PASS | `push-settings-panel.tsx:9-16` | `STATUS_TEXT` 를 모듈로 끌어올렸다. 큰 정적 SVG 는 없다 |
| `rendering-usetransition-loading` | PASS | `hooks.ts:72,100-118` | 수동 `isBusy` 는 `finally` 에서 원복하고 재진입 가드도 겸한다. 바꿔야 할 구체적 영향이 없다 (경미 5) |
| `server-serialization` | PASS | `meetings/[id]/page.tsx:13` · `(app)/layout.tsx:14` | RSC → client 로 넘어가는 건 문자열 2개와 prop 0개다. 설정 페이지는 client 라 패널 prop 은 RSC 경계가 아니다 |
| `server-no-shared-module-state` | PASS | SSR 청크 `server/chunks/ssr/_034c1ju._.js` | `let G=null`(lastSyncedMeId)은 `useEffect` 콜백 안에서만 대입된다. `new Map`(pendingDeletes)은 effect·핸들러에서 부르는 함수 안에서만 바뀐다. Fizz 는 effect 를 실행하지 않아 요청 데이터가 남지 않는다 |
| `js-early-exit` | PASS | `flows.ts:135-147,161-165,227-260` · `workspaces/utils.ts:91-107` | 판정 순서대로 일찍 return 한다 |
| `js-hoist-regexp` | PASS | `utils.ts:89` · `workspaces/utils.ts:63` · `push-notification.ts:15-17` | 렌더 경로(`resolveWorkspaceDeepLink`)는 모듈 정규식을 쓴다. `utils.ts:8-9,21` 리터럴은 흐름당 1회 호출이라 렌더 경로가 아니다 |
| `js-cache-storage` | PASS | `marker.ts:58` · `flows.ts:262` | 흐름당 읽기 3회 이하다. 다시 읽는 건 다른 탭과의 compare-and-delete 를 위한 의도라, 캐시하면 CAS 의미가 깨진다 |
| `js-set-map-lookups` | PASS | `flows.ts:82` · `workspaces/utils.ts:100,104` | 진행 중 DELETE 는 Map 이다. 워크스페이스 목록 `some`·`find` 는 렌더당 1회이고 목록이 작다 |

### 같은 라운드에서 확인한 것 (요지)

- **청크 배치**:
  - push 흐름 모듈은 셸 공용 청크 `1xdz26okyu-9u.js` 에 있다. 이 청크는 13개 `(app)` 라우트 manifest 전부에 나온다.
  - 설정 패널 청크 `0e_n1-cyz71x-.js` 는 settings manifest 에만 나온다.
  - 딥링크 toast 문구는 workspaces 청크 3개에 있다.
- **SW**:
  - `sw.js` 에 zod·패키지 코드가 0이다.
  - PR-1 경미 1 의 `static/media/sw.*.ts` 원본 노출은 이어진다: `sw.0s_zub2dizxgo.ts` 2,358 B (PR-1 때 1,770 B).
  - `push-notification.ts` 원본은 노출되지 않는다.
- **SSR 모듈 상태**: lastSyncedMeId·pendingDeletes 대입은 effect·함수 안에서만 일어난다 (위 표).
- **설정**: React Compiler 미설정 (`next.config.ts`·`package.json` grep 0). 전역 QueryClient 는 staleTime 60s · refetchOnWindowFocus false (`lib/query-client.tsx:13,23`).

### 경미 사항 (게이트 판정과 별개, 후속 처리)

1. **설정 전용 코드가 셸에 실린다.** `features/push/hooks.ts` 가 한 모듈이라 `usePushSettings`·`enablePush`·`resolvePushDeviceState`(약 2.5 KB min / 1.2 KB gz)가 셸 청크에 들어간다.
   - `usePushSettings` 를 별도 파일로 떼면 설정 청크로 내려간다. FAIL-1 수정 때 같이 하면 싸다.
2. **워크스페이스 전환마다 push-config 를 다시 받는다.** `workspaces/utils.ts:54-56` predicate 는 `["workspaces","list"]` 만 남기므로 사용자 단위인 `["push","config"]` 도 무효화된다.
   - 전환·딥링크 전환 1회마다 `GET /users/me/push-config` 가 다시 나간다 (PushSync observer 가 활성).
   - 비용은 작다. 다만 predicate 를 공유하므로 (스펙 "복제 금지") 고치면 WorkspaceSwitcher 에도 같이 적용된다.
3. **`/settings?tab=notifications` 콜드 로드 때 탭이 한 번 바뀐다.** API-001 응답 전에는 `activeTab` 이 `members` 로 떨어졌다가 응답 뒤 `notifications` 로 바뀐다 (`settings/page.tsx:88-93`).
   - 기존 `integrations`/`isOwner` 와 같은 패턴이다. 알림 딥링크는 회의 상세로 가므로 실사용 노출은 낮다.
4. **`ownerUserId` 구독은 줄일 수 있다.** `useWorkspaceDeepLink` 가 구독하는 `ownerUserId` 는 effect 안의 `useWorkspaceStore.getState()` 로 바꿀 수 있다 (`rerender-defer-reads`). 영향은 미미하다.
5. **`useTransition` 으로 바꿀 필요는 없다.** `usePushSettings` 의 수동 `isBusy` 를 `useTransition` 으로 바꿀 이유가 없다. React 19 에선 await 뒤 setState 를 다시 `startTransition` 으로 감싸야 해서 오히려 복잡해진다.
6. **`lastSyncedMeId` 를 로그아웃 때 초기화하지 않는다** [가정 — sign-in 이 soft navigation 일 때만].
   - 같은 계정이 같은 JS 수명 안에서 다시 로그인하면 동기화를 건너뛴다.
   - 문제가 되는 건 로그아웃 때 ①·② 가 모두 실패(오프라인)한 경우다. 그때 다음 전체 로드까지 이 기기가 푸시를 받는데, 설정 화면은 '꺼짐'으로 보인다 (표식이 삭제됐으므로).
   - `usePushLogoutCleanup` 에서 가드를 `null` 로 되돌리면 막힌다.
7. **PR-1 경미 1 의 연장.** sw.ts 원본이 `/_next/static/media/` 로 공개 서빙되는 상태가 이어진다. 이제 push import 줄이 들어 있지만 비밀값은 없다.

### 확인 못 한 것

- **기준선 빌드의 정확한 커밋**: main 체크아웃 `.next` 는 2026-10-02 16:22 빌드다. `ef79e3c`(16:31 머지) 직전 main 으로 보이지만 커밋을 대조하지 못했다 [가정].
  - zod 청크는 byte 동일하고 zod 버전도 4.6.5 로 같다. 그래서 FAIL-1 의 zod 몫(약 89.5–91 KB gz) 차이는 그대로 유효하다.
  - 나머지 수 KB 차이에는 다른 커밋분이 섞였을 수 있다.
- **런타임 비용**: zod 파싱·평가 ms, TTI·LCP 영향은 재지 않았다 (서버·브라우저 사용 금지).
- **수정안 효과**: (a)·(b) 의 실제 크기 효과는 재빌드로만 확인할 수 있다.
- **사용자 활성화 유지 여부** [확인 필요]: iOS Safari(홈 화면 앱)·Firefox 에서 `await getRegistration()` 뒤에 부르는 `Notification.requestPermission()` 이 사용자 활성화 안에 드는지 실기기로 확인하지 못했다. Chromium e2e 는 stub 이다.
- **테스트·린트**: vitest·Playwright·eslint 는 돌리지 않았다 (읽기 전용 지시).
- **`e2e/tests/push.spec.ts`**: React 코드가 아니라 위 규칙 대상이 아니다. 훑어본 범위에서는 `data-testid` 우선(AGENTS §8)을 지킨다.


---

## 수정 (GEN-P2-3) — 1차 FAIL-1 · 경미 1 · 경미 6 대응

- FAIL-1 → 수정안 (a) 채택:
  - `features/push/marker.ts` 의 zod 스키마를 없애고, 모듈 레벨 UUID 정규식과 `typeof` 가드로 바꿨다.
  - 파싱이 실패하거나, 추가 필드가 있거나, uuid 가 아니면 모두 "없음" 으로 본다. 의미는 그대로다.
  - 스펙 문구도 같이 고쳤다: `docs/requirements/pwa.md`·`docs/adr/035-web-push.md`.
- 경미 1 → 설정 전용 훅을 셸 모듈에서 뺐다:
  - `usePushSettings` 를 `features/push/use-push-settings.ts` 로 분리했다.
  - `hooks.ts` 에는 셸 훅 3개(`usePushConfig`·`usePushAppLoadSync`·`usePushLogoutCleanup`)만 남겼다.
- 경미 6 → 로그아웃 정리를 시작할 때 `lastSyncedMeId = null` 로 되돌린다 (`hooks.ts:58`).
- 테스트:
  - `flows.test.ts` — 표식 경계값 (null·문자열·숫자·배열·추가 필드·비 uuid·getItem throw).
  - `push-sync.test.tsx` — 같은 계정이 다시 로그인하면 동기화가 다시 돈다.

## 재게이트 (GATE-PR2-R2)

> 2026-10-02 · 대상 = GEN-P2-3 수정 · 판정자 = 새 Evaluator (cold context, 읽기 전용) · **결과: PASS — FAIL 0**
> 측정은 수정을 반영한 빌드에서 했다 (`apps/web/.next`, BUILD_ID `gHGzBcbda3Ue4pP1p3gHj`). `(app)/*/page_client-reference-manifest.js` 13개를 전부 읽어 entryJSFiles 의 gz 를 합산하고, 청크마다 zod 표지 문자열을 찾았다.

| 항목 | 판정 | 근거 |
|---|---|---|
| FAIL-1 (a) `features/push`·`lib/pwa` 의 zod import | PASS | `from 'zod` grep 0건 (`marker.ts:7-8` 주석만 남음) |
| FAIL-1 (b) `(app)/layout` 청크의 zod | PASS | layout 청크 14개에서 `Ungültige`·`toJSONSchema`·`ZodError`·`$ZodType`·`too_small`·`invalid_type` 0건. zod 청크 `3uv5qtwtf2jn_.js` 는 `/dashboard`·`/projects`·`/projects/[id]` 의 page 몫에만 있다 (기준선부터 zod 를 쓰던 라우트) |
| FAIL-1 (c) layout 그룹 gz | PASS | 13개 라우트 모두 **144,737 B**. 기준선 142,244 대비 **+2,493 B**. 셸 청크에서 push 모듈만 떼어 gz 하면 2,170 B 라 증가분과 맞는다 |
| 경미 1 `usePushSettings` 가 셸에서 빠졌나 | 해소 | 훅 표지 문자열이 settings page 청크 `2o7puymsw_6su.js` 에만 있다. 패널은 `push-settings-panel.tsx:6` 에서 직접 import 한다 |
| 경미 1 `enablePush`·`resolvePushDeviceState`·`readPushEnvironment` | 경미 유지 | 셸 청크에 남았다. `flows.ts`·`utils.ts` 가 모듈 단위로 실려서다. 빼면 줄어드는 몫은 약 0.3 KB gz |
| 경미 6 / `server-no-shared-module-state` | PASS | `lastSyncedMeId` 에 대입하는 곳은 effect 안(`hooks.ts:44-45`)과 onClick 경로의 콜백(`hooks.ts:57-60`) 두 곳뿐이다. 모듈 스코프에는 정적 초기값 `null` 만 있다 |
| `advanced-init-once` | PASS | 모듈 가드 + effect 조합이 유지된다. 재로그인 시 재동기화는 새 vitest 케이스로 확인했다 |
| `js-hoist-regexp` | PASS | `UUID_RE` 가 모듈 레벨에 있다 (`marker.ts:13`). `/i` 만 쓰고 `/g` 는 없다 |
| `client-localstorage-schema` | PASS | 키에 버전이 있다 (`kairos:push:v1`). 파싱 실패 = null, 추가 필드는 버린다 (`marker.ts:27-31, 44-53`) |
| `bundle-barrel-imports` | PASS | barrel 없음. 새 파일은 직접 경로로 import 한다 |
| vitest `src/features/push` | PASS | 4 files · 61 tests |

**라우트별 정적 JS gz 합계 (기준선 → 1차 → 수정 후)**

| 대상 | 기준선 | 1차 (HEAD `1063903`) | 수정 후 |
|---|---|---|---|
| `(app)` layout 그룹 | 142,244 | 235,793 | **144,737** |
| `/meetings/[id]` (알림 클릭 착지) | 154,012 | 247,628 | **156,572** |
| `/settings` | 183,461 | 278,067 | **187,433** |

**남은 경미 사항 (후속, 게이트 판정과 별개)**

- 설정 전용 흐름 일부(`enablePush`·`resolvePushDeviceState`·`readPushEnvironment`)가 셸 청크에 남아 있다. 약 0.3 KB gz 라 효과가 작다. 빼려면 `flows.ts` 를 셸용과 설정용으로 나눈다.
- 손으로 쓴 UUID 정규식은 RFC 9562 의 version·variant 를 보지 않는다. 소유 판정은 `userId === meId` 비교로 하므로 보안 성질은 그대로다.
- 1차 경미 2~5·7 은 그대로 남아 있다 (영향 미미, 후속).

**확인 못 한 것**

- 기준선 142,244 B 를 다시 재지 못했다. 기준선 빌드가 지워져서 1차 값을 썼다. 증가분 +2,493 B 와 push 모듈 실측 2,170 B 는 서로 맞는다.
