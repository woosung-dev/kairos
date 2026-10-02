// T-PWA-45 (키 변환 · 지원 감지) · T-PWA-56 (iOS 안내 조건) — docs/plans/active/2026-10-02-pwa/test-matrix.md
import { describe, expect, it } from "vitest";
import {
  base64UrlToUint8Array,
  isPushSupported,
  isSameApplicationServerKey,
  shouldShowIosInstallHint,
  toUpsertBody,
  uint8ArrayToBase64Url,
  type PushEnvironment,
} from "../utils";

// 65바이트 비압축 P-256 공개키 모양 (0x04 + 64바이트) — '-' '_' 가 섞이도록 고른 값
const VAPID_PUBLIC_KEY =
  "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U";

const SUPPORTED_ENV: PushEnvironment = {
  hasServiceWorker: true,
  hasPushManager: true,
  hasNotification: true,
  isSecureContext: true,
  userAgent:
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36",
  platform: "MacIntel",
  maxTouchPoints: 0,
  isNavigatorStandalone: false,
  isDisplayModeStandalone: false,
  notificationPermission: "default",
};

const IPHONE_UA =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1";
const ANDROID_UA =
  "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Mobile Safari/537.36";

describe("T-PWA-45 base64url ↔ Uint8Array", () => {
  it("VAPID 공개키를 65바이트로 풀고 같은 문자열로 되돌린다", () => {
    const bytes = base64UrlToUint8Array(VAPID_PUBLIC_KEY);
    expect(bytes).toHaveLength(65);
    expect(bytes[0]).toBe(0x04);
    expect(uint8ArrayToBase64Url(bytes)).toBe(VAPID_PUBLIC_KEY);
  });

  it("패딩이 필요한 길이도 왕복한다", () => {
    for (const length of [1, 2, 3, 4, 5]) {
      const bytes = Uint8Array.from({ length }, (_, index) => 250 - index);
      expect(base64UrlToUint8Array(uint8ArrayToBase64Url(bytes))).toEqual(bytes);
    }
  });

  it("applicationServerKey 비교 — 같은 바이트만 true", () => {
    const expected = base64UrlToUint8Array(VAPID_PUBLIC_KEY);
    expect(isSameApplicationServerKey(expected.slice().buffer, expected)).toBe(true);
    const changed = expected.slice();
    changed[10] ^= 1;
    expect(isSameApplicationServerKey(changed.buffer, expected)).toBe(false);
    expect(isSameApplicationServerKey(new ArrayBuffer(3), expected)).toBe(false);
    expect(isSameApplicationServerKey(null, expected)).toBe(false);
  });
});

describe("T-PWA-45 지원 감지", () => {
  it("SW · PushManager · Notification · secure context 가 모두 있어야 지원", () => {
    expect(isPushSupported(SUPPORTED_ENV)).toBe(true);
    for (const key of [
      "hasServiceWorker",
      "hasPushManager",
      "hasNotification",
      "isSecureContext",
    ] as const) {
      expect(isPushSupported({ ...SUPPORTED_ENV, [key]: false }), key).toBe(false);
    }
  });
});

describe("toUpsertBody — PushSubscription.toJSON() → API-002 본문", () => {
  it("endpoint · keys 만 옮긴다", () => {
    expect(
      toUpsertBody({
        endpoint: "https://fcm.googleapis.com/fcm/send/abc",
        expirationTime: null,
        keys: { p256dh: "p", auth: "a" },
      }),
    ).toEqual({ endpoint: "https://fcm.googleapis.com/fcm/send/abc", keys: { p256dh: "p", auth: "a" } });
  });

  it("endpoint 나 키가 빠지면 null", () => {
    expect(toUpsertBody({ keys: { p256dh: "p", auth: "a" } })).toBeNull();
    expect(toUpsertBody({ endpoint: "https://push.example/x", keys: { p256dh: "p" } })).toBeNull();
    expect(toUpsertBody({ endpoint: "https://push.example/x" })).toBeNull();
  });
});

describe("T-PWA-56 iOS 설치 안내 표시 조건 (REQ-011)", () => {
  it("iPhone UA + 비standalone → 표시", () => {
    expect(
      shouldShowIosInstallHint({ ...SUPPORTED_ENV, userAgent: IPHONE_UA, platform: "iPhone", maxTouchPoints: 5 }),
    ).toBe(true);
  });

  it("iPadOS (데스크톱 UA · MacIntel + 터치) → 표시", () => {
    expect(shouldShowIosInstallHint({ ...SUPPORTED_ENV, maxTouchPoints: 5 })).toBe(true);
  });

  it("홈 화면 앱(standalone) → 미표시", () => {
    const iphone = { ...SUPPORTED_ENV, userAgent: IPHONE_UA, platform: "iPhone", maxTouchPoints: 5 };
    expect(shouldShowIosInstallHint({ ...iphone, isNavigatorStandalone: true })).toBe(false);
    expect(shouldShowIosInstallHint({ ...iphone, isDisplayModeStandalone: true })).toBe(false);
  });

  it("Android · 데스크톱 → 미표시", () => {
    expect(
      shouldShowIosInstallHint({ ...SUPPORTED_ENV, userAgent: ANDROID_UA, platform: "Linux armv81", maxTouchPoints: 5 }),
    ).toBe(false);
    expect(shouldShowIosInstallHint(SUPPORTED_ENV)).toBe(false);
  });
});
