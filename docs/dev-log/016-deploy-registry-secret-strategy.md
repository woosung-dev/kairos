# ADR-016: 배포 레지스트리·시크릿 보관 전략 — GHCR/GitHub Secrets 시도 후 GAR/Secret Manager로 복귀

> 작성: 2026-05-13
> 상태: Accepted
> Supersedes: PR #23 (`feat(deploy): Artifact Registry → GHCR 전환`)
> Related: ADR-008 (DevEx Initiative — WIF 채택)

---

## 1. 컨텍스트

PR #23에서 두 가지 변경을 동시에 진행:

1. **이미지 레지스트리**: GCP Artifact Registry(GAR) → GitHub Container Registry(GHCR)
2. **앱 시크릿 보관**: GCP Secret Manager → GitHub Secrets (`--set-secrets` → `--set-env-vars`)

목적은 "AWS 이전 시 재작업 최소화" — 빌드 산출물·시크릿을 GitHub에 두면 어느 클라우드로 가도 그대로 재사용 가능.

머지 후 Opus 독립 리뷰(`docs/dev-log/codex-review-pr23.md` 검토 메모) + 업계 패턴 조사(2026-05-13)에서 다음 문제 식별:

### 1.1 GHCR 직접 pull 실패 가능성 (P0)

- GHCR 패키지는 기본 private — `gcloud run deploy --image ghcr.io/...`는 Cloud Run runtime SA가 GHCR 인증 자원이 없어 pull 실패.
- 해결책 2가지: (a) GHCR 패키지 public 전환, (b) Artifact Registry Remote Repository로 프록시.
- `woosung-dev/kairos`는 **private repo** — public 이미지 노출은 컴파일된 Python 코드 디컴파일 위험 → private 정책 위반.
- AR Remote Repo는 복잡도 추가 (PAT 발급·Secret Manager 등록·Service Agent IAM·이미지 경로 prefix).

### 1.2 GitHub Secrets `--set-env-vars` 패턴의 보안 후퇴

- Cloud Run 콘솔에 9개 시크릿이 **평문**으로 표시.
- Revision history에 평문 영구 보존 → 롤백 시 옛 값 자동 노출.
- 키 로테이션 시 모든 revision 재배포 필요.
- Cloud Audit Logs로 시크릿 접근 추적 불가 (env var 읽기는 audit 대상 아님).

### 1.3 업계 합의와의 괴리

> "Store secrets in cloud-native Secret Manager. Authenticate from GitHub Actions via Workload Identity Federation."
> — Google Cloud 공식 가이드, GitGuardian, GCP best practices 일치

업계 표준은 **WIF + Secret Manager** 조합이며, GitHub Secrets 직접 주입은 MVP/사이드 프로젝트 범위로 한정됨.

---

## 2. 결정

**C-1: 완전 revert** — 이미지·시크릿 모두 GCP 네이티브로 복귀.

```yaml
이미지:    GitHub Actions → GAR (asia-northeast3-docker.pkg.dev/woosung-dev/kairos/api)
시크릿:    GCP Secret Manager (--set-secrets reference 주입)
인증:      WIF (GCP_WIF_PROVIDER + GCP_DEPLOYER_SA, PR #23에서 도입한 부분 유지)
```

---

## 3. 대안 검토 (각 10점 만점)

| 옵션 | 즉시 작동 | 보안 | 키 로테이션 | AWS 시크릿 이식 | AWS 이미지 이식 | 일관성 | 종합 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **C-1 (이번 결정)** | 10 | 9 | 9 | 3 | 3 | 9 | **7.2** |
| C-2 (이미지만 GAR, 시크릿 GitHub) | 10 | 6 | 5 | 9 | 3 | 4 | 6.2 |
| B (GHCR + GAR 미러) | 9 | 9 | 9 | 9 | 9 | 7 | 8.6 |
| Remote Repo 패턴 (AR이 GHCR 프록시) | 9 | 9 | 9 | 8 | 8 | 7 | 8.3 |
| 현 PR #23 상태 (변경 없음) | 4 | 7 | 5 | 9 | 8 | 5 | 6.3 |

### 3.1 왜 B/Remote Repo가 아닌 C-1?

B와 Remote Repo는 종합 점수가 더 높으나 모두 "**AWS 이전이 6~12개월 내 명확히 예정된 팀**" 가정에 최적화됨.
Kairos 현 상태:
- MVP 검증 단계 (PRD §3.5 thesis 검증 중)
- AWS 이전 시기 미정 (ADR-010 참고)
- 솔로 개발자 (오버엔지니어링 비용 큼)
- 검증된 GCP 패턴(GAR + WIF + Secret Manager)이 이미 작동 중이었음

AWS 이전이 임박해지면 본 ADR을 supersede하고 Remote Repo 또는 GHCR+GAR 미러 패턴으로 재설계.

### 3.2 왜 C-2가 아닌가?

C-2(이미지만 GAR, 시크릿은 GitHub)는 "타협안"으로 보이지만:
- Cloud Run 콘솔 평문 노출은 그대로 (보안 후퇴 유지)
- 이미지·시크릿이 서로 다른 정책 → 신규 팀원 혼란
- AWS 이전 시 어차피 deploy.yml 전체 재작성 — GitHub Secrets 보존 이득이 크지 않음

---

## 4. 영향

### 4.1 코드 변경

| 파일 | 변경 |
|---|---|
| `.github/workflows/deploy.yml` | GHCR push step 제거, GAR push 복원. `--set-env-vars` 9개 시크릿 제거, `--set-secrets` reference 복원. `packages: write` 권한 제거. |
| `docs/guides/secrets.md` | "CI 전용 — GitHub Secrets" 섹션 정리: 9개 앱 시크릿 제거, GCP Secret Manager 참조로 안내. 백엔드 매트릭스 "프로덕션" 컬럼은 원래 `GCP Secret Manager`로 표기되어 있어 변경 불필요. |
| `docs/dev-log/016-deploy-registry-secret-strategy.md` | 본 ADR 신규. |

### 4.2 인프라 작업 (사용자 직접)

1. **GCP Secret Manager 9개 시크릿 등재 확인** — PR #23 이전부터 등록되어 있었으나 삭제됐을 가능성 점검.
2. **`kairos-deployer` SA의 `roles/artifactregistry.writer` 권한 복원** (PR #23 후속에서 제거됐을 경우).
3. **GitHub Secrets에서 9개 앱 시크릿 제거** (선택 — 사용 안 하지만 남아있어도 문제 없음).
4. **GHCR 패키지 `kairos/api` 삭제** (선택 — 사용 안 하지만 정리 가치 있음).

### 4.3 유지되는 부분 (PR #23 작업 중 보존)

- **WIF 인증** — `GCP_WIF_PROVIDER`, `GCP_DEPLOYER_SA` 사용 그대로.
- **E2E 인프라 안정화** — auth.setup.ts 워크스페이스 보장, CORS 우회, meeting-upload 폴링 버그 수정 등.
- **환경변수 문서화** — `secrets.md`, `README.md` 신규.

---

## 5. 자의 결정 라벨

| 라벨 | 결정 | 근거 |
|---|---|---|
| AD-36 | C-1 채택 (B 대신) | MVP 단계 오버엔지니어링 회피, AWS 이전 시기 미정 |
| AD-37 | C-2가 아닌 완전 revert | 일관성·보안 후퇴 방지 우선 |
| AD-38 | GHCR 패키지 삭제 (선택) | 사용 안 함. 정리로 혼란 회피. |

---

## 6. 후속 검토 조건

이 결정은 다음 조건 충족 시 재검토:
- AWS 이전이 6개월 이내 확정 → Remote Repo 패턴 또는 GHCR+GAR 미러 패턴으로 supersede
- 멀티 클라우드 운영 필요 발생 → 동일
- 팀 규모 2명+ → secret 분리 정책 재설계 (Secret Manager IAM 세분화)
