// 웹 푸시 FE 순수 유틸 — 키 변환 · 지원 감지 · iOS 설치 안내 조건 · 구독 → API-002 본문
// (docs/requirements/pwa.md §5.5 · §5.6)
import type { PushSubscriptionUpsertBody } from "./api";

/** VAPID 공개키(base64url, 패딩 없음) → `applicationServerKey` 용 바이트 */
export function base64UrlToUint8Array(value: string): Uint8Array<ArrayBuffer> {
  const base64 = (value + "=".repeat((4 - (value.length % 4)) % 4))
    .replace(/-/g, "+")
    .replace(/_/g, "/");
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

export function uint8ArrayToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/**
 * 기존 구독이 현재 VAPID 공개키로 만들어졌는지 — 키가 바뀌었으면(운영 키 교체) 그 구독은
 * 우리 서버가 서명한 푸시를 받지 못하므로 먼저 unsubscribe 해야 한다.
 */
export function isSameApplicationServerKey(
  current: ArrayBuffer | null,
  expected: Uint8Array,
): boolean {
  if (!current || current.byteLength !== expected.byteLength) return false;
  const currentBytes = new Uint8Array(current);
  return currentBytes.every((byte, index) => byte === expected[index]);
}

/** PushSubscription.toJSON() → API-002 본문. endpoint·keys 가 빠졌으면 null. */
export function toUpsertBody(json: PushSubscriptionJSON): PushSubscriptionUpsertBody | null {
  const endpoint = json.endpoint;
  const p256dh = json.keys?.p256dh;
  const auth = json.keys?.auth;
  if (!endpoint || !p256dh || !auth) return null;
  return { endpoint, keys: { p256dh, auth } };
}

export interface PushEnvironment {
  readonly hasServiceWorker: boolean;
  readonly hasPushManager: boolean;
  readonly hasNotification: boolean;
  readonly isSecureContext: boolean;
  readonly userAgent: string;
  readonly platform: string;
  readonly maxTouchPoints: number;
  /** iOS Safari 전용 `navigator.standalone` */
  readonly isNavigatorStandalone: boolean;
  readonly isDisplayModeStandalone: boolean;
  readonly notificationPermission: NotificationPermission | null;
}

/** 브라우저에서만 호출한다 (effect·이벤트 핸들러 안) — SSR 에는 navigator 가 없다. */
export function readPushEnvironment(): PushEnvironment {
  const hasNotification = "Notification" in window;
  return {
    hasServiceWorker: "serviceWorker" in navigator,
    hasPushManager: "PushManager" in window,
    hasNotification,
    isSecureContext: window.isSecureContext,
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    maxTouchPoints: navigator.maxTouchPoints,
    isNavigatorStandalone: "standalone" in navigator && navigator.standalone === true,
    isDisplayModeStandalone:
      typeof window.matchMedia === "function" &&
      window.matchMedia("(display-mode: standalone)").matches,
    notificationPermission: hasNotification ? Notification.permission : null,
  };
}

/** PushManager·Notification·SW 지원 + 보안 컨텍스트. SW 등록 유무는 따로 본다 (getRegistration). */
export function isPushSupported(
  env: Pick<
    PushEnvironment,
    "hasServiceWorker" | "hasPushManager" | "hasNotification" | "isSecureContext"
  >,
): boolean {
  return env.hasServiceWorker && env.hasPushManager && env.hasNotification && env.isSecureContext;
}

const IOS_DEVICE_RE = /iPad|iPhone|iPod/;

/**
 * REQ-011 — iOS·iPadOS 에서 홈 화면 앱이 아닐 때만 안내한다 (iOS 16.4+ 는 홈 화면 앱에서만 푸시,
 * Next 번들 문서 progressive-web-apps.md:88). iPadOS 는 데스크톱 UA(MacIntel)라 터치 포인트로 가른다.
 */
export function shouldShowIosInstallHint(
  env: Pick<
    PushEnvironment,
    "userAgent" | "platform" | "maxTouchPoints" | "isNavigatorStandalone" | "isDisplayModeStandalone"
  >,
): boolean {
  const isIosDevice =
    IOS_DEVICE_RE.test(env.userAgent) || (env.platform === "MacIntel" && env.maxTouchPoints > 1);
  return isIosDevice && !env.isNavigatorStandalone && !env.isDisplayModeStandalone;
}
