// 웹 푸시 기기 흐름 — 상태 판정 · 켜기 · 끄기(로그아웃 정리와 같다) · 앱 로드 동기화
// (docs/requirements/pwa.md §5.5 · §5.6)
//
// ★SW 등록은 `getRegistration()` 1회로만 얻는다. 등록 대기 promise(`serviceWorker.ready`)는 쓰지 않는다 —
//   등록 없음 상태(dev · kill-switch · 미지원/비보안 · 첫 방문 등록 전)에서는 영원히 resolve 되지 않아
//   로그아웃·설정 화면이 멈춘다 (pwa.md §4.5).
// ★푸시는 부가 기능이다 — 모든 흐름은 best-effort 이고 로그아웃·화면을 막지 않는다. 콘솔 error 도
//   남기지 않는다 (AGENTS.md §4 증거 표준 "console.error 0건").
import type { ApiClient } from "@/lib/api-client";

import { deletePushSubscription, upsertPushSubscription } from "./api";
import {
  deleteOwnerMarkerIfMatches,
  getBrowserMarkerStorage,
  readOwnerMarker,
  writeOwnerMarker,
  type MarkerStorage,
} from "./marker";
import {
  base64UrlToUint8Array,
  isPushSupported,
  isSameApplicationServerKey,
  shouldShowIosInstallHint,
  toUpsertBody,
  type PushEnvironment,
} from "./utils";

/** API-003 대기 상한이자 로그아웃 추가 지연 상한 (pwa.md §5.5) */
export const PUSH_CLEANUP_TIMEOUT_MS = 3_000;

export interface PushSubscriptionLike {
  readonly options: { readonly applicationServerKey: ArrayBuffer | null };
  toJSON(): PushSubscriptionJSON;
  unsubscribe(): Promise<boolean>;
}

export interface PushRegistrationLike {
  readonly pushManager: {
    getSubscription(): Promise<PushSubscriptionLike | null>;
    subscribe(options: PushSubscriptionOptionsInit): Promise<PushSubscriptionLike>;
  };
}

export interface PushDeviceDeps {
  readonly getRegistration: () => Promise<PushRegistrationLike | undefined>;
  readonly storage: MarkerStorage | null;
}

export interface PushEnableDeps extends PushDeviceDeps {
  readonly requestPermission: () => Promise<NotificationPermission>;
}

function getServiceWorkerRegistration(): Promise<PushRegistrationLike | undefined> {
  if (!("serviceWorker" in navigator)) return Promise.resolve(undefined);
  return navigator.serviceWorker.getRegistration().catch(() => undefined);
}

/** 브라우저에서만 호출한다 (effect·이벤트 핸들러 안). */
export function createBrowserPushDeps(): PushEnableDeps {
  return {
    getRegistration: getServiceWorkerRegistration,
    storage: getBrowserMarkerStorage(),
    // 권한 요청은 토글 클릭(켜기) 흐름에서만 부른다 — 페이지 로드 시 0회 (pwa.md §5.5)
    requestPermission: () => Notification.requestPermission(),
  };
}

/** task 가 끝나거나 ms 가 지나면 resolve — reject 하지 않는다. */
function settleWithin(task: Promise<unknown>, ms: number): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    const finish = () => {
      clearTimeout(timer);
      resolve();
    };
    task.then(finish, finish);
  });
}

// 같은 subscriptionId 의 API-003 이 앱 로드 동기화와 로그아웃에서 겹치면 요청은 1번만 나가고
// 둘 다 같은 promise 를 기다린다 (pwa.md §5.5). settle 되면 지운다.
const pendingDeletes = new Map<string, Promise<void>>();

/** API-003 best-effort — 실패·3초 초과에도 resolve 한다. 진행 중이면 그 promise 를 돌려준다. */
export function deletePushSubscriptionShared(
  api: ApiClient,
  subscriptionId: string,
): Promise<void> {
  const pending = pendingDeletes.get(subscriptionId);
  if (pending) return pending;
  const request = settleWithin(
    deletePushSubscription(api, subscriptionId),
    PUSH_CLEANUP_TIMEOUT_MS,
  ).then(() => {
    pendingDeletes.delete(subscriptionId);
  });
  pendingDeletes.set(subscriptionId, request);
  return request;
}

async function unsubscribeDevice(deps: PushDeviceDeps): Promise<void> {
  const registration = await deps.getRegistration();
  if (!registration) return;
  const subscription = await registration.pushManager.getSubscription();
  await subscription?.unsubscribe();
}

/**
 * 구독이 API-001 의 현재 VAPID 공개키로 만들어졌는지. 키를 모르면(null) 비교하지 않고 true —
 * 운영 키 교체 뒤의 옛 구독은 우리 서버가 서명한 푸시를 받지 못한다 (pwa.md §5.5 키 불일치).
 */
function matchesCurrentVapidKey(
  subscription: PushSubscriptionLike,
  vapidPublicKey: string | null,
): boolean {
  if (vapidPublicKey === null) return true;
  return isSameApplicationServerKey(
    subscription.options.applicationServerKey,
    base64UrlToUint8Array(vapidPublicKey),
  );
}

export type PushDeviceState = "ios-install" | "unavailable" | "denied" | "off" | "on";

/**
 * SCR-002 상태 판정 (마운트 · controllerchange 때). 권한을 요청하지 않는다.
 * 구독이 옛 VAPID 키로 만들어졌으면 '꺼짐'이다 — 그 구독으로는 알림이 오지 않는다.
 */
export async function resolvePushDeviceState(
  meId: string,
  vapidPublicKey: string | null,
  env: PushEnvironment,
  deps: PushDeviceDeps,
): Promise<PushDeviceState> {
  if (shouldShowIosInstallHint(env)) return "ios-install";
  if (!isPushSupported(env)) return "unavailable";
  try {
    const registration = await deps.getRegistration();
    if (!registration) return "unavailable";
    if (env.notificationPermission === "denied") return "denied";
    const subscription = await registration.pushManager.getSubscription();
    const marker = readOwnerMarker(deps.storage);
    if (!subscription || marker?.userId !== meId) return "off";
    return matchesCurrentVapidKey(subscription, vapidPublicKey) ? "on" : "off";
  } catch {
    return "unavailable";
  }
}

export type EnablePushOutcome = "on" | "unavailable" | "denied" | "dismissed";

/**
 * 켜기 — 토글 클릭 핸들러 안에서만 부른다 (권한 요청이 들어 있다).
 * 실패(구독·API-002)는 throw — 호출부가 토스트 + 토글 원복을 한다.
 */
export async function enablePush(
  api: ApiClient,
  input: { readonly meId: string; readonly vapidPublicKey: string },
  deps: PushEnableDeps,
): Promise<EnablePushOutcome> {
  const registration = await deps.getRegistration();
  if (!registration) return "unavailable";
  const permission = await deps.requestPermission();
  if (permission === "denied") return "denied";
  if (permission !== "granted") return "dismissed";

  const applicationServerKey = base64UrlToUint8Array(input.vapidPublicKey);
  let existing = await registration.pushManager.getSubscription();
  if (
    existing &&
    !isSameApplicationServerKey(existing.options.applicationServerKey, applicationServerKey)
  ) {
    await existing.unsubscribe();
    existing = null;
  }
  const subscription =
    existing ??
    (await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey }));

  try {
    const body = toUpsertBody(subscription.toJSON());
    if (!body) throw new Error("push subscription has no endpoint or keys");
    const { id } = await upsertPushSubscription(api, body);
    writeOwnerMarker(deps.storage, { userId: input.meId, subscriptionId: id });
  } catch (error) {
    // 서버 행·표식이 없는 구독을 기기에 남기지 않는다 (fail-closed)
    await subscription.unsubscribe().catch(() => false);
    throw error;
  }
  return "on";
}

/**
 * 끄기 = 로그아웃 정리 (pwa.md §5.5) — ① 표식 id 로 API-003 ② 등록이 있으면 로컬 unsubscribe
 * ③ 표식 compare-and-delete. 전부 best-effort 이고 전체가 3초 안에 끝난다 (throw 하지 않는다).
 * ①은 등록이 없어도 보낸다 — 같은 로드 안에 kill-switch 로 등록만 사라진 잔여를 지운다.
 * ①·②는 함께 시작한다 (요청은 ①이 먼저 나간다) — 느린 네트워크(①)가 로컬 unsubscribe(②)의
 * 3초 예산을 다 써 버리면 로그아웃 뒤에도 이 기기가 푸시를 받는다.
 */
export async function disablePushOnDevice(api: ApiClient, deps: PushDeviceDeps): Promise<void> {
  const marker = readOwnerMarker(deps.storage);
  await settleWithin(
    Promise.allSettled([
      marker ? deletePushSubscriptionShared(api, marker.subscriptionId) : Promise.resolve(),
      unsubscribeDevice(deps),
    ]),
    PUSH_CLEANUP_TIMEOUT_MS,
  );
  if (marker) deleteOwnerMarkerIfMatches(deps.storage, marker.subscriptionId);
}

/**
 * 앱 로드 동기화 (pwa.md §5.5 표) — `(app)` 셸이 `me`·API-001 응답 뒤에, 같은 JS 수명에서는
 * 계정이 바뀔 때마다 1회 부른다. 표식 불일치면 서버를 부르지 않고 로컬 구독만 끊는다 (fail-closed).
 * `vapidPublicKey` 는 API-001 값이다 — null(미설정·조회 실패)이면 키 비교를 건너뛴다.
 */
export async function syncPushOnAppLoad(
  api: ApiClient,
  meId: string,
  vapidPublicKey: string | null,
  deps: PushDeviceDeps,
): Promise<void> {
  try {
    const marker = readOwnerMarker(deps.storage);
    const registration = await deps.getRegistration();

    if (!registration) {
      // 등록 없음 — kill-switch 등으로 등록만 사라진 경우의 서버 행 정리. 불일치·없음이면 네트워크 0.
      if (!marker) return;
      if (marker.userId === meId) {
        await deletePushSubscriptionShared(api, marker.subscriptionId);
      }
      deleteOwnerMarkerIfMatches(deps.storage, marker.subscriptionId);
      return;
    }

    const subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      if (marker) deleteOwnerMarkerIfMatches(deps.storage, marker.subscriptionId);
      return;
    }
    if (marker?.userId !== meId) {
      // 다른 계정이 켠 구독(또는 표식 없음) — 동의 없는 수신을 막는다. 서버 행은 다음 발송의 404/410 이 정리한다.
      await subscription.unsubscribe();
      return;
    }
    if (!matchesCurrentVapidKey(subscription, vapidPublicKey)) {
      // 운영 키 교체 — 옛 키 구독은 다시 보내도(API-002) 받을 수 없다. 서버 행·로컬 구독·표식을 지우고
      // 설정 화면이 '꺼짐'을 보이게 한다. 사용자가 다시 켜면 새 키로 구독한다 (enablePush).
      await Promise.allSettled([
        deletePushSubscriptionShared(api, marker.subscriptionId),
        subscription.unsubscribe(),
      ]);
      deleteOwnerMarkerIfMatches(deps.storage, marker.subscriptionId);
      return;
    }

    // 표식 일치 — 브라우저의 endpoint 교체·서버 행 유실을 API-002 재전송으로 복구한다.
    const body = toUpsertBody(subscription.toJSON());
    if (!body) return;
    const { id } = await upsertPushSubscription(api, body);
    if (id !== marker.subscriptionId && readOwnerMarker(deps.storage)?.subscriptionId === marker.subscriptionId) {
      // 서버 행이 새로 만들어졌다 — 로그아웃 ①이 옛 id 를 지우고 새 행을 남기지 않게 표식을 바꾼다.
      writeOwnerMarker(deps.storage, { userId: meId, subscriptionId: id });
    }
  } catch {
    // best-effort — 다음 앱 로드에서 다시 판정한다.
  }
}
