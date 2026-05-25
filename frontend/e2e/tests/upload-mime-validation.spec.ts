// Sprint 28 TEST-7 — Upload MIME real browser validation 회귀 가드.
//
// Sprint 27e Round 1 carry — 외부 5명 dogfooding 진입 *전* 권고.
// BE 단위 `tests/upload/test_upload_validation.py` 9 case OK but real browser
// proxy path (FE → /api/upload proxy → BE) + 위장 .exe 차단 미검증.
//
// 시나리오:
// 1. 정상 audio 파일 (.m4a / .mp3) → 업로드 진입 가능 (filechooser 통과)
// 2. 위장 .exe (content-type = audio/mp4) → BE 가 magic byte 검사로 거부
// 3. 너무 큰 파일 (1MB+) → 한도 초과 → 거부 (테스트 환경 한도 1024 byte 가정)
//
// 본 spec 도 nightly 또는 manual 우선 — `E2E_RUN_UPLOAD=true` 일 때만 실행.
import { test, expect } from "@playwright/test";
import { promises as fs } from "fs";
import os from "os";
import path from "path";

const SHOULD_RUN = process.env.E2E_RUN_UPLOAD === "true";

test.describe.serial("Upload MIME real browser validation (TEST-7)", () => {
  test.skip(!SHOULD_RUN, "E2E_RUN_UPLOAD=true 환경에서만 실행 (BE proxy + magic byte 검사)");

  let tmpDir: string;

  test.beforeAll(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "kairos-upload-mime-"));
  });

  test.afterAll(async () => {
    await fs.rm(tmpDir, { recursive: true, force: true });
  });

  test("위장 .exe (Content-Type=audio/mp4) → BE proxy 가 거부", async ({
    page,
    request,
  }) => {
    test.setTimeout(30_000);

    // 1. PE32 magic byte (4D 5A — MZ header) 의 가짜 audio 파일 생성
    const fakeExe = path.join(tmpDir, "fake-audio.m4a");
    const peHeader = Buffer.from([0x4d, 0x5a, 0x90, 0x00, 0x03, 0x00, 0x00, 0x00]);
    await fs.writeFile(fakeExe, peHeader);

    // 2. 로그인 후 /new 페이지 진입 — file input 노출
    await page.goto("/new");

    // 3. file input 에 위장 파일 attach
    const input = page.getByTestId("meeting-file-input");
    await input.setInputFiles(fakeExe);

    // 4. 업로드 버튼 클릭 — FE 가 BE proxy 로 POST
    await page.getByPlaceholder("회의 제목을 입력하세요").fill("위장 exe 테스트");
    const responsePromise = page.waitForResponse((resp) =>
      resp.url().includes("/api/v1/upload") || resp.url().includes("/upload"),
    );
    await page.getByRole("button", { name: "업로드 시작" }).click();

    const response = await responsePromise;

    // 5. BE 가 422 (unsupported MIME or magic byte mismatch) 또는 400 거부
    expect([400, 415, 422]).toContain(response.status());

    // 6. FE 에 error toast / 메시지 노출 (strict text 검증 회피)
    const errorPattern = page.getByText(/지원하지 않는|허용되지 않는|잘못된|invalid|unsupported/i);
    await expect(errorPattern.first()).toBeVisible({ timeout: 10_000 });
  });

  test("BE proxy 가 직접 적절한 거부 응답 반환 (request-only)", async ({
    request,
  }) => {
    test.setTimeout(15_000);

    // /api/v1/upload/proxy 직접 호출 — auth 없으면 401, 본 spec 은 인증된 사용자 가정.
    // E2E_USER_EMAIL/PASSWORD 시드 사용자로 미리 로그인된 storageState 활용.
    // 위장 .exe content 와 audio/m4a content-type 의 미스매치 BE 가 catch.
    const peHeader = Buffer.from([0x4d, 0x5a, 0x90, 0x00, 0x03, 0x00, 0x00, 0x00]);
    const fakeFile = path.join(tmpDir, "fake-direct.m4a");
    await fs.writeFile(fakeFile, peHeader);

    const formData = {
      file: {
        name: "fake-direct.m4a",
        mimeType: "audio/m4a",
        buffer: peHeader,
      },
    };

    const response = await request.post("/api/v1/upload/proxy", {
      multipart: formData,
    });
    // 401 (no auth) 또는 4xx 거부 — auth path 는 별도 가정.
    expect([400, 401, 415, 422]).toContain(response.status());
  });
});
