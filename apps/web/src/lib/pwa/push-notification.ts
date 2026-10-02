// SW 웹 푸시 순수 로직 (docs/requirements/pwa.md §5.4 · §5.5 "SW 추가 핸들러") — sw.ts 와 vitest 가 같이 쓴다.
//
// ★sw.ts 의 상대 import 그래프 안이다 — 패키지 import(zod 등)·Node 전역을 쓰지 않는다 (pwa.md C-28,
//   source-scan 테스트가 막는다). 그래서 페이로드 검증은 손으로 쓴 타입 가드다.
// ★알림 URL 은 SW 가 UUID 로 조립한다 — 서버가 보낸 문자열을 URL 로 쓰지 않는다. 클릭 때 한 번 더
//   정제한다 (open redirect 방지, defense in depth).
// ★표시 문구는 kind 로 SW 가 정한다. 서버는 사람이 읽는 문자열(회의 제목 등)을 보내지 않는다 (게이트 ④).

export const PUSH_PAYLOAD_VERSION = 1;
export const NOTIFICATION_ICON = "/icons/icon-192.png";
export const NOTIFICATION_LANG = "ko";
/** 페이로드를 못 믿을 때·정제에 실패했을 때의 이동 대상 */
export const FALLBACK_NOTIFICATION_TARGET = "/dashboard";

const UUID_PATTERN = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const UUID_RE = new RegExp(`^${UUID_PATTERN}$`, "i");
const MEETING_PATH_RE = new RegExp(`^/meetings/${UUID_PATTERN}$`, "i");
const WORKSPACE_QUERY_KEY = "workspace";

export type PushKind = "meeting.completed" | "meeting.failed";

interface NotificationCopy {
  readonly title: string;
  readonly body: string;
}

const NOTIFICATION_COPY: Record<PushKind, NotificationCopy> = {
  "meeting.completed": {
    title: "회의 처리 완료",
    body: "업로드한 회의의 요약·액션이 준비됐어요.",
  },
  "meeting.failed": {
    title: "회의 처리 실패",
    body: "업로드한 회의를 처리하지 못했어요. 눌러서 확인하세요.",
  },
};

const FALLBACK_COPY: NotificationCopy = { title: "Kairos", body: "새 알림이 있어요." };

export interface MeetingPushPayload {
  readonly kind: PushKind;
  readonly meetingId: string;
  /** UUID 가 아니거나 없으면 null — 그때는 쿼리 없는 상세 URL 로 간다 */
  readonly workspaceId: string | null;
}

export interface KairosNotificationOptions {
  readonly body: string;
  readonly icon: string;
  readonly lang: string;
  /** 같은 회의의 실패 → 재처리 완료 알림이 하나로 교체된다 */
  readonly tag?: string;
  readonly data: { readonly url: string };
}

export interface KairosNotification {
  readonly title: string;
  readonly options: KairosNotificationOptions;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isUuid(value: unknown): value is string {
  return typeof value === "string" && UUID_RE.test(value);
}

function isPushKind(value: unknown): value is PushKind {
  return value === "meeting.completed" || value === "meeting.failed";
}

/** `{v, kind, meetingId, workspaceId}` 검증 (pwa.md §5.4). 통과 못 하면 null. */
export function parsePushPayload(raw: unknown): MeetingPushPayload | null {
  if (!isRecord(raw)) return null;
  if (raw.v !== PUSH_PAYLOAD_VERSION) return null;
  if (!isPushKind(raw.kind)) return null;
  if (!isUuid(raw.meetingId)) return null;
  return {
    kind: raw.kind,
    meetingId: raw.meetingId,
    workspaceId: isUuid(raw.workspaceId) ? raw.workspaceId : null,
  };
}

export function buildPushNotification(raw: unknown): KairosNotification {
  const payload = parsePushPayload(raw);
  if (!payload) {
    return {
      title: FALLBACK_COPY.title,
      options: {
        body: FALLBACK_COPY.body,
        icon: NOTIFICATION_ICON,
        lang: NOTIFICATION_LANG,
        data: { url: FALLBACK_NOTIFICATION_TARGET },
      },
    };
  }
  const copy = NOTIFICATION_COPY[payload.kind];
  const query = payload.workspaceId ? `?${WORKSPACE_QUERY_KEY}=${payload.workspaceId}` : "";
  return {
    title: copy.title,
    options: {
      body: copy.body,
      icon: NOTIFICATION_ICON,
      lang: NOTIFICATION_LANG,
      tag: `meeting-${payload.meetingId}`,
      data: { url: `/meetings/${payload.meetingId}${query}` },
    },
  };
}

export interface PushMessageDataLike {
  json(): unknown;
}

/** `event.data?.json()` — 본문 없음·JSON 파싱 실패는 throw 대신 undefined (일반 알림으로 간다). */
export function readPushData(data: PushMessageDataLike | null | undefined): unknown {
  if (!data) return undefined;
  try {
    return data.json();
  } catch {
    return undefined;
  }
}

/**
 * `push` 처리 — 항상 `showNotification` 1회 (`userVisibleOnly` 구독이라 알림 없는 push 는 허용되지 않는다).
 * 페이로드가 이상해도 throw 하지 않고 일반 알림으로 바꾼다.
 */
export function handlePush(
  data: PushMessageDataLike | null | undefined,
  showNotification: (title: string, options: KairosNotificationOptions) => Promise<void>
): Promise<void> {
  const notification = buildPushNotification(readPushData(data));
  return showNotification(notification.title, notification.options);
}

/**
 * 알림 클릭 이동 대상 정제 — 같은 origin 의 `/meetings/<uuid>` 또는 `/dashboard` 만 통과.
 * 쿼리는 `/meetings/<uuid>` 의 `workspace=<uuid>` 1개만 남기고, 나머지 쿼리·hash 는 버린다.
 * 반환값은 경로(+쿼리)다.
 */
export function resolveNotificationTarget(rawUrl: unknown, origin: string): string {
  if (typeof rawUrl !== "string") return FALLBACK_NOTIFICATION_TARGET;
  let url: URL;
  try {
    url = new URL(rawUrl, origin);
  } catch {
    return FALLBACK_NOTIFICATION_TARGET;
  }
  if (url.origin !== origin) return FALLBACK_NOTIFICATION_TARGET;
  if (!MEETING_PATH_RE.test(url.pathname)) return FALLBACK_NOTIFICATION_TARGET;
  const workspaceId = url.searchParams.get(WORKSPACE_QUERY_KEY);
  return isUuid(workspaceId)
    ? `${url.pathname}?${WORKSPACE_QUERY_KEY}=${workspaceId}`
    : url.pathname;
}

export interface WindowClientLike {
  readonly url: string;
  focus(): Promise<unknown>;
  navigate(url: string): Promise<unknown>;
}

export interface ClientsLike {
  matchAll(options: {
    type: "window";
    includeUncontrolled: boolean;
  }): Promise<readonly WindowClientLike[]>;
  openWindow(url: string): Promise<unknown>;
}

function readNotificationUrl(notificationData: unknown): unknown {
  return isRecord(notificationData) ? notificationData.url : undefined;
}

function isSameOrigin(url: string, origin: string): boolean {
  try {
    return new URL(url).origin === origin;
  } catch {
    return false;
  }
}

/**
 * `notificationclick` 처리 — 같은 origin 창이 있으면 focus + navigate, 실패하면(제어되지 않는 창의
 * navigate 는 reject 한다) 새 창. 창이 없으면 새 창.
 */
export async function openNotificationTarget(
  notificationData: unknown,
  origin: string,
  clients: ClientsLike
): Promise<void> {
  const target = new URL(
    resolveNotificationTarget(readNotificationUrl(notificationData), origin),
    origin
  ).href;
  const windows = await clients.matchAll({ type: "window", includeUncontrolled: true });
  const existing = windows.find((client) => isSameOrigin(client.url, origin));
  if (existing) {
    try {
      await existing.focus();
      await existing.navigate(target);
      return;
    } catch {
      // 아래 openWindow 로 넘어간다
    }
  }
  await clients.openWindow(target);
}
