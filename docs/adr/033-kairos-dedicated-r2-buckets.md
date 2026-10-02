# ADR-033 — Kairos 전용 R2 버킷 분리 (`kairos-prod` · `kairos-dev`)

**Status**: Accepted
**Date**: 2026-09-27
**Amends**: [ADR-028](028-oci-selfhosting.md) D3 ("R2 는 유지" — 버킷을 어디에 두는지는 정하지 않았다)

---

## 배경

2026-09-27 Gate 0 인계 작업(nightly e2e 이식) 중에 확인한 R2 상태:

- 운영·CI·로컬 개발이 **모두 한 버킷 `nexus-core-storage`** 에 쓴다. 이 버킷은 다른 프로젝트(nexus-core)와 공유한다.
- Kairos 가 쓰는 R2 토큰도 nexus-core 와 **같은 토큰**이고 범위가 All buckets 다. 서버 `.env` 와 GitHub repo-level `R2_*` 에 같은 값이 들어 있다.
- 그래서 CI 가 운영 원본을 지울 수 있는 권한으로 돌고, 로컬·CI 업로드가 운영 `uploads/` 에 섞인다. 운영 cleanup 이 그 파일들을 고아 후보로 본다.
- 곧 켤 DB 백업(체크리스트 0-11)의 덤프에는 세션 토큰·OAuth 토큰·비밀번호 해시가 들어 있다. 이것도 공유 버킷으로 가게 되어 있었다.
- **R2 토큰의 범위는 버킷 단위뿐이다** (prefix 제한 불가). 버킷을 나누지 않으면 권한도 나눌 수 없다.

## 결정

### D1. 버킷 2개

| 버킷 | 쓰는 곳 | 내용 | lifecycle |
|---|---|---|---|
| `kairos-prod` | 운영 서버 | `uploads/` · `memory/` (회의·메모 원본) + `backups/kairos/` (DB 덤프) | `backups/kairos/` 14일 (`backups-14d`) |
| `kairos-dev` | GitHub Actions e2e · 로컬 개발 | 테스트 업로드 | 전체 7일 (`expire-7d`) |

둘 다 비공개다. CORS 는 두지 않는다 — 브라우저는 R2 에 직접 닿지 않는다 (업로드는 백엔드 프록시 `POST /workspaces/{wid}/upload/file`,
다운로드 presigned URL 은 파이프라인 내부용, 녹음 미리보기는 로컬 blob URL).

### D2. 토큰 4개 — 전부 버킷 한정

| 토큰 | 권한 · 버킷 | 넣는 곳 |
|---|---|---|
| `kairos-prod-app` | Object Read & Write · `kairos-prod` | 서버 `~/kairos/.env` `R2_*` |
| `kairos-prod-readonly` | Object Read · `kairos-prod` | GitHub repo-level `R2_*` (`r2-cleanup.yml` 읽기 전용 인벤토리) |
| `kairos-dev-app` | Object Read & Write · `kairos-dev` | GitHub `E2E_R2_*` (`test.yml` · `nightly-e2e.yml`) + 로컬 `apps/api/.env` |
| `migration-src-readonly` | Object Read · `nexus-core-storage` | Super Slurper 원본 (이전 후 삭제) |

기존 공유 토큰은 nexus-core 가 쓰므로 **Kairos 쪽에서 지우지 않는다.** 범위 축소는 nexus-core 작업이다 (BL-LR-18).
`R2_ACCOUNT_ID` 는 계정 공통이라 모든 곳에서 같은 값이다.

### D3. 이전은 코드 변경 없이

DB 는 버킷 이름 없이 키만 저장한다 (`meetings.file_key` · `memory_items.r2_audio_key`). 키를 그대로 복사하고 `R2_BUCKET_NAME` 만 바꾸면 된다.

1. Cloudflare Super Slurper 로 `nexus-core-storage/uploads/` → `kairos-prod` 복사 (키 유지). `memory/` 는 객체 0개라 건너뛴다.
2. 전환: `deploy-preflight` 0 확인 → 서버 `.env` 백업 → `R2_ACCESS_KEY_ID`·`R2_SECRET_ACCESS_KEY`·`R2_BUCKET_NAME` 교체 → `up -d --no-deps api`.
3. 같은 이전을 skip-existing 으로 한 번 더 — 1과 2 사이에 올라온 파일을 옮긴다.
4. 검증: `apps/api/scripts/r2_cleanup.py` dry-run 의 `protected(referenced)` (DB 가 참조하는 키 중 버킷에 있는 수)가 이전 전 옛 버킷과 같아야 한다.

되돌리기: `.env` 백업 복원 + `up -d --no-deps api`. 옛 버킷 원본은 지우지 않았다.

## 진행 상태 (2026-10-02)

| 단계 | 상태 |
|---|---|
| 버킷 2개 + lifecycle (`backups-14d` · `expire-7d`) | ✅ |
| `kairos-dev-app` → GitHub `E2E_R2_*` · CI 전환 (#198) | ✅ nightly heavy spec 이 `kairos-dev` 업·다운로드 성공 (run 36318222143 이후 3회) |
| 운영 이전 (D3 1~4) · repo-level `R2_*` 교체 · 로컬 `.env` 교체 | ✅ 2026-10-02 (결과는 아래). 2차 이전은 전환 **전에** 돌렸고, 그 사이 업로드는 재기동 직전 옛 버킷 수로 0건 확인 |
| `kairos-dev-app` 재발급 → `E2E_R2_*` 재등록 | ✅ 2026-10-02 — 비밀번호 관리자의 키 쌍이 인증 실패(`Unauthorized`)라 재발급. 다음 nightly heavy 런에서 업·다운로드 재확인 |

이전 검증의 기준값 (옛 버킷 `nexus-core-storage`, 2026-09-27 전환 전):
- inventory `uploads/ objects=189 bytes=75387002` · `memory/ objects=0`
- dry-run `--days 7`: `referenced=88 · protected(referenced)=86 · too_young=2 · candidates=101`
- QA 파일 2개(too_young 2)를 지운 뒤 복사하므로 새 버킷 기대값 = `uploads/ objects=187` · `protected(referenced)=86`.
  88 − 86 = 2 는 이전 **전부터** 버킷에 없던 키다 (BL-LR-18).

전환 후 실측 (`kairos-prod`, 2026-10-02 — 기대값과 일치):
- inventory `uploads/ objects=187 bytes=75000120` · `memory/ objects=0`
- dry-run `--days 7`: `referenced=88 · protected(referenced)=86 · too_young=101 · candidates=0` (복사로 시각이 새로 찍혀 전부 7일 미만)
- 운영 컨테이너 쓰기·읽기·삭제 시험 OK · GitHub `R2_*`(읽기 전용) 인벤토리 run 36952278871 성공

## 기각한 대안

- **버킷 1개(`kairos`) + prefix 로 운영·CI 구분** — 토큰이 버킷 단위라 CI 토큰이 운영 원본에 쓰기 권한을 갖는다.
- **현행 유지 + CI 만 전용 버킷** — 운영 원본·덤프가 계속 공유 토큰·공유 버킷에 남는다. 사용자 판단: "관리 포인트상 별도가 맞다".
- **백업만 OCI Object Storage** — 같은 제공자에 DB 와 백업이 함께 있게 된다. R2 는 제공자가 달라 VM 을 잃어도 남는다.

## 결과

- 이전을 마치면(R4) Kairos 가 발급한 토큰 중 `kairos-prod` 에 쓸 수 있는 것은 서버 `.env` 의 하나뿐이고, GitHub 의 운영 버킷 토큰은 읽기 전용이 된다.
  단 nexus-core 의 All buckets 토큰 2개는 여전히 `kairos-prod` 에 닿는다 — 범위 축소는 BL-LR-18.
- `kairos-dev` 는 전체 7일 만료다. 로컬 DB 의 회의는 7일이 지나면 원본이 없어 재처리가 안 된다 (개발용이라 수용).
- 후속: 옛 버킷의 Kairos prefix 정리, 공유 토큰 범위 축소, `kairos-prod` 로 같이 넘어온 미참조 객체 정리 → [`REFACTORING-BACKLOG.md`](../REFACTORING-BACKLOG.md) BL-LR-18.
