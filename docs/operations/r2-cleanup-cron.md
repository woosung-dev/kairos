# R2 30일 Voice 메모 cleanup

> **Sprint 15 R-CRON / O-E lock-in**: voice 메모는 R2 store + 30일 TTL. admin endpoint 호출 →
> 30일 경과한 R2 객체 삭제 + `memory_items.r2_audio_key` NULL 처리.
>
> ★ **2026-08-16 정정** — 이 문서의 실행 절차는 GCP Cloud Scheduler / Cloud Run / Secret Manager
> 전제로 쓰여 있었고, 그것들은 [ADR-028](../adr/028-oci-selfhosting.md) 로 **전부 철거됐다.**
> **현재 실행 수단은 `.github/workflows/r2-cleanup.yml` 하나뿐이고 `workflow_dispatch` 전용이다**
> (cron 미설정 — `docs/TODO.md` BL-OCI-5). 아래 §2/§3 은 그 사실에 맞춰 다시 썼다.

## §1. 엔드포인트 명세

- **URL**: `https://kairos-api.woosung.dev/api/v1/admin/memory/r2-cleanup`
- **Method**: `POST`
- **Header**: `X-Cron-Token: <CRON_SECRET_TOKEN>`
- **Query (optional)**: `?days=30` (기본 30, 1~365 범위)
- **Response**: `{"deleted_count": N, "ttl_days": 30}`
- **인증**: Clerk JWT 우회 — `CRON_SECRET_TOKEN` 환경변수와 일치하는 헤더만 통과 (403 외 403)

## §2. CRON_SECRET_TOKEN 발급

```bash
# 32바이트 hex 토큰 생성
openssl rand -hex 32

# 서버 ~/kairos/.env 에 CRON_SECRET_TOKEN=<token> 추가 후 재기동
ssh truewords-oracle 'bash -lc "cd ~/kairos && docker compose -f docker-compose.prod.yml up -d api"'
```

로컬 테스트 시에는 `apps/api/.env` 에 같은 토큰을 넣는다.

## §3. 실행

**현재 스케줄러는 없다.** 수동 실행이 유일한 경로다.

```bash
# GitHub Actions (workflow_dispatch 전용, cron 미설정)
gh workflow run r2-cleanup.yml --repo woosung-dev/kairos -f days=30 -f delete=false   # dry-run 먼저
gh workflow run r2-cleanup.yml --repo woosung-dev/kairos -f days=30 -f delete=true
```

주기 실행이 필요해지면 오라클 VM crontab 에 curl 을 걸거나 `r2-cleanup.yml` 에 `schedule:` 을
추가한다 (BL-OCI-5).

- 매일 03:00 KST (사용자 idle 시간대)
- 응답 200 OK 외엔 GCP Cloud Logging에 alert (수동 확인 또는 PagerDuty 연동 — Sprint 16+)

## §4. 검증

```bash
# 로컬
cd apps/api && uv run uvicorn src.main:app --reload
# 다른 터미널
curl -X POST http://localhost:8000/api/v1/admin/memory/r2-cleanup \
  -H "X-Cron-Token: $CRON_SECRET_TOKEN"
# Expected: 200 + {"deleted_count": N, "ttl_days": 30}

# 잘못된 토큰
curl -X POST http://localhost:8000/api/v1/admin/memory/r2-cleanup \
  -H "X-Cron-Token: wrong"
# Expected: 403 + {"detail": "invalid cron token"}
```

## §5. 모니터링

- 실행 이력: GitHub Actions → `R2 Cleanup` 워크플로 run 로그
- 서버측: `ssh truewords-oracle 'bash -lc "docker logs --tail 200 kairos-api"'` (ADR-028 — 관측은 `docker logs`)
- 실패 알람: 없음. 수동 확인
- 삭제 카운트 trend: `memory_events` 테이블 직접 SQL 조회 (R7 metrics 페이지 통합은 Sprint 17+)
