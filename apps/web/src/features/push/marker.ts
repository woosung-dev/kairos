// 푸시 소유자 표식 — `localStorage["kairos:push:v1"] = { userId, subscriptionId }` (docs/requirements/pwa.md §5.5)
//
// ★브라우저 알림 권한은 origin 단위라 사용자를 구분하지 못한다. 이 표식이 "이 기기의 구독을 누가
//   켰는가" 의 유일한 근거다. userId 는 `useMe()` 의 내부 users.id (auth_user.id 아님).
// ★파싱 실패 = 없음. 키에 버전(v1)을 박아 두어 모양이 바뀌면 새 키로 옮긴다 (vercel client-localstorage-schema).
// ★localStorage 는 사파리 비공개 모드 등에서 throw 할 수 있다 → 모든 접근을 감싼다.
// ★검증은 손으로 쓴 타입 가드다 (zod 아님) — 이 모듈은 `(app)` 셸(PushSync·로그아웃 정리)이 import 해서
//   zod 를 쓰면 모든 인증 라우트의 공용 청크에 zod 전체가 실린다 (GATE-PR2 bundle-conditional).
//   `lib/pwa/push-notification.ts` 의 페이로드 가드와 같은 방식.

export const PUSH_OWNER_MARKER_KEY = "kairos:push:v1";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface PushOwnerMarker {
  /** 내부 users.id */
  readonly userId: string;
  /** API-002 가 돌려준 push_subscriptions.id */
  readonly subscriptionId: string;
}

function isUuid(value: unknown): value is string {
  return typeof value === "string" && UUID_RE.test(value);
}

/** JSON.parse 결과 → 표식. 모양이 다르면 null (추가 필드는 버리고 두 필드만 돌려준다). */
function parseOwnerMarker(value: unknown): PushOwnerMarker | null {
  if (typeof value !== "object" || value === null) return null;
  const { userId, subscriptionId } = value as Record<string, unknown>;
  if (!isUuid(userId) || !isUuid(subscriptionId)) return null;
  return { userId, subscriptionId };
}

export type MarkerStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export function getBrowserMarkerStorage(): MarkerStorage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readOwnerMarker(storage: MarkerStorage | null): PushOwnerMarker | null {
  if (!storage) return null;
  try {
    const raw = storage.getItem(PUSH_OWNER_MARKER_KEY);
    if (raw === null) return null;
    return parseOwnerMarker(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function writeOwnerMarker(storage: MarkerStorage | null, marker: PushOwnerMarker): void {
  if (!storage) return;
  try {
    storage.setItem(PUSH_OWNER_MARKER_KEY, JSON.stringify(marker));
  } catch {
    // 저장 실패 = 표식 없음. 다음 앱 로드 동기화가 이 기기 구독을 끊는다 (fail-closed).
  }
}

/**
 * compare-and-delete — 흐름 시작 때 읽은 subscriptionId 와 지금 값이 같을 때만 지운다.
 * 그 사이 다른 탭·켜기 흐름이 새 표식을 썼으면 남긴다.
 */
export function deleteOwnerMarkerIfMatches(
  storage: MarkerStorage | null,
  subscriptionId: string,
): void {
  if (!storage) return;
  if (readOwnerMarker(storage)?.subscriptionId !== subscriptionId) return;
  try {
    storage.removeItem(PUSH_OWNER_MARKER_KEY);
  } catch {
    // 지우지 못하면 다음 앱 로드 동기화가 다시 판정한다.
  }
}
