// favicon.ico 형식 가드 — 빌드 없이 결정적으로 (T-PWA-03 의 정적 부분, docs/requirements/pwa.md §4.2)
//
// ★Turbopack 의 ICO 디코더는 ICO 안의 PNG 항목이 RGBA(colortype 6, 8bit) 여야 한다.
//   RGB(colortype 2) 면 `next build` 가 "The PNG is not in RGBA format!" 로 실패한다
//   (2026-10-02 오케스트레이터 빌드 실측). e2e T-PWA-03 은 빌드가 성공해야 돌므로 여기서 먼저 잡는다.
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const FAVICON_PATH = path.resolve(__dirname, "../../../app/favicon.ico");
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const PNG_COLOR_TYPE_RGBA = 6;

function readIcoEntries(ico: Buffer) {
  const count = ico.readUInt16LE(4);
  return Array.from({ length: count }, (_, index) => {
    const base = 6 + 16 * index;
    const length = ico.readUInt32LE(base + 8);
    const offset = ico.readUInt32LE(base + 12);
    const body = ico.subarray(offset, offset + length);
    return {
      directorySize: ico[base] === 0 ? 256 : ico[base],
      isPng: body.subarray(0, 8).equals(PNG_SIGNATURE),
      width: body.readUInt32BE(16),
      height: body.readUInt32BE(20),
      bitDepth: body[24],
      colorType: body[25],
    };
  });
}

describe("favicon.ico", () => {
  const ico = readFileSync(FAVICON_PATH);

  it("ICO 헤더 (reserved 0 · type 1)", () => {
    expect(ico.readUInt16LE(0)).toBe(0);
    expect(ico.readUInt16LE(2)).toBe(1);
  });

  it("항목 3개 = 16·32·48, 각 항목이 8bit RGBA PNG (Turbopack ICO 디코더 요구)", () => {
    const entries = readIcoEntries(ico);
    expect(entries.map((entry) => entry.directorySize)).toEqual([16, 32, 48]);
    for (const entry of entries) {
      expect(entry.isPng, `${entry.directorySize}px PNG 시그니처`).toBe(true);
      expect([entry.width, entry.height], `${entry.directorySize}px IHDR 크기`).toEqual([
        entry.directorySize,
        entry.directorySize,
      ]);
      expect(entry.bitDepth, `${entry.directorySize}px bitdepth`).toBe(8);
      expect(entry.colorType, `${entry.directorySize}px colortype`).toBe(PNG_COLOR_TYPE_RGBA);
    }
  });
});
