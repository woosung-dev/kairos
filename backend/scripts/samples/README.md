# Sprint 15 Day 0 Spike — Audio Sample 녹음 가이드

> **목적**: `sprint15_day0_spike.py`가 측정할 audio sample 7개. founder ~30분 녹음.
>
> **파일은 git ignore** (개인 음성 데이터). `.gitignore`에 `backend/scripts/samples/*.webm` `*.mp4` 등록되어 있음.

---

## 녹음 사양

| Filename | 길이 | 환경 | 발화 내용 가이드 |
|----------|------|------|----------------|
| `chrome_10s.webm` | 10s | Chrome MacOS | "안녕하세요, 테스트 메모입니다" 정도 |
| `chrome_60s.webm` | 60s | Chrome MacOS | 평범한 회의/메모 길이 |
| `chrome_5min.webm` | 5min | Chrome MacOS | 회의 길이 stress test |
| `ios_10s.mp4` | 10s | iOS Safari | iOS MIME (mp4) 검증 |
| `ios_60s.mp4` | 60s | iOS Safari | iOS MIME 검증 |
| `ko_filler_60s.webm` | 60s | Chrome MacOS | "어… 음… 그러니까…" filler 다수 |
| `silent_10s.webm` | 10s | Chrome MacOS | 무음 (edge case) |

---

## 녹음 방법

### 옵션 0: 자동화 cli (가장 빠름, macOS only)

`backend/scripts/record_samples.sh` — ffmpeg + avfoundation 인터랙티브 녹음. 7 sample 일괄 ~15분.

```bash
chmod +x backend/scripts/record_samples.sh
bash backend/scripts/record_samples.sh           # 일반 (5min 포함)
bash backend/scripts/record_samples.sh --skip-long  # 5min skip (~10분)
bash backend/scripts/record_samples.sh --silent-only  # 무음 1개만 (smoke)
```

장점: 카운트다운 + 파일명 자동 + 코덱 자동 (webm libopus / mp4 aac). 단점: iOS sample도 macOS mic로 녹음됨 → 진짜 iOS MIME 검증 필요 시 옵션 A 병행.

### 옵션 A: 브라우저 MediaRecorder (FE 실제 흐름)

```html
<!-- record.html, 로컬에서 file:// 또는 http 서빙 -->
<button onclick="start()">시작</button>
<button onclick="stop()">중지 + 다운로드</button>
<script>
let mr, chunks = [];
async function start() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mr = new MediaRecorder(stream);
  chunks = [];
  mr.ondataavailable = e => chunks.push(e.data);
  mr.onstop = () => {
    const blob = new Blob(chunks, { type: mr.mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `record-${Date.now()}.${mr.mimeType.includes("mp4") ? "mp4" : "webm"}`;
    a.click();
  };
  mr.start();
}
function stop() { mr.stop(); }
</script>
```

iOS Safari로 같은 페이지 열어 mp4 sample 생성.

### 옵션 B: ffmpeg 직접

```bash
# 마이크 입력 → webm 10초
ffmpeg -f avfoundation -i ":0" -t 10 -c:a libopus -ar 16000 -ac 1 chrome_10s.webm

# 무음 10초 webm
ffmpeg -f lavfi -i anullsrc=channel_layout=mono:sample_rate=16000 -t 10 -c:a libopus silent_10s.webm

# 기존 wav → mp4 변환 (iOS sample 대체)
ffmpeg -i input.wav -t 10 -c:a aac ios_10s.mp4
```

---

## 검증

```bash
ls -lh backend/scripts/samples/
# 7개 파일 확인 (10s ~ 5min, webm/mp4 혼합)

cd backend
uv run python scripts/sprint15_day0_spike.py
# 출력: per-sample latency/cost + aggregate + threshold violations
# 결과 paste → docs/dev-log/sprints/sprint-15-cost-spike.md
```

누락 sample은 자동 skip + log. 최소 1개만 있어도 partial spike 가능.

---

## .gitignore 확인

`backend/scripts/samples/*.webm` `*.mp4` `*.wav` 패턴 ignore — 본 README + `.gitkeep`만 commit.
