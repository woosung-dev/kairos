#!/usr/bin/env bash
# release.yml 배포 job 이 부른다 — 배포 전용 키로 서버의 forced command 하나를 실행한다 (ADR-028 D7 Phase B).
#
#   사용: deploy-ssh.sh <tag> [--migrate]     (레포 루트에서, 배포할 커밋으로 checkout 한 상태)
#   env : DEPLOY_SSH_KEY · DEPLOY_HOST · DEPLOY_HOST_KEY  (Environment 시크릿 — 전부 시크릿이라 로그에 가려진다)
#
# 서버 쪽 authorized_keys 가 이 키를 `kairos-deploy.sh --from-ssh` 로 묶는다 — 이 키로 할 수 있는 일은
# `<tag> --files <sha256> [--migrate]` 형식의 배포 하나뿐이다. 판정(스키마 관문 · 처리 중 회의 대기 ·
# 기동 확인)은 서버 스크립트가 하고, 종료 코드를 그대로 돌려준다 (3 = 스키마 승인 필요).
# compose·서버 스크립트는 보내지 않는다 — 이 커밋의 두 파일을 이은 해시만 보내고 서버가 자기 파일과 대조한다.
set -euo pipefail
tag="${1:?tag 가 필요하다}"
migrate="${2:-}"
[[ "$tag" =~ ^sha-[0-9a-f]{7}$ ]] || { echo "✗ 태그 형식 오류: $tag"; exit 2; }
[ -z "$migrate" ] || [ "$migrate" = "--migrate" ] || { echo "✗ 두 번째 인자는 --migrate 만: $migrate"; exit 2; }

for v in DEPLOY_SSH_KEY DEPLOY_HOST DEPLOY_HOST_KEY; do
  [ -n "${!v:-}" ] || { echo "✗ Environment 에 $v 가 없다 (조용히 건너뛰지 않는다)"; exit 1; }
done
mkdir -p ~/.ssh && chmod 700 ~/.ssh
printf '%s\n' "$DEPLOY_SSH_KEY" > ~/.ssh/deploy_key && chmod 600 ~/.ssh/deploy_key
printf '%s\n' "$DEPLOY_HOST_KEY" > ~/.ssh/known_hosts
# 주석 줄만 들어 있으면 키가 0개다 — ssh 전에 잰다 (quant-bridge 2026-10-02 첫 자동 배포 실측: ssh-keyscan 첫 줄은 주석)
ssh-keygen -lf ~/.ssh/known_hosts >/dev/null || { echo "✗ DEPLOY_HOST_KEY 에 호스트 키 줄이 없다"; exit 1; }

files_sha=$(cat deploy/oci/docker-compose.prod.yml deploy/oci/bin/kairos-deploy.sh | sha256sum | cut -d' ' -f1)
# ServerAlive — 처리 중 회의 대기(최대 30분) 동안 출력이 1분에 한 줄이라 연결이 끊기지 않게 한다
# -F /dev/null · UserKnownHostsFile — 사용자 ssh 설정·기본 known_hosts 를 읽지 않는다 (맥에서 같은 명령으로 시험할 수 있게)
ssh -F /dev/null -i ~/.ssh/deploy_key -o IdentitiesOnly=yes -o BatchMode=yes \
  -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$HOME/.ssh/known_hosts" \
  -o ConnectTimeout=20 -o ServerAliveInterval=30 -o ServerAliveCountMax=6 \
  "ubuntu@$DEPLOY_HOST" "$tag --files $files_sha${migrate:+ $migrate}"
