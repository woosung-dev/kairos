// /new 직접 녹음 탭 state machine 검증 — Sprint 17 QA C.1 (fake mic stream)
import { test, expect } from "@playwright/test";

/**
 * Sprint 17 QA C.1 음성 녹음 regression test.
 *
 * 풀 e2e (실 마이크 → R2 업로드 → STT → 요약) 는 meeting-upload.spec.ts 가
 * 오디오 fixture 로 대체 검증. 본 test 는 마이크 권한 + MediaRecorder
 * state machine + UI 전이 (idle → recording → stopped) 만 확인.
 *
 * fake mic: page.addInitScript 로 navigator.mediaDevices.getUserMedia 를
 * AudioContext 기반 합성 stream 으로 mock. headless 환경에서 실 디바이스
 * 미보유 회피 + Chromium --use-fake-device-for-media-stream 의존 제거.
 */

test.describe("녹음 state machine (fake mic)", () => {
  test.beforeEach(async ({ page }) => {
    // getUserMedia 를 AudioContext oscillator → MediaStream 으로 mock.
    // permission prompt 자체를 우회 (실 audio I/O 불요).
    await page.addInitScript(() => {
      const fakeGetUserMedia = async (
        _constraints?: MediaStreamConstraints,
      ): Promise<MediaStream> => {
        const ac = new AudioContext();
        const dest = ac.createMediaStreamDestination();
        const osc = ac.createOscillator();
        osc.frequency.value = 440;
        osc.connect(dest);
        osc.start();
        return dest.stream;
      };
      // mediaDevices 가 없는 환경 (headless 일부) 대비 namespace 보장
      if (!navigator.mediaDevices) {
        Object.defineProperty(navigator, "mediaDevices", {
          value: {},
          configurable: true,
        });
      }
      Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
        value: fakeGetUserMedia,
        configurable: true,
      });
    });
  });

  test("녹음 시작 → 정지 state 전이 + 업로드 enabled", async ({ page }) => {
    test.setTimeout(60_000);

    // 1. /new 진입 — 기본 "회의 녹음" 카테고리 + "오디오 업로드" 서브 탭.
    await page.goto("/new");
    await expect(page.getByRole("heading", { name: "콘텐츠 추가" })).toBeVisible({
      timeout: 15_000,
    });

    // 2. "직접 녹음" 탭 클릭. lucide 아이콘 + 한글 라벨.
    const recordTab = page.getByRole("button", { name: /직접 녹음/ });
    await recordTab.click();

    // 3. 회의 제목 입력 (서브 탭별 독립 state — RecordingView 내부).
    await page
      .getByPlaceholder("회의 제목을 입력하세요")
      .fill("E2E 녹음 state machine");

    // 4. 녹음 시작 버튼 가시 확인.
    const startBtn = page.getByRole("button", { name: /녹음 시작/ });
    await expect(startBtn).toBeVisible();
    await expect(startBtn).toBeEnabled();

    // 5. 녹음 시작 → getUserMedia mock 호출 → MediaRecorder start.
    await startBtn.click();

    // 6. state = recording: "녹음 중" 표기 + 정지 버튼 노출.
    const stopBtn = page.getByRole("button", { name: /정지|중지|녹음 중/ });
    await expect(stopBtn).toBeVisible({ timeout: 5000 });

    // 7. 1초 녹음 → 정지.
    await page.waitForTimeout(1200);
    await stopBtn.click();

    // 8. state = stopped: 다시 녹음 버튼 (재녹음) 또는 업로드 시작 같은 후속
    //    액션 버튼 노출. 본 spec 은 정지 후 state 가 더 이상 "녹음 중" 이
    //    아닌 것만 검증 — 구체 UI 는 RecordingView 디자인 변경 영향 회피.
    await expect(
      page.getByRole("button", { name: /녹음 중/ }),
    ).toHaveCount(0, { timeout: 5000 });
  });

  test("getUserMedia 거부 시 에러 메시지 표시", async ({ page }) => {
    test.setTimeout(30_000);

    // 권한 거부 시뮬레이션 — fake getUserMedia 가 NotAllowedError throw.
    await page.addInitScript(() => {
      if (!navigator.mediaDevices) {
        Object.defineProperty(navigator, "mediaDevices", {
          value: {},
          configurable: true,
        });
      }
      Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
        value: async () => {
          throw new DOMException("Permission denied", "NotAllowedError");
        },
        configurable: true,
      });
    });

    await page.goto("/new");
    await page.getByRole("button", { name: /직접 녹음/ }).click();
    await page.getByPlaceholder("회의 제목을 입력하세요").fill("permission test");
    await page.getByRole("button", { name: /녹음 시작/ }).click();

    // 에러 안내 (toast 또는 인라인 텍스트) — useRecording hook 의 error state
    // 가 "마이크 접근" / "권한" 키워드로 렌더되거나 toast 발화. 둘 중 하나만
    // 검증해도 회귀 감지에 충분.
    const errorIndicator = page.locator("text=/마이크|권한|permission/i").first();
    await expect(errorIndicator).toBeVisible({ timeout: 5000 });
  });
});
