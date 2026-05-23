# Multi-Agent QA 시드 fixture 명세

> Sprint 18 → 19 Multi-Agent QA 검증용 시드 데이터.
> 스크립트: `backend/scripts/seed_qa_fixtures.py`
> JSON: `seed-fixtures.json`
> 메타: `qa_run_id = 2026-05-17-multi-agent`, `seeded_at = 2026-05-16T22:33:47Z`

---

## 1. 페르소나 5명 (워크스페이스 owner)

| 페르소나 | clerk_user_id | email | workspace_id | workspace_name |
|---|---|---|---|---|
| SENTINEL_A | `user_3DlHnHHk51f5QpYjN10e3goKv52` | wkddntjd3429@naver.com | `9966a04e-...` | `[QA-2026-05-17] WS-QA-SENTINEL_A-2026-05-17` |
| SENTINEL_B | `user_3DpBbgkNmN7P2oSnutENi5CuWdQ` | wkddntjd3429-0@naver.com | `ce9e5d5c-...` | `[QA-2026-05-17] WS-QA-SENTINEL_B-2026-05-17` |
| CASUAL | `user_3DpBeO7IVYHg8LbVLqpAJbmwtIv` | wkddntjd3429-1@naver.com | `539ba7f4-...` | `[QA-2026-05-17] WS-QA-CASUAL-2026-05-17` |
| MOBILE | `user_3DpBhYQlDDBXt6h2IeKVZdMjxAt` | wkddntjd3429-3@naver.com | `ecc6277f-...` | `[QA-2026-05-17] WS-QA-MOBILE-2026-05-17` |
| POWER | `user_3DpBm4GOx7FOnaF8N2l5fJH2APF` | wkddntjd3429-5@naver.com | `0e3ed472-...` | `[QA-2026-05-17] WS-QA-POWER-2026-05-17` |

공통 비밀번호: ENV `QA_PASSWORD` (실제 값은 `~/.kairos-qa-secrets/seed-credentials-2026-05-17.env`).

---

## 2. RAG visibility fixture (Sentinel A 워크스페이스 내 3 프로젝트)

| visibility | project_id | note_id | chunk_id | expected_keyword |
|---|---|---|---|---|
| public | `e649665b-...` | `01c8edbb-...` | `87741c54-...` | `alpha-public-fixture-2026.` |
| draft | `dca4a2ef-...` | `cb13aac5-...` | `eb6f88e6-...` | `beta-draft-fixture-2026.` |
| private | `867cce04-...` | `6c63085a-...` | `07a47e67-...` | `gamma-private-fixture-2026.` |

Sentinel-P0 spec (`qa-sentinel-p0.spec.ts`) 의 RAG 12 케이스가 이 chunk_id를 expected source IDs로 사용.

---

## 3. Cross-tenant fixture (Sentinel B 워크스페이스)

| 필드 | 값 |
|---|---|
| visibility | private |
| project_id | `f891fab9-...` |
| note_id | `60536ae2-...` |
| chunk_id | `65e9d772-...` |
| expected_keyword | `delta-cross-tenant-fixture-2026.` |

Sentinel A 토큰으로 이 청크가 절대 노출되지 않아야 함 (P0-1.11, P0-1.12).

---

## 4. Power fixture (Sentinel A 워크스페이스)

- projects: 4건
- notes: 5건
- (meetings/actions는 sub-agent QA 단계에서 동적 생성)

Power 페르소나가 단축키 / 벌크 / Export 검증 시 사용.

---

## 5. 안전 (cleanup)

- 모든 시드 row 이름에 `[QA-2026-05-17]` prefix 또는 `WS-QA-` workspace prefix
- `qa_run_id` metadata (workspace.metadata_json) — 추가 추적용
- cleanup: `python backend/scripts/seed_qa_fixtures.py --cleanup`
  - WS_PREFIX (`WS-QA-`) 매칭 cascade delete
  - `KAIROS_FOUNDER_CLERK_ID` ENV 설정 시 founder 매칭 차단
  - User row 보존 (Clerk dashboard 수동 정리 필요)
  - R2 object 별도 정리 (meeting 업로드 발생 시)
- dry-run: `python backend/scripts/seed_qa_fixtures.py --dry-run-cleanup`

---

## 6. 재실행 (idempotent)

같은 `clerk_user_id` User + 같은 `[QA-...]` prefix Workspace 존재 시 재사용. JWT는 60초 TTL → `frontend/e2e/tests/qa-extract-credentials.spec.ts` 로 1회 재추출 (qa-1h template 셋업 필요 시 `CLERK-JWT-TEMPLATE-SETUP.md` 가이드).
