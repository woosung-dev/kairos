# 런북: 회의가 `transcribing` / `analyzing` 에서 멈췄을 때

> 근본 해결은 **BL-OCI-4** (`docs/TODO.md`). 이 문서는 그때까지의 대응 절차다.

## 증상

- 회의 상세 화면의 진행 표시가 끝나지 않는다 (polling 이 종료되지 않음)
- `meetings.status` 가 `transcribing` 또는 `analyzing` 에서 고착
- 에러 토스트도 `failed` 상태도 뜨지 않는다 — **조용한 정지**

## 원인

`BackgroundTasks` 는 FastAPI 프로세스 안에서 돈다. **재시도가 없다.**
배포·크래시·OOM 으로 프로세스가 교체되면 진행 중이던 작업은 그대로 사라지고,
DB 의 status 만 중간 상태로 남는다.

상태 전이: `uploading → transcribing → analyzing → completed | failed`

> 실제 발생 — 2026-08-14 OCI 컷오버 때 8건(E2E 6 + uploading 2)이 이렇게 좌초해 수동 삭제했다.

## 1. 식별

정상 파이프라인의 최장 작업이 약 15분이다. **2시간 넘게 갱신이 없으면 좀비**로 본다.

```bash
printf "SELECT id, status, updated_at FROM meetings \
WHERE status IN ('transcribing','analyzing') \
AND updated_at < now() - interval '2 hours' ORDER BY updated_at;" \
| ssh truewords-oracle 'bash -lc "docker exec -i kairos-db psql -U kairos -d kairos -tA"'
```

2시간 **이내**인 것은 정상 진행 중일 수 있으니 건드리지 않는다.
(같은 임계값을 `mise run deploy-preflight` 가 배포 게이트로 쓴다.)

## 2. 로그 확인

관측 수단은 `docker logs` 다 (Sentry 는 ADR-028 로 제거됨).

```bash
ssh truewords-oracle 'bash -lc "docker logs --tail 300 kairos-api"'
```

`transcription` / `ai_processing` / circuit breaker(`ai_resilience`) 관련 예외를 찾는다.
외부 API 장애가 원인이면 조치 전에 그쪽 복구를 먼저 확인한다.

## 3. 조치

**사용자에게 재업로드를 안내하는 것이 기본이다.** 부분 결과를 살리려 하지 않는다 —
트랜스크립트가 중간까지만 있으면 요약·액션 추출이 잘못된 근거로 생성된다.

1. 원본이 R2 에 남아 있는지 확인한다 (남아 있으면 재업로드 없이 재처리 가능)
2. 좀비 row 를 `failed` 로 전이시켜 UI 가 종료 상태를 표시하게 한다
3. 사용자가 삭제 후 재업로드하면 정상 경로로 다시 돈다

> 회의 삭제 시 R2 원본은 남는다 (BL-OCI-5, 고아 파일). 잔여량은 수십 KB 수준이라 급하지 않다.

## 4. 예방

- **배포 전 `mise run deploy-preflight` 를 반드시 실행한다.** 진행 중 작업이 0 이어야 배포한다
- `deploy/oci/docker-compose.prod.yml` 의 `stop_grace_period: 900s` 는 진행 중 작업이
  끝날 시간을 주기 위한 값이다. 줄이면 이 장애가 늘어난다
- uvicorn `--workers` 를 1 에서 늘리지 않는다 — circuit breaker 와 auth 캐시가 in-process
  싱글턴이라 멀티워커에서 상태가 파편화된다

## 5. 관련

- 서버 운영 정본(부트스트랩·배포·롤백·포트 충돌 함정): [`../../../deploy/oci/README.md`](../../../deploy/oci/README.md)
- 배포 전체 그림: [`../deployment.md`](../deployment.md)
