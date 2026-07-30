# ADR-023 — second-brain.md §8 미결정 5건 lock-in (D-6 closed)

**Status**: Accepted  
**Date**: 2026-05-23  
**Updated**: 2026-07-30 (ADR-026 D7에 따른 D-6.5 부분 개정)<br>
**Sprint**: 27a (luminous-anchor)  
**관련**: ADR-004 (PARA → second-brain pivot) · ADR-014 (서비스 경계) · ADR-016 (Personal/Team IA) · ADR-022 (Clerk webhook SKIP)  
**부채 종결**: `CONTEXT-MAP.md` §7 D-6, `docs/requirements/second-brain.md` §8

## Context

`docs/requirements/second-brain.md` §8 "미결정 사항" 5건은 2026-04-04 second-brain pivot (ADR-004) 이후 22 sprint 동안 미해결. Sprint 26 (glittery-tulip) docs 거버넌스 점검 시 3 도구 (codex + agy + Opus) 가 GA dogfooding 진입 전 D-6 lock-in 필수 권고 (agy: "데이터 누수/권한 침해 risk", codex: "GA 실험 해석 오류"). Sprint 27a 에서 grill 1회로 종결.

## Decision

5건 모두 **현 코드 동작 명시화 + 신선도/audit 후속 BL 등재** 패턴. 새 entity / migration 없음.

### D-6.1 — 개인↔팀 경계 (승격 + 퇴사)

- **승격 (Personal → Team)**: I-18 (Promotion = 복제 + tombstone, 4 도메인 `ItemPromotionAudit`) 이미 운영. 사용자가 명시 액션으로 promote (자동 X).
- **퇴사 처리**: `WorkspaceMember` row 삭제 시 콘텐츠 (Meeting / Note / ActionItem / MemoryItem) 의 `creator_id` reference 는 유지. orphan creator 표시 = FE 측 fallback "삭제된 사용자". hard delete 금지.
- **신규 BL**: BL-S27-1 — `WorkspaceMember.is_active` soft delete 컬럼 신설 (현재 hard delete, 감사 trail 부재).

### D-6.2 — RAG 검색 범위 UX

- **기본 범위**: 요청자 현재 workspace 전체 (`public` + `creator 본인의 draft` + `ProjectMember 인 private`). admin/owner 는 모두.
- **사용자 전환**: Cmd+K 안 "프로젝트 범위" 드롭다운 (Sprint 3 구현). 1 project 단위 또는 워크스페이스 전체.
- **신선도 표시**: second-brain §6 Slite 모델 (🟢 ≤1M / 🟡 1-3M / 🔴 >3M) — 신규 BL.
- **신규 BL**: BL-S27-2 — RAG 응답에 신선도 라벨 + 6개월 미갱신 알림 ("이 정보가 아직 유효한가요?").

### D-6.3 — 회의 소속

- **기본**: `Meeting` = Workspace 직속. `workspace_id` only (Project 미할당 가능).
- **Project 연결**: `MeetingProjectLink` N:M (AI 자동 추천 confidence ≥ workspace.inbox_threshold 시 자동 link, 그 이하 = Inbox 적재 후 사용자 선택).
- **결정**: 현 모델 유지 (선택형). 회의 = 워크스페이스 자산, 프로젝트 = 옵션 view.

### D-6.4 — CEO/관리자 접근

- **현 동작**: `_apply_visibility_filter` (backend/src/projects/repository.py:73-114) — admin/owner 는 모든 visibility (`public` / `draft` / `private`) bypass. ProjectMember 추가 없이 private project 조회 가능.
- **결정**: 현 동작 유지. admin/owner = 신뢰 root, 매번 ProjectMember 추가는 운영 부담.
- **보안 보완**: admin 이 private project 첫 조회 시 audit log row 신설 (현재 미구현). owner 는 자체 권한 행사로 audit 면제.
- **신규 BL**: BL-S27-3 — `AdminAccessAudit` 테이블 신설 (admin × private_project_id × first_access_at). 운영 가시성 + 감사 대응.

### D-6.5 — 지식 생명주기

- **audio 원본**: R2 30일 TTL (Cloud Scheduler cron — `docs/guides/r2-cleanup-cron.md`, 이미 구현). MemoryItem.voice 도 동일 30일.
- **텍스트 (트랜스크립트 / 노트 / 액션)**: 무기한 보존. 사용자 명시적 삭제만.
- **외부 원본 예외 (`external_document`)**: Drive가 source of truth다. Drive 문서의 삭제·휴지통 이동·실제 권한 회수가 확인되면 Kairos의 추출 plain text, `EmbeddingChunk`, 관련 `SemanticCache`를 즉시 제거한다. 내부 텍스트의 무기한 보존 원칙은 변경하지 않는다. (ADR-026 D7)
  - `429`/`5xx`/network/circuit open은 일시 장애로 보고 절대 삭제하지 않는다. `stale`과 마지막 동기화 시각을 보존하고 사용자 수동 재동기화만 제공하며 자동 retry는 두지 않는다.
  - `401`/`403`은 세부 reason을 판별한다. reason을 판별할 수 없으면 purge하지 않고 `reauth_required`로 보류한다.
- **Project archive**: `Completed → Archived` 전환 시 AI 인사이트 자동 추출 (second-brain §5 구현됨). RAG 검색 포함.
- **신선도 라벨 + 6개월 알림**: D-6.2 의 BL-S27-2 와 합쳐 처리.
- **결정**: 현 동작 유지. archive 가 곧 "오래된 지식의 정착" 시점 — 자동 인사이트 추출로 보존 가치 증대.

## Consequences

### 즉시 효과
- D-6 closed. CONTEXT-MAP §7 부채 1건 감소.
- second-brain §8 미결정 → 결정 사항 으로 갱신.
- GA dogfooding 진입 시 5건 모두 명시화된 정책으로 사용자 onboarding 가능 (agy 우려 해소).

### 후속 BL (Sprint 28+)
- **BL-S27-1** ★ WorkspaceMember.is_active soft delete (퇴사 audit)
- **BL-S27-2** ★ RAG 신선도 라벨 + 6개월 stale 알림 (Slite 모델)
- **BL-S27-3** ★ AdminAccessAudit 테이블 (admin × private project 가시성)

### Trade-off
- admin/owner bypass 유지 = 운영 편의 우선, audit trail 후속 (BL-S27-3) — 즉시 보안 완벽 X
- 신선도 라벨 미구현 = 6개월 후 stale 콘텐츠 UX risk — BL-S27-2 로 빠른 처리 권장

## 회수 옵션

향후 enterprise 도입 시 admin bypass 제거 + 명시 ProjectMember 추가 요구 (BL-S27-3 audit log 가 transition base).

## References

- `docs/requirements/second-brain.md` §5-§8 (Spotify 모델 + 신선도 + 복리 사이클 + 미결정)
- `docs/adr/004-second-brain-pivot.md` (CODE 프레임워크 채택)
- `docs/adr/014-service-boundary.md` (visibility 권한 분기 위치)
- `docs/adr/016-personal-team-ia.md` (Personal/Team workspace 분리)
- `backend/src/projects/repository.py:73-114` (`_apply_visibility_filter`)
- `backend/src/projects/CONTEXT.md` (visibility 분기)
- Sprint 26 메모리: 3 도구 (codex/agy/Opus) GA 전 D-6 lock-in 권고
