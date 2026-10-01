# 운영 문서

| 알고 싶은 것 | 정본 |
|---|---|
| **서버 런북** — 부트스트랩 · 배포 실행 · 롤백 · 포트 충돌 함정 | [`deploy/oci/README.md`](../../deploy/oci/README.md) |
| 배포 전체 그림 (무엇이 어디로, 왜 자동 배포가 없는지) | [`deployment.md`](deployment.md) |
| 장애 대응 절차 | [`runbooks/`](runbooks/) |
| 환경변수 매트릭스 (로컬 / CI / 프로덕션) | [`../development/secrets.md`](../development/secrets.md) |
| 벡터 재인덱싱 | [`pgvector-reindex.md`](pgvector-reindex.md) |
| R2 객체 정리 (음성 메모 TTL · DB 미참조 객체 · 읽기 전용 인벤토리) | [`r2-cleanup-cron.md`](r2-cleanup-cron.md) |
| DB 백업 · 복원 · 복원 리허설 | [`runbooks/db-backup-restore.md`](runbooks/db-backup-restore.md) |
| 비밀번호 분실 — 운영자 수동 재설정 | [`runbooks/manual-password-reset.md`](runbooks/manual-password-reset.md) |

> 서버 런북을 이 폴더로 옮기지 않는 이유: `deploy/oci/README.md` 는
> `docker-compose.prod.yml` · `build.env.example` 과 같은 디렉터리에 있어야 한다.
> 포트 충돌·볼륨 함정 같은 내용은 그 파일들 옆에서 읽혀야 의미를 갖는다.

## 관측

`docker logs` 가 전부다. Sentry 는 ADR-028 로 제거됐다 (ADR-021 Superseded).
재도입 지점은 `apps/web/src/lib/track-error.ts` seam.

```bash
ssh oci-tokyo 'bash -lc "docker logs --tail 300 kairos-api"'
mise run deploy-status
mise run deploy-logs
```

## 아직 없는 것

- **DB 백업 cron** — 스크립트(`deploy/oci/backup/pg-backup.sh`)와 런북은 있고, **서버 crontab 등록은 사용자 몫**이다
  ([`runbooks/db-backup-restore.md`](runbooks/db-backup-restore.md) §2). 등록 확인 = `crontab -l | grep pg-backup`.
  등록 전까지는 백업이 없으므로 **`docker compose down -v` 금지** (`-v` 가 `db-data` 볼륨을 지운다),
  **Neon 프로젝트 삭제 금지** (유일한 안전망)
- **자동 배포** — BL-OCI-3. 진입 조건: 수동 배포 3회 연속 성공 + 컷오버 후 7일 무사고
- **incident / postmortem 문서** — 외부 사용자 확보 시점에 신설
