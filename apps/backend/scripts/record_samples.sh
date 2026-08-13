#!/usr/bin/env bash
# Sprint 15 Day 0 spike audio sample 녹음 자동화 (macOS only, ffmpeg + avfoundation)
# 7 sample 일괄 녹음. founder 30분 → 인터랙티브 ~15분.
#
# 의존: ffmpeg (brew install ffmpeg) — 검증 통과 (v8.1.1)
# 사용:
#   chmod +x apps/backend/scripts/record_samples.sh
#   bash apps/backend/scripts/record_samples.sh
#   bash apps/backend/scripts/record_samples.sh --device 0   # 마이크 device index 명시
#   bash apps/backend/scripts/record_samples.sh --skip-long  # 5min 큰 sample skip
#   bash apps/backend/scripts/record_samples.sh --silent-only  # silent 1개만
#
# 출력: apps/backend/scripts/samples/*.webm + *.mp4
# 후속: cd apps/backend && uv run python scripts/sprint15_day0_spike.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAMPLES_DIR="$SCRIPT_DIR/samples"
mkdir -p "$SAMPLES_DIR"

DEVICE_INDEX=""
SKIP_LONG=0
SILENT_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device) DEVICE_INDEX="$2"; shift 2 ;;
    --skip-long) SKIP_LONG=1; shift ;;
    --silent-only) SILENT_ONLY=1; shift ;;
    -h|--help)
      sed -n '2,15p' "$0"
      exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ERROR: ffmpeg 필요. brew install ffmpeg" >&2
  exit 1
fi

# ---- macOS only ----
if [[ "$(uname)" != "Darwin" ]]; then
  echo "ERROR: macOS only (ffmpeg avfoundation). Linux/Windows는 별도 처리." >&2
  exit 1
fi

# ---- Mic device 감지 (silent-only 모드에서는 skip) ----
if [[ -z "$DEVICE_INDEX" && "$SILENT_ONLY" -eq 0 ]]; then
  echo ""
  echo "===== Mic devices 검색 (ffmpeg avfoundation) ====="
  ffmpeg -hide_banner -f avfoundation -list_devices true -i "" 2>&1 | grep -A 20 "AVFoundation audio devices" || true
  echo ""
  if [[ -t 0 ]]; then
    read -rp "사용할 audio device index 입력 (보통 0): " DEVICE_INDEX || true
  fi
  DEVICE_INDEX="${DEVICE_INDEX:-0}"
fi

echo ""
echo "===== 설정 ====="
echo "Device: avfoundation :${DEVICE_INDEX}"
echo "Output: $SAMPLES_DIR"
echo "Skip long (5min): $SKIP_LONG"
echo "Silent only: $SILENT_ONLY"
echo ""

# ---- 헬퍼 ----
countdown() {
  local n="$1"
  for ((i=n; i>0; i--)); do
    printf "\r  ▶ %d초 후 시작..." "$i"
    sleep 1
  done
  printf "\r  🎙️  녹음 중...        \n"
}

record_audio() {
  # $1: filename, $2: duration sec, $3: codec/format (webm|mp4), $4: 발화 가이드
  local fname="$1" dur="$2" fmt="$3" guide="$4"
  local out="$SAMPLES_DIR/$fname"

  echo ""
  echo "------------------------------------------------------------"
  echo "  Sample: $fname ($dur sec)"
  echo "  발화 가이드: $guide"
  echo "------------------------------------------------------------"
  read -rp "  Enter 누르면 3초 카운트다운 시작 (skip=s) > " ans
  if [[ "$ans" == "s" ]]; then
    echo "  skipped."
    return
  fi
  countdown 3

  if [[ "$fmt" == "webm" ]]; then
    # Chrome 기본 = libopus webm (MediaRecorder)
    ffmpeg -hide_banner -loglevel error -y \
      -f avfoundation -i ":${DEVICE_INDEX}" -t "$dur" \
      -c:a libopus -b:a 64k -application voip \
      "$out"
  else
    # iOS = mp4 + aac
    ffmpeg -hide_banner -loglevel error -y \
      -f avfoundation -i ":${DEVICE_INDEX}" -t "$dur" \
      -c:a aac -b:a 96k \
      "$out"
  fi
  echo "  ✅ saved: $(ls -lh "$out" | awk '{print $5, $9}')"
}

record_silent() {
  # 무음 sample = lavfi anullsrc
  local fname="$1" dur="$2" fmt="$3"
  local out="$SAMPLES_DIR/$fname"
  echo ""
  echo "  Sample: $fname ($dur sec, 무음)"
  if [[ "$fmt" == "webm" ]]; then
    ffmpeg -hide_banner -loglevel error -y \
      -f lavfi -i "anullsrc=r=48000:cl=mono" -t "$dur" \
      -c:a libopus -b:a 64k \
      "$out"
  else
    ffmpeg -hide_banner -loglevel error -y \
      -f lavfi -i "anullsrc=r=48000:cl=mono" -t "$dur" \
      -c:a aac -b:a 96k \
      "$out"
  fi
  echo "  ✅ saved (silent): $(ls -lh "$out" | awk '{print $5, $9}')"
}

# ---- silent 먼저 (마이크 없이 가능) ----
record_silent "silent_10s.webm" 10 webm

if [[ "$SILENT_ONLY" -eq 1 ]]; then
  echo ""
  echo "===== silent-only 완료 ====="
  exit 0
fi

# ---- 일반 audio sample ----
record_audio "chrome_10s.webm"      10  webm "안녕하세요, 테스트 메모입니다 정도"
record_audio "chrome_60s.webm"      60  webm "평범한 회의/메모 분량 1분. 회사 + 프로젝트 + 결정사항 자유 발화"
record_audio "ios_10s.mp4"          10  mp4  "iOS MIME 검증용 짧은 발화 (내용은 자유)"
record_audio "ios_60s.mp4"          60  mp4  "iOS MIME 검증용 1분 발화"
record_audio "ko_filler_60s.webm"   60  webm "어... 음... 그러니까... filler를 자주 끼워서 1분 발화"

if [[ "$SKIP_LONG" -eq 1 ]]; then
  echo ""
  echo "===== chrome_5min skip (--skip-long). 다른 6개 완료 ====="
else
  record_audio "chrome_5min.webm"   300 webm "5분 회의 길이 stress. 회의 시나리오 자유 발화 (도중 휴식 OK, 끊지 말고 음... 으로 채움)"
fi

echo ""
echo "===== 7 sample 녹음 완료 ====="
ls -lh "$SAMPLES_DIR" | grep -E "\.(webm|mp4)$"

echo ""
echo "===== 다음 단계 ====="
echo "  cd apps/backend && uv run python scripts/sprint15_day0_spike.py"
echo "  # 결과 → git history §3.1 / §3.3 audio 결과 paste"
