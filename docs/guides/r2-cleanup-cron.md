# R2 30일 Voice 메모 cleanup — Cloud Scheduler 설정

> **Sprint 15 R-CRON / O-E lock-in**: voice 메모는 R2 store + 30일 TTL. 매일 GCP Cloud Scheduler가 admin endpoint 호출 → 30일 경과한 R2 객체 삭제 + `memory_items.r2_audio_key` NULL 처리.

## §1. 엔드포인트 명세

- **URL**: `https://<cloud-run-url>/api/v1/admin/memory/r2-cleanup`
- **Method**: `POST`
- **Header**: `X-Cron-Token: <CRON_SECRET_TOKEN>`
- **Query (optional)**: `?days=30` (기본 30, 1~365 범위)
- **Response**: `{"deleted_count": N, "ttl_days": 30}`
- **인증**: Clerk JWT 우회 — `CRON_SECRET_TOKEN` 환경변수와 일치하는 헤더만 통과 (403 외 403)

## §2. CRON_SECRET_TOKEN 발급

```bash
# 32바이트 hex 토큰 생성
openssl rand -hex 32
# 예) 7a1c4f8b2d3e5f6a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a

# Cloud Run 환경변수 / Secret Manager에 저장
gcloud secrets create cron-secret-token --replication-policy=automatic
echo -n "<token>" | gcloud secrets versions add cron-secret-token --data-file=-

# Cloud Run service 업데이트 — CRON_SECRET_TOKEN env 매핑
gcloud run services update kairos-backend \
  --update-secrets CRON_SECRET_TOKEN=cron-secret-token:latest \
  --region asia-northeast3
```

backend `.env`에는 동일 token을 `CRON_SECRET_TOKEN=...`로 저장 (로컬 테스트 시).

## §3. Cloud Scheduler 등록

```bash
gcloud scheduler jobs create http memory-r2-cleanup \
  --schedule="0 3 * * *" \
  --time-zone="Asia/Seoul" \
  --uri="https://<cloud-run-url>/api/v1/admin/memory/r2-cleanup" \
  --http-method=POST \
  --headers="X-Cron-Token=$(gcloud secrets versions access latest --secret=cron-secret-token)" \
  --location=asia-northeast3
```

- 매일 03:00 KST (사용자 idle 시간대)
- 응답 200 OK 외엔 GCP Cloud Logging에 alert (수동 확인 또는 PagerDuty 연동 — Sprint 16+)

## §4. 검증

```bash
# 로컬
cd backend && uv run uvicorn src.main:app --reload
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

- Cloud Scheduler job 실행 이력: GCP console → Cloud Scheduler → memory-r2-cleanup → "Logs"
- 실패 알람: Sprint 16+ Stackdriver alert policy 추가 (현재는 manual 확인)
- 삭제 카운트 trend: `memory_events` 테이블 직접 SQL 조회 (R7 metrics 페이지 통합은 Sprint 17+)
