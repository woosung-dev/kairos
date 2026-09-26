# R2 객체 정리 — 음성 메모 30일 TTL · 미참조 객체 정리

> ★ **2026-09-27 정정 (체크리스트 0-12 · D-001 · D-002)** — 이 문서는 `.github/workflows/r2-cleanup.yml` 을
> "고아 정리" 수단으로 안내했지만, 당시 `apps/api/scripts/r2_cleanup.py` 는 DB 참조를 보지 않고 `uploads/`
> 아래 N 일 지난 객체를 **전부** 골랐다. `delete=true` 로 돌렸다면 살아 있는 회의 원본까지 지워졌다
> (실행 이력 0건 — 피해 없음). 지금은 스크립트가 DB 참조를 대조하고, 워크플로는 **읽기 전용 인벤토리**다.
>
> 정리 수단은 서로 다른 둘이다. 섞어 부르지 않는다.
>
> | | §1 음성 메모 30일 TTL | §2 미참조 객체 정리 |
> |---|---|---|
> | 대상 | `memory_items.r2_audio_key` 가 가리키는 **참조 중인** 음성 (`memory/…`) | DB 어디서도 참조하지 않는 `uploads/…` · `memory/…` |
> | 수단 | `POST /api/v1/admin/memory/r2-cleanup` (앱이 지우고 키를 NULL 처리) | `apps/api/scripts/r2_cleanup.py` (서버에서 수동) |
> | 현재 호출 주체 | **없음** — cron·workflow 둘 다 없다 | 운영자 수동 |

R2 버킷 `nexus-core-storage` 는 **다른 프로젝트와 공유**한다 (nexus-core 는 루트 키 + `db-backups/`, Kairos DB 백업은
`backups/kairos/`). **로컬 개발·QA 도 같은 버킷의 `uploads/` 를 쓴다.** 둘 다 §2 의 안전 규칙이 전제한다.

## §1. 음성 메모 30일 TTL (admin endpoint)

- **URL**: `POST /api/v1/admin/memory/r2-cleanup` (`memory/admin_router.py`)
- **Header**: `X-Cron-Token: <CRON_SECRET_TOKEN>` — 서버 `.env` 값과 timing-safe 비교, 불일치 403
- **Query**: `?days=30` (기본 30, 1~365)
- **Response**: `{"deleted_count": N, "ttl_days": 30}` — 30일 지난 메모의 R2 객체 삭제 + `r2_audio_key` NULL

토큰 발급: `openssl rand -hex 32` → 서버 `~/kairos/.env` 의 `CRON_SECRET_TOKEN=` → `docker compose -f docker-compose.prod.yml up -d api`.

수동 실행 (서버에서 — 토큰을 argv 에 싣지 않도록 헤더를 stdin 으로 넘긴다):

```bash
cd ~/kairos
T="$(sed -n 's/^CRON_SECRET_TOKEN=//p' .env)"
printf 'X-Cron-Token: %s\n' "$T" | curl -fsS -X POST -H @- http://127.0.0.1:8200/api/v1/admin/memory/r2-cleanup
unset T
```

[확인 필요] **정기 호출 주체가 없다.** 30일 TTL 을 약속으로 유지하려면 위 명령을 서버 crontab 에 올리는 결정이 필요하다.

## §2. 미참조 객체 정리 (`apps/api/scripts/r2_cleanup.py`)

삭제된 회의·메모의 원본, 업로드 후 회의 생성까지 가지 못한 파일, 로컬 QA 가 올린 파일이 여기 해당한다.

### 안전 규칙 (전부 코드로 강제)

1. 참조 키를 **실행 시점에 DB 에서 직접** 읽는다: `meetings.file_key ∪ memory_items.r2_audio_key`
   (읽기 전용 트랜잭션). promote 복제본은 원본과 같은 키를 공유하므로 사본 하나만 남아도 보호된다.
   **참조 0건이면 중단** — 잘못된 DB 나 조회 실패를 "전부 고아" 로 읽지 않는다.
2. 참조 키는 나이와 무관하게 후보가 되지 않는다. 삭제 직전에 한 번 더 교차 검사한다.
3. prefix 는 `uploads/` · `memory/` 만. 공유 버킷의 다른 prefix 는 목록 조회조차 하지 않는다.
4. `--days` 최소 7 (기본 30) — 업로드 직후 ~ 회의 생성 사이의 객체를 보호한다.
5. `--delete` 는 `APP_ENV=production` 에서만. 로컬 개발도 같은 버킷을 쓰므로, 개발 DB 기준으로 돌리면
   운영 원본이 전부 "미참조" 로 보인다.
6. R2 키를 담는 컬럼이 새로 생기면 스크립트의 `REFERENCED_KEYS_SQL` 에 추가해야 한다 (빠뜨리면 그 객체가 후보가 된다).

⚠ 운영 DB 기준이므로 **로컬 개발·QA 가 올린 `uploads/` 객체도 후보가 된다** (운영 DB 가 참조하지 않으므로).
dry-run 목록에서 확인한 뒤 `--delete` 한다.

### 실행 — 운영 서버의 api 컨테이너 안에서

api 컨테이너에 `R2_*` · `DATABASE_URL` · `APP_ENV` · aioboto3 · asyncpg 가 전부 있다. 스크립트는 이미지에 들어 있지
않으므로(`Dockerfile` 이 `scripts/` 를 복사하지 않는다) 맥의 레포 체크아웃에서 **stdin 으로 흘려보낸다.**

```bash
# 1) dry-run — 후보 목록 + protected(referenced)/too_young/candidates 요약. 삭제 0건
ssh truewords-oracle 'bash -lc "docker exec -i kairos-api python - --days 30"' < apps/api/scripts/r2_cleanup.py

# 2) 목록을 눈으로 확인한 뒤 실제 삭제
ssh truewords-oracle 'bash -lc "docker exec -i kairos-api python - --days 30 --delete"' < apps/api/scripts/r2_cleanup.py
```

종료 코드: 0 정상 · 1 안전 규칙 거부 또는 삭제 실패 · 2 인자 오류.

## §3. GitHub Actions — 읽기 전용 인벤토리

`.github/workflows/r2-cleanup.yml` ("R2 Inventory (read-only)") 는 삭제하지 않는다. 러너는 DB 에 닿지 않아
고아를 판정할 수 없기 때문이다. prefix 별 객체 수·용량·N 일 초과 수만 출력하고 **키는 출력하지 않는다**
(공개 레포의 Actions 로그는 누구나 읽고, 키에 회의 파일명이 들어 있다).

```bash
gh workflow run r2-cleanup.yml --repo woosung-dev/kairos -f days=30
```

## §4. 검증

```bash
# 안전 규칙 테스트 — 가짜 S3·가짜 DB 참조만 쓴다 (R2·DB 접속 없음)
python3 scripts/tests/test_r2_cleanup.py
cd apps/api && uv run pytest ../../scripts/tests/test_r2_cleanup.py -q -p no:cacheprovider

# admin endpoint (§1)
cd apps/api && uv run pytest tests/memory/test_admin_cleanup.py -q
```

`test_r2_cleanup.py` 는 참조 키가 dry-run 목록·삭제 목록에 절대 들어가지 않는 것(무작위 3,000건 포함),
참조 0건·DATABASE_URL 없음·비운영 `--delete`·7일 미만·허용 밖 prefix 거부, 인벤토리의 키 미출력을 검사한다.
참조 검사를 제거한 변이본에서는 4건이 실패한다 (2026-09-27 확인).

## §5. 모니터링

- §1: `docker logs kairos-api` 의 요청 로그. 삭제 추이는 `memory_events` 직접 조회
- §2: 실행 출력이 전부다 (수동 실행)
- §3: GitHub Actions → `R2 Inventory (read-only)` run 로그
- 실패 알람: 없음. 수동 확인
